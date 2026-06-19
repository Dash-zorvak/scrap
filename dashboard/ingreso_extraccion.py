"""
Módulo de extracción desde capturas/PDF con Groq (Llama 4 Scout visión).

Fase 2 — no toca UI ni DB.
Funciones públicas:
  - extraer_post_desde_capturas(imagenes, plataforma) -> dict   (1 post, compat)
  - extraer_posts_desde_archivos(archivos, plataforma) -> dict  (N posts; PDF/img)
  - normalizar_numero(texto) -> int | None
  - resolver_fecha_relativa(texto, hoy=None) -> str | None
"""

import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any

from dashboard.llm_groq import (
    chat_vision,
    groq_disponible,
    VENTANA,
    SOLAPE,
)


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
    if not texto or not isinstance(texto, str):
        return None
    texto = texto.strip()
    if not texto or texto in ("—", "-", "N/A", "n/a"):
        return None
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
            limpio = izq + der
        elif der == "":
            try:
                v = int(izq)
                return max(v, 0) * factor if v >= 0 else None
            except ValueError:
                return None
        else:
            limpio = izq + "." + der
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
    if not texto or not isinstance(texto, str):
        return None
    t = texto.strip()
    if not t:
        return None
    if _FECHA_ISO_RE.match(t):
        return t[:10]
    if hoy is None:
        hoy = date.today()
    elif isinstance(hoy, datetime):
        hoy = hoy.date()
    base = _quitar_acentos(t.lower())
    if "anteayer" in base or "antier" in base:
        return (hoy - timedelta(days=2)).isoformat()
    if "ayer" in base:
        return (hoy - timedelta(days=1)).isoformat()
    if "hoy" in base or "ahora" in base or "recien" in base:
        return hoy.isoformat()
    m = _UNIDAD_RE.search(base)
    if m:
        n = int(m.group(1))
        u = m.group(2)
        if u in ("s", "seg", "segs", "segundos", "min", "mins", "minuto",
                 "minutos", "m", "h", "hr", "hrs", "hora", "horas"):
            return hoy.isoformat()
        if u in ("d", "dia", "dias"):
            return (hoy - timedelta(days=n)).isoformat()
        if u in ("sem", "semana", "semanas"):
            return (hoy - timedelta(days=7 * n)).isoformat()
        if u in ("mes", "meses"):
            return (hoy - timedelta(days=30 * n)).isoformat()
        if u in ("a", "ano", "anos"):
            return (hoy - timedelta(days=365 * n)).isoformat()
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
    "cares": {"valor": null, "confianza": "seguro|dudoso"},
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
- "Me gusta"=likes, "Me encanta"=loves, "Me importa"=cares, "Me divierte"=hahas,
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

IMPORTANTE — CÓMO SEGMENTAR: el documento puede contener UNO o VARIOS posts. Un MISMO
post casi siempre ocupa VARIAS páginas (su enlace en una página, la captura del post en
otra, y sus reacciones/comentarios en una o más páginas siguientes). NO confundas
"una página" con "un post".

REGLA DE SEGMENTACIÓN (críticamente importante):
- Un post NUEVO empieza ÚNICAMENTE donde aparece una URL/enlace del post
  (por ejemplo una línea con "facebook.com/..."). Esa URL marca el inicio del post.
- TODAS las páginas que vienen DESPUÉS de esa URL (la captura del post, el panel de
  reacciones y los comentarios, aunque ocupen varias páginas) pertenecen a ESE MISMO
  post, hasta que aparezca la SIGUIENTE URL.
- La URL que inicia el post es el "enlace" de ese post.
- IGNORA por completo las páginas en blanco o casi vacías; no son posts.
- Si en TODO el documento NO hay ninguna URL, trátalo como UN SOLO post (salvo que se
  vea con total claridad otro autor o cabecera de un post claramente distinto).
- Ante la duda, AGRUPA en menos posts; nunca dividas un mismo post en varios.

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
        "cares": {"valor": null, "confianza": "seguro|dudoso"},
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
- Aplica SIEMPRE la REGLA DE SEGMENTACIÓN de arriba: las páginas sin URL que continúan
  la captura, las reacciones o los comentarios NO son posts nuevos; pertenecen al post
  de la última URL vista.
- Si solo hay UN post, devuelve igualmente "posts" con un único elemento.
- "Me gusta"=likes, "Me encanta"=loves, "Me importa"=cares, "Me divierte"=hahas,
  "Me entristece"=sads, "Me asombra"=wows, "Me enoja"=angrys
- NO extraer "compartidos" ni reproducciones/vistas
- FECHA: si es absoluta, devuélvela como 'YYYY-MM-DD'. Si es RELATIVA (p.ej. 'hace 2 h', 'hace 35 min', 'ayer', 'hace 3 días', 'hace 2 sem'), copia ESE TEXTO TAL CUAL en fecha.valor; NO inventes una fecha exacta. El sistema lo convertirá.
- ENLACE: usa la URL que marca el inicio del post (facebook.com/...), aunque esté en una
  página propia separada de la captura. Si ese post no tiene URL → valor=null.
- Por cada número, la fecha y el enlace, devuelve {"valor": ..., "confianza": "..."}.
- confianza="seguro" si el dato se lee con total claridad; "dudoso" si está borroso/cortado.
- Si un dato NO se ve → valor=null.
- Transcribe comentarios TEXTUALMENTE, sin resumir ni corregir. NO inventes datos.
- Asocia cada comentario al post correcto.
"""

_PROMPT_TIKTOK_MULTI = """
Eres un extractor de datos. Analiza el documento adjunto (puede ser un PDF de varias
páginas o varias imágenes) con capturas de pantalla de TikTok.

IMPORTANTE — CÓMO SEGMENTAR: el documento puede contener UNO o VARIOS posts. Un MISMO
post casi siempre ocupa VARIAS páginas (su enlace en una página, la captura del post en
otra, y sus métricas/comentarios en una o más páginas siguientes). NO confundas
"una página" con "un post".

REGLA DE SEGMENTACIÓN (críticamente importante):
- Un post NUEVO empieza ÚNICAMENTE donde aparece una URL/enlace del post
  (por ejemplo una línea con "tiktok.com/..."). Esa URL marca el inicio del post.
- TODAS las páginas que vienen DESPUÉS de esa URL (la captura del post, sus métricas y
  los comentarios, aunque ocupen varias páginas) pertenecen a ESE MISMO post, hasta que
  aparezca la SIGUIENTE URL.
- La URL que inicia el post es el "enlace" de ese post.
- IGNORA por completo las páginas en blanco o casi vacías; no son posts.
- Si en TODO el documento NO hay ninguna URL, trátalo como UN SOLO post (salvo que se
  vea con total claridad otra cuenta o cabecera de un post claramente distinto).
- Ante la duda, AGRUPA en menos posts; nunca dividas un mismo post en varios.

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
- Aplica SIEMPRE la REGLA DE SEGMENTACIÓN de arriba: las páginas sin URL que continúan
  la captura, las métricas o los comentarios NO son posts nuevos; pertenecen al post
  de la última URL vista.
- Si solo hay UN post, devuelve igualmente "posts" con un único elemento.
- corazón=likes, marcador/guardar=favoritos, bocadillo=comentarios_count
- NO extraer "compartidos" ni "vistas" (se teclean a mano)
- FECHA: si es absoluta, devuélvela como 'YYYY-MM-DD'. Si es RELATIVA (p.ej. 'hace 2 h', 'hace 35 min', 'ayer', 'hace 3 días', 'hace 2 sem'), copia ESE TEXTO TAL CUAL en fecha.valor; NO inventes una fecha exacta. El sistema lo convertirá.
- ENLACE: usa la URL que marca el inicio del post (tiktok.com/...), aunque esté en una
  página propia separada de la captura. Si ese post no tiene URL → valor=null.
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
    if v is None:
        return None
    return normalizar_numero(str(v))


def _num_confianza(raw: Any, predeterminado: str = "no_detectado") -> dict:
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
        return {"valor": None, "confianza": "no_detectado"}
    if conf not in ("seguro", "dudoso"):
        conf = "seguro"
    if not era_iso:
        conf = "dudoso"
    return {"valor": resuelta, "confianza": conf}


def _enlace_confianza(raw: Any) -> dict:
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
                "cares": _num_confianza(reacs.get("cares")),
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
# Parseo de la respuesta de IA
# ═══════════════════════════════════

def _parsear_respuesta(texto_respuesta: str) -> dict | None:
    if not texto_respuesta or not texto_respuesta.strip():
        return None
    texto = texto_respuesta.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"(\{.*\})", texto, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


def _extraer_lista_posts(parsed: Any) -> list:
    if isinstance(parsed, list):
        return [p for p in parsed if isinstance(p, dict)]
    if isinstance(parsed, dict):
        if isinstance(parsed.get("posts"), list):
            return [p for p in parsed["posts"] if isinstance(p, dict)]
        if any(k in parsed for k in ("texto_post", "reacciones", "metricas", "comentarios")):
            return [parsed]
    return []


# ═══════════════════════════════════
# Conversión de archivos a partes inline para IA
# ═══════════════════════════════════

def _archivos_a_partes(archivos: list) -> list:
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
            continue
    return partes


def _archivos_a_paginas(archivos: list) -> list[dict]:
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
# Deduplicación y filtrado de posts
# ═══════════════════════════════════

def _post_no_vacio(contrato: dict) -> bool:
    """True si el contrato tiene algún contenido real.

    Sirve para descartar "posts" fantasma generados por páginas en blanco o
    de relleno (solo un enlace, o nada): si no hay texto, ni comentarios, ni
    enlace, ni ninguna métrica/reacción con valor → se considera vacío.
    """
    if not isinstance(contrato, dict):
        return False
    if (contrato.get("texto_post") or "").strip():
        return True
    if contrato.get("comentarios"):
        return True
    if (contrato.get("enlace") or {}).get("valor"):
        return True
    cuenta = (contrato.get("comentarios_count") or {}).get("valor")
    if cuenta is not None:
        return True
    metricas = contrato.get("reacciones") or contrato.get("metricas") or {}
    for v in metricas.values():
        if isinstance(v, dict) and v.get("valor") is not None:
            return True
    return False


def _deduplicar_posts(posts: list) -> list:
    seen = {}
    result = []
    for post in posts:
        enlace = ((post.get("enlace") or {}).get("valor") or "").strip().lower()
        if enlace:
            key = enlace
        else:
            texto = (post.get("texto_post") or "").strip()
            texto = re.sub(r"\s+", " ", texto).lower()[:80]
            if texto:
                key = "txt:" + texto
            else:
                key = None

        if key is None:
            result.append(post)
        elif key not in seen:
            seen[key] = len(result)
            result.append(post)
        else:
            idx = seen[key]
            existing = result[idx]
            existing_comments = (existing.get("comentarios_count") or {}).get("valor") or 0
            current_comments = (post.get("comentarios_count") or {}).get("valor") or 0
            if current_comments > existing_comments:
                result[idx] = post

    return result


def _depurar_posts(posts: list) -> list:
    """Filtra posts vacíos y deduplica (por enlace o texto)."""
    return _deduplicar_posts([p for p in posts if _post_no_vacio(p)])


# ═══════════════════════════════════
# Función principal MULTI-POST (PDF/imágenes)
# ═══════════════════════════════════

def extraer_posts_desde_archivos(archivos: list, plataforma: str) -> dict:
    """Extrae UNO O VARIOS posts desde archivos (PDF o imágenes) con Groq Visión.

    Para pocas páginas (≤ VENTANA): una sola llamada con prompt multi-post.
    Para muchas páginas (> VENTANA): extracción por ventanas con solape + deduplicación
    por enlace (o texto truncado a 80 chars si no hay enlace).

    En ambos caminos se filtran posts vacíos y se deduplica, de modo que un mismo
    post repartido en varias páginas (enlace + captura + comentarios) NO se divida
    en varios.

    Args:
        archivos: Lista de UploadedFile de Streamlit, bytes o imágenes PIL.
        plataforma: "facebook" | "tiktok".

    Returns:
        {"posts": [contrato, ...]} con un contrato por post detectado.
        En error grave: {"error": "<motivo>"}.
    """
    if not groq_disponible():
        return {"error": "GROQ_API_KEY no configurada en variable de entorno ni st.secrets"}

    if not archivos:
        return {"error": "No se recibieron archivos"}

    if plataforma not in ("facebook", "tiktok"):
        return {"error": f"Plataforma no soportada: {plataforma}"}

    paginas = _archivos_a_paginas(archivos)
    if not paginas:
        return {"error": "Ningún archivo pudo procesarse"}

    prompt_multi = _construir_prompt_multi(plataforma)

    # ── Pocas páginas (≤ VENTANA) → una sola llamada ──
    if len(paginas) <= VENTANA:
        ultimo_error = None
        for intento in range(2):
            try:
                texto_respuesta = chat_vision(prompt_multi, paginas)
                if not texto_respuesta or not texto_respuesta.strip():
                    ultimo_error = "Groq devolvió respuesta vacía"
                    if intento == 0:
                        prompt_multi = (
                            prompt_multi
                            + "\n\nADVERTENCIA: la respuesta anterior fue inválida. "
                            'Devuelve SOLO JSON con la forma {"posts": [...]}, sin markdown.'
                        )
                    continue

                parsed = _parsear_respuesta(texto_respuesta)
                posts_raw = _extraer_lista_posts(parsed) if parsed is not None else []
                if not posts_raw:
                    ultimo_error = "No se detectaron posts en los archivos"
                    if intento == 0:
                        prompt_multi = (
                            prompt_multi
                            + "\n\nADVERTENCIA: la respuesta anterior no fue JSON válido o no "
                            'traía posts. Devuelve SOLO JSON con la forma {"posts": [...]}.'
                        )
                    continue

                posts = [_aplicar_contrato(p, plataforma) for p in posts_raw]
                posts = _depurar_posts(posts)
                if not posts:
                    ultimo_error = "No se detectaron posts con contenido"
                    if intento == 0:
                        prompt_multi = (
                            prompt_multi
                            + "\n\nADVERTENCIA: la respuesta anterior no traía posts con "
                            'contenido. Recuerda agrupar páginas del mismo post y devolver '
                            'SOLO JSON con la forma {"posts": [...]}.'
                        )
                    continue
                return {"posts": posts}

            except Exception as e:
                ultimo_error = f"Error en llamada a Groq: {e}"
                continue

        return {"error": ultimo_error or "Error desconocido"}

    # ── Muchas páginas (> VENTANA) → extracción por ventanas + dedupe ──
    paso = max(1, VENTANA - SOLAPE)
    ultimo_error = None
    posts_raw = []

    for i in range(0, len(paginas), paso):
        ventana = paginas[i:i + VENTANA]
        extraido = False

        for intento in range(2):
            try:
                texto_respuesta = chat_vision(prompt_multi, ventana)
                if not texto_respuesta or not texto_respuesta.strip():
                    ultimo_error = "Groq devolvió respuesta vacía"
                    if intento == 0:
                        continue
                    break

                parsed = _parsear_respuesta(texto_respuesta)
                batch = _extraer_lista_posts(parsed) if parsed is not None else []
                if batch:
                    posts_raw.extend(batch)
                    extraido = True
                    break
                else:
                    ultimo_error = "No se detectaron posts en la ventana"
                    if intento == 0:
                        continue
                    break

            except Exception as e:
                ultimo_error = f"Error en extracción: {e}"
                if intento == 0:
                    continue
                break

        if not extraido:
            continue

    if not posts_raw:
        return {"error": ultimo_error or "No se pudo extraer ningún post"}

    posts_contratos = [_aplicar_contrato(p, plataforma) for p in posts_raw]
    posts_dedupe = _depurar_posts(posts_contratos)
    if not posts_dedupe:
        return {"error": ultimo_error or "No se pudo extraer ningún post con contenido"}
    return {"posts": posts_dedupe}


# ═══════════════════════════════════
# Función principal 1-POST (compat con Fase 2 original)
# ═══════════════════════════════════

def extraer_post_desde_capturas(imagenes: list, plataforma: str) -> dict:
    """Extrae datos de UN post desde capturas con Groq Visión (compat).

    Args:
        imagenes: Lista de UploadedFile de Streamlit o bytes.
        plataforma: "facebook" | "tiktok".

    Returns:
        Dict con el contrato JSON estructurado.
        En error grave retorna {"error": "<motivo>"}.
    """
    if not groq_disponible():
        return {"error": "GROQ_API_KEY no configurada en variable de entorno ni st.secrets"}

    if not imagenes:
        return {"error": "No se recibieron imágenes"}

    if plataforma not in ("facebook", "tiktok"):
        return {"error": f"Plataforma no soportada: {plataforma}"}

    image_parts = _archivos_a_partes(imagenes)
    if not image_parts:
        return {"error": "Ninguna imagen pudo procesarse"}

    prompt = _construir_prompt(plataforma)
    ultimo_error = None

    for intento in range(2):
        try:
            texto_respuesta = chat_vision(prompt, image_parts)
            if not texto_respuesta or not texto_respuesta.strip():
                ultimo_error = "Groq devolvió respuesta vacía"
                if intento == 0:
                    prompt = (
                        prompt
                        + "\n\nADVERTENCIA: la respuesta anterior fue inválida. "
                        "Devuelve SOLO JSON, sin markdown, sin texto extra."
                    )
                continue

            parsed = _parsear_respuesta(texto_respuesta)
            if parsed is None:
                ultimo_error = "No se pudo parsear el JSON de Groq"
                if intento == 0:
                    prompt = (
                        prompt
                        + "\n\nADVERTENCIA: la respuesta anterior no fue JSON válido. "
                        "Devuelve SOLO JSON, sin markdown, sin texto extra."
                    )
                continue

            return _aplicar_contrato(parsed, plataforma)

        except Exception as e:
            ultimo_error = f"Error en llamada a Groq: {e}"
            continue

    return {"error": ultimo_error or "Error desconocido"}
