"""Generador del informe PDF «Mejor medalla reciente» para el dashboard del alcalde.

Reproduce el documento editorial de la medalla con LAS MISMAS PALABRAS en su
marco fijo (doctrina «prueba del dolor» y los cuatro puntos de «contenido que no
traduce tracción») y ADAPTA en cada generación: el párrafo de alcance/impacto,
las cifras (reacciones, tasa, impresiones estimadas) y los enlaces de
referencia del post medalla. Si hay capturas guardadas del post, se incrustan.

El módulo NO depende de Streamlit. La redacción adaptativa usa el LLM de texto
(dashboard.llm_groq.chat_texto) cuando hay API key; si no, cae a una plantilla
local con las mismas frases del documento original rellenadas con los datos.
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
# Marco editorial FIJO — mismas palabras del documento original
# ══════════════════════════════════════════════════

TITULO = "ALCANCE DESTACADO Y PUNTOS SOBRE LA MEJOR MEDALLA RECIENTE DEL ALCALDE"

# Bloque «Conclusión» (doctrina prueba del dolor). Texto fijo, verbatim.
CONCLUSION_INTRO = (
    "La mejor medalla reciente del alcalde es exactamente la \u201cprueba del dolor\u201d de la "
    "que hablábamos. El reto: orientar la narrativa para que refleje la misma estructura "
    "siempre. Con una estrategia de contenido más consistente: traducción visual inmediata "
    "de emoción y evidencia tangible."
)
CONCLUSION_LEAD = "En una sola imagen se presentan 3 elementos clave:"
CONCLUSION_ELEMENTOS = [
    (
        "Emoción real",
        "la mujer llorando no actúa, eso no se fabrica y la gente lo siente.",
    ),
    (
        "Autoridad cercana",
        "el alcalde no está en un podio, está al lado de ella, con la mano encima, en el "
        "lugar de los hechos.",
    ),
    (
        "Evidencia tangible",
        "los sacos de comida apilados atrás son la prueba física de que algo concreto pasó, "
        "no solo palabras. El titular grande en rojo hace el resto: 300 perritos, un terreno "
        "donado.",
    ),
]
CONCLUSION_IGUAL = "= EXCELENCIA MEDI\u00c1TICA VISUAL"
CONCLUSION_CIERRE = (
    "Es una historia completa con héroe, beneficiario y resultado. ES Noticias la retomó "
    "porque no había nada que construir, la historia ya estaba lista para ellos: estructuraron "
    "la prueba del dolor."
)
CONCLUSION_NOTA = (
    "(Mario Durán tiene la mitad de seguidores que el alcalde Acevedo y tiene mucha más "
    "interacción en cada publicación porque cada contenido sigue la misma línea editorial: "
    "prueba del dolor.)"
)

# Sección «Contenido que no traduce tracción». Texto fijo, verbatim.
NO_TRACCION_TITULO = "CONTENIDO QUE NO TRADUCE TRACCI\u00d3N A PESAR DE EXCELENTES IM\u00c1GENES"
NO_TRACCION_PUNTOS = [
    (
        "Sin antes y después",
        "El lodo limpio no prueba nada si no viste el lodo sucio primero. La grúa instalada no "
        "impacta si no viste el hueco vacío. El cerebro necesita el contraste para sentir el "
        "logro. Sin el \u201cantes\u201d, el \u201cdespu\u00e9s\u201d no existe emocionalmente.",
    ),
    (
        "Collage de imágenes = atención dividida",
        "La foto de los perritos era UNA imagen, un solo punto de entrada visual. Estos posts "
        "tienen 3, 4, hasta 10 fotos. El ojo no sabe dónde pararse, no se ancla en nada, y en "
        "3 segundos ya pasó de largo.",
    ),
    (
        "Sin titular legible al instante",
        "Todo el texto está en el copy escrito, no en la imagen. En mobile, ese texto se corta "
        "con \u201cVer m\u00e1s\u201d antes de llegar al dato importante. Si el visual no grita el "
        "mensaje solo, perdiste. La foto de los perritos tenía el titular encima en letras "
        "grandes \u2014 se leía sin tocar la pantalla.",
    ),
    (
        "Sin protagonista + sin contexto emocional",
        "Ya lo dijimos, pero suma a todo lo anterior. Es la cuarta capa de ruido.",
    ),
]
NO_TRACCION_CIERRE = (
    "El resultado: el cerebro recibe demasiada información, sin jerarquía, sin emoción, sin "
    "contraste, sin titular. Activa el modo \u201cesto es institucional\u201d y hace scroll. "
    "Trasciende como algo administrativo y no heroico. No es que el trabajo sea malo \u2014 es "
    "que la presentación lo hace invisible. La ruta visual: prueba del dolor. Emoción real "
    "\u203a Autoridad cercana \u203a Evidencia tangible = PERCIBIDOS AL INSTANTE EN LOS "
    "PRIMEROS 3-5 SEGUNDOS."
)

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


def _parrafo_alcance_plantilla(post: dict, contexto: dict, m: dict) -> str:
    """Párrafo de alcance con las mismas frases del documento, rellenado con datos.

    Se usa cuando no hay LLM disponible (respaldo determinista).
    """
    periodo = contexto.get("periodo_label") or "el \u00faltimo per\u00edodo"
    topicos = contexto.get("topicos") or [
        "el apoyo al Club FAS", "intervenciones en calles",
        "anuncios institucionales relevantes",
    ]
    topicos_txt = ", ".join(topicos[:-1]) + " y " + topicos[-1] if len(topicos) > 1 else topicos[0]
    balance = (
        "m\u00e1s reacciones negativas que positivas"
        if m["negativas"] > m["positivas"]
        else "m\u00e1s reacciones positivas que negativas"
    )
    descripcion = (
        contexto.get("descripcion_post")
        or (post.get("message") or "").strip()
        or "el caso m\u00e1s destacado positivo del per\u00edodo"
    )
    if len(descripcion) > 220:
        descripcion = descripcion[:217].rstrip() + "\u2026"
    reac = _fmt(m["total_reacciones"]) if m["total_reacciones"] else "las reacciones del post"
    return (
        f"Durante {periodo} se publicaron contenidos de alto alcance, abarcando temas como "
        f"{topicos_txt}. El balance de data mostr\u00f3 {balance}, lo que representa una se\u00f1al "
        f"a vigilar en la percepci\u00f3n. Sin embargo, el dato m\u00e1s relevante del per\u00edodo: la "
        f"Alcald\u00eda no invirti\u00f3 un solo d\u00f3lar en ADS. El caso m\u00e1s destacado positivo \u2014"
        f"{descripcion}\u2014 fue retomado de forma espont\u00e1nea por medios de comunicaci\u00f3n, "
        f"convirti\u00e9ndose en el contenido de mayor tracci\u00f3n positiva (la medalla del alcalde) "
        f"del per\u00edodo. Las tasas de reacci\u00f3n se ubican del 5% al 10% sobre el total de "
        f"impresiones, por encima del promedio en gobierno local, donde suele estar por debajo "
        f"del 2%. Estimaci\u00f3n conservadora del alcance: si {reac} representan el 5% del total, "
        f"entonces {reac} \u00f7 0.05 = {_fmt(m['impresiones_conservador'])} impresiones; con un "
        f"enganche del 2% rondar\u00edan las {_fmt(m['impresiones_optimista'])} impresiones. "
        f"Estimamos un m\u00ednimo seguro cercano a las 800\u202f000 impresiones \u2014 casi un mill\u00f3n\u2014 "
        f"solo con las publicaciones m\u00e1s destacadas y cero inversi\u00f3n en pauta. Un n\u00famero al "
        f"que hay que prestarle atenci\u00f3n."
    )


def redactar_parrafo_ia(post: dict, contexto: dict, m: dict) -> str | None:
    """Pide al LLM un p\u00e1rrafo de alcance adaptado al post, en la misma voz.

    Devuelve None si el LLM no est\u00e1 disponible o falla (el caller usa la
    plantilla determinista como respaldo).
    """
    try:
        from dashboard.llm_groq import chat_texto, llm_disponible
    except Exception:
        try:
            from llm_groq import chat_texto, llm_disponible  # ejecuci\u00f3n directa
        except Exception:
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
        "Mant\u00e9n EXACTAMENTE el mismo tono, estructura y l\u00ednea editorial (concepto de "
        "\u00abprueba del dolor\u00bb y de tracci\u00f3n positiva), conserva TODAS las cifras tal cual "
        "aparecen y no inventes datos nuevos. Devuelve solo el p\u00e1rrafo, sin t\u00edtulos ni "
        "comillas.\n\nDatos del post medalla:\n"
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
                parrafo_alcance ya redactado, etc.).
    imagenes  : rutas de capturas guardadas del post para incrustar.
    usar_ia   : si True intenta redactar el p\u00e1rrafo de alcance con el LLM.
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

    # Alcance + KPIs
    el.append(Paragraph(escape(parrafo), S["cuerpo"]))
    el.append(_kpi_tabla(post, m, S))
    el.append(Spacer(1, 10))

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

    # Conclusi\u00f3n (doctrina prueba del dolor) — fija
    el.append(Paragraph("Conclusi\u00f3n", S["seccion"]))
    el.append(Paragraph(escape(CONCLUSION_INTRO), S["cuerpo"]))
    el.append(Paragraph(escape(CONCLUSION_LEAD), S["cuerpo"]))
    items = [
        ListItem(Paragraph(f"<b>{escape(t)}</b> \u2014 {escape(d)}", S["item"]),
                 value=None, leftIndent=6)
        for t, d in CONCLUSION_ELEMENTOS
    ]
    el.append(ListFlowable(items, bulletType="bullet", start="square",
                           leftIndent=12, spaceAfter=6))
    el.append(Paragraph(escape(CONCLUSION_IGUAL), S["igual"]))
    el.append(Paragraph(escape(CONCLUSION_CIERRE), S["cuerpo"]))
    el.append(Paragraph(escape(CONCLUSION_NOTA), S["nota"]))

    # Contenido que no traduce tracci\u00f3n — fija
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

    doc.build(buf and el, onFirstPage=_pie, onLaterPages=_pie)
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
