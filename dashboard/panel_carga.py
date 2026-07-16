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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # path-hack para imports de src/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard"))  # path-hack para imports de dashboard/ hermanos

from dashboard.estilos import CSS
from dashboard.estilos_override import CSS_OVERRIDE
from dashboard.dash_ui import _page_head
from dashboard.dash_ingesta import seccion_cargar_contenido
from dashboard.editor_db import seccion_editar_db
from dashboard.dash_temas import render_revisor_temas
from dashboard.tema_aprobaciones import (
    asegurar_tabla_en_tiktok,
    asegurar_computed_tiktok,
    asegurar_computed_externos,
)
from src.config import Config, ensure_dirs
_cfg = Config()
FACEBOOK_DB = _cfg.FACEBOOK_DB
TIKTOK_DB = _cfg.TIKTOK_DB
EXTERNOS_DB = _cfg.EXTERNOS_DB
ensure_dirs(_cfg)

from config.logging_config import configurar_logging
configurar_logging()

# ─── Migraciones estructurales 8.3 ─────
asegurar_tabla_en_tiktok(TIKTOK_DB)
asegurar_computed_tiktok(TIKTOK_DB)
asegurar_computed_externos(EXTERNOS_DB)

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

# from auth import require_auth  # deshabilitado — auth.py se mantiene intacto
# require_auth()

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

tab_carga, tab_editor, tab_aprobar, tab_aprobar_tk, tab_aprobar_ext = st.tabs([
    "📥 Cargar contenido", "🛠️ Editar base de datos",
    "✅ Aprobar temas", "✅ Aprobar temas (TikTok)", "✅ Aprobar temas (Externos)",
])
with tab_carga:
    seccion_cargar_contenido()
with tab_editor:
    seccion_editar_db()
with tab_aprobar:
    render_revisor_temas(FACEBOOK_DB, col_parent="parent_comment_id")
with tab_aprobar_tk:
    render_revisor_temas(TIKTOK_DB, tabla="comments", col_id="id", col_texto="text")
with tab_aprobar_ext:
    render_revisor_temas(EXTERNOS_DB, tabla="external_comments", col_id="comment_id", col_texto="message")
