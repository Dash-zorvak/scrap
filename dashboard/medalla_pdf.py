"""Generador del informe PDF «Mejor medalla reciente» para el dashboard del alcalde.

El documento sigue la ESTRUCTURA de la plantilla acordada (sin relleno, solo
información puntual), y se autollena con los datos reales del período:

  1. Recuadro de totales (reacciones/comentarios/compartidos/impacto total),
     sumando el post medalla + sus réplicas en medios («todas las publicaciones»).
  2. Tabla de publicaciones (medalla + cada medio) con Compartidos y Subtotal y
     nombre con hipervínculo.
  3. Párrafo de alcance + «Un número al que hay que prestarle atención» con la
     imagen del post.
  4. Conclusión «prueba del dolor»: mensaje corto + 3 elementos clave
     (Emoción real / Autoridad cercana / Evidencia tangible) adaptados al caso.
  5. Contenido que no traduce tracción (imágenes de 3 posts + anti-patrones).
  6. Referencias (enlaces de la medalla y los medios).

La parte interpretativa (mensaje corto, los 3 elementos, el medio que la retomó,
la comparación con otro alcalde) la propone la IA como BORRADOR y el analista la
edita en el panel; lo editado se pasa por `contexto['narrativa']`. Si no hay IA ni
edición, se usa un texto genérico determinista basado en los datos. El módulo NO
depende de Streamlit.
"""
from __future__ import annotations

import io
import json
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
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

# ═════════════════════════════════════
# Marco editorial GENÉRICO — doctrina reutilizable, SIN casos concretos
# ═════════════════════════════════════

TITULO = "ALCANCE DESTACADO Y PUNTOS SOBRE LA MEJOR MEDALLA RECIENTE DEL ALCALDE"

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
CONCLUSION_TITULO = "Conclusión"
NUMERO_TITULO = "Un número al que hay que prestarle atención"
REFERENCIAS_TITULO = "REFERENCIAS DE LA MEJOR MEDALLA RECIENTE"

# Claves de la narrativa adaptativa (lo que la IA propone y el analista edita).
NARRATIVA_CLAVES = (
    "mensaje_corto", "emocion_real", "autoridad_cercana",
    "evidencia_tangible", "titular", "medio_retomo", "comparacion",
)


# ═════════════════════════════════════
# Helpers de cálculo
# ═════════════════════════════════════

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


def _publicaciones_y_totales(post: dict, m: dict, medios: list) -> tuple:
    """Filas de la tabla de publicaciones (medalla + medios) y los totales.

    Los totales suman TODAS las publicaciones (la medalla y sus réplicas), tal
    como pide el recuadro de la plantilla. Las páginas externas no guardan
    compartidos, así que su columna queda en «—» y no infla el total.
    """
    rows = []
    rows.append({
        "nombre": post.get("page_name") or "Publicación medalla",
        "url": post.get("post_url") or "",
        "reac": m["total_reacciones"],
        "com": m["comentarios"],
        "comp": m["compartidos"],
        "comp_known": True,
        "medalla": True,
    })
    for med in (medios or []):
        r = int(med.get("total_reactions") or med.get("reacciones") or 0)
        c = int(med.get("comments_count") or med.get("comentarios") or 0)
        sh_raw = med.get("shares_count", med.get("compartidos"))
        comp_known = sh_raw is not None
        sh = int(sh_raw or 0)
        rows.append({
            "nombre": med.get("page_name") or med.get("nombre") or "Medio externo",
            "url": med.get("post_url") or med.get("url") or "",
            "reac": r, "com": c, "comp": sh,
            "comp_known": comp_known, "medalla": False,
        })
    for x in rows:
        x["sub"] = x["reac"] + x["com"] + x["comp"]
    tot = {
        "reac": sum(x["reac"] for x in rows),
        "com": sum(x["com"] for x in rows),
        "comp": sum(x["comp"] for x in rows),
    }
    tot["impacto"] = tot["reac"] + tot["com"] + tot["comp"]
    return rows, tot


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
    """Párrafo de alcance construido con los DATOS REALES del post (respaldo sin LLM)."""
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
    """Lectura del caso construida con los DATOS REALES del post (respaldo sin LLM)."""
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


def _narrativa_plantilla(post: dict, contexto: dict, m: dict) -> dict:
    """Borrador determinista (sin IA) de la narrativa adaptativa.

    Genérico pero NUNCA menciona un caso concreto: el mensaje corto sale del texto
    real del post y el resto reutiliza la doctrina de la «prueba del dolor».
    """
    mensaje = _descripcion_post(post, contexto, limite=90) or "la prueba del dolor"
    return {
        "mensaje_corto": mensaje,
        "emocion_real": DOCTRINA_ELEMENTOS[0][1],
        "autoridad_cercana": DOCTRINA_ELEMENTOS[1][1],
        "evidencia_tangible": DOCTRINA_ELEMENTOS[2][1],
        "titular": "",
        "medio_retomo": "",
        "comparacion": "",
    }


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
    """Pide al LLM un p\u00e1rrafo de alcance adaptado al post. None si no hay LLM."""
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
        out, _, _ = chat_texto(prompt, max_tokens=600, temperature=0.4, json=True)
        out = (out or "").strip()
        return out or None
    except Exception:
        return None


def redactar_lectura_caso_ia(post: dict, contexto: dict, m: dict) -> str | None:
    """Pide al LLM la \u00ablectura del caso\u00bb adaptada al post real. None si no hay LLM."""
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
        out, _, _ = chat_texto(prompt, max_tokens=700, temperature=0.5)
        out = (out or "").strip()
        return out or None
    except Exception:
        return None


def borrador_narrativa_ia(post: dict, contexto: dict, m: dict) -> dict | None:
    """Pide al LLM un BORRADOR JSON de la narrativa adaptativa. None si no hay LLM.

    Devuelve un dict con las NARRATIVA_CLAVES que el analista luego edita. El
    prompt prohíbe inventar hechos y mencionar otros casos; describe lo que se
    deduce del texto del post (no «ve» la imagen, así que se mantiene prudente).
    """
    chat_texto, llm_disponible = _cargar_llm()
    if not chat_texto:
        return None
    try:
        if not llm_disponible():
            return None
    except Exception:
        return None

    desc = _descripcion_post(post, contexto, limite=600)
    prompt = (
        "Eres analista de comunicaci\u00f3n pol\u00edtica. A partir del texto de la publicaci\u00f3n "
        "medalla del alcalde, propon un BORRADOR breve para el informe siguiendo la "
        "doctrina de la \u00abprueba del dolor\u00bb. Responde SOLO un objeto JSON con estas "
        "claves (texto corto en espa\u00f1ol, sin comillas internas):\n"
        "  mensaje_corto: en una frase, qu\u00e9 convierte de este caso (la \u00abprueba del dolor\u00bb).\n"
        "  emocion_real: la emoci\u00f3n genuina que transmite.\n"
        "  autoridad_cercana: c\u00f3mo se muestra la autoridad cercana (a partir del texto).\n"
        "  evidencia_tangible: la prueba concreta de que algo pas\u00f3.\n"
        "  titular: c\u00f3mo deber\u00eda leerse el titular al instante.\n"
        "  medio_retomo: nombre del medio que lo retom\u00f3 si se infiere del contexto; si no, deja \"\".\n"
        "Reglas: usa EXCLUSIVAMENTE los datos de ESTA publicaci\u00f3n, no inventes hechos ni "
        "cifras, no menciones ejemplos de otros casos ni otros alcaldes. Si algo no se puede "
        "deducir, deja la cadena vac\u00eda.\n\n"
        f"Autor/p\u00e1gina: {post.get('page_name','')}\n"
        f"Texto del post: {desc}\n"
        f"Reacciones {m['total_reacciones']} (positivas {m['positivas']}, negativas "
        f"{m['negativas']}), comentarios {m['comentarios']}, compartidos {m['compartidos']}."
    )
    try:
        out, _, _ = chat_texto(prompt, max_tokens=600, temperature=0.4, json=True)
        data = json.loads(out)
        if not isinstance(data, dict):
            return None
        limpio = {}
        for k in NARRATIVA_CLAVES:
            v = data.get(k)
            if isinstance(v, (str, int, float)):
                limpio[k] = str(v).strip()
        return limpio or None
    except Exception:
        return None


def borrador_narrativa(post: dict, contexto: dict | None = None,
                       usar_ia: bool = True) -> dict:
    """Borrador completo de la narrativa (IA + respaldo determinista).

    Lo usa el panel: genera un borrador editable. Siempre devuelve todas las
    NARRATIVA_CLAVES (las que la IA no aporte quedan con el respaldo genérico o
    vacías).
    """
    contexto = dict(contexto or {})
    m = metricas_post(post)
    base = _narrativa_plantilla(post, contexto, m)
    if usar_ia:
        ia = borrador_narrativa_ia(post, contexto, m)
        if ia:
            for k, v in ia.items():
                if v:
                    base[k] = v
    return base


def _resolver_narrativa(post: dict, contexto: dict, m: dict, usar_ia: bool) -> dict:
    """Narrativa final del PDF: lo editado por el analista manda; si no hay nada
    editado y hay IA, se pide un borrador; en último caso, respaldo determinista.
    """
    base = _narrativa_plantilla(post, contexto, m)
    dada = dict(contexto.get("narrativa") or {})
    tiene_edicion = any(
        dada.get(k) for k in ("mensaje_corto", "emocion_real",
                              "autoridad_cercana", "evidencia_tangible")
    )
    if not tiene_edicion and usar_ia:
        ia = borrador_narrativa_ia(post, contexto, m)
        if ia:
            for k, v in ia.items():
                if v:
                    base[k] = v
    for k, v in dada.items():
        if k in NARRATIVA_CLAVES and v:
            base[k] = str(v)
    return base


# ═════════════════════════════════════
# Estilos
# ═════════════════════════════════════

_TINTA = colors.HexColor("#0f172a")
_ACENTO = colors.HexColor("#b91c1c")
_GRIS = colors.HexColor("#475569")
_SUAVE = colors.HexColor("#e2e8f0")


def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=15, leading=19, textColor=_TINTA, spaceAfter=4,
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


def _kpi_tabla(tot: dict, S: dict) -> Table:
    """Recuadro de totales: Reacciones | Comentarios | Compartidos | Impacto total."""
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
        celda(_fmt(tot["reac"]), "TOTAL REACCIONES"),
        celda(_fmt(tot["com"]), "TOTAL COMENTARIOS"),
        celda(_fmt(tot["comp"]), "TOTAL COMPARTIDOS"),
        celda(_fmt(tot["impacto"]), "IMPACTO TOTAL"),
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


def _publicaciones_tabla(rows: list, S: dict) -> Table:
    """Tabla de publicaciones (medalla + medios): nombre con enlace, reacciones,
    comentarios, compartidos y subtotal, con una fila de totales."""
    def _h(txt):
        return Paragraph(f'<font color="#ffffff"><b>{escape(txt)}</b></font>', S["item"])

    filas = [[_h("Publicaci\u00f3n"), _h("Reacciones"), _h("Comentarios"),
              _h("Compartidos"), _h("Subtotal")]]
    for row in rows:
        nombre = escape(str(row["nombre"]))
        if row.get("medalla"):
            nombre = f"\U0001f3c5 {nombre}"
        url = row.get("url") or ""
        if url:
            celda_nombre = Paragraph(
                f'<a href="{escape(str(url))}" color="#1d4ed8">{nombre}</a>', S["item"])
        else:
            celda_nombre = Paragraph(nombre, S["item"])
        comp_txt = _fmt(row["comp"]) if row.get("comp_known") else "\u2014"
        filas.append([
            celda_nombre,
            Paragraph(_fmt(row["reac"]), S["item"]),
            Paragraph(_fmt(row["com"]), S["item"]),
            Paragraph(comp_txt, S["item"]),
            Paragraph(_fmt(row["sub"]), S["item"]),
        ])
    tot_reac = sum(r["reac"] for r in rows)
    tot_com = sum(r["com"] for r in rows)
    tot_comp = sum(r["comp"] for r in rows)
    filas.append([
        Paragraph("<b>Total</b>", S["item"]),
        Paragraph(f"<b>{_fmt(tot_reac)}</b>", S["item"]),
        Paragraph(f"<b>{_fmt(tot_com)}</b>", S["item"]),
        Paragraph(f"<b>{_fmt(tot_comp)}</b>", S["item"]),
        Paragraph(f"<b>{_fmt(tot_reac + tot_com + tot_comp)}</b>", S["item"]),
    ])
    t = Table(filas, colWidths=[62 * mm, 27 * mm, 27 * mm, 27 * mm, 27 * mm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _TINTA),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eef2f7")),
        ("BOX", (0, 0), (-1, -1), 0.5, _SUAVE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _SUAVE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
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


def _bloque_conclusion(n: dict, S: dict) -> list:
    """Flowables de la conclusión «prueba del dolor» con los 3 elementos adaptados."""
    out = []
    mensaje = n.get("mensaje_corto") or "la prueba del dolor"
    out.append(Paragraph(
        f"La mejor medalla reciente del alcalde es exactamente \u00ab{escape(mensaje)}\u00bb. "
        "El reto es orientar la narrativa para que refleje siempre la misma estructura: "
        "traducci\u00f3n visual inmediata de emoci\u00f3n y evidencia tangible.", S["cuerpo"]))
    out.append(Paragraph(escape(DOCTRINA_LEAD), S["cuerpo"]))
    evid = (n.get("evidencia_tangible") or "").strip()
    tit = (n.get("titular") or "").strip()
    if tit:
        evid = (evid + " " + ("El titular: " + tit if not tit.lower().startswith("el titular") else tit)).strip()
    elementos = [
        ("Emoci\u00f3n real", n.get("emocion_real") or DOCTRINA_ELEMENTOS[0][1]),
        ("Autoridad cercana", n.get("autoridad_cercana") or DOCTRINA_ELEMENTOS[1][1]),
        ("Evidencia tangible", evid or DOCTRINA_ELEMENTOS[2][1]),
    ]
    items = [
        ListItem(Paragraph(f"<b>{escape(t)}</b> \u2014 {escape(d)}", S["item"]), leftIndent=6)
        for t, d in elementos
    ]
    out.append(ListFlowable(items, bulletType="bullet", start="square",
                            leftIndent=12, spaceAfter=6))
    out.append(Paragraph(escape(DOCTRINA_IGUAL), S["igual"]))
    medio = (n.get("medio_retomo") or "").strip()
    if medio:
        out.append(Paragraph(
            f"Es una historia completa con h\u00e9roe, beneficiario y resultado. "
            f"{escape(medio)} la retom\u00f3 porque no hab\u00eda nada que construir: la historia "
            f"ya estaba lista.", S["cuerpo"]))
    else:
        out.append(Paragraph(
            "Es una historia completa con h\u00e9roe, beneficiario y resultado. Los medios la "
            "retoman porque no hay nada que construir: la historia ya est\u00e1 lista.",
            S["cuerpo"]))
    comp = (n.get("comparacion") or "").strip()
    if comp:
        out.append(Paragraph(escape(comp), S["nota"]))
    return out


# ═════════════════════════════════════
# Generador principal
# ═════════════════════════════════════

def generar_pdf_medalla(
    post: dict,
    contexto: dict | None = None,
    imagenes: list | None = None,
    usar_ia: bool = True,
) -> bytes:
    """Genera el informe PDF de la medalla y devuelve los bytes.

    post      : fila de fb_posts (dict) del post medalla.
    contexto  : datos adaptativos (periodo_label, topicos, enlaces, descripcion_post,
                medios, narrativa editable, no_traccion, etc.).
    imagenes  : rutas de capturas guardadas del post medalla para incrustar.
    usar_ia   : si True intenta redactar alcance/narrativa con el LLM.
    """
    contexto = dict(contexto or {})
    imagenes = list(imagenes or [])
    S = _estilos()
    m = metricas_post(post)
    medios = contexto.get("medios") or []

    parrafo = contexto.get("parrafo_alcance")
    if not parrafo and usar_ia:
        parrafo = redactar_parrafo_ia(post, contexto, m)
    if not parrafo:
        parrafo = _parrafo_alcance_plantilla(post, contexto, m)

    narrativa = _resolver_narrativa(post, contexto, m, usar_ia)

    enlaces = contexto.get("enlaces") or []
    if not enlaces and post.get("post_url"):
        enlaces = [post["post_url"]]

    rows, tot = _publicaciones_y_totales(post, m, medios)
    no_traccion = contexto.get("no_traccion") or []

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

    # 1) Recuadro de totales (todas las publicaciones)
    el.append(_kpi_tabla(tot, S))
    el.append(Paragraph(
        "Suma de todas las publicaciones (medalla + r\u00e9plicas en medios). "
        "Impacto total = reacciones + comentarios + compartidos.", S["nota"]))
    el.append(Spacer(1, 6))

    # 2) Tabla de publicaciones
    el.append(_publicaciones_tabla(rows, S))
    el.append(Spacer(1, 10))

    # 3) P\u00e1rrafo de alcance (adaptativo)
    el.append(Paragraph(escape(parrafo), S["cuerpo"]))

    # 4) Un n\u00famero al que hay que prestarle atenci\u00f3n + imagen del post
    el.append(Paragraph(escape(NUMERO_TITULO), S["seccion"]))
    el.append(Paragraph(
        f"Estimaci\u00f3n conservadora: ~{_fmt(m['impresiones_conservador'])} impresiones "
        "con las publicaciones m\u00e1s destacadas y sin inversi\u00f3n en pauta.", S["cuerpo"]))
    if imagenes:
        img = _imagen_flowable(imagenes[0])
        if img is not None:
            el.append(img)
            el.append(Spacer(1, 6))

    # 5) Conclusi\u00f3n — prueba del dolor (adaptativa, editable)
    el.append(Paragraph(escape(CONCLUSION_TITULO), S["seccion"]))
    el.extend(_bloque_conclusion(narrativa, S))

    # 6) Contenido que no traduce tracci\u00f3n (im\u00e1genes + anti-patrones gen\u00e9ricos)
    el.append(Paragraph(escape(NO_TRACCION_TITULO), S["seccion"]))
    for nt in no_traccion:
        cap = nt.get("page_name") or nt.get("nombre") or "Publicaci\u00f3n"
        el.append(Paragraph(f"<b>{escape(str(cap))}</b>", S["item"]))
        for ruta in (nt.get("imagenes") or [])[:1]:
            img = _imagen_flowable(ruta, max_alto_mm=70)
            if img is not None:
                el.append(img)
        el.append(Spacer(1, 4))
    pts = [
        ListItem(Paragraph(f"<b>{escape(t)}.</b> {escape(d)}", S["item"]), leftIndent=6)
        for t, d in NO_TRACCION_PUNTOS
    ]
    el.append(ListFlowable(pts, bulletType="1", leftIndent=14, spaceAfter=6))
    el.append(Paragraph(escape(NO_TRACCION_CIERRE), S["cuerpo"]))

    # 7) Referencias — din\u00e1micas
    el.append(Paragraph(escape(REFERENCIAS_TITULO), S["seccion"]))
    hubo_ref = False
    for url in enlaces:
        url_s = escape(str(url))
        el.append(Paragraph(
            f"\u2022 <a href=\"{url_s}\" color=\"#1d4ed8\">{url_s}</a>", S["enlace"]))
        hubo_ref = True
    for med in medios:
        u = med.get("post_url") or med.get("url")
        if u:
            u_s = escape(str(u))
            nombre = escape(str(med.get("page_name") or med.get("nombre") or "Medio"))
            el.append(Paragraph(
                f"\u2022 {nombre}: <a href=\"{u_s}\" color=\"#1d4ed8\">{u_s}</a>",
                S["enlace"]))
            hubo_ref = True
    if not hubo_ref:
        el.append(Paragraph("Sin enlaces de referencia registrados.", S["nota"]))
    for ruta in (imagenes[1:] if len(imagenes) > 1 else []):
        img = _imagen_flowable(ruta)
        if img is not None:
            el.append(Spacer(1, 6))
            el.append(img)

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
