"""PANEL·SANTA ANA — Inteligencia Ciudadana (dashboard del alcalde).

App delgada de SOLO LECTURA: arma la barra lateral (período/plataforma) y
despacha los cuatro bloques de análisis. La lógica de cada sección vive en
módulos dash_bloque1..4 y los helpers de UI en dash_ui. Esto evita un app.py
gigante y facilita el mantenimiento.

La carga de contenido vive en una app aparte (dashboard/panel_carga.py) que
solo usa el analista en local; este dashboard no expone ninguna opción de
ingesta.
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard"))

from config import FACEBOOK_DB, TIKTOK_DB
from dashboard.estilos import CSS
from dashboard.estilos_override import CSS_OVERRIDE
from dashboard.dash_periodos import OPCIONES_PERIODO
from dashboard.dash_ui import _docstrip
from dashboard.dash_bloque1 import render_bloque1_pulso
from dashboard.dash_bloque2 import render_bloque2_audiencia
from dashboard.dash_bloque3 import render_bloque3_riesgo
from dashboard.dash_bloque4 import render_bloque4_inteligencia
from dashboard.medalla_dashboard import render_descarga_medalla

st.set_page_config(
    page_title="PANEL·SANTA ANA — Inteligencia Ciudadana",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(CSS, unsafe_allow_html=True)
st.markdown(CSS_OVERRIDE, unsafe_allow_html=True)

# ─── Fecha de actualización (usada en topbar y sidebar) ─────
ultima_fecha = datetime.now()
try:
    conn = sqlite3.connect(FACEBOOK_DB)
    max_fb = pd.read_sql("SELECT MAX(created_time) as m FROM fb_engagement", conn).iloc[0]['m']
    conn.close()
    conn = sqlite3.connect(TIKTOK_DB)
    max_tk = pd.read_sql("SELECT MAX(created_at) as m FROM tiktok_engagement", conn).iloc[0]['m']
    conn.close()
    fechas = []
    if max_fb: fechas.append(pd.Timestamp(max_fb))
    if max_tk: fechas.append(pd.Timestamp(max_tk))
    ultima_fecha = max(fechas) if fechas else datetime.now()
    dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    meses_short = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
    fecha_str = f"{dias[ultima_fecha.weekday()]} {ultima_fecha.day} de {meses[ultima_fecha.month-1]}, {ultima_fecha.year}"
    fecha_corta = f"{ultima_fecha.day:02d} {meses_short[ultima_fecha.month-1]} {ultima_fecha.year}"
except Exception:
    fecha_str = "No disponible"
    fecha_corta = "N/D"

st.session_state["fecha_ref"] = ultima_fecha

# ─── Topbar institucional ──────────────
st.markdown(f"""
<div class="topbar">
    <div class="topbar-brand">PANEL <span class="sep">·</span> SANTA ANA <span class="sep">/</span> <span class="who">Inteligencia Ciudadana</span></div>
    <div class="topbar-meta">ACTUALIZADO <span class="acc">·</span> {fecha_str.upper()}</div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR · CONSOLA EJECUTIVA ───────
st.sidebar.markdown("""
<div class="sys-header">
    <div class="sys-brand">PANEL·SANTA ANA</div>
    <div class="sys-brand-sub">INTELIGENCIA CIUDADANA</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--r-sm);padding:11px 13px;margin-bottom:18px">
    <div style="display:flex;align-items:center;justify-content:space-between;font-family:var(--font-mono);font-size:11px;letter-spacing:1.4px;color:var(--fg-muted);font-weight:600;text-transform:uppercase">
        <span>SYS</span>
        <span style="display:flex;align-items:center;gap:6px">
            <span style="width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 0 3px rgba(34,197,94,0.18);display:inline-block"></span>
            <span style="color:var(--green);letter-spacing:1.2px">OPERACIONAL</span>
        </span>
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;font-family:var(--font-mono);font-size:11px;letter-spacing:1.2px;color:var(--fg-muted);font-weight:600;margin-top:9px;text-transform:uppercase">
        <span>FEED</span>
        <span style="color:var(--accent)">{fecha_corta}</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="sys-section-label" style="color:var(--accent);display:flex;align-items:center;gap:6px"><span style="font-size:8px">▣</span><span>PARÁMETROS</span></div>', unsafe_allow_html=True)

periodo = st.sidebar.selectbox("PERÍODO", OPCIONES_PERIODO)

if periodo == "Personalizado":
    _ref_date = pd.Timestamp(ultima_fecha).date()
    _c1, _c2 = st.sidebar.columns(2)
    with _c1:
        _desde = st.date_input("DESDE", value=_ref_date.replace(day=1), key="fp_desde")
    with _c2:
        _hasta = st.date_input("HASTA", value=_ref_date, key="fp_hasta")
    st.session_state["fecha_desde"] = _desde
    st.session_state["fecha_hasta"] = _hasta
else:
    st.session_state["fecha_desde"] = None
    st.session_state["fecha_hasta"] = None

plataforma = st.sidebar.selectbox("PLATAFORMA", [
    "Ambas", "Facebook", "TikTok"
])

st.sidebar.markdown(f"""
<div style="margin-top:26px;padding-top:14px;border-top:1px solid var(--border);font-family:var(--font-mono);color:var(--fg-muted);letter-spacing:0.4px;line-height:1.6">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;font-size:11px;text-transform:uppercase;letter-spacing:1.4px;font-weight:600">
        <span>ACTUALIZADO</span>
        <span style="color:var(--accent)">{fecha_corta}</span>
    </div>
    <div style="color:var(--fg-secondary);font-size:10.5px;line-height:1.5">{fecha_str}</div>
    <div style="color:var(--fg-dim);font-size:10px;margin-top:12px;letter-spacing:1px;text-transform:uppercase;border-top:1px solid var(--border-soft);padding-top:8px">PANEL·SANTA ANA <span style="color:var(--accent-2)">·</span> v1.0 <span style="color:var(--accent-2)">·</span> CONFIDENCIAL</div>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════
# DASHBOARD (solo lectura)
# ═════════════════════════════════════════════════════════

tab_pulso, tab_audiencia, tab_riesgo, tab_inteligencia = st.tabs([
    "PULSO GENERAL", "SEGMENTACIÓN DE AUDIENCIA",
    "RIESGO Y AUTENTICIDAD", "MEMORIA E INTELIGENCIA APLICADA"
])
with tab_pulso:
    render_bloque1_pulso(periodo, plataforma)
with tab_audiencia:
    render_bloque2_audiencia(periodo, plataforma)
with tab_riesgo:
    render_bloque3_riesgo(periodo, plataforma)
with tab_inteligencia:
    render_bloque4_inteligencia(periodo, plataforma)
    st.markdown("---")
    with st.expander("📄 Informe de la mejor medalla reciente", expanded=True):
        render_descarga_medalla(periodo)

_docstrip(periodo, plataforma, fecha_str)
