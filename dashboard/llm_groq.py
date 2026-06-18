"""
Cliente Groq (API compatible OpenAI) para visión y texto.
Configuración vía variables de entorno o st.secrets.

Variables de entorno:
  GROQ_API_KEY
  GROQ_BASE_URL       (default: https://api.groq.com/openai/v1)
  GROQ_VISION_MODEL   (default: meta-llama/llama-4-scout-17b-16e-instruct)
  GROQ_TEXT_MODEL     (default: llama-3.3-70b-versatile)
  GROQ_VENTANA_PAGINAS (default: 4)
  GROQ_SOLAPE_PAGINAS  (default: 1)
"""

import base64
import os
import time
from openai import OpenAI


# ── Configuración desde entorno ──

VISION_MODEL = os.environ.get(
    "GROQ_VISION_MODEL",
    "meta-llama/llama-4-scout-17b-16e-instruct",
)
TEXT_MODEL = os.environ.get(
    "GROQ_TEXT_MODEL",
    "llama-3.3-70b-versatile",
)
VENTANA = int(os.environ.get("GROQ_VENTANA_PAGINAS", "4"))
SOLAPE = int(os.environ.get("GROQ_SOLAPE_PAGINAS", "1"))


# ── Cliente lazy ──

_cliente: OpenAI | None = None


def _get_groq_client() -> OpenAI | None:
    global _cliente
    if _cliente is not None:
        return _cliente

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st

            api_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            api_key = None

    if not api_key:
        return None

    base_url = os.environ.get(
        "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
    )
    _cliente = OpenAI(
        api_key=api_key, base_url=base_url, timeout=90.0, max_retries=0
    )
    return _cliente


def groq_disponible() -> bool:
    return _get_groq_client() is not None


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
            if max_side > 1600:
                ratio = 1600 / max_side
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                img = img.resize((new_w, new_h), PILImage.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
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
    prompt: str, paginas: list, max_tokens: int = 8192
) -> str:
    """Envía prompt + páginas (como imágenes) al modelo de visión Groq.

    paginas: list[{"mime_type": str, "data": bytes}]
    Devuelve el texto de la respuesta.
    Lanza ValueError si no hay API key configurada.
    """
    client = _get_groq_client()
    if not client:
        raise ValueError(
            "GROQ_API_KEY no configurada en variable de entorno ni st.secrets"
        )

    contenido = _paginas_a_contenido(prompt, paginas)
    messages = [{"role": "user", "content": contenido}]

    def _call():
        resp = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

    return _retry_with_backoff(_call)


# ── chat_texto: prompt textual → texto ──

def chat_texto(
    prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    json: bool = False,
) -> str:
    """Envía un prompt de texto al modelo de texto Groq.

    Si json=True, pide response_format json_object.
    Devuelve el texto de la respuesta.
    Lanza ValueError si no hay API key configurada.
    """
    client = _get_groq_client()
    if not client:
        raise ValueError(
            "GROQ_API_KEY no configurada en variable de entorno ni st.secrets"
        )

    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": TEXT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json:
        kwargs["response_format"] = {"type": "json_object"}

    def _call():
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content

    return _retry_with_backoff(_call)
