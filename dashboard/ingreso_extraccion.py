"""
Módulo de extracción desde capturas con Gemini Vision.

Fase 2 — no toca UI ni DB.
Funciones:
  - extraer_post_desde_capturas(imagenes, plataforma) -> dict
  - normalizar_numero(texto) -> int | None
"""

import json
import re
from typing import Any

GEMINI_MODEL = "gemini-2.0-flash"


# ═══════════════════════════════════════════════
# Normalizador determinista de números
# ═══════════════════════════════════════════════

_SUFIJOS = [
    ("millones", 1_000_000),
    ("millon", 1_000_000),
    ("mil", 1_000),
    ("m", 1_000_000),
    ("k", 1_000),
]


def normalizar_numero(texto: str | None) -> int | None:
    """Normaliza un string numérico a entero.

    "1.234" / "1,234" → 1234
    "1.2 K" / "1.2k" → 1200
    "34 mil"           → 34000
    "2 millones" / "2 M" → 2_000_000
    "1,2 mil"          → 1200
    "" / "—" / None    → None
    """
    if not texto or not isinstance(texto, str):
        return None
    texto = texto.strip()
    if not texto or texto in ("—", "-", "N/A", "n/a"):
        return None

    # --- extraer sufijo multiplicador ---
    texto_plano = texto.lower().replace(" ", "")
    factor = 1
    for sufijo, mult in _SUFIJOS:
        if texto_plano.endswith(sufijo):
            resto = texto_plano[: -len(sufijo)]
            if resto and (resto[-1].isdigit() or resto[-1] in ".,"):
                factor = mult
                texto = resto
                break

    if not texto or texto in ("—", "-"):
        return None

    # --- determinar separador decimal vs. de miles ---
    partes = re.split(r"[,.]", texto)

    if len(partes) == 1:
        try:
            v = int(partes[0])
            return max(v, 0) * factor if v >= 0 else None
        except ValueError:
            return None

    if len(partes) >= 3:
        seps = re.findall(r"[,.]", texto)
        if len(set(seps)) == 1:
            limpio = "".join(partes)
        else:
            limpio = "".join(partes[:-1]) + "." + partes[-1]
    else:
        izq, der = partes
        if len(der) == 3 and len(izq) <= 3:
            limpio = izq + der  # separador de miles
        elif der == "":
            try:
                v = int(izq)
                return max(v, 0) * factor if v >= 0 else None
            except ValueError:
                return None
        else:
            limpio = izq + "." + der  # separador decimal

    try:
        v = float(limpio)
        v_total = int(v * factor)
        return max(v_total, 0) if v_total >= 0 else None
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════
# Detección de MIME type real para imágenes
# ═══════════════════════════════════════════════

def _detectar_mime(data: bytes, declarado: str | None = None) -> str:
    """Detecta el mime real de la imagen. Respeta el declarado si es image/*."""
    if declarado and declarado.startswith("image/"):
        return declarado
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


# ═══════════════════════════════════════════════
# Configuración de Gemini (diferida)
# ═══════════════════════════════════════════════

def _configurar_gemini() -> bool:
    """Lee la clave de st.secrets o variable de entorno y configura la API.

    Retorna True si ok, False si no hay clave disponible.
    """
    import os
    import streamlit as st
    import google.generativeai as genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            api_key = None
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False


# ═══════════════════════════════════════════════
# Prompts por plataforma
# ═══════════════════════════════════════════════

_PROMPT_FACEBOOK = """
Eres un extractor de datos. Analiza las imágenes de esta captura de pantalla de Facebook.

DEVUELVE SOLO JSON, SIN texto adicional, con esta estructura exacta:

{
  "texto_post": "string (texto del post, vacío si no se ve)",
  "fecha": {"valor": "YYYY-MM-DD o null", "confianza": "seguro|dudoso"},
  "autor_pagina": "nombre de la página o null",
  "reacciones": {
    "likes": {"valor": 0, "confianza": "seguro|dudoso"},
    "loves": {"valor": null, "confianza": "seguro|dudoso"},
    "hahas": {"valor": null, "confianza": "seguro|dudoso"},
    "sads": {"valor": null, "confianza": "seguro|dudoso"},
    "wows": {"valor": null, "confianza": "seguro|dudoso"},
    "angrys": {"valor": null, "confianza": "seguro|dudoso"},
    "total": {"valor": null, "confianza": "seguro|dudoso"}
  },
  "comentarios_count": {"valor": null, "confianza": "seguro|dudoso"},
  "comentarios": [
    {"texto": "texto literal", "autor": "nombre o null"}
  ]
}

REGLAS:
- "Me gusta"=likes, "Me encanta"=loves, "Me divierte"=hahas,
  "Me entristece"=sads, "Me asombra"=wows, "Me enoja"=angrys
- NO extraer "compartidos" ni reproducciones/vistas
- Por cada número y la fecha, devuelve {"valor": ..., "confianza": "..."}.
- confianza="seguro" si el dato se lee con total claridad.
- confianza="dudoso" si se ve pero está borroso, ambiguo o cortado.
- Si el dato NO se ve → valor=null (la confianza se ignora en ese caso).
- Transcribe comentarios TEXTUALMENTE, sin resumir ni corregir
- NO inventes datos
- Analiza TODAS las imágenes; los comentarios pueden estar en varias
- Extrae TODOS los comentarios visibles (sin límite)
"""

_PROMPT_TIKTOK = """
Eres un extractor de datos. Analiza las imágenes de esta captura de pantalla de TikTok.

DEVUELVE SOLO JSON, SIN texto adicional, con esta estructura exacta:

{
  "texto_post": "string (descripción, vacío si no se ve)",
  "fecha": {"valor": "YYYY-MM-DD o null", "confianza": "seguro|dudoso"},
  "autor_cuenta": "nombre de la cuenta o null",
  "metricas": {
    "likes": {"valor": null, "confianza": "seguro|dudoso"},
    "favoritos": {"valor": null, "confianza": "seguro|dudoso"},
    "comentarios_count": {"valor": null, "confianza": "seguro|dudoso"}
  },
  "comentarios": [
    {"texto": "texto literal", "autor": "nombre o null"}
  ]
}

REGLAS:
- corazón=likes, marcador/guardar=favoritos, bocadillo=comentarios_count
- NO extraer "compartidos" ni "vistas" (se teclean a mano)
- Por cada número y la fecha, devuelve {"valor": ..., "confianza": "..."}.
- confianza="seguro" si el dato se lee con total claridad.
- confianza="dudoso" si se ve pero está borroso, ambiguo o cortado.
- Si el dato NO se ve → valor=null (la confianza se ignora en ese caso).
- Transcribe comentarios TEXTUALMENTE, sin resumir ni corregir
- NO inventes datos
- Analiza TODAS las imágenes; los comentarios pueden estar en varias
- Extrae TODOS los comentarios visibles (sin límite)
"""


def _construir_prompt(plataforma: str) -> str:
    if plataforma == "facebook":
        return _PROMPT_FACEBOOK
    elif plataforma == "tiktok":
        return _PROMPT_TIKTOK
    raise ValueError(f"Plataforma no soportada: {plataforma}")


# ═══════════════════════════════════════════════
# Aplicación del contrato JSON de salida
# ═══════════════════════════════════════════════

def _norm(v: Any) -> int | None:
    """Normaliza un valor numérico crudo de Gemini via normalizar_numero.

    None → None; int → int; str como '1.2K' → 1200; ilegible → None.
    """
    if v is None:
        return None
    return normalizar_numero(str(v))


def _num_confianza(raw: Any, predeterminado: str = "no_detectado") -> dict:
    """Procesa un campo numérico que Gemini devuelve como {valor, confianza}
    o como número suelto (compat). Normaliza el valor con _norm."""
    if isinstance(raw, dict):
        valor = _norm(raw.get("valor"))
        conf = raw.get("confianza")
    else:
        valor = _norm(raw)
        conf = None
    if valor is None:
        return {"valor": None, "confianza": predeterminado}
    if conf not in ("seguro", "dudoso"):
        conf = "seguro"
    return {"valor": valor, "confianza": conf}


def _fecha_confianza(raw: Any) -> dict:
    """Igual que _num_confianza pero sin normalizar (la fecha es string ISO)."""
    if isinstance(raw, dict):
        valor = raw.get("valor") or None
        conf = raw.get("confianza")
    else:
        valor = raw or None
        conf = None
    if valor is None:
        return {"valor": None, "confianza": "no_detectado"}
    if conf not in ("seguro", "dudoso"):
        conf = "seguro"
    return {"valor": valor, "confianza": conf}


def _aplicar_contrato(respuesta: dict, plataforma: str) -> dict:
    """Rellena la plantilla del contrato con lo que devolvió Gemini.

    compartidos/vistas siempre null + "manual".
    """
    if plataforma == "facebook":
        reacs = respuesta.get("reacciones", {})
        return {
            "plataforma": "facebook",
            "texto_post": respuesta.get("texto_post") or "",
            "fecha": _fecha_confianza(respuesta.get("fecha")),
            "autor_pagina": respuesta.get("autor_pagina") or None,
            "reacciones": {
                "likes": _num_confianza(reacs.get("likes")),
                "loves": _num_confianza(reacs.get("loves")),
                "hahas": _num_confianza(reacs.get("hahas")),
                "sads": _num_confianza(reacs.get("sads")),
                "wows": _num_confianza(reacs.get("wows")),
                "angrys": _num_confianza(reacs.get("angrys")),
                "total": _num_confianza(reacs.get("total"), predeterminado="dudoso"),
            },
            "comentarios_count": _num_confianza(respuesta.get("comentarios_count")),
            "compartidos": {"valor": None, "confianza": "manual"},
            "vistas": {"valor": None, "confianza": "manual"},
            "comentarios": [
                {
                    "texto": c.get("texto", ""),
                    "autor": c.get("autor") or None,
                    "confianza": "seguro",
                }
                for c in (respuesta.get("comentarios") or [])
            ],
        }

    elif plataforma == "tiktok":
        metrics = respuesta.get("metricas", {})
        return {
            "plataforma": "tiktok",
            "texto_post": respuesta.get("texto_post") or "",
            "fecha": _fecha_confianza(respuesta.get("fecha")),
            "autor_cuenta": respuesta.get("autor_cuenta") or None,
            "metricas": {
                "likes": _num_confianza(metrics.get("likes")),
                "favoritos": _num_confianza(metrics.get("favoritos")),
                "comentarios_count": _num_confianza(metrics.get("comentarios_count")),
                "compartidos": {"valor": None, "confianza": "manual"},
                "vistas": {"valor": None, "confianza": "manual"},
            },
            "comentarios": [
                {
                    "texto": c.get("texto", ""),
                    "autor": c.get("autor") or None,
                    "confianza": "seguro",
                }
                for c in (respuesta.get("comentarios") or [])
            ],
        }

    raise ValueError(f"Plataforma no soportada: {plataforma}")


# ═══════════════════════════════════════════════
# Parseo de la respuesta de Gemini
# ═══════════════════════════════════════════════

def _parsear_respuesta(texto_respuesta: str) -> dict | None:
    """Extrae el primer JSON válido de la respuesta de Gemini."""
    if not texto_respuesta or not texto_respuesta.strip():
        return None

    texto = texto_respuesta.strip()

    # Intento 1: parse directo
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # Intento 2: bloque ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Intento 3: primer { ... }
    m = re.search(r"(\{.*\})", texto, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    return None


# ═══════════════════════════════════════════════
# Función principal
# ═══════════════════════════════════════════════

def extraer_post_desde_capturas(imagenes: list, plataforma: str) -> dict:
    """Extrae datos de un post desde capturas de pantalla con Gemini Vision.

    Args:
        imagenes: Lista de UploadedFile de Streamlit o bytes.
        plataforma: "facebook" | "tiktok".

    Returns:
        Dict con el contrato JSON estructurado.
        En error grave retorna {"error": "<motivo>"}.
    """
    # ── Validaciones tempranas ──
    if not _configurar_gemini():
        return {"error": "GOOGLE_API_KEY no configurada en st.secrets ni variable de entorno"}

    if not imagenes:
        return {"error": "No se recibieron imágenes"}

    if plataforma not in ("facebook", "tiktok"):
        return {"error": f"Plataforma no soportada: {plataforma}"}

    # ── Convertir imágenes a bytes ──
    image_parts = []
    for img in imagenes:
        try:
            if hasattr(img, "getvalue"):
                data = img.getvalue()
                mime = _detectar_mime(data, getattr(img, "type", None))
            elif isinstance(img, bytes):
                data = img
                mime = _detectar_mime(data)
            else:
                import io
                from PIL import Image
                buf = io.BytesIO()
                if hasattr(img, "save"):
                    img.save(buf, format="PNG")
                else:
                    Image.open(img).save(buf, format="PNG")
                data = buf.getvalue()
                mime = "image/png"
            image_parts.append({"mime_type": mime, "data": data})
        except Exception:
            continue  # imagen corrupta → saltar

    if not image_parts:
        return {"error": "Ninguna imagen pudo procesarse"}

    # ── Llamada a Gemini ──
    import google.generativeai as genai

    prompt = _construir_prompt(plataforma)
    modelo = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={"response_mime_type": "application/json"},
    )

    contenido = [prompt] + image_parts
    ultimo_error = None

    for intento in range(2):
        try:
            respuesta = modelo.generate_content(contenido)

            if not respuesta or not respuesta.text:
                ultimo_error = "Gemini devolvió respuesta vacía"
                if intento == 0:
                    contenido[0] = (
                        prompt
                        + "\n\nADVERTENCIA: la respuesta anterior fue inválida. "
                        "Devuelve SOLO JSON, sin markdown, sin texto extra."
                    )
                continue

            parsed = _parsear_respuesta(respuesta.text)
            if parsed is None:
                ultimo_error = "No se pudo parsear el JSON de Gemini"
                if intento == 0:
                    contenido[0] = (
                        prompt
                        + "\n\nADVERTENCIA: la respuesta anterior no fue JSON válido. "
                        "Devuelve SOLO JSON, sin markdown, sin texto extra."
                    )
                continue

            return _aplicar_contrato(parsed, plataforma)

        except Exception as e:
            ultimo_error = f"Error en llamada a Gemini: {e}"
            continue

    return {"error": ultimo_error or "Error desconocido"}
