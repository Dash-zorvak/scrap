"""PANEL·SANTA ANA — Inteligencia Ciudadana.

Lee data/analysis.json generado por el analista externo y renderiza
los cuatro bloques ejecutivos. Sin cálculo en runtime, sin ML, sin LLM.
"""

import json
import os
import pandas as pd
import streamlit as st
from datetime import datetime

from estilos import CSS
from estilos_override import CSS_OVERRIDE

# ── Ruta al JSON de análisis ──────────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSIS_PATH = os.path.join(_BASE, "data", "analysis.json")


def _cargar_analysis():
    """Carga analysis.json. Retorna None si no existe o está corrupto."""
    try:
        with open(ANALYSIS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _get(data, *keys, default="—"):
    """Navega claves anidadas con fallback seguro."""
    val = data
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
        if val is None:
            return default
    return val


def _render_card(html):
    """Renderiza HTML dinámico eliminando líneas vacías internas que
    Streamlit interpretaría como fin de bloque HTML (y el resto como
    bloque de código indentado en texto literal)."""
    limpio = "\n".join(line for line in html.split("\n") if line.strip())
    st.markdown(limpio, unsafe_allow_html=True)


def _expander_enlaces(enlaces, label="Ver todos los enlaces de referencia"):
    """Muestra la lista completa de enlaces en un expander, solo si hay datos."""
    if enlaces:
        with st.expander(f"{label} ({len(enlaces)})"):
            for url in enlaces:
                st.markdown(f"- {url}")


def _card_explicacion_simple(texto):
    """Card de lenguaje llano, siempre visible ANTES de la fórmula técnica."""
    if texto:
        st.markdown(f"""
<div style="background:var(--accent-soft);border-radius:var(--r-sm);padding:10px 14px;margin-bottom:8px;font-size:13px;color:var(--fg-primary)">
{texto}
</div>
""", unsafe_allow_html=True)


# ── Configuración de página ───────────────────────────────────────────
st.set_page_config(
    page_title="PANEL·SANTA ANA — Inteligencia Ciudadana",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(CSS_OVERRIDE, unsafe_allow_html=True)

# ── Cargar datos ──────────────────────────────────────────────────────
data = _cargar_analysis()

# ── Fechas para topbar ────────────────────────────────────────────────
if data:
    fecha_datos = _get(data, "meta", "fecha_datos_hasta", default="")
    periodo_label = _get(data, "meta", "periodo", default="")
    plataforma_label = _get(data, "meta", "plataforma", default="")
    try:
        _dt = datetime.fromisoformat(fecha_datos)
        dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        meses = ["enero","febrero","marzo","abril","mayo","junio","julio",
                 "agosto","septiembre","octubre","noviembre","diciembre"]
        meses_s = ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"]
        fecha_str = f"{dias[_dt.weekday()]} {_dt.day} de {meses[_dt.month-1]}, {_dt.year}"
        fecha_corta = f"{_dt.day:02d} {meses_s[_dt.month-1]} {_dt.year}"
    except Exception:
        fecha_str = fecha_datos
        fecha_corta = fecha_datos
else:
    fecha_str = "Análisis pendiente"
    fecha_corta = "N/D"
    periodo_label = "—"
    plataforma_label = "—"

# ── Topbar ────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="topbar">
    <div class="topbar-brand">PANEL <span class="sep">·</span> SANTA ANA
    <span class="sep">/</span>
    <span class="who">Inteligencia Ciudadana</span></div>
    <div class="topbar-meta">ACTUALIZADO <span class="acc">·</span>
    {fecha_str.upper()}</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────
st.sidebar.markdown("""
<div class="sys-header">
    <div class="sys-brand">PANEL·SANTA ANA</div>
    <div class="sys-brand-sub">INTELIGENCIA CIUDADANA</div>
</div>
""", unsafe_allow_html=True)

_estado_color = "var(--green)" if data else "var(--amber)"
_estado_txt = "OPERACIONAL" if data else "SIN DATOS"
st.sidebar.markdown(f"""
<div style="background:var(--bg-card);border:1px solid var(--border);
border-radius:var(--r-sm);padding:11px 13px;margin-bottom:18px">
    <div style="display:flex;align-items:center;justify-content:space-between;
    font-family:var(--font-mono);font-size:11px;letter-spacing:1.4px;
    color:var(--fg-muted);font-weight:600;text-transform:uppercase">
        <span>SYS</span>
        <span style="display:flex;align-items:center;gap:6px">
            <span style="width:6px;height:6px;border-radius:50%;
            background:{_estado_color};display:inline-block"></span>
            <span style="color:{_estado_color};letter-spacing:1.2px">
            {_estado_txt}</span>
        </span>
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;
    font-family:var(--font-mono);font-size:11px;letter-spacing:1.2px;
    color:var(--fg-muted);font-weight:600;margin-top:9px;text-transform:uppercase">
        <span>FEED</span>
        <span style="color:var(--accent)">{fecha_corta}</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="margin-top:26px;padding-top:14px;border-top:1px solid var(--border);
font-family:var(--font-mono);color:var(--fg-muted);letter-spacing:0.4px;line-height:1.6">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:1.4px;
    font-weight:600;margin-bottom:6px;color:var(--fg-secondary)">PERÍODO</div>
    <div style="color:var(--accent);font-size:11px">{periodo_label}</div>
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:1.4px;
    font-weight:600;margin-top:10px;margin-bottom:6px;color:var(--fg-secondary)">
    PLATAFORMA</div>
    <div style="color:var(--accent);font-size:11px">{plataforma_label}</div>
    <div style="color:var(--fg-dim);font-size:10px;margin-top:16px;
    letter-spacing:1px;text-transform:uppercase;border-top:1px solid var(--border);
    padding-top:8px">PANEL·SANTA ANA <span style="color:var(--accent-2)">·</span>
    v2.0 <span style="color:var(--accent-2)">·</span> CONFIDENCIAL</div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PANTALLA DE ESPERA si no hay JSON
# ════════════════════════════════════════════════════════════
if not data:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;
    justify-content:center;min-height:60vh;text-align:center;gap:20px">
        <div style="font-family:var(--font-mono);font-size:48px;
        color:var(--fg-dim)">◈</div>
        <div style="font-family:var(--font-mono);font-size:11px;
        letter-spacing:2px;color:var(--accent);text-transform:uppercase">
        ANÁLISIS PENDIENTE</div>
        <div style="font-size:15px;color:var(--fg-secondary);max-width:460px;
        line-height:1.7">
            El análisis del día aún no está disponible.<br>
            Contacte al equipo técnico para actualizar el sistema.
        </div>
        <div style="font-family:var(--font-mono);font-size:10px;
        color:var(--fg-dim);letter-spacing:1px">
        data/analysis.json · NO ENCONTRADO</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ════════════════════════════════════════════════════════════
# TABS PRINCIPALES
# ════════════════════════════════════════════════════════════
tab_pulso, tab_audiencia, tab_riesgo, tab_intel = st.tabs([
    "PULSO GENERAL",
    "SEGMENTACIÓN DE AUDIENCIA",
    "RIESGO Y AUTENTICIDAD",
    "MEMORIA E INTELIGENCIA APLICADA",
])

# ════════════════════════════════════════════════════════════
# UTILIDADES DE RENDERIZADO
# ════════════════════════════════════════════════════════════

_EMO_DEFS = [
    # Alegría (joy)
    ("serenidad", "Serenidad", "var(--green)"),
    ("alegria", "Alegría", "var(--green)"),
    ("euforia", "Euforia", "var(--green)"),
    # Confianza (trust)
    ("aceptacion", "Aceptación", "var(--green)"),
    ("confianza", "Confianza", "var(--green)"),
    ("admiracion", "Admiración", "var(--green)"),
    # Miedo (fear)
    ("aprension", "Aprensión", "var(--amber)"),
    ("preocupacion", "Preocupación", "var(--amber)"),
    ("terror", "Terror / Pánico", "var(--red)"),
    # Sorpresa (surprise)
    ("distraccion", "Distracción", "var(--amber)"),
    ("sorpresa", "Sorpresa", "var(--amber)"),
    ("asombro", "Asombro", "var(--amber)"),
    # Tristeza (sadness)
    ("melancolia", "Melancolía", "var(--red)"),
    ("tristeza", "Tristeza", "var(--red)"),
    ("dolor", "Dolor / Pena", "var(--red)"),
    # Desagrado (disgust)
    ("aburrimiento", "Aburrimiento", "var(--amber)"),
    ("desagrado", "Desagrado", "var(--red)"),
    ("repulsion", "Repulsión", "var(--red)"),
    # Enojo (anger)
    ("fastidio", "Fastidio", "var(--amber)"),
    ("enojo", "Enojo", "var(--red)"),
    ("furia", "Furia / Ira", "var(--red)"),
    # Anticipación (anticipation)
    ("interes", "Interés", "var(--amber)"),
    ("expectativa", "Expectativa", "var(--amber)"),
    ("vigilancia", "Vigilancia", "var(--amber)"),
    # Díadas
    ("optimismo", "Optimismo", "var(--green)"),
    ("amor_civico", "Cariño / Aprecio", "var(--green)"),
    ("sumision", "Resignación", "var(--amber)"),
    ("asombro_temeroso", "Sobrecogimiento", "var(--red)"),
    ("desaprobacion", "Desaprobación", "var(--red)"),
    ("remordimiento", "Remordimiento", "var(--red)"),
    ("desprecio", "Desprecio", "var(--red)"),
    ("agresividad", "Agresividad", "var(--red)"),
    # Posturas cívicas
    ("reclamo", "Reclamo", "var(--red)"),
    ("objecion", "Objeción", "var(--amber)"),
    ("satisfaccion", "Satisfacción", "var(--green)"),
    ("calma", "Calma", "var(--green)"),
    ("reconocimiento", "Reconocimiento", "var(--green)"),
    ("ironia", "Ironía", "var(--amber)"),
]


def _render_emociones_barras(ie, show_caption=True):
    """Renderiza 10 barras horizontales de emociones."""
    for emo, label, color in _EMO_DEFS:
        pct = ie.get(f"pct_{emo}", 0) if isinstance(ie, dict) else 0
        st.markdown(f"""
        <div class="bar-row">
            <div class="bar-row-label">{label}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div>
            </div>
            <div class="bar-row-val">{pct:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# BLOQUE I — PULSO GENERAL
# ════════════════════════════════════════════════════════════
with tab_pulso:
    b1 = data.get("bloque1", {})

    st.markdown("""
    <div class="page-head">
        <div class="page-overline">BLOQUE I</div>
        <div class="page-h">Pulso General · Lectura Ciudadana</div>
        <div class="page-sub">Síntesis ejecutiva del clima narrativo, la intensidad
        de la conversación y la concentración temática.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 01 · Clima Narrativo ──────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">01 · Clima Narrativo</div></div>', unsafe_allow_html=True)
    cn = b1.get("clima_narrativo", {})
    fav = cn.get("pct_favorable", 0)
    neu = cn.get("pct_neutral", 0)
    adv = cn.get("pct_critico", 0)
    dom = cn.get("tono_dominante", "—")
    n_tot = cn.get("n_total_comentarios", 0)
    tend = cn.get("tendencia", 0)
    narrativa_cn = _get(cn, "narrativa", default="Sin datos de clima narrativo.")

    tend_color = "var(--green)" if tend > 0.1 else ("var(--red)" if tend < -0.1 else "var(--amber)")
    tend_label = "↑ mejorando" if tend > 0.1 else ("↓ empeorando" if tend < -0.1 else "→ estable")

    st.markdown(f"""
    <div class="panel">
        <div class="panel-head">
            <div class="panel-title">TONO DOMINANTE · {dom.upper()}</div>
            <div class="panel-meta">{n_tot:,} COMENTARIOS · TENDENCIA
            <span style="color:{tend_color}">{tend_label}</span></div>
        </div>
        <div class="bar-tri" style="height:18px;border-radius:3px">
            <span class="bar-tri-pos" style="width:{fav:.1f}%"></span>
            <span class="bar-tri-neu" style="width:{neu:.1f}%"></span>
            <span class="bar-tri-neg" style="width:{adv:.1f}%"></span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:13px">
            <span style="color:var(--green)">A favor {fav:.0f}%</span>
            <span style="color:var(--amber)">Neutral {neu:.0f}%</span>
            <span style="color:var(--red)">Crítico {adv:.0f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="interpretation">
        <div class="interpretation-label">LECTURA EJECUTIVA</div>
        <div class="interpretation-texto">{narrativa_cn}</div>
    </div>
    """, unsafe_allow_html=True)
    _expander_enlaces(cn.get("enlaces_referencia", []))

    # ── 02 · Índice de Emociones ───────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">02 · Índice de Emociones</div></div>', unsafe_allow_html=True)
    ie = b1.get("indice_emociones", {})
    has_data = ie and any(ie.get(f"pct_{e}", 0) for e, _, _ in _EMO_DEFS)
    if has_data:
        emo_dom = ie.get("emocion_dominante", "—")
        emos_ordenadas = sorted(_EMO_DEFS, key=lambda t: ie.get(f"pct_{t[0]}", 0), reverse=True)

        st.session_state.setdefault("b1_emo_activa", emos_ordenadas[0][0])
        emo_activa = st.session_state["b1_emo_activa"]

        e, label, color = next(
            t for t in emos_ordenadas if t[0] == emo_activa
        )
        pct = ie.get(f"pct_{e}", 0)

        st.markdown(f"""
        <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:10px">
            <div style="font-family:var(--font-mono);font-size:11px;color:var(--fg-muted)">
            EMOCIÓN DOMINANTE: <span style="color:var(--accent);font-weight:700">{emo_dom}</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="bar-row" style="margin-bottom:6px">
            <div class="bar-row-label">{label}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div>
            </div>
            <div class="bar-row-val">{pct:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

        # Pill selector — CSS override + horizontal radio
        st.markdown("""
        <style>
        div[data-testid="stRadio"] > div {
            display: flex !important;
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            white-space: nowrap !important;
            gap: 6px;
            padding-bottom: 6px;
            scrollbar-width: thin;
        }
        div[data-testid="stRadio"] label {
            display: inline-flex !important;
            align-items: center;
            padding: 5px 14px;
            border-radius: 20px;
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            font-size: 12px;
            font-family: var(--font-mono);
            cursor: pointer;
            transition: all 0.15s;
            flex-shrink: 0;
            color: var(--fg-secondary);
        }
        div[data-testid="stRadio"] input[type="radio"] {
            display: none !important;
        }
        div[data-testid="stRadio"] label:has(input:checked) {
            background: var(--accent-soft);
            border-color: var(--accent);
            color: var(--accent);
            font-weight: 700;
        }
        div[data-testid="stRadio"] label:hover {
            border-color: var(--accent);
        }
        </style>
        """, unsafe_allow_html=True)

        emo_labels = {e: label for e, label, _ in _EMO_DEFS}
        st.radio(
            "Seleccionar emoción",
            options=[e for e, _, _ in emos_ordenadas],
            format_func=lambda e: f"{emo_labels[e]} {ie.get(f'pct_{e}',0):.1f}%",
            key="b1_emo_activa",
            horizontal=True,
            label_visibility="collapsed",
        )

        narrativa_ie = _get(ie, "narrativa", default="—")
        st.markdown(f"""
        <div class="interpretation">
            <div class="interpretation-label">LECTURA EJECUTIVA</div>
            <div class="interpretation-texto">{narrativa_ie}</div>
        </div>
        """, unsafe_allow_html=True)
        _card_explicacion_simple(ie.get("explicacion_simple", ""))
        _expander_enlaces(ie.get("enlaces_referencia", []))
    else:
        st.markdown('<div class="status-info">Índice de emociones no disponible.</div>', unsafe_allow_html=True)

    # ── 03 · Intensidad ───────────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">03 · Intensidad de la Conversación</div></div>', unsafe_allow_html=True)
    it = b1.get("intensidad", {})
    vol_hoy = it.get("vol_hoy", 0)
    prom = it.get("promedio_semanal", 0)
    pct = it.get("pct_diferencia", 0)
    etiq_int = it.get("etiqueta", "—")
    narrativa_it = _get(it, "narrativa", default="Sin datos de intensidad.")
    maxv = max(vol_hoy, prom, 1)

    col_hoy = "var(--red)" if pct > 15 else ("var(--blue)" if pct < -15 else "var(--accent)")
    signo = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"

    st.markdown(f"""
    <div class="exec-card">
        <div style="font-family:var(--font-mono);font-size:9px;letter-spacing:1.6px;color:var(--accent);font-weight:600;text-transform:uppercase;margin-bottom:4px">LECTURA EJECUTIVA</div>
        <div style="margin-bottom:12px;font-size:13px;color:var(--fg-primary);line-height:1.7">{narrativa_it}</div>
        <div style="border-top:1px solid var(--border);padding-top:12px">
            <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:4px">
                <div style="font-family:var(--font-mono);font-size:10px;color:var(--fg-muted);letter-spacing:0.6px">INTENSIDAD DEL ÚLTIMO DÍA</div>
                <div style="font-family:var(--font-mono);font-size:9px;color:var(--fg-dim)">
                {it.get('fecha_hoy','—')} · {it.get('n_dias_referencia',0)} DÍAS DE REFERENCIA</div>
            </div>
            <div style="display:flex;align-items:baseline;gap:14px;margin:4px 0 12px">
                <span style="font-size:44px;font-weight:700;line-height:1;
                color:{col_hoy}">{signo}</span>
                <span style="font-size:15px;color:var(--fg-secondary)">{etiq_int}</span>
            </div>
            <div class="bar-row">
                <div class="bar-row-label">ÚLTIMO DÍA</div>
                <div class="bar-track"><div class="bar-fill"
                style="width:{vol_hoy/maxv*100:.1f}%;background:{col_hoy}"></div></div>
                <div class="bar-row-val">{vol_hoy:,}</div>
            </div>
            <div class="bar-row">
                <div class="bar-row-label">PROMEDIO</div>
                <div class="bar-track"><div class="bar-fill bar-fill-blu"
                style="width:{prom/maxv*100:.1f}%"></div></div>
                <div class="bar-row-val">{prom:,}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    _expander_enlaces(it.get("enlaces_referencia", []))
    formula_it = _get(it, "formula_usada", default="")
    if formula_it:
        st.caption(f"Fórmula: {formula_it}")

    # ── 04 · Concentración Temática ───────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">04 · Concentración Temática</div></div>', unsafe_allow_html=True)
    ct = b1.get("concentracion_tematica", {})
    ramas = sorted(ct.get("ramas", []), key=lambda r: _get(r, "share", default=0), reverse=True)
    nivel_ct = ct.get("nivel", "")
    narrativa_ct = _get(ct, "narrativa", default="Sin datos de concentración temática.")
    col_ct = {"dominado": "var(--red)", "liderado": "var(--amber)", "fragmentado": "var(--green)"}.get(nivel_ct, "var(--accent)")
    paleta = ["var(--accent)","#a78bfa","#f59e0b","#34d399","#f472b6","#60a5fa","#fbbf24","#4ade80","#fb7185","#818cf8"]
    segmentos = "".join(f'<span style="display:inline-block;height:100%;background:{paleta[i%len(paleta)]};width:{_get(r, "share", default=0):.1f}%"></span>' for i,r in enumerate(ramas))
    filas = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;font-size:12px;flex:0 0 auto;white-space:nowrap;background:rgba(255,255,255,0.03);padding:6px 10px;border-radius:6px">'
        f'<span style="width:10px;height:10px;border-radius:2px;background:{paleta[i%len(paleta)]};display:inline-block;flex:none"></span>'
        f'<span style="color:var(--fg-primary)">{r.get("tema","—")}</span>'
        f'<span style="color:var(--fg-secondary)">{r.get("n",0)} pubs · {_get(r, "share", default=0):.0f}%</span>'
        f'</div>'
        for i,r in enumerate(ramas)
    )

    st.markdown(f"""
    <div class="interpretation">
        <div class="interpretation-label">LECTURA EJECUTIVA</div>
        <div class="interpretation-texto">{narrativa_ct}</div>
    </div>
    """, unsafe_allow_html=True)
    _expander_enlaces(ct.get("enlaces_referencia", []))
    st.markdown(f"""
    <div class="panel">
        <div class="panel-head">
            <div class="panel-title" style="color:{col_ct}">{ct.get('estado','—').upper()}</div>
            <div class="panel-meta">{ct.get('n_temas',0)} TEMAS</div>
        </div>
        <div class="bar-tri" style="height:18px;border-radius:3px">{segmentos}</div>
        <div style="margin-top:12px"><div style="display:flex;flex-direction:row;gap:10px;overflow-x:auto;overflow-y:hidden;padding-bottom:8px;margin-top:8px;max-width:100%">{filas}</div></div>
    </div>
    """, unsafe_allow_html=True)

    temas_acel = ct.get("temas_acelerando", [])
    temas_desacel = ct.get("temas_desacelerando", [])
    if temas_acel or temas_desacel:
        st.markdown(f"""
        <div style="display:flex;gap:20px;flex-wrap:wrap;margin:6px 0 10px;font-size:12px">
            <div><span style="color:var(--red)">🔺 TEMAS ACELERANDO:</span>
            <span style="color:var(--fg-secondary)"> {', '.join(temas_acel) if temas_acel else '—'}</span></div>
            <div><span style="color:var(--green)">🔻 TEMAS DESACELERANDO:</span>
            <span style="color:var(--fg-secondary)"> {', '.join(temas_desacel) if temas_desacel else '—'}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ── 05 · Métricas de Rendimiento (NUEVA) ───────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">05 · Métricas de Rendimiento</div></div>', unsafe_allow_html=True)
    mr = b1.get("metricas_rendimiento", {})
    if mr and any(v for v in [mr.get("engagement_rate"), mr.get("ratio_amor_enojo"), mr.get("alcance_estimado")]):
        narrativa_mr = _get(mr, "narrativa", default="")
        if narrativa_mr:
            st.markdown(f"""
            <div class="interpretation">
                <div class="interpretation-label">LECTURA EJECUTIVA</div>
                <div class="interpretation-texto">{narrativa_mr}</div>
            </div>
            """, unsafe_allow_html=True)
        _expander_enlaces(mr.get("enlaces_referencia", []))
        st.markdown(f"""
        <p style="font-size:11px;color:var(--fg-muted);margin-top:4px;margin-bottom:10px">
        Engagement: {mr.get("engagement_rate",0):.1f}% · Ratio amor/enojo:
        {mr.get("ratio_amor_enojo",0):.1f} · Reacciones: {mr.get("reacciones_positivas",0):,}
        / {mr.get("reacciones_negativas",0):,} · Alcance estimado:
        {mr.get("alcance_estimado",0):,}</p>
        """, unsafe_allow_html=True)
        pfunciona = mr.get("porque_funciona", "")
        if pfunciona:
            st.markdown(f"""
            <div style="background:var(--green-soft);border:1px solid var(--green-strong);border-radius:var(--r-sm);
            padding:14px 18px;margin-bottom:10px">
                <div style="font-family:var(--font-mono);font-size:9px;letter-spacing:1.6px;
                color:var(--green);font-weight:600;text-transform:uppercase;margin-bottom:4px">
                POR QUÉ ESTÁ FUNCIONANDO</div>
                <div style="font-size:13px;color:var(--fg-primary);line-height:1.7">{pfunciona}</div>
            </div>
            """, unsafe_allow_html=True)
        _card_explicacion_simple(mr.get("explicacion_simple", ""))
    else:
        st.markdown('<div class="status-info">Métricas de rendimiento no disponibles.</div>', unsafe_allow_html=True)

    # ── 06 · Termómetro de Lugares ─────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">06 · Termómetro de Lugares</div></div>', unsafe_allow_html=True)
    termometro_lugares = b1.get("termometro_lugares", [])
    if not termometro_lugares:
        st.markdown('<div class="status-info">Sin datos de lugares.</div>', unsafe_allow_html=True)
    else:
        # a) Sort by nivel_tension descending
        sorted_lugares = sorted(termometro_lugares, key=lambda x: x.get("nivel_tension", 0), reverse=True)

        def tension_color(t):
            if t > 60: return "var(--red)"
            if t > 30: return "var(--amber)"
            return "var(--green)"

        cards_html = []
        for lugar in sorted_lugares:
            tension = lugar.get("nivel_tension", 0)
            border_color = tension_color(tension)
            emo_dom = lugar.get("emocion_dominante", "")

            # b) Thermometer bar
            thermo_bar = f"""
            <div style="position:relative;height:6px;border-radius:3px;
            background:linear-gradient(to right, var(--green), var(--amber), var(--red));
            margin:6px 0 10px 0">
                <div style="position:absolute;top:-3px;left:{tension}%;
                width:2px;height:12px;background:#fff;border-radius:1px;
                box-shadow:0 0 3px rgba(0,0,0,0.4)"></div>
            </div>
            """

            citas_html = "".join(
                f'<div style="font-style:italic;color:var(--fg-secondary);font-size:12px;margin-top:4px">"{c}"</div>'
                for c in lugar.get("citas_ejemplo", [])[:1]
            )

            tema_str = ""
            td = lugar.get("tema_dominante", "")
            if td:
                tema_str = (
                    f'<div style="font-size:11px;color:var(--fg-muted);margin-top:4px">'
                    f'⚑ {td.replace("_"," ").title()} ({lugar.get("n_tema_dominante",0)} críticos)</div>'
                )

            narrativa_txt = lugar.get("narrativa", "")
            narrativa_html = (
                f'<div style="font-size:12px;color:var(--fg-primary);margin-top:6px;line-height:1.6">{narrativa_txt}</div>'
                if narrativa_txt else ""
            )

            _emo_fields = [
                "pct_serenidad","pct_alegria","pct_euforia","pct_aceptacion","pct_confianza",
                "pct_admiracion","pct_aprension","pct_preocupacion","pct_terror","pct_distraccion",
                "pct_sorpresa","pct_asombro","pct_melancolia","pct_tristeza","pct_dolor",
                "pct_aburrimiento","pct_desagrado","pct_repulsion","pct_fastidio","pct_enojo",
                "pct_furia","pct_interes","pct_expectativa","pct_vigilancia","pct_optimismo",
                "pct_amor_civico","pct_sumision","pct_asombro_temeroso","pct_desaprobacion",
                "pct_remordimiento","pct_desprecio","pct_agresividad","pct_reclamo","pct_objecion",
                "pct_satisfaccion","pct_calma","pct_reconocimiento","pct_ironia",
            ]
            top_emos = sorted(
                ((f.replace("pct_", "").replace("_", " ").title(), lugar.get(f, 0)) for f in _emo_fields),
                key=lambda t: t[1], reverse=True,
            )
            top_emos = [(name, val) for name, val in top_emos if val > 0][:3]
            emo_chips = "".join(
                f'<span style="font-size:11px;padding:2px 8px;background:var(--bg-elevated);'
                f'border-radius:10px;color:var(--fg-secondary);margin:2px">{name} '
                f'<strong>{val:.1f}%</strong></span>'
                for name, val in top_emos
            )

            card = f"""
            <div class="exec-card" style="flex:0 0 auto;width:340px;white-space:normal;
            border-left:3px solid {border_color}">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div class="exec-card-title">{lugar.get('lugar','—').upper()}</div>
                    <div style="font-size:10px;color:{border_color};font-weight:600">
                    {lugar.get('n_comentarios',0)} coms · {emo_dom.upper() if emo_dom else '—'}</div>
                </div>
                <div style="font-size:10px;color:var(--fg-muted);margin-top:2px">
                Tensión {tension:.0f}%</div>
                {thermo_bar}
                {tema_str}
                {emo_chips}
                {citas_html}
                {narrativa_html}
            </div>
            """
            cards_html.append(card)

        scroll_container = f"""
        <div style="display:flex;flex-direction:row;gap:12px;overflow-x:auto;
        overflow-y:hidden;padding-bottom:8px;max-width:100%">{''.join(cards_html)}</div>
        """
        st.markdown(" ".join(scroll_container.split()), unsafe_allow_html=True)

        for lugar in sorted_lugares:
            _expander_enlaces(lugar.get("enlaces_referencia", []), label=f"Ver enlaces de {lugar.get('lugar','este lugar')}")

    # ── Pulso IQ ──────────────────────────────────────────────────────
    iq = b1.get("pulso_iq", {})
    if iq.get("valor") or iq.get("cuadrante"):
        iq_val = iq.get("valor", 0)
        iq_cuad = iq.get("cuadrante", "—")
        iq_narr = _get(iq, "narrativa", default="—")
        iq_comp = iq.get("componentes", {})
        chips_iq = "".join(
            f'<span style="font-size:11px;padding:2px 8px;background:var(--bg-elevated);'
            f'border-radius:10px;color:var(--fg-secondary);margin:2px">{k.capitalize()} '
            f'<strong>{v:.0f}</strong></span>'
            for k, v in iq_comp.items() if v
        )
        st.markdown(f"""
        <div style="margin-top:12px">
            <div class="section-header"><div class="section-title">Pulso en un Número</div></div>
            <div class="panel" style="text-align:center">
                <div style="font-size:64px;font-weight:700;color:var(--accent);line-height:1">{iq_val}</div>
                <div style="font-family:var(--font-mono);font-size:10px;letter-spacing:1.5px;
                text-transform:uppercase;color:var(--fg-muted);margin-top:8px">{iq_cuad.upper()}</div>
                <div style="font-size:12px;color:var(--fg-secondary);margin-top:10px;line-height:1.6">{iq_narr}</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;justify-content:center">{chips_iq}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        _card_explicacion_simple(iq.get("explicacion_simple", ""))
        _expander_enlaces(iq.get("enlaces_referencia", []))

    # ── Cierre factual ────────────────────────────────────────────────
    cierre = b1.get("cierre_factual", "")
    if cierre:
        st.markdown(f"""
        <div class="interpretation" style="margin-top:16px">
            <div class="interpretation-label">En resumen:</div>
            <div class="interpretation-texto">{cierre}</div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# BLOQUE II — SEGMENTACIÓN DE AUDIENCIA
# ════════════════════════════════════════════════════════════
with tab_audiencia:
    b2 = data.get("bloque2", {})

    st.markdown("""
    <div class="page-head">
        <div class="page-overline">BLOQUE II</div>
        <div class="page-h">Segmentación de Audiencia</div>
        <div class="page-sub">Mapa de públicos, polarización, voces de influencia
        y temas emergentes detectados en la conversación.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 07 · Mapa de Públicos ─────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">07 · Mapa de Públicos</div></div>', unsafe_allow_html=True)
    mp = b2.get("mapa_publicos", {})
    mp_sim = mp.get("pct_simpatizantes", 0)
    mp_neu = mp.get("pct_neutrales", 0)
    mp_crit = mp.get("pct_criticos", 0)
    mp_n = mp.get("n_total", 0)
    formula_mp = mp.get("formula_usada", "")
    n_sim = mp.get("n_simpatizantes", 0)
    n_neu = mp.get("n_neutrales", 0)
    n_crit = mp.get("n_criticos", 0)
    total_posts = mp.get("total_posts_analizados", 0)

    _card_explicacion_simple(mp.get("explicacion_simple",""))

    st.markdown(f"""
    <div class="panel">
        <div class="panel-head">
            <div class="panel-title">DISTRIBUCIÓN DE COMENTARIOS</div>
            <div class="panel-meta">{mp_n:,} COMENTARIOS ANALIZADOS</div>
        </div>
        <div class="bar-tri" style="height:18px;border-radius:3px">
            <span class="bar-tri-pos" style="width:{mp_sim:.1f}%"></span>
            <span class="bar-tri-neu" style="width:{mp_neu:.1f}%"></span>
            <span class="bar-tri-neg" style="width:{mp_crit:.1f}%"></span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:13px">
            <span style="color:var(--green)">Simpatizantes {mp_sim:.0f}%</span>
            <span style="color:var(--amber)">Neutrales {mp_neu:.0f}%</span>
            <span style="color:var(--red)">Críticos {mp_crit:.0f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if n_sim or n_neu or n_crit:
        st.markdown(f"""
        <div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin-bottom:8px">
            <div class="stat-card">
                <div class="stat-value" style="color:var(--green)">{n_sim:,}</div>
                <div class="stat-label">SIMPATIZANTES</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:var(--amber)">{n_neu:,}</div>
                <div class="stat-label">NEUTRALES</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color:var(--red)">{n_crit:,}</div>
                <div class="stat-label">CRÍTICOS</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if total_posts:
        st.caption(f"De {mp_n} comentarios analizados de {total_posts} publicaciones")
    if formula_mp:
        st.caption(f"Fórmula: {formula_mp}")

    _expander_enlaces(mp.get("enlaces_referencia",[]))

    # ── 08 · Polarización ─────────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">08 · Polarización</div></div>', unsafe_allow_html=True)
    pol = b2.get("polarizacion", {})
    pol_idx = pol.get("indice", 0)
    pol_nivel = pol.get("nivel", "—")
    pol_narr = _get(pol, "narrativa", default="—")
    pol_nota = pol.get("nota_metodologica", "")
    pol_color = {"confrontación": "var(--red)", "dividida": "var(--amber)", "consenso": "var(--green)"}.get(pol_nivel, "var(--accent)")
    st.markdown(f"""
    <div class="indicator indicator-{'critical' if pol_nivel=='confrontación' else ('warning' if pol_nivel=='dividida' else 'positive')}">
        <div class="indicator-dot"></div>
        <div>
            <div class="indicator-text">{pol_nivel.upper()}</div>
            <div style="font-size:12px;color:var(--fg-secondary);margin-top:4px">{pol_narr}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if pol_nota:
        st.markdown(
            f'<div class="status-info"><span class="status-label status-label-caution">LIMITACIÓN</span> '
            f'{pol_nota}</div>',
            unsafe_allow_html=True
        )

    _card_explicacion_simple(pol.get("explicacion_simple",""))
    _expander_enlaces(pol.get("enlaces_referencia",[]))

    # ── 09 · Voces de Influencia (EXPANDIDA) ──────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">09 · Voces de Influencia</div></div>', unsafe_allow_html=True)
    voces = b2.get("voces_influencia", [])
    if voces:
        for v in voces:
            postura = v.get("postura", "")
            postura_badge = ""
            if postura:
                pc = {"positiva": "var(--green)", "neutral": "var(--amber)", "negativa": "var(--red)"}.get(postura, "var(--fg-muted)")
                postura_badge = f'<span style="font-family:var(--font-mono);font-size:9px;color:{pc};font-weight:600;text-transform:uppercase">· {postura}</span>'

            cita_v = v.get("cita_destacada", "")
            cita_html = f'<div style="font-size:11px;color:var(--fg-secondary);font-style:italic;margin-top:6px">"{cita_v}"</div>' if cita_v else ""

            eng = v.get("engagement", 0)
            sum_sub = v.get("reacciones_totales", 0) + v.get("comentarios_totales", 0) + v.get("compartidos_totales", 0)
            inconsistente = eng > 0 and sum_sub == 0
            inc_badge = '<span style="font-family:var(--font-mono);font-size:9px;color:var(--amber);font-weight:600;text-transform:uppercase">⚠️ Dato inconsistente: engagement reportado sin submétricas</span>' if inconsistente else ""

            _render_card(f"""
            <div class="exec-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div class="exec-card-title">{v.get('pagina','—')} {postura_badge}</div>
                </div>
                {inc_badge}
                <div style="font-family:var(--font-mono);font-size:10px;color:var(--fg-secondary);margin:6px 0">
                    Publicaciones: <strong>{v.get('publicaciones',0):,}</strong> ·
                    Alcance: <strong>{v.get('alcance_estimado',0):,}</strong> ·
                    Engagement: <strong>{eng:,}</strong> ·
                    Reacciones: <strong>{v.get('reacciones_totales',0):,}</strong> ·
                    Comentarios: <strong>{v.get('comentarios_totales',0):,}</strong> ·
                    Compartidos: <strong>{v.get('compartidos_totales',0):,}</strong>
                </div>
                <div style="font-size:11px;color:var(--fg-muted)">
                    Tema predominante: <strong>{v.get('tema_predominante','—')}</strong> ·
                    Tono: <strong>{v.get('tono_predominante','—')}</strong>
                </div>
                {cita_html}
                <div style="font-family:var(--font-mono);font-size:9px;color:var(--fg-dim);margin-top:6px">
                n_enlaces: {v.get('n_enlaces',0)}</div>
            </div>
            """)
            _expander_enlaces(v.get("enlaces_referencia",[]), label="Ver enlaces de esta voz")
    else:
        st.markdown('<div class="status-info">Sin datos de voces de influencia.</div>', unsafe_allow_html=True)

    # ── 10 · Temas Emergentes LDA (EXPANDIDA) ─────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">10 · Temas Emergentes</div></div>', unsafe_allow_html=True)
    temas_lda = b2.get("temas_emergentes_lda", [])
    if temas_lda:
        for t in temas_lda:
            tendencia_lda = t.get("tendencia", "")
            tend_badge = ""
            if tendencia_lda == "acelerando":
                tend_badge = '<span style="color:var(--red);font-size:10px">🔺 ACELERANDO</span>'
            elif tendencia_lda == "desacelerando":
                tend_badge = '<span style="color:var(--green);font-size:10px">🔻 DESACELERANDO</span>'

            pct_apoyo_t = t.get("pct_apoyo", 0)
            pct_neu_t = t.get("pct_neutral", 0)
            pct_crit_t = t.get("pct_critica", 0)

            # Top 5 emociones del tema
            ie_tema = t.get("indice_emociones", {})
            emos_tema = ""
            if ie_tema and isinstance(ie_tema, dict):
                sorted_emos = sorted(
                    [(k, v) for k, v in ie_tema.items() if k.startswith("pct_") and v],
                    key=lambda x: x[1], reverse=True
                )[:5]
                if sorted_emos:
                    emo_labels = []
                    for ek, ev in sorted_emos:
                        ename = ek.replace("pct_", "")
                        emo_labels.append(f"{ename} {ev:.1f}%")
                    emos_tema = " · ".join(emo_labels)

            # Palabras clave como chips
            palabras = t.get("palabras_clave", [])
            chips = "".join(
                f'<span style="display:inline-block;font-family:var(--font-mono);font-size:9px;color:var(--accent);background:var(--accent-soft);padding:2px 8px;border-radius:2px;margin:2px 4px 2px 0">{p}</span>'
                for p in palabras
            )

            ejemplos = "".join(
                f'<div style="font-size:11px;color:var(--fg-secondary);font-style:italic;margin-top:3px">"{e}"</div>'
                for e in t.get("comentarios_ejemplo", [])[:2]
            )

            _render_card(f"""
            <div class="exec-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div class="exec-card-title">{t.get('tema','—').upper()} · PESO {t.get('peso',0):.2f}</div>
                    {tend_badge}
                </div>
                <div style="font-family:var(--font-mono);font-size:10px;color:var(--fg-muted);margin:6px 0">
                {t.get('n_comentarios',0)} coment · {t.get('pct_del_total',0):.1f}% del total ·
                Δ sem: {t.get('pct_cambio_semana',0):.1f}%</div>
                {f'<div class="bar-tri" style="height:6px;width:120px;margin:6px 0"><span class="bar-tri-pos" style="width:{pct_apoyo_t:.0f}%"></span><span class="bar-tri-neu" style="width:{pct_neu_t:.0f}%"></span><span class="bar-tri-neg" style="width:{pct_crit_t:.0f}%"></span></div>' if pct_apoyo_t or pct_neu_t or pct_crit_t else ''}
                {f'<div style="font-size:10px;color:var(--fg-secondary);margin:4px 0">{emos_tema}</div>' if emos_tema else ''}
                {f'<div style="margin:4px 0">{chips}</div>' if chips else ''}
                {ejemplos}
            </div>
            """)
    else:
        st.markdown('<div class="status-info">Mínimo 10 comentarios requeridos para detectar temas emergentes.</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# BLOQUE III — RIESGO Y AUTENTICIDAD
# ════════════════════════════════════════════════════════════
with tab_riesgo:
    b3 = data.get("bloque3", {})

    st.markdown("""
    <div class="page-head">
        <div class="page-overline">BLOQUE III</div>
        <div class="page-h">Riesgo y Autenticidad</div>
        <div class="page-sub">Autenticidad de la conversación, nivel de alerta
        institucional, velocidad de propagación y puntos de fricción activos.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 11 · Autenticidad ─────────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">11 · Autenticidad</div></div>', unsafe_allow_html=True)
    aut = b3.get("autenticidad", {})
    aut_org = aut.get("pct_organico", 0)
    aut_coo = aut.get("pct_coordinado", 0)
    aut_dup = aut.get("n_duplicados", 0)
    aut_narr = _get(aut, "narrativa", default="—")
    formula_aut = aut.get("formula_usada", "")
    st.markdown(f"""
    <div class="panel">
        <div class="panel-head">
            <div class="panel-title">ORGÁNICO VS COORDINADO</div>
            <div class="panel-meta">{aut_dup} MENSAJES DUPLICADOS DETECTADOS</div>
        </div>
        <div style="font-size:13px;color:var(--fg-secondary);line-height:1.7;
        margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border)">
            {aut_narr}
        </div>
        <div class="bar-row">
            <div class="bar-row-label">ORGÁNICO</div>
            <div class="bar-track"><div class="bar-fill bar-fill-grn" style="width:{aut_org:.1f}%"></div></div>
            <div class="bar-row-val" style="color:var(--green)">{aut_org:.0f}%</div>
        </div>
        <div class="bar-row">
            <div class="bar-row-label">COORDINADO</div>
            <div class="bar-track"><div class="bar-fill bar-fill-red" style="width:{aut_coo:.1f}%"></div></div>
            <div class="bar-row-val" style="color:var(--red)">{aut_coo:.0f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    _card_explicacion_simple(aut.get("explicacion_simple", ""))
    _expander_enlaces(aut.get("enlaces_referencia", []))
    if formula_aut:
        st.caption(f"Fórmula: {formula_aut}")

    # ── 12 · Nivel de Alerta ──────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">12 · Nivel de Alerta</div></div>', unsafe_allow_html=True)
    na = b3.get("nivel_alerta", {})
    semaforo = na.get("semaforo", "verde")
    riesgo = na.get("indice_riesgo", 0)
    tema_ppal = na.get("tema_principal", "")
    emocion_ppal = na.get("emocion_principal", "")
    alertas_cb = na.get("alertas_cambridge", [])
    formula_riesgo = na.get("formula_riesgo", "")
    sem_map = {"verde": ("positive", "var(--green)", "SITUACIÓN CONTROLADA"),
               "amarillo": ("warning", "var(--amber)", "ATENCIÓN REQUERIDA"),
               "rojo": ("critical", "var(--red)", "ALERTA ACTIVA")}
    sem_cls, sem_col, sem_lbl = sem_map.get(semaforo, sem_map["verde"])

    riesgo_sub = f"Índice de riesgo {riesgo}/100"
    if tema_ppal or emocion_ppal:
        riesgo_sub += f" — impulsado por {tema_ppal}" if tema_ppal else ""
        riesgo_sub += f" con emoción dominante {emocion_ppal}" if emocion_ppal else ""

    st.markdown(f"""
    <div class="indicator indicator-{sem_cls}">
        <div class="indicator-dot"></div>
        <div>
            <div class="indicator-text">{sem_lbl}</div>
            <div style="font-family:var(--font-mono);font-size:11px;
            color:var(--fg-muted);margin-top:4px">
            {riesgo_sub}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    na_pct_neg = na.get("pct_negativos", 0)
    na_idx_enojo = na.get("indice_enojo_reacciones", 0)
    na_bal_conf = na.get("balance_confrontacion", 0)
    na_n_fricc = na.get("n_temas_friccion", 0)
    st.markdown(f"""
    <div class="stat-row" style="grid-template-columns:repeat(4,1fr);margin-bottom:8px">
        <div class="stat-card">
            <div class="stat-value" style="color:var(--red)">{na_pct_neg:.1f}%</div>
            <div class="stat-label">% NEGATIVOS</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:var(--amber)">{na_idx_enojo:.1f}</div>
            <div class="stat-label">ÍNDICE ENOJO</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:var(--red)">{na_bal_conf:.1f}</div>
            <div class="stat-label">BALANCE CONFRONTACIÓN</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="color:var(--amber)">{na_n_fricc}</div>
            <div class="stat-label">TEMAS EN FRICCIÓN</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    _card_explicacion_simple(na.get("explicacion_simple", ""))
    if formula_riesgo:
        st.caption(f"Fórmula de riesgo: {formula_riesgo}")

    if alertas_cb:
        for alerta in alertas_cb:
            st.markdown(f"""
            <div class="pattern-card pattern-card-critical">
                <div style="font-family:var(--font-mono);font-size:9px;
                color:var(--red);letter-spacing:1.4px;font-weight:600;
                text-transform:uppercase">{alerta.get('tipo','—')}</div>
                <div style="font-size:12px;color:var(--fg-secondary);
                margin-top:4px">{alerta.get('descripcion','—')}</div>
            </div>
            """, unsafe_allow_html=True)
            _expander_enlaces(alerta.get("enlaces_referencia", []))

    # ── 13 · Velocidad de Propagación (EXPANDIDA) ─────────────────────
    st.markdown('<div class="section-header"><div class="section-title">13 · Velocidad de Propagación</div></div>', unsafe_allow_html=True)
    vp = b3.get("velocidad_propagacion", {})
    vp_proy = vp.get("proyeccion_24h", "—")
    vp_narr = _get(vp, "narrativa", default="—")
    vp_formula = vp.get("formula_usada", "")
    vp_col = {"acelerando": "var(--red)", "estable": "var(--accent)", "desacelerando": "var(--green)"}.get(vp_proy, "var(--fg-muted)")
    st.markdown(f"""
    <div class="exec-card">
        <div class="exec-card-title">PROYECCIÓN 24-48H</div>
        <div class="exec-card-value" style="color:{vp_col}">{vp_proy.upper()}</div>
        <div class="exec-card-sub">{vp_narr}</div>
    </div>
    """, unsafe_allow_html=True)
    if vp_formula:
        st.caption(f"Fórmula: {vp_formula}")
    _card_explicacion_simple(vp.get("explicacion_simple", ""))
    _expander_enlaces(vp.get("enlaces_referencia", []))

    # Serie diaria de tendencia
    tendencia_dias = vp.get("tendencia_dias", [])
    if tendencia_dias:
        st.markdown('<div style="margin:12px 0 6px;font-size:12px;color:var(--fg-secondary)">Tendencia diaria</div>', unsafe_allow_html=True)
        if isinstance(tendencia_dias[0], dict):
            df = pd.DataFrame(tendencia_dias)
        else:
            df = pd.DataFrame({"valor": tendencia_dias})
        st.line_chart(df, use_container_width=True, height=200)

    temas_acel_vp = vp.get("temas_acelerando", [])
    temas_desacel_vp = vp.get("temas_desacelerando", [])
    if temas_acel_vp or temas_desacel_vp:
        st.markdown(f"""
        <div style="display:flex;gap:20px;flex-wrap:wrap;margin:6px 0 10px;font-size:12px">
            <div><span style="color:var(--red)">🔺 TEMAS ACELERANDO:</span>
            <span style="color:var(--fg-secondary)"> {', '.join(temas_acel_vp) if temas_acel_vp else '—'}</span></div>
            <div><span style="color:var(--green)">🔻 TEMAS DESACELERANDO:</span>
            <span style="color:var(--fg-secondary)"> {', '.join(temas_desacel_vp) if temas_desacel_vp else '—'}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ── 14 · Puntos de Fricción (EXPANDIDA) ───────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">14 · Puntos de Fricción</div></div>', unsafe_allow_html=True)
    fricciones = b3.get("puntos_friccion", [])
    if fricciones:
        for fr in fricciones:
            accel_badge = "🔺 ACELERANDO" if fr.get("acelerando") else ""
            n_comp_total = fr.get("n_comentarios_total", 0)
            n_neg = fr.get("n_negativos", 0)
            if n_comp_total > 0:
                fr_count_str = f"{n_neg} de {n_comp_total} comentarios ({fr.get('pct_del_total', 0):.1f}%)"
            else:
                fr_count_str = f"{n_neg} neg"
            _render_card(f"""
            <div class="pattern-card pattern-card-critical">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <div style="font-family:var(--font-mono);font-size:10px;
                    color:var(--red);font-weight:600;letter-spacing:1px;
                    text-transform:uppercase">{fr.get('tema','—')} · {fr.get('zona','—')}</div>
                    <div style="display:flex;gap:8px;align-items:center">
                        <div style="font-family:var(--font-mono);font-size:10px;
                        color:var(--fg-muted)">{fr_count_str}</div>
                        <div style="font-size:10px;color:var(--red)">{accel_badge}</div>
                    </div>
                </div>
                <div style="font-size:12px;color:var(--fg-secondary);
                font-style:italic">"{fr.get('cita','—')}"</div>
                <div style="font-family:var(--font-mono);font-size:10px;
                color:var(--amber);margin-top:6px">
                Emoción: {fr.get('emocion_dominante','—')} · 
                Enojo reacciones: {fr.get('reacciones_enojo',0)}</div>
                <div style="font-size:11px;color:var(--accent);margin-top:6px;
                border-top:1px solid var(--border);padding-top:6px">
                ⟶ {fr.get('recomendacion_accion','—')}</div>
            </div>
            """)
            _card_explicacion_simple(fr.get("explicacion_simple", ""))
            _expander_enlaces(fr.get("enlaces_relacionados", []), label="Ver enlaces de este punto")
    else:
        st.markdown('<div class="status-info">Sin puntos de fricción activos en el período.</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# BLOQUE IV — MEMORÁNDUM ESTRATÉGICO
# ════════════════════════════════════════════════════════════
with tab_intel:
    b4 = data.get("bloque4", {})
    meta = data.get("meta", {})

    st.markdown("""
    <div class="page-head">
        <div class="page-overline">BLOQUE IV</div>
        <div class="page-h">Memorándum Estratégico</div>
        <div class="page-sub">Briefing ejecutivo de inteligencia aplicada:
        contexto histórico, narrativas, riesgos y recomendaciones.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 15 · Recomendaciones Basadas en Métricas (NUEVA) ──────────────
    recos = b4.get("recomendaciones_basadas_en_metricas", [])
    if recos:
        st.markdown('<div class="section-header"><div class="section-title">15 · Recomendaciones Basadas en Métricas</div></div>', unsafe_allow_html=True)
        for r in recos:
            prioridad_color = {"alta": "var(--red)", "media": "var(--amber)", "baja": "var(--green)"}.get(r.get("prioridad",""), "var(--fg-muted)")
            st.markdown(f"""
            <div class="exec-card" style="border-left:3px solid {prioridad_color}">
                <div style="display:flex;justify-content:space-between">
                    <div class="exec-card-title">REC #{r.get('numero',0)} · PRIORIDAD {r.get('prioridad','—').upper()}</div>
                    <div style="font-family:var(--font-mono);font-size:10px;color:var(--fg-muted)">
                    {r.get('metrica_base','—')}: {r.get('valor_metrica',0)}</div>
                </div>
                <div style="font-size:13px;color:var(--fg-primary);margin-top:6px">{r.get('recomendacion','—')}</div>
                <div style="font-family:var(--font-mono);font-size:10px;color:var(--fg-muted);margin-top:4px">
                Umbral de acción: {r.get('umbral_accion','—')}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Memorándum existente ──────────────────────────────────────────
    st.markdown(f"""
    <div class="memo-container">
        <div class="memo-header">
            <div class="memo-title">MEMORÁNDUM DE INTELIGENCIA CIUDADANA</div>
            <div class="memo-ref">PERÍODO: {meta.get('periodo','—').upper()} ·
            DATOS HASTA: {meta.get('fecha_datos_hasta','—')} ·
            PLATAFORMA: {meta.get('plataforma','—').upper()} ·
            CLASIFICACIÓN: CONFIDENCIAL</div>
        </div>
    """, unsafe_allow_html=True)

    _secciones = [
        ("01", "Eco Histórico", "eco_historico"),
        ("02", "Lección Aprendida", "leccion_aprendida"),
        ("03", "Brecha Percepción-Realidad", "brecha_percepcion_realidad"),
        ("05", "Contexto No Visible", "contexto_no_visible"),
        ("06", "Correlación Contenido-Reacción", "correlacion_contenido_reaccion"),
        ("07", "Comparativa Sectorial", "comparativa_sectorial"),
        ("08", "Proyección de Escenario", "proyeccion_escenario"),
        ("09", "Recomendación Estratégica", "recomendacion_estrategica"),
    ]
    for num, titulo, key in _secciones:
        raw = b4.get(key, {})
        if isinstance(raw, dict):
            texto = _get(raw, "narrativa", default="—")
            enlaces = raw.get("enlaces_referencia", [])
        else:
            texto = raw if raw else "—"
            enlaces = []
        if texto and texto != "—":
            st.markdown(f"""
            <div class="memo-section">
                <div class="memo-section-number">§ {num}</div>
                <div class="memo-section-title">{titulo}</div>
                <div class="memo-body">{texto}</div>
            </div>
            <hr class="memo-divider">
            """, unsafe_allow_html=True)
        _expander_enlaces(enlaces, label=f"Ver fuentes — {titulo}")

    # Temas emergentes evolución
    temas_evo = b4.get("temas_emergentes_evolucion", [])
    if temas_evo:
        st.markdown("""
        <div class="memo-section">
            <div class="memo-section-number">§ 04</div>
            <div class="memo-section-title">Temas Emergentes — Evolución</div>
        </div>
        """, unsafe_allow_html=True)
        estado_col = {"emergente": "var(--amber)", "en auge": "var(--green)", "en declive": "var(--red)", "en extinción": "var(--red)", "estable": "var(--fg-muted)"}
        for t in temas_evo:
            col = estado_col.get(t.get("estado",""), "var(--fg-muted)")
            st.markdown(f"""
            <div class="memo-item" style="border-left-color:{col};color:{col}">
                {t.get('tema','—')} ·
                <span style="color:var(--fg-secondary)">{t.get('estado','—').upper()}</span> ·
                {t.get('variacion_semanal','—')}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Temas en extinción
    temas_ext = b4.get("temas_extinction", [])
    if temas_ext:
        st.markdown('<div class="section-header" style="margin-top:20px"><div class="section-title">Temas en Extinción</div></div>', unsafe_allow_html=True)
        for t in temas_ext:
            st.markdown(f"""
            <div class="memo-item memo-item-negativo">
                {t.get('tema','—')} · {t.get('variacion_semanal','—')}
            </div>
            """, unsafe_allow_html=True)

    # ── 16 · Resumen de Evidencia (NUEVA) ─────────────────────────────
    ev = b4.get("resumen_evidencia", {})
    enlaces = data.get("meta", {}).get("enlaces_analizados", [])

    if ev or enlaces:
        st.markdown('<div class="section-header" style="margin-top:24px"><div class="section-title">16 · Evidencia y Respaldo</div></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head">
                <div class="panel-title">FUENTES ANALIZADAS</div>
                <div class="panel-meta">{ev.get('periodo_cobertura','—')}</div>
            </div>
            <div class="stat-row" style="grid-template-columns:repeat(4,1fr)">
                <div class="stat-card">
                    <div class="stat-value">{ev.get('total_enlaces_analizados',0)}</div>
                    <div class="stat-label">ENLACES</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{ev.get('total_reacciones_sumadas',0):,}</div>
                    <div class="stat-label">REACCIONES</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{ev.get('total_impresiones',0):,}</div>
                    <div class="stat-label">IMPRESIONES</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{ev.get('total_comentarios',0):,}</div>
                    <div class="stat-label">COMENTARIOS</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if enlaces:
            st.markdown('<div class="exec-subheader">Lista de enlaces analizados</div>', unsafe_allow_html=True)
            for url in enlaces:
                st.markdown(
                    f'<a href="{url}" target="_blank" rel="noopener" '
                    f'style="display:block;font-family:var(--font-mono);font-size:10px;'
                    f'color:var(--accent);margin:3px 0;text-decoration:none">🔗 {url}</a>',
                    unsafe_allow_html=True
                )
