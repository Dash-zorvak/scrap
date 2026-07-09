# -*- coding: utf-8 -*-
"""Snippets de Streamlit para pegar dentro de dashboard/app.py, en la seccion
`with tab_pulso:` (Bloque I - Pulso general).

No es un archivo ejecutable por si solo: son bloques de reemplazo comentados,
para que los copies en el lugar exacto donde hoy dibujas cada seccion. Usan
las funciones de bloque1_narrativas.py y el catalogo de
tema_taxonomia_expandida.py.
"""

import streamlit as st
import pandas as pd

from tema_taxonomia_expandida import EMOCIONES, EMOCION_LABELS, emociones_por_familia, FAMILIAS_LABELS
from bloque1_narrativas import narrativa_emocion_seleccionada


# ---------------------------------------------------------------------------
# 02 . INDICE DE EMOCIONES -- selector debajo de la grafica
# ---------------------------------------------------------------------------
# Reemplaza el bloque actual que dibuja "la lista y las barras" de una vez
# por esto. `emo = b1.get("indice_emociones", {})` ya existe mas arriba en tu
# app.py; se reutiliza aqui.

def render_indice_emociones(emo: dict):
    st.subheader("02 · Índice de Emociones")

    conteos = {k: v.get("n", v) if isinstance(v, dict) else v
               for k, v in emo.get("conteos", {}).items() if k in EMOCIONES}
    if not conteos:
        st.info("No hay datos de emociones para este periodo.")
        return

    labels_presentes = {k: EMOCION_LABELS.get(k, k) for k in conteos}

    # --- grafica completa (todas las emociones con datos) ---
    df_todas = pd.DataFrame({
        "Emocion": list(labels_presentes.values()),
        "Comentarios": list(conteos.values()),
    }).sort_values("Comentarios", ascending=False)
    st.bar_chart(df_todas.set_index("Emocion"))

    st.caption(emo.get("narrativa", ""))

    # --- selector debajo de la grafica: agrupado por familia para no listar
    #     30 opciones sueltas de golpe ---
    familias = emociones_por_familia()
    opciones_por_familia = {
        FAMILIAS_LABELS[fam]: [k for k in claves if k in conteos]
        for fam, claves in familias.items()
        if any(k in conteos for k in claves)
    }

    familia_sel = st.selectbox("Familia de emocion", list(opciones_por_familia.keys()), key="bloque1_familia_emocion")
    claves_disponibles = opciones_por_familia[familia_sel]
    clave_sel = st.selectbox(
        "Emocion",
        claves_disponibles,
        format_func=lambda k: labels_presentes.get(k, k),
        key="bloque1_emocion_sel",
    )

    # Al seleccionar, mostrar SOLO la grafica de esa emocion (no todas) + el
    # mensaje de cual domina mas.
    df_una = pd.DataFrame({"Emocion": [labels_presentes[clave_sel]], "Comentarios": [conteos[clave_sel]]})
    st.bar_chart(df_una.set_index("Emocion"))
    st.write(narrativa_emocion_seleccionada(clave_sel, conteos, labels_presentes))


# ---------------------------------------------------------------------------
# 04 . CONCENTRACION TEMATICA -- una sola card consolidada
# ---------------------------------------------------------------------------
# Sustituye las 2-3 piezas sueltas (grafica + "TEMAS ACELERANDO/DESACELERANDO"
# + texto descriptivo aparte) por un unico bloque ordenado.

def render_concentracion_tematica(ct: dict):
    st.subheader("04 · Concentración Temática")

    ramas = ct.get("ramas", [])
    if not ramas:
        st.info("No hay temas clasificados en este periodo.")
        return

    df = pd.DataFrame(ramas)[["tema", "n", "share", "pct_cambio_semana"]]
    df.columns = ["Tema", "Comentarios", "Participación", "Cambio semanal (%)"]

    with st.container(border=True):
        col_izq, col_der = st.columns([1.3, 1])
        with col_izq:
            st.bar_chart(df.set_index("Tema")["Comentarios"])
        with col_der:
            st.metric("HHI (concentración)", f"{ct.get('hhi', 0):.2f}", help="0 = repartido, 1 = un solo tema domina")
            st.metric("Tema principal", ct.get("top_tema", "—"))

        st.markdown("---")
        st.write(ct.get("narrativa", ""))  # ya trae acelerando/desacelerando + formula HHI embebidos


# ---------------------------------------------------------------------------
# 05 . METRICAS DE RENDIMIENTO -- numeros + explicacion + enlaces
# ---------------------------------------------------------------------------

def render_metricas_rendimiento(mr: dict):
    st.subheader("05 · Métricas de Rendimiento")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Engagement rate", f"{mr.get('engagement_rate', 0):.2f}")
    c2.metric("Ratio amor/enojo", mr.get("ratio_amor_enojo") if mr.get("ratio_amor_enojo") is not None else "s/d")
    c3.metric("Reacciones + / -", f"{mr.get('reacciones_positivas_pct', 0)} / {mr.get('reacciones_negativas_pct', 0)}")
    c4.metric("Alcance estimado", f"{mr.get('alcance_estimado', 0):,}")

    st.write(mr.get("narrativa", ""))

    enlaces = mr.get("enlaces_referencia", [])
    if enlaces:
        st.caption("Fuentes: " + " · ".join(f"[Publicación {i+1}]({url})" for i, url in enumerate(enlaces)))


# ---------------------------------------------------------------------------
# 06 . TERMOMETRO DE ZONAS -- por zona, con score y fuente
# ---------------------------------------------------------------------------

def render_termometro_zonas(zonas: list):
    st.subheader("06 · Termómetro de Zonas")
    st.caption("Mide el tono de los comentarios geolocalizados a cada zona, no de toda la conversación general.")

    for z in zonas:
        with st.container(border=True):
            st.markdown(f"**{z.get('zona')}** — nivel de tensión: {z.get('nivel_tension')} (score {z.get('score_zona', 0):+.3f})")
            st.write(z.get("narrativa", ""))
