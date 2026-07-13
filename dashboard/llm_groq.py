"""
Cliente LLM (API compatible con OpenAI) para visión y texto.

Migrado a NVIDIA NIM (build.nvidia.com) para usar modelos de razonamiento
potentes con presupuesto 0 (tier gratis ~40 req/min). Sigue siendo compatible
con OpenAI, así que cambiar de proveedor/modelo solo requiere variables de
entorno; NO hace falta tocar el código.

Resolución de configuración (de mayor a menor prioridad). Se conservan los
nombres antiguos GROQ_* como respaldo para no romper despliegues en transición:

  API key:    LLM_API_KEY   -> NVIDIA_API_KEY -> GROQ_API_KEY
  Base URL:   LLM_BASE_URL  -> GROQ_BASE_URL  -> https://integrate.api.nvidia.com/v1
  Texto:      LLM_TEXT_MODEL     -> GROQ_TEXT_MODEL   -> deepseek-ai/deepseek-v4-flash
  Verificador (cascada): LLM_VERIFIER_MODEL          -> z-ai/glm-5.1
  Visión:     LLM_VISION_MODEL   -> GROQ_VISION_MODEL -> qwen/qwen3.5-397b-a17b
  Visión (respaldo): LLM_VISION_FALLBACK            -> (sin respaldo por defecto; solo modelos multi-imagen)

  Proveedor de TEXTO separado (opcional). Permite enviar el TEXTO a otro
  proveedor (p. ej. OpenCode Zen) y mantener la VISIÓN (Phi) en NVIDIA:
    Texto API key:  LLM_TEXT_API_KEY -> OPENCODE_API_KEY  (si faltan, usa la key principal)
    Texto Base URL: LLM_TEXT_BASE_URL (si hay OPENCODE_API_KEY y no se define,
                    usa https://opencode.ai/zen/v1)
  Si no defines nada de lo anterior, texto y visión comparten el mismo cliente
  que antes (sin cambios de comportamiento).

Cascada de visión: si el modelo primario de visión falla con un error de
servidor/modelo (5xx, 404, función DEGRADED "cannot be invoked", "modelo no
disponible") o porque el modelo solo admite UNA imagen ("at most 1 image"), se
cae automáticamente al siguiente modelo de LLM_VISION_FALLBACK en orden. Esto
evita que un modelo roto server-side (como el viejo nemotron-nano-vl-8b) o una
función degradada tumbe la ingesta por PDF. Reintentar el mismo modelo roto no
sirve, así que esos errores NO se reintentan in situ: disparan la cascada. Solo
los errores transitorios de rate-limit y timeouts se reintentan con backoff
(LLM_MAX_REINTENTOS, por defecto 3) antes de propagarse. Los errores de
autenticación y los 400 de petición (salvo el de multi-imagen) se propagan sin
probar respaldos. LLM_VISION_FALLBACK admite una lista separada por comas.

IMPORTANTE (multi-imagen): la ingesta envía VARIAS imágenes por llamada
(ventanas de páginas/posts). El modelo de visión y cualquier respaldo DEBEN
admitir múltiples imágenes por prompt. Si configuras un modelo de una sola
imagen como meta/llama-3.2-11b-vision-instruct, NIM lo rechaza con 400 ("At most
1 image(s) may be provided in one prompt"); ese error ahora también dispara la
cascada hacia el siguiente respaldo, pero si TODOS los modelos configurados son
de una sola imagen la ingesta fallará. Configura siempre modelos multi-imagen.

En local, las variables se leen de un archivo .env (cargado con load_dotenv).
En HF Spaces / Railway vienen del entorno del contenedor. Si el primario
(DeepSeek V4 Flash) sigue clasificando mal casos claros, basta con poner
LLM_TEXT_MODEL=deepseek-ai/deepseek-v4-pro (sin tocar codigo).

IMPORTANTE: los slugs exactos de los modelos pueden variar en build.nvidia.com.
Verifícalos en https://build.nvidia.com/models y ajústalos por entorno si hace
falta. Si algún modelo rechaza response_format=json_object, desactiva el modo
JSON con LLM_JSON_MODE=0 (el prompt ya pide JSON explícitamente).
"""

import base64
import logging
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

# Carga .env en local para que los slugs de modelos y la API key esten
# disponibles aunque este modulo se use fuera del dashboard (p. ej. el pipeline
# de clasificacion). Es idempotente y no sobreescribe variables ya definidas en
# el entorno (HF / Railway), asi que es seguro llamarlo aqui.
load_dotenv()


def _primer_env(*nombres, default=None):
    """Devuelve el primer valor de entorno no vacío entre `nombres`."""
    for n in nombres:
        v = os.environ.get(n)
        if v:
            return v
    return default


def _lista_env(nombre, default):
    """Lista separada por comas desde el entorno; `default` (lista) si no está."""
    raw = os.environ.get(nombre)
    if not raw:
        return list(default)
    return [x.strip() for x in raw.split(",") if x.strip()]


# ── Configuración desde entorno ──

TEXT_MODEL = _primer_env(
    "LLM_TEXT_MODEL", "GROQ_TEXT_MODEL",
    default="deepseek-ai/deepseek-v4-flash",
)
VERIFIER_MODEL = _primer_env(
    "LLM_VERIFIER_MODEL",
    default="z-ai/glm-5.1",
)
VISION_MODEL = _primer_env(
    "LLM_VISION_MODEL", "GROQ_VISION_MODEL",
    default="qwen/qwen3.5-397b-a17b",
)
# Modelos de respaldo de visión: se prueban en orden si el primario falla con
# un error de servidor/modelo (5xx/404/DEGRADED) o si solo admite una imagen.
# IMPORTANTE: la ingesta envía VARIAS imágenes por llamada (ventanas de
# páginas/posts), así que el respaldo debe ser un modelo MULTI-IMAGEN. NO uses
# modelos de una sola imagen como meta/llama-3.2-11b-vision-instruct: NIM los
# rechaza con 400 ("At most 1 image(s) may be provided in one prompt"); ese
# error ahora dispara la cascada, pero si todos los modelos son de una imagen la
# ingesta fallará. Por defecto no hay respaldo; configúralo con
# LLM_VISION_FALLBACK solo con otro modelo multi-imagen.
VISION_FALLBACKS = _lista_env(
    "LLM_VISION_FALLBACK",
    [],
)
VENTANA = int(os.environ.get("GROQ_VENTANA_PAGINAS", "4"))
SOLAPE = int(os.environ.get("GROQ_SOLAPE_PAGINAS", "1"))
GROQ_MAX_LADO = int(os.environ.get("GROQ_MAX_LADO", "1280"))
GROQ_JPEG_QUALITY = int(os.environ.get("GROQ_JPEG_QUALITY", "82"))

# Algunos modelos de NIM no aceptan response_format=json_object. Si es el caso,
# pon LLM_JSON_MODE=0: se omite el response_format pero el prompt sigue pidiendo
# JSON, y el parseo (json.loads) sigue funcionando.
JSON_MODE = os.environ.get("LLM_JSON_MODE", "1") not in ("0", "false", "False", "")

# Reintentos con backoff ante errores transitorios (rate limit y timeouts) antes
# de propagar el error. Los 5xx y las funciones DEGRADED NO se reintentan in
# situ: los maneja la cascada de visión cayendo a otro modelo (_es_error_modelo).
_MAX_REINTENTOS = int(os.environ.get("LLM_MAX_REINTENTOS", "3"))


def _es_modelo_deepseek(model: str) -> bool:
    """True si el modelo es de la familia DeepSeek (necesita apagar el modo de razonamiento explícitamente en NIM para no agotar max_tokens pensando)."""
    return "deepseek" in (model or "").lower()


# ── Cliente lazy ──

# Clientes lazy: se inicializan en primera llamada y se reciclan si la key/url
# no cambia. Asignación atómica en CPython (GIL) hace esto seguro para el
# caso de uso actual (Streamlit mono-proceso o multi-thread con GIL activo).
# Si se migra a Gunicorn multi-process o a async (asyncio), reemplazar con
# contextvariables o un pool de clientes por proceso.
_cliente: OpenAI | None = None
_cliente_api_key: str | None = None
_cliente_base_url: str | None = None
_cliente_texto: OpenAI | None = None
_cliente_texto_api_key: str | None = None
_cliente_texto_base_url: str | None = None


def _get_groq_client() -> OpenAI | None:
    """Cliente principal (visión y, por defecto, texto). Usa el endpoint NVIDIA."""
    global _cliente, _cliente_api_key, _cliente_base_url

    api_key = _primer_env("LLM_API_KEY", "NVIDIA_API_KEY", "GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st

            api_key = (
                st.secrets.get("LLM_API_KEY")
                or st.secrets.get("NVIDIA_API_KEY")
                or st.secrets.get("GROQ_API_KEY")
            )
        except Exception:
            api_key = None

    if not api_key:
        return None

    base_url = _primer_env(
        "LLM_BASE_URL", "GROQ_BASE_URL",
        default="https://integrate.api.nvidia.com/v1",
    )

    if (
        _cliente is not None
        and _cliente_api_key == api_key
        and _cliente_base_url == base_url
    ):
        return _cliente

    _cliente = OpenAI(
        api_key=api_key, base_url=base_url, timeout=90.0, max_retries=0
    )
    _cliente_api_key = api_key
    _cliente_base_url = base_url
    return _cliente


def _get_text_client() -> OpenAI | None:
    """Cliente para el modelo de TEXTO.

    Permite un proveedor distinto al de visión (p. ej. OpenCode Zen para el
    análisis de texto y NVIDIA/Phi para las imágenes). Si no hay configuración
    específica de texto (LLM_TEXT_API_KEY / OPENCODE_API_KEY / LLM_TEXT_BASE_URL),
    reutiliza el cliente principal y conserva el comportamiento anterior.
    """
    global _cliente_texto, _cliente_texto_api_key, _cliente_texto_base_url

    text_key = _primer_env("LLM_TEXT_API_KEY", "OPENCODE_API_KEY")
    text_base = _primer_env("LLM_TEXT_BASE_URL")

    # Sin configuración específica de texto: comparte el cliente principal.
    if not text_key and not text_base:
        return _get_groq_client()

    api_key = text_key or _primer_env("LLM_API_KEY", "NVIDIA_API_KEY", "GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st

            api_key = (
                st.secrets.get("LLM_TEXT_API_KEY")
                or st.secrets.get("OPENCODE_API_KEY")
                or st.secrets.get("LLM_API_KEY")
            )
        except Exception:
            api_key = None
    if not api_key:
        return _get_groq_client()

    base_url = text_base or "https://opencode.ai/zen/v1"

    if (
        _cliente_texto is not None
        and _cliente_texto_api_key == api_key
        and _cliente_texto_base_url == base_url
    ):
        return _cliente_texto

    _cliente_texto = OpenAI(
        api_key=api_key, base_url=base_url, timeout=90.0, max_retries=0
    )
    _cliente_texto_api_key = api_key
    _cliente_texto_base_url = base_url
    return _cliente_texto


def groq_disponible() -> bool:
    return _get_text_client() is not None or _get_groq_client() is not None


# Alias con nombre neutral de proveedor (el backend ya no es necesariamente Groq).
llm_disponible = groq_disponible


# ── Reintento con backoff ──

def _retry_with_backoff(func, *args, max_retries=None, **kwargs):
    if max_retries is None:
        max_retries = _MAX_REINTENTOS
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            err_str = str(e).lower()
            es_rate = "429" in err_str or "rate" in err_str or "quota" in err_str
            es_timeout = (
                "timed out" in err_str
                or "timeout" in err_str
                or "connection" in err_str
                or e.__class__.__name__ in ("APITimeoutError", "APIConnectionError")
            )
            if (es_rate or es_timeout) and attempt < max_retries - 1:
                dormir = 2 ** (attempt + 1) if es_rate else (attempt + 1) * 2
                logger.info(
                    "Backoff en intento %d/%d: durmiendo %.1fs (%s)",
                    attempt + 1, max_retries, dormir,
                    "rate limit" if es_rate else "timeout/connection",
                )
                time.sleep(dormir)
                continue
            raise
    raise last_exc


# ── Cascada de visión: selección de modelos y clasificación de errores ──

def _es_error_modelo(exc) -> bool:
    """True si el error sugiere que conviene caer al siguiente modelo de visión.

    Cubre modelos no disponibles (5xx/404/desconocido), funciones DEGRADED de
    NIM (400 "DEGRADED function cannot be invoked") y modelos que solo admiten
    una imagen (la ingesta envía varias). Los demás errores (auth, 400 de
    petición) se propagan sin probar respaldos.
    """
    s = str(exc).lower()
    señales = (
        "500", "502", "503", "504", "404",
        "internal server error", "bad gateway", "service unavailable",
        "gateway timeout", "not found", "does not exist", "unknown model",
        "model_not_found", "no longer supported", "decommission",
        # Función temporalmente degradada en NIM: el modelo no está operativo.
        "degraded", "cannot be invoked",
        # Modelo de una sola imagen: cae al siguiente (que debe ser multi-imagen).
        "at most 1 image", "at most one image", "only one image",
    )
    return any(x in s for x in señales)


def _modelos_vision(model: str | None = None) -> list:
    """Orden de modelos a intentar para visión.

    Si `model` es explícito, se respeta sin cascada. Si no, se usa el primario
    (VISION_MODEL) seguido de los respaldos (VISION_FALLBACKS), sin duplicados.
    """
    if model:
        return [model]
    modelos = [VISION_MODEL]
    for m in VISION_FALLBACKS:
        if m and m not in modelos:
            modelos.append(m)
    return modelos


# ── chat_vision: prompt + imágenes → JSON ──

def _paginas_a_contenido(prompt: str, paginas: list) -> list:
    contenido: list = [{"type": "text", "text": prompt}]
    for pagina in paginas:
        mime = pagina.get("mime_type", "image/png")
        raw = pagina.get("data", b"")
        try:
            from PIL import Image as PILImage

            import io

            img = PILImage.open(io.BytesIO(raw))
            w, h = img.size
            max_side = max(w, h)
            if max_side > GROQ_MAX_LADO:
                ratio = GROQ_MAX_LADO / max_side
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                img = img.resize((new_w, new_h), PILImage.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=GROQ_JPEG_QUALITY)
                raw = buf.getvalue()
                mime = "image/jpeg"
        except Exception:
            pass
        b64 = base64.b64encode(raw).decode("utf-8")
        contenido.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })
    return contenido


def chat_vision(
    prompt: str, paginas: list, max_tokens: int = 8192, model: str | None = None
) -> str:
    """Envía prompt + páginas (como imágenes) al modelo de visión.

    paginas: list[{"mime_type": str, "data": bytes}]
    Devuelve el texto de la respuesta.

    Si `model` no se especifica, usa el primario (VISION_MODEL) y, ante un error
    de servidor/modelo (5xx/404/DEGRADED) o de modelo de una sola imagen, cae
    automáticamente a los modelos de VISION_FALLBACKS en orden. Con `model`
    explícito no hay cascada. Lanza ValueError si no hay API key configurada.
    """
    client = _get_groq_client()
    if not client:
        raise ValueError(
            "LLM API key no configurada (LLM_API_KEY / NVIDIA_API_KEY / GROQ_API_KEY)"
        )

    contenido = _paginas_a_contenido(prompt, paginas)
    messages = [{"role": "user", "content": contenido}]

    modelos = _modelos_vision(model)
    ultimo_exc = None
    for idx, m in enumerate(modelos):
        kwargs = {
            "model": m,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        if JSON_MODE:
            kwargs["response_format"] = {"type": "json_object"}

        def _call():
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content

        try:
            respuesta = _retry_with_backoff(_call)
            if idx > 0:
                print(
                    f"[llm_groq] visión: usando modelo de respaldo '{m}' "
                    f"(el primario falló)."
                )
            return respuesta
        except Exception as e:
            ultimo_exc = e
            es_ultimo = idx == len(modelos) - 1
            if _es_error_modelo(e) and not es_ultimo:
                print(
                    f"[llm_groq] visión: modelo '{m}' no disponible ({e}); "
                    f"probando respaldo…"
                )
                continue
            raise
    if ultimo_exc:
        raise ultimo_exc


# ── chat_texto: prompt textual → texto ──

def chat_texto(
    prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    json: bool = False,
    model: str | None = None,
) -> tuple[str, str, str | None]:
    """Envía un prompt de texto al modelo de texto.

    `model` permite forzar un modelo distinto al TEXT_MODEL por defecto (lo usa
    la cascada para invocar al verificador). Si json=True y el modo JSON está
    activo, pide response_format json_object.
    Usa el cliente de texto (`_get_text_client`), que puede apuntar a un
    proveedor distinto del de visión.
    Lanza ValueError si no hay API key configurada.

    Devuelve una tupla: (content, finish_reason, reasoning_content).
    reasoning_content puede ser None si el proveedor no lo expone.
    """
    client = _get_text_client()
    if not client:
        raise ValueError(
            "LLM API key no configurada (LLM_TEXT_API_KEY / OPENCODE_API_KEY / LLM_API_KEY)"
        )

    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": model or TEXT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json and JSON_MODE:
        kwargs["response_format"] = {"type": "json_object"}

    # DeepSeek en NIM: apagar razonamiento explícitamente para no agotar max_tokens
    if _es_modelo_deepseek(kwargs["model"]):
        kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": False}}

    def _call():
        resp = client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        content = choice.message.content
        finish_reason = choice.finish_reason
        # Some providers (e.g., DeepSeek on NIM) expose reasoning_content on the message
        reasoning_content = getattr(choice.message, "reasoning_content", None)
        return content, finish_reason, reasoning_content

    return _retry_with_backoff(_call)
