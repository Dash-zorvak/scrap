"""Funciones puras de calculo y derivacion de estilos.

Todas las formulas inline que estaban en app.py se centralizan aqui.
Cada funcion es pura (sin side effects, sin Streamlit, sin DB).

Bloque 6.1: Reimplementacion literal de §D-I segun 'Agente Analista — instrucciones'.
"""
import hashlib
import math
from datetime import datetime, timezone
from typing import Sequence


# ── Coercion helpers ──

def n(v, default=0.0):
    """Coerce any value to float safely."""
    if isinstance(v, dict):
        v = v.get("valor")
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def s(v, default="—"):
    """Coerce any value to string safely."""
    if v is None or v == "":
        return default
    return str(v)


def get(d, *keys, default="—"):
    """Safe nested dict traversal."""
    val = d
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
        if val is None:
            return default
    return val


def clamp(valor, vmin, vmax):
    """Clamp valor between vmin and vmax."""
    return max(vmin, min(vmax, valor))


# ── Color / style derivation ──

_PALETTE = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#34495e", "#e91e63", "#00bcd4",
]


def theme_color_hash(tema):
    """Deterministic color from theme name using MD5."""
    idx = int(hashlib.md5(str(tema).encode("utf-8")).hexdigest(), 16) % len(_PALETTE)
    return _PALETTE[idx]


def tendency_style(tend):
    """Tendency value -> (color, label)."""
    if tend > 0.1:
        return "var(--green)", f"↑ +{tend:.1f} pts"
    elif tend < -0.1:
        return "var(--red)", f"↓ {tend:.1f} pts"
    else:
        return "var(--amber)", "→ sin cambio"


def concentration_level_color(nivel):
    """Concentration level -> CSS color."""
    return {
        "dominado": "var(--red)",
        "liderado": "var(--amber)",
        "fragmentado": "var(--green)",
    }.get(nivel, "var(--accent)")


def tension_color(t):
    """Tension level (0-100) -> CSS color."""
    if t > 60:
        return "var(--red)"
    if t > 30:
        return "var(--amber)"
    return "var(--green)"


def thermo_position(tension):
    """Thermometer indicator left position (%)."""
    return min(tension, 97)


def intensity_color_and_sign(pct):
    """Intensity pct difference -> (color, formatted sign string)."""
    if pct > 15:
        col = "var(--red)"
    elif pct < -15:
        col = "var(--blue)"
    else:
        col = "var(--accent)"
    signo = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"
    return col, signo


def normalize_bar_widths(vol_hoy, promedio):
    """Normalize two bar values relative to max. Returns (w_hoy%, w_prom%)."""
    maxv = max(vol_hoy, promedio, 1)
    return vol_hoy / maxv * 100, promedio / maxv * 100


def priority_color(prioridad):
    """Recommendation priority -> CSS color."""
    return {
        "alta": "var(--red)",
        "media": "var(--amber)",
        "baja": "var(--green)",
    }.get(prioridad, "var(--fg-muted)")


def evolution_state_color(estado):
    """Topic evolution state -> CSS color."""
    return {
        "emergente": "var(--amber)",
        "en auge": "var(--green)",
        "en declive": "var(--red)",
        "en extincion": "var(--red)",
        "estable": "var(--fg-muted)",
    }.get(estado, "var(--fg-muted)")


def projection_color(proyeccion):
    """Propagation projection -> CSS color."""
    return {
        "acelerando": "var(--red)",
        "estable": "var(--accent)",
        "desacelerando": "var(--green)",
    }.get(proyeccion, "var(--fg-muted)")


def polarization_color(nivel):
    """Polarization level -> CSS color."""
    return {
        "confrontacion": "var(--red)",
        "dividida": "var(--amber)",
        "consenso": "var(--green)",
    }.get(nivel, "var(--accent)")


# ── Data extraction / sorting ──

def top_emotions(data_dict, n_top=3, prefix="pct_"):
    """Extract top N emotions from a dict with pct_* fields, sorted descending."""
    items = [
        (k.replace(prefix, "").replace("_", " ").title(), n(data_dict.get(k, 0)))
        for k in data_dict
        if k.startswith(prefix)
    ]
    items.sort(key=lambda t: t[1], reverse=True)
    return [(name, val) for name, val in items if val > 0][:n_top]


def engagement_inconsistency_badge(voz):
    """Check engagement vs sub-metrics consistency. Returns True if inconsistent."""
    eng = n(voz.get("engagement", 0))
    sum_sub = (
        n(voz.get("reacciones_totales", 0))
        + n(voz.get("comentarios_totales", 0))
        + n(voz.get("compartidos_totales", 0))
    )
    return eng > 0 and sum_sub == 0


def friccion_count_string(fr):
    """Format friction point count with percentage."""
    n_comp_total = n(fr.get("n_comentarios_total", 0))
    n_neg = n(fr.get("n_negativos", 0))
    if n_comp_total > 0:
        pct = n(fr.get("pct_del_total", 0))
        return f"{n_neg:,.0f} de {n_comp_total:,.0f} comentarios ({pct:.1f}%)"
    return f"{n_neg:,.0f} neg"


def share_totals_valid(ramas, tolerance=1.5):
    """Check if theme shares sum to 100% within tolerance."""
    suma = sum(
        get(r, "share", default=0) for r in ramas
        if isinstance(r, dict) and isinstance(get(r, "share", default=0), (int, float))
    )
    return abs(suma - 100) <= tolerance


def format_date_es(iso_date):
    """Format ISO date to Spanish string. Returns (full, short) tuple."""
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    meses_s = ["ene", "feb", "mar", "abr", "may", "jun",
               "jul", "ago", "sep", "oct", "nov", "dic"]
    dt = datetime.fromisoformat(iso_date)
    full = f"{dias[dt.weekday()]} {dt.day} de {meses[dt.month - 1]}, {dt.year}"
    short = f"{dt.day:02d} {meses_s[dt.month - 1]} {dt.year}"
    return full, short


def emotion_pcts_for_theme(emo_counts):
    """Given {emotion: count}, return {emotion: pct} for all valid emotions."""
    from dashboard.tema_taxonomia import EMOCIONES_VALIDAS
    total = sum(emo_counts.values()) or 1
    return {
        e: round(emo_counts.get(e, 0) / total * 100, 1)
        for e in EMOCIONES_VALIDAS
    }


def dominant_emotion(emo_counts):
    """Return the emotion with the highest count, or 'calma' if empty."""
    from dashboard.tema_taxonomia import EMOCIONES_VALIDAS
    if not emo_counts:
        return "calma"
    return max(EMOCIONES_VALIDAS, key=lambda e: emo_counts.get(e, 0))


# ═══════════════════════════════════════════════════════════════════════════════
# §D — Engagement, amor/enojo, engagementBasis
# ═══════════════════════════════════════════════════════════════════════════════


def engagement_rate_fb(likes, loves, cares, hahas, wows, sads, angrys,
                       comments, shares, views, n_posts=0):
    """§D — Engagement Rate Facebook.

    Fórmula literal: ER_fb = (reacciones + comentarios + compartidos) / vistas * 100
    reacciones = likes + loves + cares + hahas + wows + sads + angrys

    Si vistas > 0 → ER = interacciones / vistas * 100, basis = "views".
    Si vistas == 0 y n_posts > 0 → proxy = interacciones / n_posts, basis = "per_post".
    Si vistas == 0 y n_posts == 0 y eng > 0 → fallback: eng como valor absoluto,
        basis = "engagement_abs" (no es una tasa pero preserva la información).
    Si eng == 0 → 0.0, basis = "sin_datos".

    Retorna (er, basis_label).
    """
    reacciones = sum(n(v) for v in [likes, loves, cares, hahas, wows, sads, angrys])
    eng = reacciones + n(comments) + n(shares)
    vistas = n(views)
    posts = n(n_posts)
    if vistas > 0:
        return round(eng / vistas * 100, 2), "views"
    if posts > 0 and eng > 0:
        return round(eng / posts, 2), "per_post"
    if eng > 0:
        return round(eng, 2), "engagement_abs"
    return 0.0, "sin_datos"


def engagement_rate_tk(views, likes, shares, favorites, comments, n_videos=0):
    """§D — Engagement Rate TikTok.

    Fórmula literal: ER_tk = (likes + shares + favorites + comments) / views * 100

    Nota de consistencia: el documento fuente original de TikTok no incluye *100,
    pero por consistencia interna con Facebook (ambos expresan tasa como %),
    se aplica *100 a ambas plataformas. Documentado en PR Bloque 6.1.

    Si views > 0 → ER = interacciones / views * 100, basis = "views".
    Si views == 0 y n_videos > 0 → proxy = interacciones / n_videos, basis = "per_post".
    Si views == 0 y n_videos == 0 y eng > 0 → fallback: eng como valor absoluto,
        basis = "engagement_abs" (no es una tasa pero preserva la información).
    Si eng == 0 → 0.0, basis = "sin_datos".

    Retorna (er, basis_label).
    """
    eng = n(likes) + n(shares) + n(favorites) + n(comments)
    vistas = n(views)
    videos = n(n_videos)
    if vistas > 0:
        return round(eng / vistas * 100, 2), "views"
    if videos > 0 and eng > 0:
        return round(eng / videos, 2), "per_post"
    if eng > 0:
        return round(eng, 2), "engagement_abs"
    return 0.0, "sin_datos"


def engagement_rate_externos(total_reactions, comments_count, n_posts=0):
    """§D — Engagement Rate para fuentes Externas.

    Fórmula (decisión de ingeniería v2 — auditoría forense H1):
        ER_ext = (total_reactions + comments_count) / n_posts

    Nota: la fuente de datos Externos no provee vistas/impresiones,
    por lo que se usa un proxy por post. Esta métrica es separada e
    independiente del ER Oficial (FB+TK). No deben promediarse.

    Si n_posts > 0 → ER = eng / n_posts, basis = "per_post".
    Si n_posts == 0 y eng > 0 → fallback: eng como valor absoluto,
        basis = "engagement_abs".
    Si eng == 0 → 0.0, basis = "sin_datos".

    Retorna (er, basis_label).
    """
    eng = n(total_reactions) + n(comments_count)
    posts = n(n_posts)
    if posts > 0:
        return round(eng / posts, 2), "per_post"
    if eng > 0:
        return round(eng, 2), "engagement_abs"
    return 0.0, "sin_datos"


def ratio_amor_enojo_fb(likes, loves, cares, hahas, sads, angrys):
    """§D — Ratio amor/enojo Facebook.

    R = (likes + loves + cares) / (angrys + sads + hahas)

    Si denominador == 0 → infinito representado como 999.0.
    """
    amor = n(likes) + n(loves) + n(cares)
    enojo = n(angrys) + n(sads) + n(hahas)
    if enojo == 0:
        return 999.0 if amor > 0 else 0.0
    return round(amor / enojo, 2)


def reacciones_positivas_fb(likes, loves, cares):
    """§D — Conteo de reacciones positivas Facebook."""
    return sum(n(v) for v in [likes, loves, cares])


def reacciones_negativas_fb(angrys, sads, hahas):
    """§D — Conteo de reacciones negativas Facebook."""
    return sum(n(v) for v in [angrys, sads, hahas])


def interacciones_fb(likes, loves, cares, hahas, wows, sads, angrys,
                     comments, shares):
    """§D — Total de interacciones FB = reacciones + comments + shares."""
    reacciones = sum(n(v) for v in [likes, loves, cares, hahas, wows, sads, angrys])
    return reacciones + n(comments) + n(shares)


# ═══════════════════════════════════════════════════════════════════════════════
# §E — Reacciones: net_sentiment, controversy, effectiveness, approval, NSI, risk
# ═══════════════════════════════════════════════════════════════════════════════


def net_sentiment_reacciones(likes, loves, cares, hahas, wows, sads, angrys):
    """§E — Net Sentiment basado en reacciones de Facebook.

    Fórmula literal:
        negativas = angrys + sads + hahas
        total_reactions = likes + loves + cares + wows + hahas + sads + angrys
        net_sentiment = (likes + loves + cares - negativas) / total_reactions

    Nota: wows se incluyen en el total como reacción neutra (no positiva
    ni negativa). Decisión de ingeniería v2 — auditoría forense H6.

    Rango: -1 a +1. Métrica separada de NSI (que usa posts).
    """
    amor = n(likes) + n(loves) + n(cares)
    negativas = n(angrys) + n(sads) + n(hahas)
    total_reactions = amor + n(wows) + negativas
    if total_reactions == 0:
        return 0.0
    return round((amor - negativas) / total_reactions, 4)


def controversy_reacciones(likes, loves, cares, hahas, wows, sads, angrys):
    """§E — Controversy basada en reacciones de Facebook.

    Fórmula literal:
        negativas = angrys + sads + hahas
        total_reactions = likes + loves + cares + wows + hahas + sads + angrys
        controversy = negativas / total_reactions

    Nota: wows se incluyen en el total como reacción neutra.
    Decisión de ingeniería v2 — auditoría forense H6.

    Rango: 0 a 1.
    """
    negativas = n(angrys) + n(sads) + n(hahas)
    amor = n(likes) + n(loves) + n(cares)
    total_reactions = amor + n(wows) + negativas
    if total_reactions == 0:
        return 0.0
    return round(negativas / total_reactions, 4)


def effectiveness_reacciones(likes, loves, cares, hahas, wows, sads, angrys):
    """§E — Effectiveness basada en reacciones de Facebook.

    Fórmula literal:
        effectiveness = (likes + loves + cares) / total_reactions

    Nota: wows se incluyen en el total como reacción neutra.
    Decisión de ingeniería v2 — auditoría forense H6.

    Rango: 0 a 1. Proporción de reacciones positivas sobre el total.
    """
    amor = n(likes) + n(loves) + n(cares)
    negativas = n(angrys) + n(sads) + n(hahas)
    total_reactions = amor + n(wows) + negativas
    if total_reactions == 0:
        return 0.0
    return round(amor / total_reactions, 4)


def approval_pct_reacciones(likes, loves, cares, hahas, wows, sads, angrys):
    """§E — Aprobación % basada en reacciones de Facebook.

    Fórmula literal:
        aprobacion% = (likes + loves + cares) / max(total_reactions, 1) * 100

    Nota: wows se incluyen en el total como reacción neutra.
    Decisión de ingeniería v2 — auditoría forense H6.

    Rango: 0 a 100.
    """
    amor = n(likes) + n(loves) + n(cares)
    negativas = n(angrys) + n(sads) + n(hahas)
    total_reactions = amor + n(wows) + negativas
    return round(amor / max(total_reactions, 1) * 100, 1)


def rejection_pct_reacciones(likes, loves, cares, hahas, wows, sads, angrys):
    """§E — Rechazo % basada en reacciones de Facebook.

    Fórmula literal:
        rechazo% = negativas / max(total_reactions, 1) * 100

    Nota: wows se incluyen en el total como reacción neutra.
    Decisión de ingeniería v2 — auditoría forense H6.

    Rango: 0 a 100.
    """
    negativas = n(angrys) + n(sads) + n(hahas)
    amor = n(likes) + n(loves) + n(cares)
    total_reactions = amor + n(wows) + negativas
    return round(negativas / max(total_reactions, 1) * 100, 1)


def net_sentiment_index(n_positivos, n_negativos, n_total):
    """§E — Net Sentiment Index (NSI) basado en posts.

    Fórmula literal:
        nsi = ((posts_positivos - posts_negativos) / total_posts) * 100

    Rango: -100 a +100. Esta es la métrica de sentimiento por posts,
    distinta de net_sentiment_reacciones que usa reacciones de FB.
    """
    total = n(n_total)
    if total == 0:
        return 0.0
    return round((n(n_positivos) - n(n_negativos)) / total * 100, 1)


def nsi_deviation(nsi_value):
    """§E — NSI Deviation.

    Fórmula literal:
        nsi_deviation = max(0, (50 - nsi) / 100)

    Cuanto más bajo el NSI (más negativo), mayor la desviación.
    Rango: 0 a 0.5+ (cuando nsi=-50 → deviation=1.0).
    """
    return max(0, (50 - n(nsi_value)) / 100)


def vol_factor(total_posts):
    """§E — Volume Factor.

    Fórmula literal:
        vol_factor = min(2.0, 1.0 + total_posts / 1000)

    Factor de escala por volumen de posts. Mínimo 1.0, máximo 2.0.
    """
    return min(2.0, 1.0 + n(total_posts) / 1000)


def risk_reputacional(nsi_value, max_topic_controversy, vf):
    """§E — Risk Reputacional.

    Fórmula (decisión de ingeniería v2 — auditoría forense H5):
        riskReputacional = clamp(
            (max_topic_controversy * 0.50 + nsi_deviation * 0.50) * vol_factor,
            0, 1
        )

    Donde:
        - max_topic_controversy: la controversia (negativas/reacciones) más alta
          entre todos los temas del período (0 a 1).
        - nsi_deviation = max(0, (50 - nsi) / 100)
        - vol_factor = min(2.0, 1.0 + total_posts / 1000)

    Cambio vs. v1: se eliminó el factor *10 sobre max_topic_controversy
    que saturaba el índice con ~20% de controversia. La fórmula v1 no
    estaba documentada en ningún documento metodológico oficial
    (011_POPULARIDAD_DIGITAL.md, 012_RIESGO_DIGITAL.md solo describen
    la metodología de forma genérica; 028_FORMULA_REFERENCE.md es un
    documento de gobernanza sin fórmulas concretas). Esta nueva versión
    asigna peso igualitario (50/50) a controversia y desviación NSI,
    con vol_factor como amplificador (1x a 2x).

    Rango: 0 a 1.
    """
    dev = nsi_deviation(nsi_value)
    raw = (n(max_topic_controversy) * 0.50 + dev * 0.50) * n(vf)
    return round(clamp(raw, 0, 1), 4)


# ═══════════════════════════════════════════════════════════════════════════════
# §F — Alertas (ICI, SDI, EFI, TAI, ZDI) con cooldown y series de tiempo
# ═══════════════════════════════════════════════════════════════════════════════


# Sensibilidad temática ajustada: bases por tema (rangos del documento)
TOPIC_SENSITIVITY_BASES = {
    "corrupcion": 1.45,
    "soborno": 1.45,
    "malversacion": 1.45,
    "seguridad": 1.35,
    "delincuencia": 1.35,
    "servicios_basicos": 1.05,
    "educacion": 0.8,
    "ambiente": 0.8,
    "cultura": 0.8,
    "deportes": 0.8,
}

# Cooldowns en días por tipo de alerta
COOLDOWN_DAYS = {
    "ICI": 3,
    "SDI": 7,
    "EFI": 7,
    "TAI": 3,
    "ZDI": 7,
}


def calcular_sensibilidad_tema(tema, base_sensibilidad, cv_28d=0, velocidad=0):
    """§F — Sensibilidad temática ajustada.

    Fórmula literal:
        ajustada = base * (1 + min(cv_28d * 0.3, 0.5)) * (1 + min(|velocidad| * 0.2, 0.4))
        acotado a [0.5, 2.0]

    Args:
        tema: nombre del tema para buscar base en TOPIC_SENSITIVITY_BASES.
        base_sensibilidad: valor base si el tema no está en el diccionario.
        cv_28d: coeficiente de variación de 28 días del tema.
        velocidad: velocidad de cambio reciente del tema.
    """
    base = TOPIC_SENSITIVITY_BASES.get(tema, base_sensibilidad)
    factor_cv = min(cv_28d * 0.3, 0.5)
    factor_vel = min(abs(velocidad) * 0.2, 0.4)
    ajustada = base * (1 + factor_cv) * (1 + factor_vel)
    return clamp(ajustada, 0.5, 2.0)


def calcular_sensibilidad_para_alertas(tema, monthly_theme_controversy, fecha_hasta):
    """§F — Calcula sensibilidad ajustada para un tema específico.

    Deriva cv_28d y velocidad de la serie histórica mensual de controversia
    por tema (monthly_theme_controversy de get_fb_monthly_theme_controversy).

    cv_28d = desviación estándar / media de los valores de controversia
             del tema en los últimos 6 meses (aproximación a 28 días * 6).
    velocidad = (mes_actual - mes_anterior) / max(|mes_anterior|, 0.01).
        Si solo hay 1 mes de datos para el tema, velocidad = 0.

    Args:
        tema: nombre del tema a buscar.
        monthly_theme_controversy: lista de dicts [{mes, tema, controversy, n_posts}].
        fecha_hasta: ISO date del fin del período (para filtrar meses anteriores).

    Returns:
        float: sensibilidad ajustada entre 0.5 y 2.0.
    """
    meses_tema = [
        r["controversy"] for r in monthly_theme_controversy
        if r["tema"] == tema and r["n_posts"] >= 2
    ]
    if not meses_tema:
        return calcular_sensibilidad_tema(tema, 1.0, cv_28d=0, velocidad=0)

    cv_28d = 0.0
    if len(meses_tema) >= 2:
        media_c = sum(meses_tema) / len(meses_tema)
        if media_c > 0:
            var_c = sum((v - media_c) ** 2 for v in meses_tema) / len(meses_tema)
            cv_28d = math.sqrt(var_c) / media_c

    velocidad = 0.0
    if len(meses_tema) >= 2:
        actual = meses_tema[-1]
        previo = meses_tema[-2]
        velocidad = (actual - previo) / max(abs(previo), 0.01)

    return calcular_sensibilidad_tema(tema, 1.0, cv_28d=cv_28d, velocidad=velocidad)


def _zscore(valor, media, desviacion):
    """Calcula z-score. Retorna 0 si desviación es 0."""
    if desviacion == 0:
        return 0.0
    return (valor - media) / desviacion


def detectar_ici(controversia_actual, historial_controversia, umbral_base=2.0):
    """§F — ICI: Intensidad Conversacional basada en series de tiempo.

    Fórmula literal:
        z-score de la controversia del período actual contra media/desviación
        de períodos mensuales previos (mínimo 4 meses de historia).
        Alerta si z > umbral_base (por defecto 2.0σ, ajustable por
        sensibilidad temática: umbral_base = 2.0 * sensibilidad_ajustada).
        Severidad fija en valores absolutos de z (independiente del umbral):
            z > 3.0 → severidad 4
            z > 2.5 → severidad 3
            otro (z > umbral_base) → severidad 2

    Args:
        controversia_actual: controversia del período actual (0-1).
        historial_controversia: lista de controversias mensuales previos.
        umbral_base: umbral de z-score ajustado por sensibilidad (default 2.0).

    Returns:
        dict con {tipo, severidad, valor, umbral, descripcion, enlaces_referencia}
        o None si no hay alerta.
    """
    if len(historial_controversia) < 4:
        return None
    media = sum(historial_controversia) / len(historial_controversia)
    varianza = sum((v - media) ** 2 for v in historial_controversia) / len(historial_controversia)
    desviacion = math.sqrt(varianza)
    z = _zscore(controversia_actual, media, desviacion)
    if z <= umbral_base:
        return None
    if z > 3.0:
        severidad = 4
    elif z > 2.5:
        severidad = 3
    else:
        severidad = 2
    return {
        "tipo": "ICI",
        "severidad": severidad,
        "valor": round(z, 3),
        "umbral": round(umbral_base, 3),
        "descripcion": (
            f"Intensidad conversacional alta: z-score={z:.2f}σ "
            f"(controversia actual={controversia_actual:.3f}, "
            f"media histórica={media:.3f}, umbral={umbral_base:.2f}σ)"
        ),
        "enlaces_referencia": [],
    }


def detectar_sdi(sentimiento_neto_actual, sentimiento_neto_previo):
    """§F — SDI: Sentimiento Dominante Individual.

    Fórmula literal:
        SDI = (sentimiento_neto_actual - sentimiento_neto_previo)
              / max(|sentimiento_neto_previo|, 0.01)
        Alerta si SDI ≤ -0.20.

    Args:
        sentimiento_neto_actual: NSI del período actual.
        sentimiento_neto_previo: NSI del período previo.

    Returns:
        dict o None.
    """
    denominador = max(abs(n(sentimiento_neto_previo)), 0.01)
    sdi = (n(sentimiento_neto_actual) - n(sentimiento_neto_previo)) / denominador
    if sdi > -0.20:
        return None
    severidad = 3 if sdi <= -0.50 else 2
    return {
        "tipo": "SDI",
        "severidad": severidad,
        "valor": round(sdi, 4),
        "umbral": -0.20,
        "descripcion": (
            f"Caída de sentimiento: SDI={sdi:.3f} "
            f"(actual={sentimiento_neto_actual:.1f}, previo={sentimiento_neto_previo:.1f})"
        ),
        "enlaces_referencia": [],
    }


def detectar_efi(er_actual, er_previo, total_reacciones):
    """§F — EFI: Emociones Fuertes Individuales.

    Fórmula literal:
        EFI = (ER_actual - ER_previo) / max(ER_previo, 0.001)
        Alerta si EFI ≤ -0.30 y hay al menos 30 reacciones.

    Args:
        er_actual: engagement rate del período actual.
        er_previo: engagement rate del período previo.
        total_reacciones: total de reacciones del período actual.

    Returns:
        dict o None.
    """
    if n(total_reacciones) < 30:
        return None
    denominador = max(n(er_previo), 0.001)
    efi = (n(er_actual) - n(er_previo)) / denominador
    if efi > -0.30:
        return None
    severidad = 3 if efi <= -0.50 else 2
    return {
        "tipo": "EFI",
        "severidad": severidad,
        "valor": round(efi, 4),
        "umbral": -0.30,
        "descripcion": (
            f"Caída de engagement: EFI={efi:.3f} "
            f"(ER actual={er_actual:.2f}, ER previo={er_previo:.2f}, "
            f"reacciones={total_reacciones})"
        ),
        "enlaces_referencia": [],
    }


def detectar_tai(ratio_enojo_tema, ratio_enojo_general, n_posts_tema, umbral_base=2.0):
    """§F — TAI: Tema Aislado de Interés.

    Fórmula literal:
        TAI = ratio_enojo_del_tema / ratio_enojo_general
        Alerta si TAI > umbral_base (por defecto 2.0, ajustable por
        sensibilidad temática: umbral_base = 2.0 * sensibilidad_ajustada),
        ratio_enojo_del_tema > 3%, y tema tiene ≥3 posts.

    Args:
        ratio_enojo_tema: proporción de enojo en posts de este tema (0-1).
        ratio_enojo_general: proporción de enojo general (0-1).
        n_posts_tema: número de posts de este tema.
        umbral_base: umbral ajustado por sensibilidad del tema (default 2.0).

    Returns:
        dict o None.
    """
    if n_posts_tema < 3 or ratio_enojo_tema <= 0.03:
        return None
    denom = max(n(ratio_enojo_general), 0.001)
    tai = n(ratio_enojo_tema) / denom
    if tai <= umbral_base:
        return None
    severidad = 3 if tai > 4.0 else 2
    return {
        "tipo": "TAI",
        "severidad": severidad,
        "valor": round(tai, 3),
        "umbral": round(umbral_base, 3),
        "descripcion": (
            f"Tema con enojo desproporcionado: TAI={tai:.2f} "
            f"(enojo tema={ratio_enojo_tema*100:.1f}%, "
            f"enojo general={ratio_enojo_general*100:.1f}%, "
            f"posts tema={n_posts_tema}, umbral={umbral_base:.2f})"
        ),
        "enlaces_referencia": [],
    }


def detectar_zdi(pct_negativos_zona, n_posts_zona):
    """§F — ZDI: Zona Dominante.

    Fórmula literal:
        Alerta si la tasa de publicaciones/comentarios negativos de una zona
        supera 25%, con al menos 3 publicaciones de esa zona.

    Args:
        pct_negativos_zona: porcentaje de negativos en la zona (0-100).
        n_posts_zona: número de posts/comentarios de esa zona.

    Returns:
        dict o None.
    """
    if n_posts_zona < 3 or n(pct_negativos_zona) <= 25.0:
        return None
    severidad = 3 if pct_negativos_zona > 50.0 else 2
    return {
        "tipo": "ZDI",
        "severidad": severidad,
        "valor": round(n(pct_negativos_zona), 1),
        "umbral": 25.0,
        "descripcion": (
            f"Zona con alta negatividad: {pct_negativos_zona:.1f}% negativos "
            f"(umbral: 25%, posts zona: {n_posts_zona})"
        ),
        "enlaces_referencia": [],
    }


def verificar_cooldown(fecha_alerta_anterior, fecha_actual, tipo_alerta):
    """Verifica si una alerta puede dispararse según su cooldown.

    Args:
        fecha_alerta_anterior: ISO timestamp de la última alerta del mismo tipo,
            o None si no hay alerta previa.
        fecha_actual: ISO timestamp actual.
        tipo_alerta: string ICI/SDI/EFI/TAI/ZDI.

    Returns:
        True si puede dispararse (cooldown expiró o no hay previa).
    """
    cooldown_dias = COOLDOWN_DAYS.get(tipo_alerta, 7)
    if fecha_alerta_anterior is None:
        return True
    try:
        anterior = datetime.fromisoformat(fecha_alerta_anterior.replace("Z", "+00:00"))
        actual = datetime.fromisoformat(fecha_actual.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return True
    if anterior.tzinfo is None:
        anterior = anterior.replace(tzinfo=timezone.utc)
    if actual.tzinfo is None:
        actual = actual.replace(tzinfo=timezone.utc)
    delta = actual - anterior
    return delta.days >= cooldown_dias


# ═══════════════════════════════════════════════════════════════════════════════
# §G — HHI (Herfindahl-Hirschman Index) de concentración temática
# ═══════════════════════════════════════════════════════════════════════════════


def calcular_hhi(shares: Sequence[float]):
    """§G — Herfindahl-Hirschman Index.

    HHI = Σ(share_i²)

    Donde share_i es la fracción (0-1) del tema i sobre el total.
    Los shares de entrada se esperan como porcentajes (0-100).
    Retorna HHI en escala 0-1 (dividido entre 10000 para normalizar).
    """
    total = sum(n(s) for s in shares)
    if total == 0:
        return 0.0
    hhi_raw = sum((n(s) / total) ** 2 for s in shares)
    return round(hhi_raw, 4)


# ═══════════════════════════════════════════════════════════════════════════════
# §H — Pulso IQ (7 dimensiones, pesos, plataforma, cuadrante)
# ═══════════════════════════════════════════════════════════════════════════════

# Pesos de las 7 dimensiones (suma = 6.0)
DIMENSION_WEIGHTS = {
    "aprobacion": 1.0,
    "conexion": 1.0,
    "tranquilidad": 1.0,
    "diversidad_temas": 0.8,
    "presencia_zonas": 0.7,
    "consistencia": 0.9,
    "atencion": 0.6,
}

# Peso global por plataforma (no matriz por dimensión)
PLATFORM_IQ_WEIGHTS = {
    "facebook": 0.55,
    "tiktok": 0.45,
}

# Default para consistencia cuando hay datos insuficientes
CONSISTENCIA_DEFAULT = 50.0


def _clamp0100(valor):
    """Clamp a rango 0-100."""
    return max(0.0, min(100.0, n(valor)))


def calcular_aprobacion(promedio_sentiment_order):
    """§H — Dimensión Aprobación.

    Fórmula literal:
        score = clamp((promedio + 2) * 25, 0, 100)

    Donde promedio es el promedio de SENTIMENT_ORDER de los posts del período.
    SENTIMENT_ORDER: muy_positivo=2, positivo=1, neutral=0, negativo=-1, muy_negativo=-2.
    """
    return _clamp0100((n(promedio_sentiment_order) + 2) * 25)


def calcular_conexion_con_vistas(interacciones, vistas):
    """§H — Dimensión Conexión (con vistas).

    Fórmula literal:
        eng_rate = (reacciones+comentarios+compartidos)/vistas
        score = min(100, eng_rate * 2000)
    """
    vistas_val = n(vistas)
    if vistas_val == 0:
        return 0.0
    eng_rate = n(interacciones) / vistas_val
    return min(100.0, eng_rate * 2000)


def calcular_conexion_sin_vistas(interacciones, total_posts):
    """§H — Dimensión Conexión (sin vistas, proxy).

    Fórmula literal:
        score = min(100, (reacciones+comentarios+compartidos)/total_posts / 50 * 100)
    """
    posts = n(total_posts)
    if posts == 0:
        return 0.0
    return min(100.0, n(interacciones) / posts / 50 * 100)


def calcular_tranquilidad(angrys, sads, hahas, total_reacciones):
    """§H — Dimensión Tranquilidad.

    Fórmula literal:
        controversia = (angrys+sads+hahas)/total_reacciones
        score = clamp((1 - controversia) * 100, 0, 100)
    """
    total = n(total_reacciones)
    if total == 0:
        return 50.0
    negativas = n(angrys) + n(sads) + n(hahas)
    controversia = negativas / total
    return _clamp0100((1 - controversia) * 100)


def calcular_diversidad_temas(n_posts_con_tema, n_posts_total):
    """§H — Dimensión Diversidad de Temas.

    Fórmula literal:
        % de posts con un tema asignado (no vacío) — no el HHI.
    """
    total = n(n_posts_total)
    if total == 0:
        return 0.0
    return _clamp0100(n(n_posts_con_tema) / total * 100)


def calcular_presencia_zonas(n_posts_con_zona, n_posts_total):
    """§H — Dimensión Presencia en Zonas.

    Fórmula literal:
        % de posts con una zona/ubicación detectada — no el logaritmo.
    """
    total = n(n_posts_total)
    if total == 0:
        return 0.0
    return _clamp0100(n(n_posts_con_zona) / total * 100)


def calcular_consistencia(promedios_mensuales):
    """§H — Dimensión Consistencia.

    Fórmula literal:
        Agrupar sentimiento promedio por mes; calcular desviación estándar
        entre promedios mensuales; score = clamp(100 - desviacion_estandar * 30, 0, 100).

    Default 50 SOLO si hay <2 meses de historia O si el total de posts
    válidos (sumando todos los meses) es menor a 5.

    Args:
        promedios_mensuales: lista de tuplas (avg_sentiment, n_posts_por_mes).
    """
    if len(promedios_mensuales) < 2:
        return CONSISTENCIA_DEFAULT
    total_posts = sum(n_posts for _, n_posts in promedios_mensuales)
    if total_posts < 5:
        return CONSISTENCIA_DEFAULT
    avgs = [avg for avg, _ in promedios_mensuales]
    media = sum(avgs) / len(avgs)
    varianza = sum((v - media) ** 2 for v in avgs) / len(avgs)
    desviacion = math.sqrt(varianza)
    return _clamp0100(100 - desviacion * 30)


def calcular_atencion(total_comentarios, total_posts):
    """§H — Dimensión Atención.

    Fórmula literal:
        promedio_comentarios_por_post = total_comentarios/total_posts
        score = min(100, promedio_comentarios_por_post * 10)
    """
    posts = n(total_posts)
    if posts == 0:
        return 0.0
    promedio = n(total_comentarios) / posts
    return min(100.0, promedio * 10)


def calcular_pulso_iq_fb(
    promedio_sentiment_order,
    interacciones, vistas,
    angrys, sads, hahas, total_reacciones,
    n_posts_con_tema, n_posts_total,
    n_posts_con_zona,
    total_comentarios,
    promedios_mensuales=None,
):
    """§H — Pulso IQ (Facebook) con las 7 dimensiones literales.

    Retorna dict {dimension: valor_0_100}.
    """
    if promedios_mensuales is None:
        promedios_mensuales = []
    dims = {}
    dims["aprobacion"] = calcular_aprobacion(promedio_sentiment_order)
    if vistas > 0:
        dims["conexion"] = calcular_conexion_con_vistas(interacciones, vistas)
    else:
        dims["conexion"] = calcular_conexion_sin_vistas(interacciones, n_posts_total)
    dims["tranquilidad"] = calcular_tranquilidad(angrys, sads, hahas, total_reacciones)
    dims["diversidad_temas"] = calcular_diversidad_temas(n_posts_con_tema, n_posts_total)
    dims["presencia_zonas"] = calcular_presencia_zonas(n_posts_con_zona, n_posts_total)
    dims["consistencia"] = calcular_consistencia(promedios_mensuales)
    dims["atencion"] = calcular_atencion(total_comentarios, n_posts_total)
    return {k: round(v, 2) for k, v in dims.items()}


def calcular_pulso_iq_tk(
    promedio_sentiment_order,
    interacciones, vistas,
    angrys, sads, hahas, total_reacciones,
    n_videos_con_tema, n_videos_total,
    n_videos_con_zona,
    total_comentarios,
    promedios_mensuales=None,
):
    """§H — Pulso IQ (TikTok) con las 7 dimensiones literales.

    Retorna dict {dimension: valor_0_100}.
    """
    if promedios_mensuales is None:
        promedios_mensuales = []
    dims = {}
    dims["aprobacion"] = calcular_aprobacion(promedio_sentiment_order)
    if vistas > 0:
        dims["conexion"] = calcular_conexion_con_vistas(interacciones, vistas)
    else:
        dims["conexion"] = calcular_conexion_sin_vistas(interacciones, n_videos_total)
    dims["tranquilidad"] = calcular_tranquilidad(angrys, sads, hahas, total_reacciones)
    dims["diversidad_temas"] = calcular_diversidad_temas(n_videos_con_tema, n_videos_total)
    dims["presencia_zonas"] = calcular_presencia_zonas(n_videos_con_zona, n_videos_total)
    dims["consistencia"] = calcular_consistencia(promedios_mensuales)
    dims["atencion"] = calcular_atencion(total_comentarios, n_videos_total)
    return {k: round(v, 2) for k, v in dims.items()}


def pulso_iq_score(dims_fb, dims_tk):
    """§H — Pondera dimensiones FB+TK con pesos de 6.0.

    iq_plataforma = Σ(dimension * weight) / 6.0
    iq_general = iq_facebook * 0.55 + iq_tiktok * 0.45

    Si solo hay FB → iq = iq_fb (escala 0-100).
    Si solo hay TK → iq = iq_tk.
    """
    hay_fb = dims_fb is not None
    hay_tk = dims_tk is not None
    if not hay_fb and not hay_tk:
        return 0.0, {}

    def _iq_from_dims(dims):
        if not dims:
            return 0.0
        suma_ponderada = sum(
            n(dims.get(k, 0)) * w for k, w in DIMENSION_WEIGHTS.items()
        )
        return suma_ponderada / 6.0

    iq_fb = _iq_from_dims(dims_fb) if hay_fb else 0.0
    iq_tk = _iq_from_dims(dims_tk) if hay_tk else 0.0

    if hay_fb and hay_tk:
        iq_score = iq_fb * PLATFORM_IQ_WEIGHTS["facebook"] + iq_tk * PLATFORM_IQ_WEIGHTS["tiktok"]
    elif hay_fb:
        iq_score = iq_fb
    else:
        iq_score = iq_tk

    combined = {}
    if hay_fb:
        combined.update({f"fb_{k}": v for k, v in dims_fb.items()})
    if hay_tk:
        combined.update({f"tk_{k}": v for k, v in dims_tk.items()})

    return round(iq_score, 2), combined


def pulso_iq_cuadrante(score, dims):
    """§H — Cuadrante del Pulso IQ.

    Fórmula literal:
        Eje X = aprobacion (sola, no promediada con otras dimensiones)
        Eje Y = conexion (sola)
        Ambos ≥ 50 → LIDERAZGO
        X ≥ 50, Y < 50 → INSTITUCIONAL
        X < 50, Y ≥ 50 → POPULISTA
        Ambos < 50 → CRISIS

    Busca 'aprobacion' y 'conexion' en dims, o con prefijo fb_/tk_.
    """
    if not dims:
        return ""
    aprobacion = n(dims.get("aprobacion", dims.get("fb_aprobacion", dims.get("tk_aprobacion", 0))))
    conexion = n(dims.get("conexion", dims.get("fb_conexion", dims.get("tk_conexion", 0))))
    if aprobacion >= 50 and conexion >= 50:
        return "LIDERAZGO"
    if aprobacion >= 50 and conexion < 50:
        return "INSTITUCIONAL"
    if aprobacion < 50 and conexion >= 50:
        return "POPULISTA"
    return "CRISIS"


# ═══════════════════════════════════════════════════════════════════════════════
# §I — Autenticidad / Coeficiente de variación del volumen diario
# ═══════════════════════════════════════════════════════════════════════════════


def coeficiente_variacion(daily_volumes: Sequence[float]):
    """§I — Coeficiente de variación del volumen diario.

    CV = σ / μ

    Si CV > 0.5, la conversación es volátil (patrón sospechoso).
    Si CV ≤ 0.5, la conversación es estable y orgánica.
    Retorna (cv, es_organico).
    """
    vals = [n(v) for v in daily_volumes if n(v) > 0]
    if len(vals) < 2:
        return 0.0, True
    media = sum(vals) / len(vals)
    if media == 0:
        return 0.0, True
    varianza = sum((v - media) ** 2 for v in vals) / len(vals)
    sigma = math.sqrt(varianza)
    cv = sigma / media
    return round(cv, 3), cv <= 0.5


def autenticidad_pct(daily_volumes):
    """§I — Porcentaje orgánico vs coordinado.

    Si CV ≤ 0.5 → pct_organico = 100%
    Si CV > 0.5 → pct_coordinado = min(CV * 50, 80)%, pct_organico = 100 - coordinado
    """
    cv, es_organico = coeficiente_variacion(daily_volumes)
    if es_organico:
        return 100.0, 0.0
    coordinado = min(cv * 50, 80.0)
    return round(100 - coordinado, 1), round(coordinado, 1)
