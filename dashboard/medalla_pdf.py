"""Generador del informe PDF «Mejor medalla reciente» para el dashboard del alcalde.

El documento separa con claridad dos capas:

  • DOCTRINA GENÉRICA reutilizable: el marco de evaluación «prueba del dolor» y
    los anti-patrones de «contenido que no traduce tracción». Es metodología,
    NO menciona ningún caso concreto, y por eso puede repetirse cada período.

  • LECTURA DEL CASO + ALCANCE, que se ADAPTAN en cada generación al post medalla
    real del período: de qué trata la publicación, sus cifras (reacciones, tasa,
    impresiones estimadas), las réplicas en medios y los enlaces de referencia.
    Si hay capturas guardadas del post, se incrustan.

El módulo NO depende de Streamlit. La redacción adaptativa usa el LLM de texto
(dashboard.llm_groq.chat_texto) cuando hay API key; si no, cae a una plantilla
local determinista construida con los datos reales del post.
"""
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ══════════════════════════════════════════════════
# Marco editorial GENÉRICO — doctrina reutilizable, SIN casos concretos
# ══════════════════════════════════════════════════

TITULO = "ALCANCE DESTACADO Y PUNTOS SOBRE LA MEJOR MEDALLA RECIENTE DEL ALCALDE"

# Doctrina «prueba del dolor». Texto fijo PERO genérico: describe el MÉTODO de
# evaluación, nunca un caso particular. La lectura del caso real se redacta aparte.
DOCTRINA_TITULO = "Cómo se evalúa la medalla (la «prueba del dolor»)"
DOCTRINA_INTRO = (
    "La mejor medalla reciente del alcalde se evalúa con la «prueba del dolor»: el "
    "contenido que mejor traduce tracción positiva es el que comunica, en una sola "
    "lectura visual inmediata, una historia completa. La meta es una línea editorial "
    "consistente: traducción visual de emoción y evidencia tangible."
)
DOCTRINA_LEAD = "En una sola imagen deberían leerse 3 elementos clave:"
DOCTRINA_ELEMENTOS = [
    (
        "Emoción real",
        "una emoción genuina que la gente siente de inmediato y que no se puede fabricar.",
    ),
    (
        "Autoridad cercana",
        "el alcalde presente y al lado de la gente, en el lugar de los hechos, no en un podio.",
    ),
    (
        "Evidencia tangible",
        "una prueba física y concreta de que algo pasó —no solo palabras— con un titular "
        "legible al instante.",
    ),
]
DOCTRINA_IGUAL = "= EXCELENCIA MEDIÁTICA VISUAL"
DOCTRINA_CIERRE = (
    "Cuando los tres elementos están presentes la historia se cuenta sola —con héroe, "
    "beneficiario y resultado— y los medios la retoman porque no hay nada que construir: "
    "la historia ya está lista. Esa es la estructura de la prueba del dolor."
)

# Sección «Contenido que no traduce tracción». Texto fijo y genérico.
NO_TRACCION_TITULO = "CONTENIDO QUE NO TRADUCE TRACCIÓN A PESAR DE EXCELENTES IMÁGENES"
NO_TRACCION_PUNTOS = [
    (
        "Sin antes y después",
        "El cerebro necesita el contraste para sentir el logro: una calle limpia no prueba "
        "nada si no se vio antes sucia; una obra terminada no impacta sin el «antes». Sin "
        "el «antes», el «después» no existe emocionalmente.",
    ),
    (
        "Collage de imágenes = atención dividida",
        "Una sola imagen es un único punto de entrada visual. Con 3, 4 o 10 fotos el ojo no "
        "sabe dónde pararse, no se ancla en nada, y en 3 segundos ya pasó de largo.",
    ),
    (
        "Sin titular legible al instante",
        "Si todo el mensaje vive en el copy escrito, en mobile se corta con «Ver más» antes "
        "de llegar al dato importante. Si el visual no grita el mensaje por sí solo, se "
        "pierde: el titular debe leerse sin tocar la pantalla.",
    ),
    (
        "Sin protagonista + sin contexto emocional",
        "Sin una persona y una emoción que sostengan la historia, todo lo demás se suma como "
        "una capa más de ruido.",
    ),
]
NO_TRACCION_CIERRE = (
    "El resultado: el cerebro recibe demasiada información, sin jerarquía, sin emoción, sin "
    "contraste y sin titular. Activa el modo «esto es institucional» y hace scroll; el "
    "contenido trasciende como algo administrativo y no heroico. No es que el trabajo sea "
    "malo — es que la presentación lo hace invisible. La ruta visual que sí funciona: "
    "Emoción real › Autoridad cercana › Evidencia tangible = PERCIBIDOS AL INSTANTE EN LOS "
    "PRIMEROS 3-5 SEGUNDOS."
)

LECTURA_TITULO = "Lectura del caso — por qué es la medalla del período"
REFERENCIAS_TITULO = "REFERENCIAS DE LA MEJOR MEDALLA RECIENTE"


# ══════════════════════════════════════════════════
# Helpers de cálculo
# ══════════════════════════════════════════════════

REACCIONES_POSITIVAS = ("loves_count", "cares_count", "wows_count")
REACCIONES_NEGATIVAS = ("angrys_count", "sads_count")
REACCIONES_TODAS = (
    "likes_count", "loves_count", "cares_count", "hahas_count",
    "wows_count", "sads_count", "angrys_count",
)


def _i(post: dict, key: str) -> int:
    try:
        return int(post.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _fmt(n) -> str:
    try:
        return f"{int(round(float(n))):,}".replace(",", "\u202f")
    except (TypeError, ValueError):
        return str(n)


def total_reacciones(post: dict) -> int:
    return sum(_i(post, k) for k in REACCIONES_TODAS)


def metricas_post(post: dict) -> dict:
    """Calcula las métricas derivadas de un post para el informe."""
    positivas = sum(_i(post, k) for k in REACCIONES_POSITIVAS)
    negativas = sum(_i(post, k) for k in REACCIONES_NEGATIVAS)
    total_reac = total_reacciones(post)
    comentarios = _i(post, "comments_count")
    compartidos = _i(post, "shares_count")
    engagement = total_reac + comentarios + compartidos
    base = total_reac if total_reac > 0 else engagement
    # Mismo razonamiento del documento: si las reacciones son el 5% del total
    # de impresiones, impresiones = reacciones / 0.05 (conservador). Al 2% de
    # enganche, impresiones = reacciones / 0.02 (optimista).
    impresiones_conservador = round(base / 0.05) if base else 0
    impresiones_optimista = round(base / 0.02) if base else 0
    return {
        "positivas": positivas,
        "negativas": negativas,
        "total_reacciones": total_reac,
        "comentarios": comentarios,
        "compartidos": compartidos,
        "engagement": engagement,
        "impresiones_conservador": impresiones_conservador,
        "impresiones_optimista": impresiones_optimista,
    }


def _topicos_txt(topicos: list) -> str:
    if not topicos:
        return ""
    if len(topicos) == 1:
        return f", abarcando temas como {topicos[0]}"
    return f", abarcando temas como {', '.join(topicos[:-1])} y {topicos[-1]}"


def _descripcion_post(post: dict, contexto: dict, limite: int = 220) -> str:
    desc = (
        contexto.get("descripcion_post")
        or (post.get("message") or "").strip()
    )
    if not desc:
        return ""
    desc = " ".join(str(desc).split())
    if len(desc) > limite:
        desc = desc[: limite - 1].rstrip() + "\u2026"
    return desc


def _parrafo_alcance_plantilla(post: dict, contexto: dict, m: dict) -> str:
    """Párrafo de alcance construido con los DATOS REALES del post (respaldo sin LLM).

    Ya no asume ningún caso por defecto (antes caía siempre al caso del FAS) ni
    inventa cifras (ADS, 800k): todo lo cuantitativo sale de las métricas del post.
    """
    periodo = contexto.get("periodo_label") or "el \u00faltimo per\u00edodo"
    alcance_temas = _topicos_txt(contexto.get("topicos") or [])
    balance = (
        "m\u00e1s reacciones negativas que positivas"
        if m["negativas"] > m["positivas"]
        else "m\u00e1s reacciones positivas que negativas"
    )
    descripcion = _descripcion_post(post, contexto) or "el caso m\u00e1s destacado del per\u00edodo"
    reac = _fmt(m["total_reacciones"]) if m["total_reacciones"] else "las reacciones del post"
    return (
        f"Durante {periodo} se publicaron contenidos de alto alcance{alcance_temas}. "
        f"El balance de reacciones mostr\u00f3 {balance}, una se\u00f1al a vigilar en la "
        f"percepci\u00f3n. El caso m\u00e1s destacado del per\u00edodo \u2014{descripcion}\u2014 fue el "
        f"contenido de mayor tracci\u00f3n positiva (la medalla del alcalde) y el que m\u00e1s "
        f"se prest\u00f3 a ser retomado de forma espont\u00e1nea por los medios. Estimaci\u00f3n de "
        f"alcance a partir de las reacciones registradas: si {reac} representan el 5% del "
        f"total de impresiones, equivalen a {_fmt(m['impresiones_conservador'])} "
        f"impresiones; con un enganche del 2% rondar\u00edan las "
        f"{_fmt(m['impresiones_optimista'])} impresiones. Las cifras provienen de los datos "
        f"del per\u00edodo cargados en el panel, sin inversi\u00f3n en pauta."
    )


def _lectura_caso_plantilla(post: dict, contexto: dict, m: dict) -> str:
    """Lectura del caso construida con los DATOS REALES del post (respaldo sin LLM).

    Describe la publicación medalla concreta del período y por qué fue la de mayor
    tracción, leída con la doctrina de la «prueba del dolor». NO usa ningún caso
    de ejemplo.
    """
    pagina = post.get("page_name") or "la p\u00e1gina oficial"
    desc = _descripcion_post(post, contexto, limite=300)
    if desc:
        base = f"La medalla del per\u00edodo corresponde a una publicaci\u00f3n de {pagina}: \u00ab{desc}\u00bb. "
    else:
        base = f"La medalla del per\u00edodo corresponde a una publicaci\u00f3n de {pagina}. "
    balance = (
        "con m\u00e1s reacciones positivas que negativas"
        if m["positivas"] >= m["negativas"]
        else "con un balance de reacciones que conviene vigilar"
    )
    cierre = (
        f"Reuni\u00f3 {_fmt(m['total_reacciones'])} reacciones, {_fmt(m['comentarios'])} "
        f"comentarios y {_fmt(m['compartidos'])} compartidos, {balance}, lo que la "
        f"convierte en el contenido de mayor tracci\u00f3n del per\u00edodo. Evaluada con la "
        f"prueba del dolor, su fuerza est\u00e1 en traducir el hecho de forma visual e "
        f"inmediata \u2014una emoci\u00f3n reconocible, la autoridad presente y una evidencia "
        f"tangible\u2014 sin depender del texto para entenderse."
    )
    return base + cierre


def _cargar_llm():
    """Importa (chat_texto, llm_disponible) tolerando ejecución como paquete o suelta."""
    try:
        from dashboard.llm_groq import chat_texto, llm_disponible
        return chat_texto, llm_disponible
    except Exception:
        try:
            from llm_groq import chat_texto, llm_disponible
            return chat_texto, llm_disponible
        except Exception:
            return None, None


def redactar_parrafo_ia(post: dict, contexto: dict, m: dict) -> str | None:
    """Pide al LLM un p\u00e1rrafo de alcance adaptado al post, en la misma voz.

    Devuelve None si el LLM no est\u00e1 disponible o falla (el caller usa la
    plantilla determinista como respaldo).
    """
    chat_texto, llm_disponible = _cargar_llm()
    if not chat_texto:
        return None
    try:
        if not llm_disponible():
            return None
    except Exception:
        return None

    plantilla = _parrafo_alcance_plantilla(post, contexto, m)
    prompt = (
        "Eres analista de comunicaci\u00f3n pol\u00edtica. Reescribe el siguiente p\u00e1rrafo de "
        "\u00abalcance destacado\u00bb para el informe de la \u00abmejor medalla reciente del alcalde\u00bb. "
        "Mant\u00e9n el mismo tono y l\u00ednea editorial (concepto de \u00abprueba del dolor\u00bb y de "
        "tracci\u00f3n positiva), conserva TODAS las cifras tal cual aparecen, usa "
        "EXCLUSIVAMENTE los datos de ESTA publicaci\u00f3n, no inventes datos y no menciones "
        "ejemplos de otros casos. Devuelve solo el p\u00e1rrafo, sin t\u00edtulos ni comillas.\n\n"
        "Datos del post medalla:\n"
        f"- Autor/p\u00e1gina: {post.get('page_name','')}\n"
        f"- Texto del post: {(post.get('message') or '')[:600]}\n"
        f"- Reacciones totales: {m['total_reacciones']} (positivas {m['positivas']}, "
        f"negativas {m['negativas']}), comentarios {m['comentarios']}, compartidos "
        f"{m['compartidos']}.\n"
        f"- Impresiones estimadas: {m['impresiones_conservador']} (5%) a "
        f"{m['impresiones_optimista']} (2%).\n\nP\u00e1rrafo base a reescribir:\n{plantilla}"
    )
    try:
        out = chat_texto(prompt, max_tokens=900, temperature=0.5)
        out = (out or "").strip()
        return out or None
    except Exception:
        return None


def redactar_lectura_caso_ia(post: dict, contexto: dict, m: dict) -> str | None:
    """Pide al LLM la \u00ablectura del caso\u00bb adaptada al post real del per\u00edodo.

    Devuelve None si el LLM no est\u00e1 disponible o falla (el caller usa la
    plantilla determinista como respaldo).
    """
    chat_texto, llm_disponible = _cargar_llm()
    if not chat_texto:
        return None
    try:
        if not llm_disponible():
            return None
    except Exception:
        return None

    plantilla = _lectura_caso_plantilla(post, contexto, m)
    prompt = (
        "Eres analista de comunicaci\u00f3n pol\u00edtica. Redacta la \u00ablectura del caso\u00bb de la "
        "mejor medalla reciente del alcalde: explica en 3 a 5 frases de qu\u00e9 trata la "
        "publicaci\u00f3n medalla de ESTE per\u00edodo y por qu\u00e9 fue el contenido de mayor "
        "tracci\u00f3n, evalu\u00e1ndola con la doctrina de la \u00abprueba del dolor\u00bb (emoci\u00f3n real, "
        "autoridad cercana, evidencia tangible). Usa EXCLUSIVAMENTE los datos de esta "
        "publicaci\u00f3n; no inventes hechos ni cifras y no menciones ejemplos de otros casos. "
        "Devuelve solo el texto, sin t\u00edtulos ni comillas.\n\n"
        f"- Autor/p\u00e1gina: {post.get('page_name','')}\n"
        f"- Texto del post: {(post.get('message') or '')[:600]}\n"
        f"- Reacciones totales: {m['total_reacciones']} (positivas {m['positivas']}, "
        f"negativas {m['negativas']}), comentarios {m['comentarios']}, compartidos "
        f"{m['compartidos']}.\n\nBorrador base:\n{plantilla}"
    )
    try:
        out = chat_texto(prompt, max_tokens=700, temperature=0.5)
        out = (out or "").strip()
        return out or None
    except Exception:
        return None


# ══════════════════════════════════════════════════
# Estilos
# ══════════════════════════════════════════════════

_TINTA = colors.HexColor("#0f172a")
_ACENTO = colors.HexColor("#b91c1c")
_GRIS = colors.HexColor("#475569")
_SUAVE = colors.HexColor("#e2e8f0")


def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=16, leading=20, textColor=_TINTA, spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=12, textColor=_GRIS, spaceAfter=10,
        ),
        "seccion": ParagraphStyle(
            "seccion", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=_ACENTO, spaceBefore=14,
            spaceAfter=6,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo", parent=base["Normal"], fontName="Helvetica",
            fontSize=10, leading=15, textColor=_TINTA, alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "item": ParagraphStyle(
            "item", parent=base["Normal"], fontName="Helvetica",
            fontSize=10, leading=14, textColor=_TINTA, alignment=TA_JUSTIFY,
        ),
        "igual": ParagraphStyle(
            "igual", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=12, leading=16, textColor=_ACENTO, spaceBefore=4,
            spaceAfter=8,
        ),
        "nota": ParagraphStyle(
            "nota", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=9, leading=13, textColor=_GRIS, spaceAfter=6,
        ),
        "enlace": ParagraphStyle(
            "enlace", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, leading=14, textColor=colors.HexColor("#1d4ed8"),
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.5, leading=10, textColor=_GRIS,
        ),
    }


def _kpi_tabla(post: dict, m: dict, S: dict) -> Table:
    def celda(valor, etiqueta):
        return [
            Paragraph(f"<b>{valor}</b>", ParagraphStyle(
                "kv", fontName="Helvetica-Bold", fontSize=14, leading=16,
                textColor=_TINTA, alignment=1)),
            Paragraph(etiqueta, ParagraphStyle(
                "kl", fontName="Helvetica", fontSize=7.5, leading=9,
                textColor=_GRIS, alignment=1)),
        ]
    datos = [
        celda(_fmt(m["total_reacciones"]), "REACCIONES"),
        celda(_fmt(m["comentarios"]), "COMENTARIOS"),
        celda(_fmt(m["compartidos"]), "COMPARTIDOS"),
        celda(_fmt(m["impresiones_conservador"]), "IMPRESIONES (EST.)"),
    ]
    fila_val = [d[0] for d in datos]
    fila_lab = [d[1] for d in datos]
    t = Table([fila_val, fila_lab], colWidths=[42 * mm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, _SUAVE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _SUAVE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _medios_tabla(medios: list, S: dict) -> Table:
    """Tabla de r\u00e9plicas en p\u00e1ginas externas: nombre, reacciones, comentarios y enlace."""
    def _h(txt):
        return Paragraph(f'<font color="#ffffff"><b>{escape(txt)}</b></font>', S["item"])

    filas = [[_h("Medio / p\u00e1gina externa"), _h("Reacciones"),
              _h("Comentarios"), _h("Enlace")]]
    tot_reac = 0
    tot_com = 0
    for med in medios:
        nombre = str(med.get("page_name") or med.get("nombre") or "\u2014")
        reac = int(med.get("total_reactions") or med.get("reacciones") or 0)
        com = int(med.get("comments_count") or med.get("comentarios") or 0)
        tot_reac += reac
        tot_com += com
        url = med.get("post_url") or med.get("url") or ""
        if url:
            url_s = escape(str(url))
            enlace = Paragraph(
                f'<a href="{url_s}" color="#1d4ed8">Ver publicaci\u00f3n</a>', S["enlace"])
        else:
            enlace = Paragraph("\u2014", S["enlace"])
        filas.append([
            Paragraph(escape(nombre), S["item"]),
            Paragraph(_fmt(reac), S["item"]),
            Paragraph(_fmt(com), S["item"]),
            enlace,
        ])
    # Fila de totales
    filas.append([
        Paragraph("<b>Total r\u00e9plicas</b>", S["item"]),
        Paragraph(f"<b>{_fmt(tot_reac)}</b>", S["item"]),
        Paragraph(f"<b>{_fmt(tot_com)}</b>", S["item"]),
        Paragraph(f"{len(medios)} medio(s)", S["enlace"]),
    ])
    t = Table(filas, colWidths=[70 * mm, 28 * mm, 28 * mm, 44 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _TINTA),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eef2f7")),
        ("BOX", (0, 0), (-1, -1), 0.5, _SUAVE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _SUAVE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _imagen_flowable(ruta: str, max_ancho_mm: float = 170, max_alto_mm: float = 110):
    try:
        from PIL import Image as PILImage
        with PILImage.open(ruta) as im:
            w, h = im.size
        if not w or not h:
            return None
        max_w = max_ancho_mm * mm
        max_h = max_alto_mm * mm
        ratio = min(max_w / w, max_h / h)
        return RLImage(ruta, width=w * ratio, height=h * ratio)
    except Exception:
        return None


# ══════════════════════════════════════════════════
# Generador principal
# ══════════════════════════════════════════════════

def generar_pdf_medalla(
    post: dict,
    contexto: dict | None = None,
    imagenes: list | None = None,
    usar_ia: bool = True,
) -> bytes:
    """Genera el informe PDF de la medalla y devuelve los bytes.

    post      : fila de fb_posts (dict) del post medalla.
    contexto  : datos adaptativos (periodo_label, topicos, enlaces, descripcion_post,
                parrafo_alcance/lectura_caso ya redactados, etc.).
    imagenes  : rutas de capturas guardadas del post para incrustar.
    usar_ia   : si True intenta redactar el alcance y la lectura con el LLM.
    """
    contexto = dict(contexto or {})
    imagenes = list(imagenes or [])
    S = _estilos()
    m = metricas_post(post)

    # P\u00e1rrafo de alcance (h\u00edbrido: IA si hay, si no plantilla determinista).
    parrafo = contexto.get("parrafo_alcance")
    if not parrafo and usar_ia:
        parrafo = redactar_parrafo_ia(post, contexto, m)
    if not parrafo:
        parrafo = _parrafo_alcance_plantilla(post, contexto, m)

    # Lectura del caso adaptada al post real (reemplaza la antigua conclusi\u00f3n fija).
    lectura = contexto.get("lectura_caso")
    if not lectura and usar_ia:
        lectura = redactar_lectura_caso_ia(post, contexto, m)
    if not lectura:
        lectura = _lectura_caso_plantilla(post, contexto, m)

    enlaces = contexto.get("enlaces") or []
    if not enlaces and post.get("post_url"):
        enlaces = [post["post_url"]]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=16 * mm,
        title="Informe \u2014 Mejor medalla reciente",
        author="PANEL\u00b7SANTA ANA",
    )
    el = []
    el.append(Paragraph(escape(TITULO), S["titulo"]))
    periodo = contexto.get("periodo_label") or "per\u00edodo vigente"
    generado = datetime.now().strftime("%d/%m/%Y %H:%M")
    el.append(Paragraph(
        f"Per\u00edodo: {escape(str(periodo))} \u2022 Generado: {generado}", S["subtitulo"]))
    el.append(HRFlowable(width="100%", thickness=1, color=_SUAVE))
    el.append(Spacer(1, 6))

    # Alcance + KPIs (adaptativo)
    el.append(Paragraph(escape(parrafo), S["cuerpo"]))
    el.append(_kpi_tabla(post, m, S))
    el.append(Spacer(1, 10))

    # Lectura del caso (adaptativo)
    el.append(Paragraph(LECTURA_TITULO, S["seccion"]))
    el.append(Paragraph(escape(lectura), S["cuerpo"]))

    # Repercusi\u00f3n en medios / p\u00e1ginas externas — din\u00e1mica
    medios = contexto.get("medios") or []
    el.append(Paragraph("Repercusi\u00f3n en medios y p\u00e1ginas externas", S["seccion"]))
    el.append(Paragraph(
        "N\u00fameros que gener\u00f3 la r\u00e9plica de la medalla en cada p\u00e1gina externa:",
        S["subtitulo"]))
    if medios:
        el.append(_medios_tabla(medios, S))
    else:
        el.append(Paragraph(
            "Sin r\u00e9plicas externas registradas para este post en el per\u00edodo.",
            S["nota"]))
    el.append(Spacer(1, 4))

    # Doctrina (prueba del dolor) — gen\u00e9rica/fija
    el.append(Paragraph(DOCTRINA_TITULO, S["seccion"]))
    el.append(Paragraph(escape(DOCTRINA_INTRO), S["cuerpo"]))
    el.append(Paragraph(escape(DOCTRINA_LEAD), S["cuerpo"]))
    items = [
        ListItem(Paragraph(f"<b>{escape(t)}</b> \u2014 {escape(d)}", S["item"]),
                 value=None, leftIndent=6)
        for t, d in DOCTRINA_ELEMENTOS
    ]
    el.append(ListFlowable(items, bulletType="bullet", start="square",
                           leftIndent=12, spaceAfter=6))
    el.append(Paragraph(escape(DOCTRINA_IGUAL), S["igual"]))
    el.append(Paragraph(escape(DOCTRINA_CIERRE), S["cuerpo"]))

    # Contenido que no traduce tracci\u00f3n — gen\u00e9rica/fija
    el.append(Paragraph(escape(NO_TRACCION_TITULO), S["seccion"]))
    pts = [
        ListItem(Paragraph(f"<b>{escape(t)}.</b> {escape(d)}", S["item"]),
                 leftIndent=6)
        for t, d in NO_TRACCION_PUNTOS
    ]
    el.append(ListFlowable(pts, bulletType="1", leftIndent=14, spaceAfter=6))
    el.append(Paragraph(escape(NO_TRACCION_CIERRE), S["cuerpo"]))

    # Referencias — din\u00e1micas
    el.append(Paragraph(escape(REFERENCIAS_TITULO), S["seccion"]))
    if enlaces:
        for url in enlaces:
            url_s = escape(str(url))
            el.append(Paragraph(
                f"\u2022 <a href=\"{url_s}\" color=\"#1d4ed8\">{url_s}</a>",
                S["enlace"]))
    else:
        el.append(Paragraph(
            "Sin enlaces de referencia registrados para este post.", S["nota"]))

    # Capturas embebidas (si se guardaron en la ingesta)
    if imagenes:
        el.append(Spacer(1, 8))
        el.append(Paragraph("Publicaci\u00f3n (capturas):", S["subtitulo"]))
        for ruta in imagenes:
            img = _imagen_flowable(ruta)
            if img is not None:
                el.append(img)
                el.append(Spacer(1, 6))

    doc.build(el, onFirstPage=_pie, onLaterPages=_pie)
    return buf.getvalue()


def _pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_GRIS)
    canvas.drawString(
        20 * mm, 10 * mm,
        "PANEL\u00b7SANTA ANA \u2014 Inteligencia Ciudadana \u00b7 Documento confidencial")
    canvas.drawRightString(190 * mm, 10 * mm, "P\u00e1g. %d" % doc.page)
    canvas.restoreState()
