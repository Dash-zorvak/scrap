"""UI de aprobación manual de temas (100% manual, sin IA).

Cada comentario se revisa uno por uno: el analista selecciona un tema englobante
y una postura (apoyo/crítica/neutral). Solo los comentarios aprobados cuentan
en las tarjetas de Temas Emergentes.
"""

import streamlit as st

from dashboard.tema_aprobaciones import guardar_aprobacion, resumen_revision
from dashboard.tema_taxonomia import TEMAS_VISIBLES, TEMA_LABELS, EMOCIONES, EMOCION_LABELS, EMOCION_DEFAULT

# Opciones del selector de tema: temas englobantes + 'sin tema'.
_OPCIONES = list(TEMAS_VISIBLES) + ["no_aplica"]

# Opciones del selector de postura.
_POSTURA_OPCIONES = ["apoyo", "critica", "neutral"]
_POSTURA_LABELS_UI = {
    "apoyo": "👍 Apoyo",
    "critica": "👎 Crítica",
    "neutral": "➖ Neutral",
}

# Opciones del selector de emoción.
_EMOCION_OPCIONES = list(EMOCIONES.keys())
_EMOCION_LABELS_UI = dict(EMOCION_LABELS)


def _label_opcion(clave):
    if clave == "no_aplica":
        return "— Sin tema / descartar —"
    return TEMA_LABELS.get(clave, clave)


def _label_postura(clave):
    return _POSTURA_LABELS_UI.get(clave, clave)


def _ids_aprobados_en_periodo(db_path):
    """IDs de comentarios que ya tienen aprobación."""
    from dashboard.tema_aprobaciones import ids_aprobados
    return ids_aprobados(db_path)


def render_revisor_temas(db_path):
    with st.expander("✍️ Revisar y aprobar temas", expanded=False):
        import sqlite3
        ids_ok = _ids_aprobados_en_periodo(db_path)
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT comment_id, message FROM fb_comments "
                "WHERE message IS NOT NULL AND message != ''"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        pendientes = [(cid, msg) for cid, msg in rows if cid not in ids_ok]

        if not pendientes:
            st.markdown(
                '<div class="status-info">No hay comentarios pendientes de revisión.</div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            f'<p style="font-size:11px;color:var(--fg-muted)">Selecciona un tema y postura '
            f'para cada comentario ({len(pendientes)} pendientes).</p>',
            unsafe_allow_html=True,
        )

        for cid, texto in pendientes:
            texto_clean = (texto or "").replace('"', "'")
            st.markdown(
                f'<div style="font-size:13px;padding:8px 10px;margin:8px 0 4px 0;'
                f'background:var(--bg-elevated);border-radius:6px;border-left:3px solid var(--accent)">'
                f'«{texto_clean}»</div>',
                unsafe_allow_html=True,
            )
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                sel = st.selectbox(
                    "Tema", _OPCIONES, format_func=_label_opcion,
                    key=f"sel_{cid}", label_visibility="collapsed",
                )
            with c2:
                sel_postura = st.selectbox(
                    "Postura", _POSTURA_OPCIONES, format_func=_label_postura,
                    key=f"post_{cid}", label_visibility="collapsed",
                )
            with c3:
                sel_emocion = st.selectbox(
                    "Emoción", _EMOCION_OPCIONES, format_func=lambda x: _EMOCION_LABELS_UI.get(x, x),
                    key=f"emo_{cid}", label_visibility="collapsed",
                )
            with c4:
                if st.button("Aprobar", key=f"ap_{cid}"):
                    guardar_aprobacion(
                        db_path, cid, sel, texto=texto,
                        tema_sugerido=None, tono="literal",
                        confianza=None, postura=sel_postura,
                        emocion=sel_emocion,
                    )
                    st.rerun()