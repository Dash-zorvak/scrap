"""Funciones puras de calculo y derivacion de estilos.

Todas las formulas inline que estaban en app.py se centralizan aqui.
Cada funcion es pura (sin side effects, sin Streamlit, sin DB).
"""
import hashlib
import math
from datetime import datetime
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
                       comments, shares, views):
    """§D — Engagement Rate Facebook.

    ER_fb = (reacciones + comentarios + compartidos) / vistas * 100
    reacciones = likes + loves + cares + hahas + wows + sads + angrys

    Si vistas == 0, se usa engagementBasis proxy (sin vistas).
    Retorna (er, basis_label).
    """
    reacciones = sum(n(v) for v in [likes, loves, cares, hahas, wows, sads, angrys])
    eng = reacciones + n(comments) + n(shares)
    vistas = n(views)
    if vistas > 0:
        return round(eng / vistas * 100, 2), "vistas"
    if eng > 0:
        return round(eng, 2), "engagement_abs"
    return 0.0, "sin_datos"


def engagement_rate_tk(views, likes, shares, favorites, comments):
    """§D — Engagement Rate TikTok.

    ER_tk = (likes + shares + favorites + comments) / views * 100

    Si views == 0, se retorna engagement absoluto como proxy.
    Retorna (er, basis_label).
    """
    eng = n(likes) + n(shares) + n(favorites) + n(comments)
    vistas = n(views)
    if vistas > 0:
        return round(eng / vistas * 100, 2), "vistas"
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


# ═══════════════════════════════════════════════════════════════════════════════
# §E — Net sentiment, controversy, effectiveness, approval, NSI, risk
# ═══════════════════════════════════════════════════════════════════════════════


def net_sentiment_index(n_positivos, n_negativos, n_total):
    """§E — Net Sentiment Index (NSI).

    NSI = (n_positivos - n_negativos) / n_total * 100

    Rango: -100 a +100.
    """
    total = n(n_total)
    if total == 0:
        return 0.0
    return round((n(n_positivos) - n(n_negativos)) / total * 100, 1)


def controversy_index(pct_favorable, pct_critico):
    """§E — Controversy Index (CI).

    CI = min(pct_favorable, pct_critico) / max(pct_favorable, pct_critico)

    Rango: 0 a 1.  0 = sin controversia, 1 = perfectamente dividido.
    """
    fav = n(pct_favorable)
    crit = n(pct_critico)
    mx = max(fav, crit)
    if mx == 0:
        return 0.0
    return round(min(fav, crit) / mx, 3)


def effectiveness_index(tono_score, n_comentarios, n_posts):
    """§E — Effectiveness Index (EI).

    EI = tono_score * log(1 + n_comentarios) / log(1 + n_posts)

    Rango: -200 a +200 (tono_score ∈ [-100,100] * factor de volumen).
    """
    ts = n(tono_score)
    nc = n(n_comentarios)
    np_ = n(n_posts)
    if np_ == 0:
        return 0.0
    factor = math.log(1 + nc) / math.log(1 + np_)
    return round(ts * factor, 1)


def approval_pct(pct_favorable, pct_neutral):
    """§E — Aprobación %.

    Aprobación = pct_favorable + 0.5 * pct_neutral

    La neutralidad se cuenta como media aprobación.
    """
    return round(n(pct_favorable) + 0.5 * n(pct_neutral), 1)


def rejection_pct(pct_critico, pct_neutral):
    """§E — Rechazo %.

    Rechazo = pct_critico + 0.5 * pct_neutral
    """
    return round(n(pct_critico) + 0.5 * n(pct_neutral), 1)


def vol_factor(vol_hoy, promedio_semanal):
    """§E — Volume Factor (VF).

    VF = vol_hoy / promedio_semanal

    Indicador de spike: VF > 1.5 indica volumen por encima de lo normal.
    """
    prom = n(promedio_semanal)
    if prom == 0:
        return 1.0
    return round(n(vol_hoy) / prom, 2)


def risk_reputacional(pct_critico, angrys_ratio, hhi_tema):
    """§E — Risk Reputacional (RR).

    RR = (pct_critico * 0.4 + angrys_ratio * 0.3 + hhi_tema * 0.3) * 100

    Donde:
      - pct_critico: porcentaje de sentimiento crítico (0-1)
      - angrys_ratio: proporción de angrys en reacciones totales (0-1)
      - hhi_tema: HHI de concentración temática del tema crítico (0-1)

    Rango: 0 a 100.
    """
    pc = min(n(pct_critico) / 100, 1.0)
    ar = min(n(angrys_ratio), 1.0)
    ht = min(n(hhi_tema), 1.0)
    return round((pc * 0.4 + ar * 0.3 + ht * 0.3) * 100, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# §F — Alertas (ICI, SDI, EFI, TAI, ZDI)
# ═══════════════════════════════════════════════════════════════════════════════

# Umbrales fijos (sensibilidad estándar)
THRESHOLDS = {
    "ici": {"pct_negativos": 30.0, "severidad": "alta"},      # Intensidad Conversacional
    "sdi": {"pct_negativos": 50.0, "severidad": "critica"},    # Sentimiento Dominante
    "efi": {"ratio_angrys": 0.15, "severidad": "alta"},        # Emociones Fuertes
    "tai": {"controversy": 0.4, "severidad": "media"},         # Tema Aislado
    "zdi": {"pct_zona_neg": 40.0, "severidad": "alta"},        # Zona Dominante
}


def _detectar_alertas(pct_critico, angrys_ratio, controversy_score,
                      sensibilidad=None):
    """§F — Detecta las 5 alertas con sus umbrales.

    Retorna lista de dicts [{tipo, severidad, valor, umbral, descripcion}].
    """
    umb = sensibilidad or THRESHOLDS
    alertas = []

    # ICI — Intensidad Conversacional
    if n(pct_critico) >= umb["ici"]["pct_negativos"]:
        alertas.append({
            "tipo": "ICI",
            "severidad": umb["ici"]["severidad"],
            "valor": round(n(pct_critico), 1),
            "umbral": umb["ici"]["pct_negativos"],
            "descripcion": (
                f"Intensidad conversacional alta: {n(pct_critico):.1f}% de "
                f"comentarios críticos (umbral: {umb['ici']['pct_negativos']}%)"
            ),
        })

    # SDI — Sentimiento Dominante Individual
    if n(pct_critico) >= umb["sdi"]["pct_negativos"]:
        alertas.append({
            "tipo": "SDI",
            "severidad": umb["sdi"]["severidad"],
            "valor": round(n(pct_critico), 1),
            "umbral": umb["sdi"]["pct_negativos"],
            "descripcion": (
                f"Sentimiento crítico dominante: {n(pct_critico):.1f}% "
                f"(umbral: {umb['sdi']['pct_negativos']}%)"
            ),
        })

    # EFI — Emociones Fuertes Individuales
    if n(angrys_ratio) >= umb["efi"]["ratio_angrys"]:
        alertas.append({
            "tipo": "EFI",
            "severidad": umb["efi"]["severidad"],
            "valor": round(n(angrys_ratio), 3),
            "umbral": umb["efi"]["ratio_angrys"],
            "descripcion": (
                f"Reacciones de enojo altas: {n(angrys_ratio)*100:.1f}% de "
                f"reacciones totales (umbral: {umb['efi']['ratio_angrys']*100:.0f}%)"
            ),
        })

    # TAI — Tema Aislado de Interés
    if n(controversy_score) >= umb["tai"]["controversy"]:
        alertas.append({
            "tipo": "TAI",
            "severidad": umb["tai"]["severidad"],
            "valor": round(n(controversy_score), 3),
            "umbral": umb["tai"]["controversy"],
            "descripcion": (
                f"Controversia elevada: índice de {n(controversy_score):.3f} "
                f"(umbral: {umb['tai']['controversy']})"
            ),
        })

    # ZDI — Zona Dominante (placeholder: requiere datos geográficos)
    # Se activa externamente cuando hay datos de zona.

    return alertas


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

# Pesos de las 7 dimensiones del Pulso IQ (suma = 1.0)
DIMENSION_WEIGHTS = {
    "aprobacion": 0.25,
    "conexion": 0.15,
    "tranquilidad": 0.15,
    "diversidad": 0.10,
    "presencia": 0.15,
    "consistencia": 0.10,
    "atencion": 0.10,
}

# Pesos por plataforma (FB vs TK) para cada dimensión
PLATFORM_WEIGHTS = {
    "facebook": {
        "aprobacion": 0.6, "conexion": 0.5, "tranquilidad": 0.5,
        "diversidad": 0.4, "presencia": 0.6, "consistencia": 0.5,
        "atencion": 0.5,
    },
    "tiktok": {
        "aprobacion": 0.4, "conexion": 0.5, "tranquilidad": 0.5,
        "diversidad": 0.6, "presencia": 0.4, "consistencia": 0.5,
        "atencion": 0.5,
    },
}


def _normalizar_0_100(valor, vmin=0, vmax=100):
    """Normaliza un valor al rango 0-100."""
    if vmax == vmin:
        return 50.0
    return max(0.0, min(100.0, (n(valor) - vmin) / (vmax - vmin) * 100))


def calcular_pulso_iq_fb(pct_favorable, pct_critico, n_comentarios,
                         n_posts, shares, tono_score,
                         n_temas_unicos=0):
    """§H — Pulso IQ (Facebook) con las 7 dimensiones.

    Dimensiones:
      aprobacion: % favorable
      conexion: engagement_rate proxy (comentarios/posts)
      tranquilidad: 100 - % crítico
      diversidad: diversidad de temas (1 - HHI normalizado)
      presencia: volumen normalizado (log scale)
      consistencia: variación del tono (placeholder → 50)
      atencion: n_comentarios / n_posts

    Retorna dict {dimension: valor_0_100}.
    """
    dims = {}
    dims["aprobacion"] = _normalizar_0_100(n(pct_favorable), 0, 100)
    dims["conexion"] = _normalizar_0_100(
        n(n_comentarios) / max(n(n_posts), 1), 0, 50
    )
    dims["tranquilidad"] = _normalizar_0_100(100 - n(pct_critico), 0, 100)
    hhi = calcular_hhi(shares) if shares else 0.0
    dims["diversidad"] = _normalizar_0_100((1 - hhi) * 100, 0, 100)
    dims["presencia"] = _normalizar_0_100(
        math.log(1 + n(n_comentarios)), 0, math.log(1 + 1000)
    )
    dims["consistencia"] = 50.0  # Placeholder: requiere histórico
    dims["atencion"] = _normalizar_0_100(
        n(n_comentarios) / max(n(n_posts), 1), 0, 20
    )
    return dims


def calcular_pulso_iq_tk(pct_favorable, pct_critico, n_comentarios,
                         n_videos, shares, tono_score,
                         n_temas_unicos=0):
    """§H — Pulso IQ (TikTok) con las 7 dimensiones."""
    dims = {}
    dims["aprobacion"] = _normalizar_0_100(n(pct_favorable), 0, 100)
    dims["conexion"] = _normalizar_0_100(
        n(n_comentarios) / max(n(n_videos), 1), 0, 50
    )
    dims["tranquilidad"] = _normalizar_0_100(100 - n(pct_critico), 0, 100)
    hhi = calcular_hhi(shares) if shares else 0.0
    dims["diversidad"] = _normalizar_0_100((1 - hhi) * 100, 0, 100)
    dims["presencia"] = _normalizar_0_100(
        math.log(1 + n(n_comentarios)), 0, math.log(1 + 500)
    )
    dims["consistencia"] = 50.0
    dims["atencion"] = _normalizar_0_100(
        n(n_comentarios) / max(n(n_videos), 1), 0, 20
    )
    return dims


def pulso_iq_score(dims_fb, dims_tk):
    """§H — Pondera dimensiones FB+TK y retorna score compuesto 0-100.

    Si solo hay FB, se usa 100% FB. Si solo TK, 100% TK.
    Si hay ambos, se pondera por PLATFORM_WEIGHTS.
    """
    hay_fb = dims_fb is not None
    hay_tk = dims_tk is not None
    if not hay_fb and not hay_tk:
        return 0.0, {}

    combined = {}
    for dim in DIMENSION_WEIGHTS:
        fb_val = n(dims_fb.get(dim, 50)) if hay_fb else None
        tk_val = n(dims_tk.get(dim, 50)) if hay_tk else None
        if hay_fb and hay_tk:
            pw_fb = PLATFORM_WEIGHTS["facebook"][dim]
            pw_tk = PLATFORM_WEIGHTS["tiktok"][dim]
            combined[dim] = round(fb_val * pw_fb + tk_val * pw_tk, 1)
        elif hay_fb:
            combined[dim] = fb_val
        else:
            combined[dim] = tk_val

    score = sum(combined[d] * DIMENSION_WEIGHTS[d] for d in DIMENSION_WEIGHTS)
    return round(score, 1), combined


def pulso_iq_cuadrante(score, dims):
    """§H — Cuadrante del Pulso IQ.

    Ejes:
      Eje X: (aprobacion + conexion + presencia) / 3  (positividad)
      Eje Y: (tranquilidad + consistencia) / 2         (estabilidad)

    Cuadrantes:
      LIDERAZGO:     X ≥ 50, Y ≥ 50
      INSTITUCIONAL: X < 50,  Y ≥ 50
      POPULISTA:     X ≥ 50, Y < 50
      CRISIS:        X < 50,  Y < 50
    """
    if not dims:
        return ""
    eje_x = (
        n(dims.get("aprobacion", 50))
        + n(dims.get("conexion", 50))
        + n(dims.get("presencia", 50))
    ) / 3
    eje_y = (
        n(dims.get("tranquilidad", 50))
        + n(dims.get("consistencia", 50))
    ) / 2
    if eje_x >= 50 and eje_y >= 50:
        return "LIDERAZGO"
    if eje_x < 50 and eje_y >= 50:
        return "INSTITUCIONAL"
    if eje_x >= 50 and eje_y < 50:
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
