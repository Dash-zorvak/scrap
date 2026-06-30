"""Sección de descarga del informe PDF de la medalla en el dashboard del alcalde.

SOLO LECTURA: toma la medalla aprobada vigente (medalla_store), arma el contexto
(post FB + réplicas externas seleccionadas + capturas guardadas) y ofrece la
descarga del PDF. La selección y edición viven en el panel de carga del analista,
no aquí.

La descarga se ofrece de forma AUTOMÁTICA: en cuanto hay una medalla vigente, el
informe se prepara y el botón de descarga aparece sin que el alcalde tenga que
pulsar nada. El PDF se cachea por medalla vigente (post + momento de aprobación)
para no regenerarlo en cada rerun de Streamlit; si el analista aprueba otra
medalla, la firma cambia y se regenera solo.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import medalla_store  # noqa: E402
import medalla_seleccion  # noqa: E402
from capturas_store import listar_capturas  # noqa: E402
from medalla_pdf import generar_pdf_medalla  # noqa: E402
import db_edits  # noqa: E402


def _rerun():
    """Re-ejecuta la app (compatibilidad entre versiones de Streamlit)."""
    try:
        st.rerun()
    except AttributeError:  # Streamlit < 1.27
        st.experimental_rerun()


def render_descarga_medalla(periodo=None):
    st.markdown("### Informe — Mejor medalla reciente")
    vigente = medalla_store.get_medalla_vigente()
    if not vigente or not vigente.get("post_id"):
        st.info(
            "Aún no hay una medalla aprobada. El analista la selecciona y aprueba "
            "en el panel de carga de contenido."
        )
        return

    post = db_edits.leer_post(vigente["post_id"])
    if not post:
        st.warning("La medalla aprobada ya no existe en la base de datos.")
        return

    medios = medalla_seleccion.externos_por_ids(vigente.get("medios") or [])
    fecha = str(post.get("created_time") or "")[:10]
    st.caption(
        f"Medalla vigente: {post.get('page_name', '')} · {fecha} · "
        f"{len(medios)} réplica(s) externa(s)"
    )

    # El contexto se construye con los DATOS REALES del post medalla vigente. En
    # particular `descripcion_post` (el texto del post) es lo que permite que el
    # alcance y la lectura del caso del PDF se adapten al hecho real del período
    # (antes, sin este dato, la plantilla caía siempre al caso por defecto).
    contexto = {
        "periodo_label": vigente.get("periodo_label") or (periodo or ""),
        "descripcion_post": (post.get("message") or "").strip(),
        "enlaces": [post.get("post_url")] if post.get("post_url") else [],
        "medios": medios,
    }
    imagenes = listar_capturas(post.get("post_id"))

    # El informe se prepara automáticamente: el alcalde no debe pulsar nada para
    # poder descargarlo. Se cachea por medalla vigente (post_id + momento de
    # aprobación) para no regenerarlo en cada rerun de Streamlit. Si el analista
    # aprueba otra medalla, la firma cambia y se regenera solo.
    firma = f"{vigente.get('post_id')}|{vigente.get('decidido_en')}"
    cache = st.session_state.get("medalla_pdf_cache") or {}
    if cache.get("firma") != firma or not cache.get("bytes"):
        with st.spinner("Preparando informe…"):
            try:
                pdf = generar_pdf_medalla(
                    post, contexto, imagenes=imagenes, usar_ia=True
                )
                cache = {"firma": firma, "bytes": pdf}
                st.session_state["medalla_pdf_cache"] = cache
            except Exception as e:  # nunca romper el dashboard del alcalde
                st.error(f"No se pudo generar el informe: {e}")
                cache = {}

    if cache.get("bytes"):
        st.download_button(
            "Descargar informe de la medalla (PDF)",
            data=cache["bytes"],
            file_name="informe_medalla.pdf",
            mime="application/pdf",
            key="dl_medalla",
        )
        if st.button("Regenerar informe", key="btn_regen_medalla"):
            st.session_state.pop("medalla_pdf_cache", None)
            _rerun()
