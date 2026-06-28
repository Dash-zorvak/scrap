"""Bloque II — Segmentación de Audiencia.

Estaciones: Mapa de Públicos, Polarización, Voces de Influencia y Temas
Emergentes. Mapa y Polarización usan la fuente unica (dash_fuente) filtrada por
el periodo, sobre el 100% de los comentarios y con el sentimiento por
comentario (no el promedio de la publicacion).

Nota: el Cruce Tema x Zona y el Perfil de Audiencia (OCEAN) se retiraron por
falta de datos confiables (geografia / clasificacion incompleta). Las "Voces de
influencia" a nivel de autor ciudadano quedan pendientes hasta que la captura
guarde la identidad del autor; por ahora se muestran las paginas oficiales.
"""

import streamlit as st

from config import FACEBOOK_DB
from dashboard.dash_metrics import cargar_fb_engagement
from dashboard.dash_audiencia import calcular_polarizacion
from dashboard.dash_periodos import rango_periodo, filtrar_por_fecha, etiqueta_rango
from dashboard.dash_fuente import cargar_comentarios_periodo, distribucion_sentimiento
from dashboard.dash_temas import render_temas_emergentes
from dashboard.dash_ui import (
    _page_head,
    hay_datos,
    card_explicativa,
    referencias_publicaciones,
)


def render_bloque2_audiencia(periodo, plataforma):
    ref = st.session_state.get("fecha_ref")
    ini, fin = rango_periodo(
        periodo, ref,
        st.session_state.get("fecha_desde"),
        st.session_state.get("fecha_hasta"),
    )

    _page_head(
        "SEGMENTACIÓN DE AUDIENCIA / ANÁLISIS DE PÚBLICOS",
        "Estructura de públicos y voces de influencia",
        "Composición de quienes participan en la conversación: a favor, neutrales y críticos; nivel de polarización y páginas que concentran la interacción.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> {etiqueta_rango(ini, fin).upper()} <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    df_coment = cargar_comentarios_periodo(ini, fin)
    dist = distribucion_sentimiento(df_coment)

    # ── 1. MAPA DE PÚBLICOS ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Mapa de Públicos</div><div class="section-subtitle">Composición de la audiencia según el tono de sus comentarios.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué está ocurriendo: cómo se divide la audiencia entre quienes apoyan, quienes son neutrales y quienes critican.",
        "Cada porcentaje es la parte de los comentarios de ese tono, sobre el 100% del período.",
    )
    if dist["n_total"] > 0:
        total = dist["n_total"]
        p_pos = dist["pct_favorable"]; p_neu = dist["pct_neutral"]; p_neg = dist["pct_critico"]
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head">
                <div class="panel-title">DISTRIBUCIÓN DE PÚBLICOS</div>
                <div class="panel-meta">{int(total):,} COMENTARIOS · 100% DEL PERÍODO</div>
            </div>
            <div class="bar-tri" style="height:16px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{p_pos:.1f}%"></span>
                <span class="bar-tri-neu" style="width:{p_neu:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{p_neg:.1f}%"></span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px">
                <div class="stat-card" style="border-top:2px solid var(--green);padding:14px"><div class="stat-value" style="color:var(--green)">{p_pos:.0f}%</div><div class="stat-label">A FAVOR</div></div>
                <div class="stat-card" style="border-top:2px solid var(--amber);padding:14px"><div class="stat-value" style="color:var(--amber)">{p_neu:.0f}%</div><div class="stat-label">NEUTRAL</div></div>
                <div class="stat-card" style="border-top:2px solid var(--red);padding:14px"><div class="stat-value" style="color:var(--red)">{p_neg:.0f}%</div><div class="stat-label">CRÍTICO</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        referencias_publicaciones(limit=10, titulo="PUBLICACIONES ANALIZADAS")
    else:
        st.markdown('<div class="status-info">No hay comentarios en el período seleccionado.</div>', unsafe_allow_html=True)

    # ── 2. POLARIZACIÓN — solo lenguaje natural ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Polarización</div><div class="section-subtitle">Si la conversación está en consenso o partida en dos posturas enfrentadas.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué está ocurriendo: si la ciudadanía opina de forma parecida o está partida entre apoyo y crítica.",
        "Mientras más parejas sean las dos posturas, más dividida está la conversación; si una domina, hay consenso.",
    )
    pol = calcular_polarizacion(df_coment["sentiment_score"]) if dist["n_total"] > 0 and "sentiment_score" in df_coment.columns else None
    if pol and (pol["n_favor"] + pol["n_contra"]) > 0:
        comprometidos = pol["n_favor"] + pol["n_contra"]
        lado_favor = pol["lado"] == "favor"
        if pol["nivel"] == "confrontacion":
            col_nivel = "var(--red)"; titular = "Conversación dividida"
            conclusion = "La ciudadanía está dividida: hay casi tantos comentarios a favor como en contra."
        elif pol["nivel"] == "dividida":
            col_nivel = "var(--amber)"
            if lado_favor:
                titular = "Predomina el apoyo, con críticas"
                conclusion = "La mayoría de quienes opinan lo hacen a favor, pero hay una minoría crítica visible."
            else:
                titular = "Predomina la crítica, con apoyos"
                conclusion = "La mayoría de quienes opinan lo hacen en contra, aunque hay una minoría que apoya."
        else:
            col_nivel = "var(--green)"
            if lado_favor:
                titular = "Consenso a favor"
                conclusion = "Hay consenso: casi todos los comentarios con postura son de apoyo."
            else:
                titular = "Consenso crítico"
                conclusion = "Hay consenso en contra: casi todos los comentarios con postura son críticos."
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_nivel}">{titular.upper()}</div><div class="panel-meta">{comprometidos:,} COMENTARIOS CON POSTURA</div></div>
            <div style="font-size:16px;font-weight:600;color:var(--fg-primary);margin:2px 0 12px">{conclusion}</div>
            <div class="bar-tri" style="height:16px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{pol['pct_favor']:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{pol['pct_contra']:.1f}%"></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:13px">
                <span style="color:var(--green)">A favor {pol['pct_favor']:.0f}%</span>
                <span style="color:var(--red)">En contra {pol['pct_contra']:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif dist["n_total"] > 0:
        st.markdown('<div class="panel"><div class="panel-head"><div class="panel-title" style="color:var(--green)">CONVERSACIÓN MAYORITARIAMENTE NEUTRAL</div></div><div style="font-size:16px;font-weight:600;color:var(--fg-primary)">La mayoría de los comentarios son neutrales; no hay una confrontación marcada entre posturas.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">No hay comentarios en el período seleccionado.</div>', unsafe_allow_html=True)

    # ── 3. VOCES DE INFLUENCIA (páginas oficiales) ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Voces de Influencia</div><div class="section-subtitle">Páginas oficiales que concentran la mayor interacción.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué está ocurriendo: qué páginas oficiales concentran la mayor parte de la interacción ciudadana.",
        "La barra más larga es la página con más reacciones y comentarios en el período.",
    )
    df_fb_raw = filtrar_por_fecha(cargar_fb_engagement(FACEBOOK_DB), "created_time", ini, fin)
    if df_fb_raw is not None and not df_fb_raw.empty:
        top_pages = df_fb_raw.groupby('page_name').agg(
            engagement=('engagement_total', 'sum'),
            posts=('post_id', 'count')
        ).reset_index().sort_values('engagement', ascending=False).head(5)
        max_eng = top_pages['engagement'].max() if not top_pages.empty else 1
        rows_html = ""
        for _, r in top_pages.iterrows():
            pct = (r['engagement'] / max_eng * 100) if max_eng > 0 else 0
            rows_html += f'<div class="bar-row"><div class="bar-row-label">{r["page_name"]}</div><div class="bar-track"><div class="bar-fill bar-fill-cy" style="width:{pct:.1f}%"></div></div><div class="bar-row-val">{int(r["engagement"]):,} · {int(r["posts"])}p</div></div>'
        st.markdown(f'<div class="panel"><div class="panel-head"><div class="panel-title">TOP 5 · PÁGINAS OFICIALES</div><div class="panel-meta">INTERACCIÓN · # PUBLICACIONES</div></div>{rows_html}</div>', unsafe_allow_html=True)
        referencias_publicaciones(limit=8, titulo="PUBLICACIONES DE LAS PÁGINAS")
    else:
        st.markdown('<div class="status-info">Sin datos de interacción para identificar voces en este período.</div>', unsafe_allow_html=True)

    # ── 4. TEMAS EMERGENTES ──
    render_temas_emergentes(FACEBOOK_DB)
