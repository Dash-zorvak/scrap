"""PANEL DE CARGA — Analista (app separada, SOLO LOCAL).

App Streamlit independiente del dashboard del alcalde. Aquí el analista carga
informes, evidencia y briefings hacia el pipeline de inteligencia. NO se expone
públicamente: se ejecuta en local y opera sobre la misma base de datos local que
el resto del proyecto (config.py).

Ejecutar:
    streamlit run dashboard/panel_carga.py

Mantener este panel separado de app.py asegura que el alcalde nunca vea la
opción de "cargar contenido" en su dashboard.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard"))

from dashboard.estilos import CSS
from dashboard.estilos_override import CSS_OVERRIDE
from dashboard.dash_ui import _page_head
from dashboard.dash_ingesta import seccion_cargar_contenido
from dashboard.editor_db import seccion_editar_db
from dashboard.dash_temas import render_revisor_temas
from dashboard.config import FACEBOOK_DB

# ─── Estado de sesión ────────────────
if "lote_ingreso" not in st.session_state:
    st.session_state["lote_ingreso"] = []

st.set_page_config(
    page_title="PANEL DE CARGA — Analista",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(CSS, unsafe_allow_html=True)
st.markdown(CSS_OVERRIDE, unsafe_allow_html=True)

# ─── Topbar (uso interno del analista) ─────
st.markdown("""
<div class="topbar">
    <div class="topbar-brand">PANEL DE CARGA <span class="sep">/</span> <span class="who">Analista</span></div>
    <div class="topbar-meta">USO INTERNO <span class="acc">·</span> LOCAL</div>
</div>
""", unsafe_allow_html=True)

_page_head(
    "OPERACIÓN / CARGA DE CONTENIDO",
    "Centro de ingesta de informes y evidencia",
    "Cargue informes consolidados, evidencia documental y briefings diarios. Cada documento se incorpora al pipeline de inteligencia."
)

st.markdown("""
<div class="doc-center">
    <div class="doc-label">
        <div class="doc-icon-box">PDF</div>
        <div class="doc-info">
            <div class="doc-filename">Informe Consolidado del Día</div>
            <div class="doc-meta">CENTRO DE DOCUMENTACIÓN EJECUTIVA · BRIEFING DIARIO CORPORATIVO</div>
        </div>
    </div>
    <div class="doc-empty">
        <div class="doc-empty-label">Sin documento disponible. El informe consolidado se genera automáticamente al procesar los datos del día.</div>
    </div>
</div>
""", unsafe_allow_html=True)

tab_carga, tab_editor, tab_aprobar = st.tabs([
    "📥 Cargar contenido", "🛠️ Editar base de datos", "✅ Aprobar temas"
])
with tab_carga:
    seccion_cargar_contenido()
with tab_editor:
    seccion_editar_db()
with tab_aprobar:
    render_revisor_temas(FACEBOOK_DB)
