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
  Texto:      LLM_TEXT_MODEL     -> GROQ_TEXT_MODEL   -> deepseek-ai/deepseek-v3.2
  Verificador (cascada): LLM_VERIFIER_MODEL          -> zai-org/glm-4.6
  Visión:     LLM_VISION_MODEL   -> GROQ_VISION_MODEL -> nvidia/llama-3.1-nemotron-nano-vl-8b-v1

IMPORTANTE: los slugs exactos de los modelos pueden variar en build.nvidia.com.
Verifícalos en https://build.nvidia.com/models y ajústalos por entorno si hace
falta. Si algún modelo rechaza response_format=json_object, desactiva el modo
JSON con LLM_JSON_MODE=0 (el prompt ya pide JSON explícitamente).
"""

import base64
import os
import time
from openai import OpenAI


def _primer_env(*nombres, default=None):
    """Devuelve el primer valor de entorno no vacío entre `nombres`."""
    for n in nombres:
        v = os.environ.get(n)
        if v:
            return v
    return default


# ── Configuración desde entorno ──

TEXT_MODEL = _primer_env(
    "LLM_TEXT_MODEL", "GROQ_TEXT_MODEL",
    default="deepseek-ai/deepseek-v3.2",
)
VERIFIER_MODEL = _primer_env(
    "LLM_VERIFIER_MODEL",
    default="zai-org/glm-4.6",
)
VISION_MODEL = _primer_env(
    "LLM_VISION_MODEL", "GROQ_VISION_MODEL",
    default="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
)
VENTANA = int(os.environ.get("GROQ_VENTANA_PAGINAS", "4"))
SOLAPE = int(os.environ.get("GROQ_SOLAPE_PAGINAS", "1"))
GROQ_MAX_LADO = int(os.environ.get("GROQ_MAX_LADO", "1280"))
GROQ_JPEG_QUALITY = int(os.environ.get("GROQ_JPEG_QUALITY", "82"))

# Algunos modelos de NIM no aceptan response_format=json_object. Si es el caso,
# pon LLM_JSON_MODE=0: se omite el response_format pero el prompt sigue pidiendo
# JSON, y el parseo (json.loads) sigue funcionando.
JSON_MODE = os.environ.get("LLM_JSON_MODE", "1") not in ("0", "false", "False", "")


# ── Cliente lazy ──

_cliente: OpenAI | None = None


def _get_groq_client() -> OpenAI | None:
    global _cliente
    if _cliente is not None:
        return _cliente

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
    _cliente = OpenAI(
        api_key=api_key, base_url=base_url, timeout=90.0, max_retries=0
    )
    return _cliente


def groq_disponible() -> bool:
    return _get_groq_client() is not None


# Alias con nombre neutral de proveedor (el backend ya no es necesariamente Groq).
llm_disponible = groq_disponible


# ── Reintento con backoff ──

def _retry_with_backoff(func, *args, max_retries=3, **kwargs):
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            err_str = str(e).lower()
            if "429" in err_str or "rate" in err_str or "quota" in err_str:
                if attempt < max_retries - 1:
                    time.sleep(2 ** (attempt + 1))
                continue
            raise
    raise last_exc


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
    Lanza ValueError si no hay API key configurada.
    """
    client = _get_groq_client()
    if not client:
        raise ValueError(
            "LLM API key no configurada (LLM_API_KEY / NVIDIA_API_KEY / GROQ_API_KEY)"
        )

    contenido = _paginas_a_contenido(prompt, paginas)
    messages = [{"role": "user", "content": contenido}]

    kwargs = {
        "model": model or VISION_MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if JSON_MODE:
        kwargs["response_format"] = {"type": "json_object"}

    def _call():
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content

    return _retry_with_backoff(_call)


# ── chat_texto: prompt textual → texto ──

def chat_texto(
    prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    json: bool = False,
    model: str | None = None,
) -> str:
    """Envía un prompt de texto al modelo de texto.

    `model` permite forzar un modelo distinto al TEXT_MODEL por defecto (lo usa
    la cascada para invocar al verificador). Si json=True y el modo JSON está
    activo, pide response_format json_object.
    Lanza ValueError si no hay API key configurada.
    """
    client = _get_groq_client()
    if not client:
        raise ValueError(
            "LLM API key no configurada (LLM_API_KEY / NVIDIA_API_KEY / GROQ_API_KEY)"
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

    def _call():
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content

    return _retry_with_backoff(_call)
