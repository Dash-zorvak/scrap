"""Funciones puras de calculo y derivacion de estilos.

Todas las formulas inline que estaban en app.py se centralizan aqui.
Cada funcion es pura (sin side effects, sin Streamlit, sin DB).
"""
import hashlib
from datetime import datetime


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
