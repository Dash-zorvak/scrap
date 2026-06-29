"""Sección de descarga del informe PDF de la medalla en el dashboard del alcalde.

SOLO LECTURA: toma la medalla aprobada vigente (medalla_store), arma el contexto
(post FB + réplicas externas seleccionadas + capturas guardadas) y ofrece la
descarga del PDF. La selección y edición viven en el panel de carga del analista,
no aquí.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import FACEBOOK_DB  # type: ignore
except Exception:
    FACEBOOK_DB = os.getenv("FACEBOOK_DB", "facebook.db")

import medalla_store  # noqa: E402
import medalla_seleccion  # noqa: E402
from capturas_store import listar_capturas  # noqa: E402
from medalla_pdf import generar_pdf_medalla  # noqa: E402
import db_edits  # noqa: E402

try:
    from src.storage.db import LocalStorage  # type: ignore
except Exception:
    from storage.db import LocalStorage  # type: ignore


def _store():
    return LocalStorage(db_path=FACEBOOK_DB)


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

    contexto = {
        "periodo_label": vigente.get("periodo_label") or (periodo or ""),
        "enlaces": [post.get("post_url")] if post.get("post_url") else [],
        "medios": medios,
    }
    imagenes = listar_capturas(post.get("post_id"))

    if st.button("Generar informe PDF", type="primary", key="btn_gen_medalla"):
        with st.spinner("Generando informe…"):
            try:
                pdf = generar_pdf_medalla(post, contexto, imagenes=imagenes, usar_ia=True)
                st.session_state["medalla_pdf_bytes"] = pdf
            except Exception as e:  # nunca romper el dashboard del alcalde
                st.error(f"No se pudo generar el informe: {e}")

    if st.session_state.get("medalla_pdf_bytes"):
        st.download_button(
            "Descargar informe de la medalla (PDF)",
            data=st.session_state["medalla_pdf_bytes"],
            file_name="informe_medalla.pdf",
            mime="application/pdf",
            key="dl_medalla",
        )
