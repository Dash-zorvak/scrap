"""PANEL·SANTA ANA — Inteligencia Ciudadana.

Lee data/analysis.json generado por el analista externo y renderiza
los cuatro bloques ejecutivos. Sin cálculo en runtime, sin ML, sin LLM.
"""

import json
import os
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
    narrativa_cn = cn.get("narrativa", "Sin datos de clima narrativo.")

    tend_color = "var(--green)" if tend > 0.1 else ("var(--red)" if tend < -0.1 else "var(--amber)")
    tend_label = "↑ mejorando" if tend > 0.1 else ("↓ empeorando" if tend < -0.1 else "→ estable")

    st.markdown(f"""
    <div class="interpretation">
        <div class="interpretation-label">LECTURA EJECUTIVA</div>
        <div class="interpretation-texto">{narrativa_cn}</div>
    </div>
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

    # ── 02 · Intensidad ───────────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">02 · Intensidad de la Conversación</div></div>', unsafe_allow_html=True)
    it = b1.get("intensidad", {})
    vol_hoy = it.get("vol_hoy", 0)
    prom = it.get("promedio_semanal", 0)
    pct = it.get("pct_diferencia", 0)
    etiq_int = it.get("etiqueta", "—")
    narrativa_it = it.get("narrativa", "Sin datos de intensidad.")
    maxv = max(vol_hoy, prom, 1)

    col_hoy = "var(--red)" if pct > 15 else ("var(--blue)" if pct < -15 else "var(--accent)")
    signo = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"

    st.markdown(f"""
    <div class="interpretation">
        <div class="interpretation-label">LECTURA EJECUTIVA</div>
        <div class="interpretation-texto">{narrativa_it}</div>
    </div>
    <div class="panel">
        <div class="panel-head">
            <div class="panel-title">INTENSIDAD DEL ÚLTIMO DÍA</div>
            <div class="panel-meta">{it.get('fecha_hoy','—')} ·
            {it.get('n_dias_referencia',0)} DÍAS DE REFERENCIA</div>
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
    """, unsafe_allow_html=True)

    # ── 03 · Concentración Temática ───────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">03 · Concentración Temática</div></div>', unsafe_allow_html=True)
    ct = b1.get("concentracion_tematica", {})
    ramas = ct.get("ramas", [])
    nivel_ct = ct.get("nivel", "")
    narrativa_ct = ct.get("narrativa", "Sin datos de concentración temática.")
    col_ct = {"dominado": "var(--red)", "liderado": "var(--amber)", "fragmentado": "var(--green)"}.get(nivel_ct, "var(--accent)")
    paleta = ["var(--accent)","#a78bfa","#f59e0b","#34d399","#f472b6","#60a5fa","#fbbf24","#4ade80","#fb7185","#818cf8"]
    segmentos = "".join(f'<span style="display:inline-block;height:100%;background:{paleta[i%len(paleta)]};width:{r.get("share",0):.1f}%"></span>' for i,r in enumerate(ramas))
    filas = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin-top:6px;font-size:13px">'
        f'<span style="width:10px;height:10px;border-radius:2px;background:{paleta[i%len(paleta)]};display:inline-block;flex:none"></span>'
        f'<span style="flex:1;color:var(--fg-primary)">{r.get("tema","—")}</span>'
        f'<span style="color:var(--fg-secondary)">{r.get("n",0)} publicaciones · {r.get("share",0):.0f}%</span>'
        f'</div>'
        for i,r in enumerate(ramas)
    )

    st.markdown(f"""
    <div class="interpretation">
        <div class="interpretation-label">LECTURA EJECUTIVA</div>
        <div class="interpretation-texto">{narrativa_ct}</div>
    </div>
    <div class="panel">
        <div class="panel-head">
            <div class="panel-title" style="color:{col_ct}">{ct.get('estado','—').upper()}</div>
            <div class="panel-meta">{ct.get('n_temas',0)} TEMAS</div>
        </div>
        <div class="bar-tri" style="height:18px;border-radius:3px">{segmentos}</div>
        <div style="margin-top:12px">{filas}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sub-tarjetas ──────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        # Termómetro colonias
        st.markdown('<div class="section-header"><div class="section-title">Termómetro de Colonias</div></div>', unsafe_allow_html=True)
        colonias = b1.get("termometro_colonias", [])
        if colonias:
            filas_col = "".join(
                f'<div class="bar-row">'
                f'<div class="bar-row-label">{c.get("zona","—")}</div>'
                f'<div class="bar-track"><div class="bar-fill bar-fill-grn" style="width:{c.get("pct_apoyo",0):.0f}%"></div></div>'
                f'<div class="bar-row-val" style="color:var(--green)">{c.get("pct_apoyo",0):.0f}% apoyo</div>'
                f'</div>'
                for c in colonias
            )
            st.markdown(f'<div class="panel">{filas_col}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-info">Sin datos de zonas.</div>', unsafe_allow_html=True)

    with col_b:
        # Pulso IQ
        st.markdown('<div class="section-header"><div class="section-title">Pulso en un Número</div></div>', unsafe_allow_html=True)
        iq = b1.get("pulso_iq", {})
        iq_val = iq.get("valor", 0)
        iq_cuad = iq.get("cuadrante", "—")
        iq_narr = iq.get("narrativa", "—")
        st.markdown(f"""
        <div class="panel" style="text-align:center">
            <div style="font-size:64px;font-weight:700;color:var(--accent);line-height:1">{iq_val}</div>
            <div style="font-family:var(--font-mono);font-size:10px;letter-spacing:1.5px;
            text-transform:uppercase;color:var(--fg-muted);margin-top:8px">{iq_cuad.upper()}</div>
            <div style="font-size:12px;color:var(--fg-secondary);margin-top:10px;line-height:1.6">{iq_narr}</div>
        </div>
        """, unsafe_allow_html=True)

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

    # ── 04 · Mapa de Públicos ─────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">04 · Mapa de Públicos</div></div>', unsafe_allow_html=True)
    mp = b2.get("mapa_publicos", {})
    mp_sim = mp.get("pct_simpatizantes", 0)
    mp_neu = mp.get("pct_neutrales", 0)
    mp_crit = mp.get("pct_criticos", 0)
    mp_n = mp.get("n_total", 0)
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

    # ── 05 · Polarización ─────────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">05 · Polarización</div></div>', unsafe_allow_html=True)
    pol = b2.get("polarizacion", {})
    pol_idx = pol.get("indice", 0)
    pol_nivel = pol.get("nivel", "—")
    pol_narr = pol.get("narrativa", "—")
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

    # ── 06 · Voces de Influencia ──────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">06 · Voces de Influencia</div></div>', unsafe_allow_html=True)
    voces = b2.get("voces_influencia", [])
    if voces:
        max_eng = max((v.get("engagement", 0) for v in voces), default=1)
        filas_v = "".join(
            f'<div class="bar-row">'
            f'<div class="bar-row-label">{v.get("pagina","—")}</div>'
            f'<div class="bar-track"><div class="bar-fill bar-fill-cy" style="width:{v.get("engagement",0)/max_eng*100:.1f}%"></div></div>'
            f'<div class="bar-row-val">{v.get("engagement",0):,} · {v.get("publicaciones",0)} posts</div>'
            f'</div>'
            for v in voces
        )
        st.markdown(f'<div class="panel">{filas_v}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Sin datos de voces de influencia.</div>', unsafe_allow_html=True)

    # ── 07 · Temas Emergentes LDA ─────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">07 · Temas Emergentes</div></div>', unsafe_allow_html=True)
    temas_lda = b2.get("temas_emergentes_lda", [])
    if temas_lda:
        for t in temas_lda:
            ejemplos = " · ".join(f'"{e}"' for e in t.get("comentarios_ejemplo", [])[:2])
            st.markdown(f"""
            <div class="exec-card">
                <div class="exec-card-title">{t.get('tema','—').upper()} · PESO {t.get('peso',0):.2f}</div>
                <div style="font-size:12px;color:var(--fg-secondary);margin-top:4px">{ejemplos}</div>
            </div>
            """, unsafe_allow_html=True)
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

    # ── 08 · Autenticidad ─────────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">08 · Autenticidad</div></div>', unsafe_allow_html=True)
    aut = b3.get("autenticidad", {})
    aut_org = aut.get("pct_organico", 0)
    aut_coo = aut.get("pct_coordinado", 0)
    aut_dup = aut.get("n_duplicados", 0)
    aut_narr = aut.get("narrativa", "—")
    st.markdown(f"""
    <div class="interpretation">
        <div class="interpretation-label">LECTURA EJECUTIVA</div>
        <div class="interpretation-texto">{aut_narr}</div>
    </div>
    <div class="panel">
        <div class="panel-head">
            <div class="panel-title">ORGÁNICO VS COORDINADO</div>
            <div class="panel-meta">{aut_dup} MENSAJES DUPLICADOS DETECTADOS</div>
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

    # ── 09 · Nivel de Alerta ──────────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">09 · Nivel de Alerta</div></div>', unsafe_allow_html=True)
    na = b3.get("nivel_alerta", {})
    semaforo = na.get("semaforo", "verde")
    riesgo = na.get("indice_riesgo", 0)
    alertas_cb = na.get("alertas_cambridge", [])
    sem_map = {"verde": ("positive", "var(--green)", "SITUACIÓN CONTROLADA"),
               "amarillo": ("warning", "var(--amber)", "ATENCIÓN REQUERIDA"),
               "rojo": ("critical", "var(--red)", "ALERTA ACTIVA")}
    sem_cls, sem_col, sem_lbl = sem_map.get(semaforo, sem_map["verde"])

    st.markdown(f"""
    <div class="indicator indicator-{sem_cls}">
        <div class="indicator-dot"></div>
        <div>
            <div class="indicator-text">{sem_lbl}</div>
            <div style="font-family:var(--font-mono);font-size:11px;
            color:var(--fg-muted);margin-top:4px">
            ÍNDICE DE RIESGO: <span style="color:{sem_col}">{riesgo}/100</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if alertas_cb:
        for alerta in alertas_cb:
            st.markdown(f"""
            <div class="pattern-card pattern-card-critical">
                <div style="font-family:var(--font-mono);font-size:9px;
                color:var(--red);letter-spacing:1.4px;font-weight:600;
                text-transform:uppercase">{alerta.get('tipo','—')}</div>
                <div style="font-size:12px;color:var(--fg-secondary);
                margin-top:4px">{alerta.get('detalle','—')}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── 10 · Velocidad de Propagación ────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">10 · Velocidad de Propagación</div></div>', unsafe_allow_html=True)
    vp = b3.get("velocidad_propagacion", {})
    vp_proy = vp.get("proyeccion_24h", "—")
    vp_narr = vp.get("narrativa", "—")
    vp_col = {"acelerando": "var(--red)", "estable": "var(--accent)", "desacelerando": "var(--green)"}.get(vp_proy, "var(--fg-muted)")
    st.markdown(f"""
    <div class="exec-card">
        <div class="exec-card-title">PROYECCIÓN 24-48H</div>
        <div class="exec-card-value" style="color:{vp_col}">{vp_proy.upper()}</div>
        <div class="exec-card-sub">{vp_narr}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── 11 · Puntos de Fricción ───────────────────────────────────────
    st.markdown('<div class="section-header"><div class="section-title">11 · Puntos de Fricción</div></div>', unsafe_allow_html=True)
    fricciones = b3.get("puntos_friccion", [])
    if fricciones:
        for fr in fricciones:
            st.markdown(f"""
            <div class="pattern-card pattern-card-critical">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <div style="font-family:var(--font-mono);font-size:10px;
                    color:var(--red);font-weight:600;letter-spacing:1px;
                    text-transform:uppercase">{fr.get('tema','—')}</div>
                    <div style="font-family:var(--font-mono);font-size:10px;
                    color:var(--fg-muted)">{fr.get('n_negativos',0)} negativos</div>
                </div>
                <div style="font-size:12px;color:var(--fg-secondary);
                font-style:italic">"{fr.get('cita','—')}"</div>
            </div>
            """, unsafe_allow_html=True)
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
        texto = b4.get(key, "")
        if texto:
            st.markdown(f"""
            <div class="memo-section">
                <div class="memo-section-number">§ {num}</div>
                <div class="memo-section-title">{titulo}</div>
                <div class="memo-body">{texto}</div>
            </div>
            <hr class="memo-divider">
            """, unsafe_allow_html=True)

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
