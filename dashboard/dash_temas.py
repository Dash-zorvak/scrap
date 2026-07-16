"""UI de aprobación manual de temas (100% manual, sin IA).

Cada comentario se revisa uno por uno: el analista selecciona un tema englobante,
una postura (apoyo/crítica/neutral) con intensidad, una o más emociones, una
entidad/subtema específico (opcional) y relevancia al post.

Solo los comentarios aprobados y no marcados como 'ruido_conversacional' cuentan
en las tarjetas de Temas Emergentes.

Campos nuevos (Puntos 1-4):
  - subtema_especifico: entidad o subtema concreto (autocompletado + libre)
  - intensidad_postura: leve/moderada/fuerte (solo para apoyo/crítica)
  - emociones: multiselect de 1+ emociones (reemplaza selector único)
  - relevancia_al_post: directo_al_post/tangencial_via_respuesta/ruido_conversacional
  - Contexto de comentario padre: visible solo para Facebook (único con parent_comment_id)
"""

import json
import streamlit as st

from dashboard.tema_aprobaciones import (
    guardar_aprobacion,
    resumen_revision,
    INTENSIDADES_POSTURA,
    INTENSIDAD_POSTURA_DEFAULT,
    RELEVANCIAS_POST,
    RELEVANCIA_DEFAULT,
)
from dashboard.tema_taxonomia import (
    TEMAS_VISIBLES,
    TEMA_LABELS,
    EMOCIONES,
    EMOCION_LABELS,
    EMOCION_DEFAULT,
    EMOCIONES_VALIDAS,
)
from dashboard.entidades_taxonomia import (
    ENTIDADES,
    ENTIDAD_LABELS,
    ENTIDADES_VALIDAS,
    etiqueta_entidad,
)

# Opciones del selector de tema: temas englobantes + 'sin tema'.
_OPCIONES = list(TEMAS_VISIBLES) + ["no_aplica"]

# Opciones del selector de postura.
_POSTURA_OPCIONES = ["apoyo", "critica", "neutral"]
_POSTURA_LABELS_UI = {
    "apoyo": "👍 Apoyo",
    "critica": "👎 Crítica",
    "neutral": "➖ Neutral",
}

# Opciones del selector de emoción (multiselect).
_EMOCION_OPCIONES = list(EMOCIONES.keys())
_EMOCION_LABELS_UI = dict(EMOCION_LABELS)

# Opciones de intensidad de postura.
_INTENSIDAD_OPCIONES = ["leve", "moderada", "fuerte"]
_INTENSIDAD_LABELS_UI = {
    "leve": " Leve",
    "moderada": " Moderada",
    "fuerte": " Fuerte",
}

# Opciones de relevancia al post.
_RELEVANCIA_OPCIONES = ["directo_al_post", "tangencial_via_respuesta", "ruido_conversacional"]
_RELEVANCIA_LABELS_UI = {
    "directo_al_post": " Directo al post",
    "tangencial_via_respuesta": " Tangencial (vía respuesta)",
    "ruido_conversacional": " Ruido conversacional",
}


def _label_opcion(clave):
    if clave == "no_aplica":
        return "— Sin tema / descartar —"
    return TEMA_LABELS.get(clave, clave)


def _label_postura(clave):
    return _POSTURA_LABELS_UI.get(clave, clave)


def _label_emocion(clave):
    return _EMOCION_LABELS_UI.get(clave, clave)


def _label_intensidad(clave):
    return _INTENSIDAD_LABELS_UI.get(clave, clave)


def _label_relevancia(clave):
    return _RELEVANCIA_LABELS_UI.get(clave, clave)


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


def _registrar_entidad_propuesta(entidad_texto, ejemplo_texto=""):
    """Registra una entidad nueva写入手写 en taxonomias_pendientes.json (Punto 1)."""
    from analytics._propuestas import _registrar_propuesta
    clave = f"entidad_nueva_{entidad_texto.strip().lower().replace(' ', '_')}"
    _registrar_propuesta(
        clave_propuesta=clave,
        ejemplo_texto=ejemplo_texto,
        tipo="entidad",
        familia_mas_cercana="",
    )


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
    # Detectar si esta DB tiene parent_comment_id
    tiene_padre = col_parent is not None

    with st.expander("✍️ Revisar y aprobar temas", expanded=False):
        import sqlite3
        ids_ok = _ids_aprobados_en_periodo(db_path)
        try:
            conn = sqlite3.connect(db_path)
            if tiene_padre:
                rows = conn.execute(
                    f"SELECT {col_id}, {col_texto}, {col_parent} FROM {tabla} "
                    f"WHERE {col_texto} IS NOT NULL AND {col_texto} != ''"
                ).fetchall()
            else:
                rows_raw = conn.execute(
                    f"SELECT {col_id}, {col_texto} FROM {tabla} "
                    f"WHERE {col_texto} IS NOT NULL AND {col_texto} != ''"
                ).fetchall()
                rows = [(cid, msg, None) for cid, msg in rows_raw]
            conn.close()
        except Exception:
            rows = []
        pendientes = [(cid, msg, parent) for cid, msg, parent in rows
                      if cid not in ids_ok]

        if not pendientes:
            st.markdown(
                '<div class="status-info">No hay comentarios pendientes de revisión.</div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            f'<p style="font-size:11px;color:var(--fg-muted)">Selecciona tema, '
            f'postura, emociones y relevancia para cada comentario '
            f'({len(pendientes)} pendientes).</p>',
            unsafe_allow_html=True,
        )

        for cid, texto, parent_id in pendientes:
            from dashboard.html_safety import safe_text
            texto_clean = safe_text(texto)
            st.markdown(
                f'<div style="font-size:13px;padding:8px 10px;margin:8px 0 4px 0;'
                f'background:var(--bg-elevated);border-radius:6px;border-left:3px solid var(--accent)">'
                f'«{texto_clean}»</div>',
                unsafe_allow_html=True,
            )

            # Contexto del comentario padre (Punto 4)
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

            # ─── Fila 1: Tema + Postura + Intensidad + Emociones ──────
            c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
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
                # Intensidad solo relevante para apoyo/crítica
                if sel_postura in ("apoyo", "critica"):
                    sel_intensidad = st.selectbox(
                        "Intensidad", _INTENSIDAD_OPCIONES,
                        format_func=_label_intensidad,
                        index=1,  # default: moderada
                        key=f"int_{cid}", label_visibility="collapsed",
                    )
                else:
                    sel_intensidad = INTENSIDAD_POSTURA_DEFAULT
            with c4:
                sel_emociones = st.multiselect(
                    "Emociones", _EMOCION_OPCIONES,
                    format_func=_label_emocion,
                    default=[EMOCION_DEFAULT],
                    key=f"emo_{cid}", label_visibility="collapsed",
                )

            # ─── Fila 2: Entidad + Relevancia + Aprobar ──────────────
            c5, c6, c7 = st.columns([2, 2, 1])
            with c5:
                # Entidad/subtema específico (Punto 1)
                opciones_entidad = [""] + list(ENTIDADES_VALIDAS)
                entidad_sel = st.selectbox(
                    "Entidad/subtema",
                    opciones_entidad,
                    format_func=lambda x: etiqueta_entidad(x) if x else "— Sin entidad específica —",
                    key=f"ent_{cid}", label_visibility="collapsed",
                )
                # Opción de escribir entidad nueva
                entidad_nueva = st.text_input(
                    "O escribir entidad nueva",
                    key=f"ent_new_{cid}",
                    placeholder="Escriba una entidad nueva...",
                    label_visibility="collapsed",
                )
                subtema_final = None
                if entidad_nueva.strip():
                    subtema_final = entidad_nueva.strip()
                elif entidad_sel:
                    subtema_final = ENTIDAD_LABELS.get(entidad_sel, entidad_sel)
            with c6:
                sel_relevancia = st.selectbox(
                    "Relevancia al post", _RELEVANCIA_OPCIONES,
                    format_func=_label_relevancia,
                    index=0,  # default: directo_al_post
                    key=f"rel_{cid}", label_visibility="collapsed",
                )
            with c7:
                if st.button("Aprobar", key=f"ap_{cid}"):
                    # Registrar entidad nueva si fue escrita a mano
                    if entidad_nueva.strip():
                        _registrar_entidad_propuesta(
                            entidad_nueva.strip(), ejemplo_texto=texto[:200]
                        )

                    guardar_aprobacion(
                        db_path, cid, sel, texto=texto,
                        tema_sugerido=None, tono=None,
                        confianza=None, postura=sel_postura,
                        emociones=sel_emociones,
                        subtema_especifico=subtema_final,
                        intensidad_postura=sel_intensidad,
                        relevancia_al_post=sel_relevancia,
                    )
                    st.rerun()
