"""UI de aprobación manual de temas (100% manual, sin IA).

Cada comentario se revisa uno por uno: el analista selecciona un tema
englobante y aprueba. La postura se deriva automáticamente de la emoción
(clasificada fuera del panel por el usuario usando colores en capturas).

Solo los comentarios aprobados cuentan en las tarjetas de Temas Emergentes.
"""

import json
import streamlit as st

from analytics.topic import classify_topic
from dashboard.tema_aprobaciones import (
    guardar_aprobacion,
    resumen_revision,
)
from dashboard.tema_taxonomia import (
    TEMAS_VISIBLES,
    TEMA_LABELS,
    EMOCIONES,
    EMOCION_LABELS,
    EMOCION_DEFAULT,
    EMOCIONES_VALIDAS,
)

# Opciones del selector de tema: temas englobantes + 'sin tema'.
_OPCIONES = list(TEMAS_VISIBLES) + ["no_aplica"]


def _label_opcion(clave):
    if clave == "no_aplica":
        return "— Sin tema / descartar —"
    return TEMA_LABELS.get(clave, clave)


def _ids_aprobados_en_periodo(db_path):
    """IDs de comentarios que ya tienen aprobación."""
    from dashboard.tema_aprobaciones import ids_aprobados
    return ids_aprobados(db_path)


def _obtener_texto_padre(db_path, parent_comment_id, tabla="fb_comments"):
    """Obtiene el texto de un comentario padre (solo Facebook tiene parent_comment_id)."""
    if not parent_comment_id:
        return None
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            f"SELECT message FROM {tabla} WHERE comment_id = ?",
            (parent_comment_id,)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def render_revisor_temas(db_path, tabla="fb_comments", col_id="comment_id",
                          col_texto="message", col_parent=None):
    """Renderiza la interfaz de revisión y aprobación de un comentario.

    Args:
        db_path: ruta a la base de datos.
        tabla: nombre de la tabla de comentarios.
        col_id: columna del ID del comentario.
        col_texto: columna del texto del comentario.
        col_parent: columna del comment_id padre (solo Facebook tiene
            parent_comment_id). Si es None, no se busca contexto padre.
    """
    tiene_padre = col_parent is not None

    with st.expander("✍️ Revisar y aprobar temas", expanded=False):
        import sqlite3
        ids_ok = _ids_aprobados_en_periodo(db_path)
        try:
            conn = sqlite3.connect(db_path)
            if tiene_padre:
                rows = conn.execute(
                    f"SELECT {col_id}, {col_texto}, {col_parent}, emocion FROM {tabla} "
                    f"WHERE {col_texto} IS NOT NULL AND {col_texto} != ''"
                ).fetchall()
            else:
                rows_raw = conn.execute(
                    f"SELECT {col_id}, {col_texto}, emocion FROM {tabla} "
                    f"WHERE {col_texto} IS NOT NULL AND {col_texto} != ''"
                ).fetchall()
                rows = [(cid, msg, None, emocion) for cid, msg, emocion in rows_raw]
            conn.close()
        except Exception:
            rows = []
        pendientes = [(cid, msg, parent, emocion) for cid, msg, parent, emocion in rows
                      if cid not in ids_ok]

        if not pendientes:
            st.markdown(
                '<div class="status-info">No hay comentarios pendientes de revisión.</div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            f'<p style="font-size:11px;color:var(--fg-muted)">Selecciona tema '
            f'para cada comentario '
            f'({len(pendientes)} pendientes).</p>',
            unsafe_allow_html=True,
        )

        for cid, texto, parent_id, emocion_guardada in pendientes:
            from dashboard.html_safety import safe_text
            texto_clean = safe_text(texto)
            st.markdown(
                f'<div style="font-size:13px;padding:8px 10px;margin:8px 0 4px 0;'
                f'background:var(--bg-elevated);border-radius:6px;border-left:3px solid var(--accent)">'
                f'«{texto_clean}»</div>',
                unsafe_allow_html=True,
            )

            if tiene_padre and parent_id:
                texto_padre = _obtener_texto_padre(db_path, parent_id, tabla)
                if texto_padre:
                    padre_clean = safe_text(str(texto_padre))
                    st.markdown(
                        f'<div style="font-size:11px;padding:4px 8px;margin:0 0 6px 12px;'
                        f'color:var(--fg-muted);border-left:2px solid var(--border-default)">'
                        f'↩ Respondiendo a: «{padre_clean[:200]}»</div>',
                        unsafe_allow_html=True,
                    )

            resultado_tema = classify_topic(texto)
            tema_contado = resultado_tema.tema if resultado_tema.tema in _OPCIONES else "no_aplica"
            default_idx = _OPCIONES.index(tema_contado)

            c1, c2 = st.columns([5, 1])
            with c1:
                sel = st.selectbox(
                    "Tema", _OPCIONES, format_func=_label_opcion,
                    key=f"sel_{cid}", label_visibility="collapsed",
                    index=default_idx,
                )
            if resultado_tema.n_coincidencias:
                st.caption(
                    f"Conteo léxico: {_label_opcion(tema_contado)} "
                    f"({resultado_tema.n_coincidencias} coincidencia(s): "
                    f"{', '.join(resultado_tema.evidence[:5])})"
                )
            with c2:
                if st.button("Aprobar", key=f"ap_{cid}"):
                    guardar_aprobacion(
                        db_path, cid, sel, texto=texto,
                        tema_sugerido=tema_contado,
                        tono=None, confianza=None,
                        emocion=emocion_guardada or None,
                    )
                    st.rerun()
