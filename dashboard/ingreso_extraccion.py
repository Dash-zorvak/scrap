"""
Módulo de extracción desde capturas/PDF con Gemini Vision.

Fase 2 — no toca UI ni DB.
Funciones públicas:
  - extraer_post_desde_capturas(imagenes, plataforma) -> dict   (1 post, compat)
  - extraer_posts_desde_archivos(archivos, plataforma) -> dict  (N posts; PDF/img)
  - normalizar_numero(texto) -> int | None
  - resolver_fecha_relativa(texto, hoy=None) -> str | None

Novedades:
  - Soporta PDF nativo (Gemini procesa PDF multipágina como inline_data).
  - Un mismo archivo (p.ej. un PDF) puede contener VARIOS posts: el motor los
    segmenta y devuelve una lista bajo la clave 'posts'.
  - Extrae automáticamente el ENLACE del post (post_url) visible en el archivo,
    con marca de confianza (seguro|dudoso|no_detectado).
  - Resuelve fechas relativas ('hace 2 h', 'ayer', 'hace 3 días') a 'YYYY-MM-DD'.
"""

import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any

GEMINI_MODEL = "gemini-2.0-flash"


# ═══════════════════════════════════
# Normalizador determinista de números
# ═══════════════════════════════════

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


# ═══════════════════════════════════
# Resolución de fechas relativas → absolutas (determinista)
# ═══════════════════════════════════

_FECHA_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

_UNIDAD_RE = re.compile(
    r"(\d+)\s*"
    r"(meses|mes|semanas|semana|sem|minutos|minuto|mins|min|horas|hora|hrs|hr|"
    r"dias|dia|anos|ano|segundos|segs|seg|h|d|m|s|a)\b"
)


def _quitar_acentos(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def resolver_fecha_relativa(texto, hoy=None):
    """Convierte una fecha relativa o absoluta (texto) a 'YYYY-MM-DD'.

    Ejemplos (con hoy = 2026-06-18):
      '2026-05-01'      -> '2026-05-01'   (ya es ISO, passthrough)
      'hace 2 h' / '2h' -> '2026-06-18'   (segundos/minutos/horas = hoy)
      'ayer'            -> '2026-06-17'
      'anteayer'        -> '2026-06-16'
      'hace 3 dias'     -> '2026-06-15'
      'hace 2 semanas'  -> '2026-06-04'
      'hace 2 meses'    -> '2026-04-19'
      '17 de junio'     -> '2026-06-17'
    Devuelve None si el texto está vacío o no se puede interpretar.
    """
    if not texto or not isinstance(texto, str):
        return None
    t = texto.strip()
    if not t:
        return None

    # Ya es una fecha ISO -> passthrough (primeros 10 caracteres)
    if _FECHA_ISO_RE.match(t):
        return t[:10]

    if hoy is None:
        hoy = date.today()
    elif isinstance(hoy, datetime):
        hoy = hoy.date()

    base = _quitar_acentos(t.lower())

    # Palabras clave
    if "anteayer" in base or "antier" in base:
        return (hoy - timedelta(days=2)).isoformat()
    if "ayer" in base:
        return (hoy - timedelta(days=1)).isoformat()
    if "hoy" in base or "ahora" in base or "recien" in base:
        return hoy.isoformat()

    # "hace N <unidad>" o "N<unidad>"
    m = _UNIDAD_RE.search(base)
    if m:
        n = int(m.group(1))
        u = m.group(2)
        if u in ("s", "seg", "segs", "segundos", "min", "mins", "minuto",
                 "minutos", "m", "h", "hr", "hrs", "hora", "horas"):
            return hoy.isoformat()  # segundos/minutos/horas -> hoy
        if u in ("d", "dia", "dias"):
            return (hoy - timedelta(days=n)).isoformat()
        if u in ("sem", "semana", "semanas"):
            return (hoy - timedelta(days=7 * n)).isoformat()
        if u in ("mes", "meses"):
            return (hoy - timedelta(days=30 * n)).isoformat()
        if u in ("a", "ano", "anos"):
            return (hoy - timedelta(days=365 * n)).isoformat()

    # "17 de junio" / "5 de enero de 2025" / "5 ene"
    m = re.search(r"(\d{1,2})\s*(?:de\s+)?([a-z]+)\.?(?:\s+(?:de\s+)?(\d{4}))?", base)
    if m:
        dia = int(m.group(1))
        mes_txt = m.group(2)
        mes_num = None
        for nombre, num in _MESES.items():
            if nombre.startswith(mes_txt[:3]):
                mes_num = num
                break
        if mes_num is not None:
            anio = int(m.group(3)) if m.group(3) else hoy.year
            try:
                d = date(anio, mes_num, dia)
            except ValueError:
                return None
            # Sin año explícito y fecha futura -> asumir año anterior
            if not m.group(3) and d > hoy:
                try:
                    d = date(anio - 1, mes_num, dia)
                except ValueError:
                    return None
            return d.isoformat()

    return None


# ═══════════════════════════════════
# Detección de MIME type real (imágenes + PDF)
# ═══════════════════════════════════

def _detectar_mime(data: bytes, declarado: str | None = None) -> str:
    """Detecta el mime real del archivo. Respeta el declarado si es image/* o PDF.

    Soporta: JPEG, PNG, WEBP y PDF (application/pdf). Fallback: image/png.
    """
    if declarado and (declarado.startswith("image/") or declarado == "application/pdf"):
        return declarado
    if data[:4] == b"%PDF":
        return "application/pdf"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


# ═══════════════════════════════════
# Renderizado de PDF a imágenes por página (PyMuPDF)
# ═══════════════════════════════════

def _pdf_a_imagenes(data: bytes, dpi: int = 150) -> list[bytes]:
    """Abre un PDF con PyMuPDF y devuelve una lista de PNG (bytes), uno por página."""
    try:
        import fitz
    except ImportError:
        return []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        paginas = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            paginas.append(pix.tobytes("png"))
        doc.close()
        return paginas
    except Exception:
        return []


# ═══════════════════════════════════
# Configuración de Gemini (diferida)
# ═══════════════════════════════════

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


# ═══════════════════════════════════
# Prompts por plataforma (1 post — compat)
# ═══════════════════════════════════

_PROMPT_FACEBOOK = """
Eres un extractor de datos. Analiza las imágenes de esta captura de pantalla de Facebook.

DEVUELVE SOLO JSON, SIN texto adicional, con esta estructura exacta:

{
  "texto_post": "string (texto del post, vacío si no se ve)",
  "fecha": {"valor": "YYYY-MM-DD, o el texto relativo tal cual (p.ej. 'hace 2 h', 'ayer'), o null", "confianza": "seguro|dudoso"},
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
- FECHA: si es absoluta, devuélvela como 'YYYY-MM-DD'. Si es RELATIVA (p.ej. 'hace 2 h', 'hace 35 min', 'ayer', 'hace 3 días', 'hace 2 sem'), copia ESE TEXTO TAL CUAL en fecha.valor; NO inventes una fecha exacta. El sistema lo convertirá.
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
  "fecha": {"valor": "YYYY-MM-DD, o el texto relativo tal cual (p.ej. 'hace 2 h', 'ayer'), o null", "confianza": "seguro|dudoso"},
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
- FECHA: si es absoluta, devuélvela como 'YYYY-MM-DD'. Si es RELATIVA (p.ej. 'hace 2 h', 'hace 35 min', 'ayer', 'hace 3 días', 'hace 2 sem'), copia ESE TEXTO TAL CUAL en fecha.valor; NO inventes una fecha exacta. El sistema lo convertirá.
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


# ═══════════════════════════════════
# Prompts MULTI-POST (segmentación + enlace) — PDF/imágenes
# ═══════════════════════════════════

_PROMPT_FACEBOOK_MULTI = """
Eres un extractor de datos. Analiza el documento adjunto (puede ser un PDF de varias
páginas o varias imágenes) con capturas de pantalla de Facebook.

IMPORTANTE: el documento puede contener VARIOS posts DISTINTOS. Debes SEGMENTARLO e
identificar cada post por separado. Cada post suele incluir su propio texto, sus
reacciones, sus comentarios y, frecuentemente, su ENLACE (URL) pegado junto a la captura.

DEVUELVE SOLO JSON, SIN texto adicional, con esta estructura exacta:

{
  "posts": [
    {
      "texto_post": "string (texto del post, vacío si no se ve)",
      "fecha": {"valor": "YYYY-MM-DD, o el texto relativo tal cual (p.ej. 'hace 2 h', 'ayer'), o null", "confianza": "seguro|dudoso"},
      "autor_pagina": "nombre de la página o null",
      "enlace": {"valor": "https://... o null", "confianza": "seguro|dudoso"},
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
  ]
}

REGLAS:
- Si solo hay UN post, devuelve igualmente "posts" con un único elemento.
- "Me gusta"=likes, "Me encanta"=loves, "Me divierte"=hahas,
  "Me entristece"=sads, "Me asombra"=wows, "Me enoja"=angrys
- NO extraer "compartidos" ni reproducciones/vistas
- FECHA: si es absoluta, devuélvela como 'YYYY-MM-DD'. Si es RELATIVA (p.ej. 'hace 2 h', 'hace 35 min', 'ayer', 'hace 3 días', 'hace 2 sem'), copia ESE TEXTO TAL CUAL en fecha.valor; NO inventes una fecha exacta. El sistema lo convertirá.
- ENLACE: busca la URL del post (facebook.com/...). Si está escrita/pegada en el
  documento úsala; si no aparece → valor=null.
- Por cada número, la fecha y el enlace, devuelve {"valor": ..., "confianza": "..."}.
- confianza="seguro" si el dato se lee con total claridad; "dudoso" si está borroso/cortado.
- Si un dato NO se ve → valor=null.
- Transcribe comentarios TEXTUALMENTE, sin resumir ni corregir. NO inventes datos.
- Asocia cada comentario al post correcto.
"""

_PROMPT_TIKTOK_MULTI = """
Eres un extractor de datos. Analiza el documento adjunto (puede ser un PDF de varias
páginas o varias imágenes) con capturas de pantalla de TikTok.

IMPORTANTE: el documento puede contener VARIOS posts DISTINTOS. Debes SEGMENTARLO e
identificar cada post por separado. Cada post suele incluir su descripción, sus métricas,
sus comentarios y, frecuentemente, su ENLACE (URL) pegado junto a la captura.

DEVUELVE SOLO JSON, SIN texto adicional, con esta estructura exacta:

{
  "posts": [
    {
      "texto_post": "string (descripción, vacío si no se ve)",
      "fecha": {"valor": "YYYY-MM-DD, o el texto relativo tal cual (p.ej. 'hace 2 h', 'ayer'), o null", "confianza": "seguro|dudoso"},
      "autor_cuenta": "nombre de la cuenta o null",
      "enlace": {"valor": "https://... o null", "confianza": "seguro|dudoso"},
      "metricas": {
        "likes": {"valor": null, "confianza": "seguro|dudoso"},
        "favoritos": {"valor": null, "confianza": "seguro|dudoso"},
        "comentarios_count": {"valor": null, "confianza": "seguro|dudoso"}
      },
      "comentarios": [
        {"texto": "texto literal", "autor": "nombre o null"}
      ]
    }
  ]
}

REGLAS:
- Si solo hay UN post, devuelve igualmente "posts" con un único elemento.
- corazón=likes, marcador/guardar=favoritos, bocadillo=comentarios_count
- NO extraer "compartidos" ni "vistas" (se teclean a mano)
- FECHA: si es absoluta, devuélvela como 'YYYY-MM-DD'. Si es RELATIVA (p.ej. 'hace 2 h', 'hace 35 min', 'ayer', 'hace 3 días', 'hace 2 sem'), copia ESE TEXTO TAL CUAL en fecha.valor; NO inventes una fecha exacta. El sistema lo convertirá.
- ENLACE: busca la URL del post (tiktok.com/...). Si está escrita/pegada en el
  documento úsala; si no aparece → valor=null.
- Por cada número, la fecha y el enlace, devuelve {"valor": ..., "confianza": "..."}.
- confianza="seguro" si el dato se lee con total claridad; "dudoso" si está borroso/cortado.
- Si un dato NO se ve → valor=null.
- Transcribe comentarios TEXTUALMENTE, sin resumir ni corregir. NO inventes datos.
- Asocia cada comentario al post correcto.
"""


def _construir_prompt_multi(plataforma: str) -> str:
    if plataforma == "facebook":
        return _PROMPT_FACEBOOK_MULTI
    elif plataforma == "tiktok":
        return _PROMPT_TIKTOK_MULTI
    raise ValueError(f"Plataforma no soportada: {plataforma}")


# ═══════════════════════════════════
# Aplicación del contrato JSON de salida
# ═══════════════════════════════════

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


def _fecha_confianza(raw: Any, hoy=None) -> dict:
    """Procesa la fecha que Gemini devuelve como {valor, confianza} o string.

    Resuelve fechas relativas ('hace 2 h', 'ayer', ...) y absolutas no-ISO a
    'YYYY-MM-DD' usando `hoy` (por defecto, la fecha actual). Si el valor fue
    inferido de una expresión relativa/natural, la confianza se degrada a
    'dudoso'. Si no se puede interpretar, se marca como no_detectado.
    """
    if isinstance(raw, dict):
        valor = raw.get("valor") or None
        conf = raw.get("confianza")
    else:
        valor = raw or None
        conf = None
    if valor is None:
        return {"valor": None, "confianza": "no_detectado"}

    texto = str(valor).strip()
    era_iso = bool(_FECHA_ISO_RE.match(texto))
    resuelta = resolver_fecha_relativa(texto, hoy=hoy)
    if resuelta is None:
        # No interpretable -> mejor no_detectado que guardar basura
        return {"valor": None, "confianza": "no_detectado"}

    if conf not in ("seguro", "dudoso"):
        conf = "seguro"
    if not era_iso:
        # Fecha inferida de texto relativo/natural -> degradar confianza
        conf = "dudoso"
    return {"valor": resuelta, "confianza": conf}


def _enlace_confianza(raw: Any) -> dict:
    """Procesa el enlace (post_url) que Gemini devuelve como {valor, confianza}
    o como string suelto. No normaliza (es una URL)."""
    if isinstance(raw, dict):
        valor = raw.get("valor") or None
        conf = raw.get("confianza")
    else:
        valor = raw or None
        conf = None
    if valor is None:
        return {"valor": None, "confianza": "no_detectado"}
    valor = str(valor).strip() or None
    if valor is None:
        return {"valor": None, "confianza": "no_detectado"}
    if conf not in ("seguro", "dudoso"):
        conf = "seguro"
    return {"valor": valor, "confianza": conf}


def _aplicar_contrato(respuesta: dict, plataforma: str) -> dict:
    """Rellena la plantilla del contrato con lo que devolvió Gemini.

    compartidos/vistas siempre null + "manual".
    enlace: {valor, confianza} (no_detectado si no vino).
    """
    if plataforma == "facebook":
        reacs = respuesta.get("reacciones", {})
        return {
            "plataforma": "facebook",
            "texto_post": respuesta.get("texto_post") or "",
            "fecha": _fecha_confianza(respuesta.get("fecha")),
            "autor_pagina": respuesta.get("autor_pagina") or None,
            "enlace": _enlace_confianza(respuesta.get("enlace")),
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
            "enlace": _enlace_confianza(respuesta.get("enlace")),
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


# ═══════════════════════════════════
# Parseo de la respuesta de Gemini
# ═══════════════════════════════════

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


def _extraer_lista_posts(parsed: Any) -> list:
    """Normaliza la respuesta multi-post a una lista de dicts de post.

    Acepta: {"posts": [...]} | [ ... ] | un solo post suelto.
    """
    if isinstance(parsed, list):
        return [p for p in parsed if isinstance(p, dict)]
    if isinstance(parsed, dict):
        if isinstance(parsed.get("posts"), list):
            return [p for p in parsed["posts"] if isinstance(p, dict)]
        # Fallback: respuesta de un solo post sin envoltura
        if any(k in parsed for k in ("texto_post", "reacciones", "metricas", "comentarios")):
            return [parsed]
    return []


# ═══════════════════════════════════
# Segmentación (pasada 1 del flujo de dos pasadas)
# ═══════════════════════════════════

_PROMPT_SEGMENTACION_TEMPLATE = (
    "Eres un segmentador de documentos. Te paso N imágenes que son páginas CONSECUTIVAS "
    "de capturas de pantalla de {platform}. Varias páginas seguidas pueden pertenecer al "
    "MISMO post (la publicación y sus comentarios). Agrupa las páginas en posts distintos.\n\n"
    "Devuelve SOLO JSON, sin texto extra:\n"
    '{{"posts": [{{"paginas": [1, 2], "enlace": "https://... o null"}}]}}\n\n'
    "Reglas: numeración 1-based en el mismo orden recibido; cada página pertenece a UN solo "
    "post; las páginas de un post son consecutivas; si una página tiene una URL pegada "
    "normalmente marca el inicio de un post; enlace = la URL del post si aparece, si no null."
)


def _extraer_grupos(parsed: Any) -> list | None:
    """Extrae grupos de páginas de la respuesta de segmentación.

    Acepta: {"posts": [{"paginas": [1,2], "enlace": "..."}]}
    Devuelve None si no se puede extraer nada.
    """
    if not isinstance(parsed, dict):
        return None
    posts = parsed.get("posts")
    if not isinstance(posts, list):
        return None
    grupos = []
    for p in posts:
        if not isinstance(p, dict):
            continue
        paginas = p.get("paginas")
        if not isinstance(paginas, list) or not paginas:
            continue
        enlace = p.get("enlace")
        grupos.append({"paginas": paginas, "enlace": enlace})
    return grupos if grupos else None


# ═══════════════════════════════════
# Conversión de archivos a partes inline para Gemini
# ═══════════════════════════════════

def _archivos_a_partes(archivos: list) -> list:
    """Convierte UploadedFile/bytes/PIL a partes inline_data {mime_type, data}.

    Soporta PDF e imágenes. Los archivos corruptos se saltan.
    """
    partes = []
    for arch in archivos:
        try:
            if hasattr(arch, "getvalue"):
                data = arch.getvalue()
                mime = _detectar_mime(data, getattr(arch, "type", None))
            elif isinstance(arch, bytes):
                data = arch
                mime = _detectar_mime(data)
            else:
                import io
                from PIL import Image
                buf = io.BytesIO()
                if hasattr(arch, "save"):
                    arch.save(buf, format="PNG")
                else:
                    Image.open(arch).save(buf, format="PNG")
                data = buf.getvalue()
                mime = "image/png"
            partes.append({"mime_type": mime, "data": data})
        except Exception:
            continue  # archivo corrupto → saltar
    return partes


# ═══════════════════════════════════
# Conversión de archivos a páginas (imágenes individuales por página)
# ═══════════════════════════════════

def _archivos_a_paginas(archivos: list) -> list[dict]:
    """Convierte archivos (UploadedFile/bytes/PIL/Pdf) a partes inline UNA POR PÁGINA.

    Un PDF se rasteriza → tantas partes image/png como páginas.
    Una imagen → una parte con su mime original.
    Archivos corruptos → se saltan.
    """
    partes = []
    for arch in archivos:
        try:
            if hasattr(arch, "getvalue"):
                data = arch.getvalue()
                mime = _detectar_mime(data, getattr(arch, "type", None))
            elif isinstance(arch, bytes):
                data = arch
                mime = _detectar_mime(data)
            else:
                import io
                from PIL import Image
                buf = io.BytesIO()
                if hasattr(arch, "save"):
                    arch.save(buf, format="PNG")
                else:
                    Image.open(arch).save(buf, format="PNG")
                data = buf.getvalue()
                mime = "image/png"

            if mime == "application/pdf":
                for png_bytes in _pdf_a_imagenes(data):
                    partes.append({"mime_type": "image/png", "data": png_bytes})
            else:
                partes.append({"mime_type": mime, "data": data})
        except Exception:
            continue
    return partes


# ═══════════════════════════════════
# Función principal MULTI-POST (PDF/imágenes)
# ═══════════════════════════════════

def extraer_posts_desde_archivos(archivos: list, plataforma: str) -> dict:
    """Extrae UNO O VARIOS posts desde archivos (PDF o imágenes) con Gemini Vision.

    Args:
        archivos: Lista de UploadedFile de Streamlit, bytes o imágenes PIL.
        plataforma: "facebook" | "tiktok".

    Returns:
        {"posts": [contrato, ...]} con un contrato por post detectado.
        En error grave: {"error": "<motivo>"}.
    """
    if not _configurar_gemini():
        return {"error": "GOOGLE_API_KEY no configurada en st.secrets ni variable de entorno"}

    if not archivos:
        return {"error": "No se recibieron archivos"}

    if plataforma not in ("facebook", "tiktok"):
        return {"error": f"Plataforma no soportada: {plataforma}"}

    paginas = _archivos_a_paginas(archivos)
    if not paginas:
        return {"error": "Ningún archivo pudo procesarse"}

    import google.generativeai as genai

    modelo = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={"response_mime_type": "application/json", "max_output_tokens": 8192},
    )

    # ── Una sola página → ruta tradicional (compat) ──
    if len(paginas) <= 1:
        prompt = _construir_prompt_multi(plataforma)
        contenido = [prompt] + paginas
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
                            'Devuelve SOLO JSON con la forma {"posts": [...]}, sin markdown.'
                        )
                    continue

                parsed = _parsear_respuesta(respuesta.text)
                posts_raw = _extraer_lista_posts(parsed) if parsed is not None else []
                if not posts_raw:
                    ultimo_error = "No se detectaron posts en los archivos"
                    if intento == 0:
                        contenido[0] = (
                            prompt
                            + "\n\nADVERTENCIA: la respuesta anterior no fue JSON válido o no "
                            'traía posts. Devuelve SOLO JSON con la forma {"posts": [...]}.'
                        )
                    continue

                posts = [_aplicar_contrato(p, plataforma) for p in posts_raw]
                return {"posts": posts}

            except Exception as e:
                ultimo_error = f"Error en llamada a Gemini: {e}"
                continue

        return {"error": ultimo_error or "Error desconocido"}

    # ── Múltiples páginas → dos pasadas ──
    # PASADA 1: segmentación
    prompt_seg = _PROMPT_SEGMENTACION_TEMPLATE.format(platform=plataforma)
    ultimo_error = None
    grupos = None

    try:
        respuesta_seg = modelo.generate_content([prompt_seg] + paginas)
        if respuesta_seg and respuesta_seg.text:
            parsed_seg = _parsear_respuesta(respuesta_seg.text)
            grupos = _extraer_grupos(parsed_seg)
    except Exception as e:
        ultimo_error = f"Error en segmentación: {e}"

    if not grupos:
        # Fallback: tratar todo como un solo grupo
        grupos = [{"paginas": list(range(1, len(paginas) + 1)), "enlace": None}]

    # PASADA 2: extraer cada post por separado
    prompt_unico = _construir_prompt(plataforma)
    posts = []

    for grupo in grupos:
        idxs = [i - 1 for i in grupo.get("paginas", [])]
        idxs = [i for i in idxs if 0 <= i < len(paginas)]
        if not idxs:
            continue

        paginas_grupo = [paginas[i] for i in idxs]
        contrato = None

        for intento in range(2):
            try:
                contenido = [prompt_unico] + paginas_grupo
                respuesta = modelo.generate_content(contenido)

                if not respuesta or not respuesta.text:
                    if intento == 0:
                        continue
                    ultimo_error = "Gemini devolvió respuesta vacía"
                    continue

                parsed = _parsear_respuesta(respuesta.text)
                if parsed is None:
                    if intento == 0:
                        continue
                    ultimo_error = "No se pudo parsear el JSON"
                    continue

                contrato = _aplicar_contrato(parsed, plataforma)

                # Inyectar enlace de la pasada 1 si el contrato no detectó uno
                enlace_grupo = grupo.get("enlace")
                if enlace_grupo:
                    enlace_actual = (contrato.get("enlace") or {}).get("valor")
                    if not enlace_actual:
                        contrato["enlace"] = _enlace_confianza(enlace_grupo)

                posts.append(contrato)
                break

            except Exception as e:
                ultimo_error = f"Error en llamada a Gemini: {e}"
                continue

        if contrato is None:
            # Si un grupo falla, continuamos con los demás
            continue

    if not posts:
        return {"error": ultimo_error or "No se pudo extraer ningún post"}
    return {"posts": posts}


# ═══════════════════════════════════
# Función principal 1-POST (compat con Fase 2 original)
# ═══════════════════════════════════

def extraer_post_desde_capturas(imagenes: list, plataforma: str) -> dict:
    """Extrae datos de UN post desde capturas con Gemini Vision (compat).

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

    image_parts = _archivos_a_partes(imagenes)
    if not image_parts:
        return {"error": "Ninguna imagen pudo procesarse"}

    # ── Llamada a Gemini ──
    import google.generativeai as genai

    prompt = _construir_prompt(plataforma)
    modelo = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={"response_mime_type": "application/json", "max_output_tokens": 8192},
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
