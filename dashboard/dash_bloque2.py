"""Bloque II — Segmentación de Audiencia.

Estaciones: Mapa de Públicos, Polarización, Voces de Influencia y Temas
Emergentes. Mapa y Polarización usan la fuente unica (dash_fuente) filtrada por
el periodo y la plataforma, sobre el 100% de los comentarios. La Polarizacion
parte de la MISMA distribucion de sentimiento que el Mapa/Clima
(dash_fuente.distribucion_sentimiento), no de fb_comments.sentiment_score.

Filtro por plataforma:
  - Facebook -> solo Facebook. TikTok -> solo TikTok. Ambas -> combinados.
  - Voces de influencia combina las paginas de la(s) plataforma(s) activa(s).
  - Temas Emergentes se calcula a partir de la clasificacion tematica de
    Facebook; en la vista exclusiva de TikTok se oculta (no hay equivalente
    fiable) en lugar de mostrar datos de otra plataforma.

Nota: el Cruce Tema x Zona y el Perfil de Audiencia (OCEAN) se retiraron por
falta de datos confiables. Las "Voces de influencia" a nivel de autor ciudadano
quedan pendientes; por ahora se muestran las paginas oficiales.
"""

import pandas as pd
import streamlit as st

from config import FACEBOOK_DB, TIKTOK_DB
from dashboard.dash_audiencia import polarizacion_desde_conteos
from dashboard.dash_periodos import rango_periodo, etiqueta_rango
from dashboard.dash_fuente import (
    cargar_comentarios_periodo,
    distribucion_sentimiento,
    cargar_engagement_periodo,
)
from dashboard.dash_temas import render_temas_emergentes
from dashboard.dash_ui import (
    _page_head,
    hay_datos,
    card_explicativa,
    card_narrativa,
    referencias_publicaciones,
)


def _voces_influencia(plataforma, df_fb=None, df_tk=None):
    """Top 5 paginas por interaccion, combinando solo la(s) plataforma(s) activa(s).

    Recibe df_fb y df_tk ya cargados y filtrados por cargar_engagement_periodo.
    Ambos exponen page_name y engagement_total, de modo que la mezcla solo ocurre
    cuando el filtro es "Ambas".
    """
    plat = str(plataforma or "").lower()
    frames = []
    if "tik" not in plat and df_fb is not None and not df_fb.empty and "page_name" in df_fb.columns:
        g = df_fb.groupby("page_name").agg(
            engagement=("engagement_total", "sum"),
            posts=("post_id", "count"),
        ).reset_index()
        frames.append(g)
    if plat != "facebook" and df_tk is not None and not df_tk.empty and "page_name" in df_tk.columns:
        item_col = "id" if "id" in df_tk.columns else "post_id"
        g = df_tk.groupby("page_name").agg(
            engagement=("engagement_total", "sum"),
            posts=(item_col, "count"),
        ).reset_index()
        frames.append(g)
    if not frames:
        return None
    combinado = pd.concat(frames, ignore_index=True)
    combinado = combinado.groupby("page_name").agg(
        engagement=("engagement", "sum"),
        posts=("posts", "sum"),
    ).reset_index().sort_values("engagement", ascending=False).head(5)
    return combinado


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

    df_coment = cargar_comentarios_periodo(ini, fin, plataforma)
    dist = distribucion_sentimiento(df_coment, plataforma)

    # Voces de influencia: una sola llamada a cargar_engagement_periodo
    # devuelve (df_fb, df_tk) ya filtrados por plataforma y fecha.
    df_fb, df_tk = cargar_engagement_periodo(ini, fin, plataforma)

    # ── 1. MAPA DE PÚBLICOS ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Mapa de Públicos</div></div>', unsafe_allow_html=True)
    if dist["n_total"] > 0:
        card_narrativa(
            f"De <strong>{dist['n_total']:,}</strong> comentarios, <strong>{dist['pct_favorable']:.0f}%</strong> son a favor, {dist['pct_neutral']:.0f}% neutrales y <strong>{dist['pct_critico']:.0f}%</strong> críticos.",
            tono="neutral",
        )
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
        referencias_publicaciones(limit=10, titulo="Enlaces de referencias bibliográficas", plataforma=plataforma)
    else:
        st.markdown('<div class="status-info">No hay comentarios en el período seleccionado.</div>', unsafe_allow_html=True)

    # ── 2. POLARIZACIÓN — solo lenguaje natural ──
    pol = polarizacion_desde_conteos(dist["n_favorable"], dist["n_critico"], dist["n_total"]) if dist["n_total"] > 0 else None
    st.markdown('<div class="section-header"><div class="section-title">02 · Polarización</div></div>', unsafe_allow_html=True)
    if pol and (pol["n_favor"] + pol["n_contra"]) > 0:
        if pol["nivel"] == "confrontacion":
            _txt = f"La conversación está <strong>dividida</strong>: casi tantos comentarios a favor ({pol['pct_favor']:.0f}%) como en contra ({pol['pct_contra']:.0f}%)."
            _tono = "neutral"
        elif pol["nivel"] == "dividida":
            if pol["lado"] == "favor":
                _txt = f"<strong>Predomina el apoyo</strong> ({pol['pct_favor']:.0f}%), con una minoría crítica visible ({pol['pct_contra']:.0f}%)."
                _tono = "favorable"
            else:
                _txt = f"<strong>Predomina la crítica</strong> ({pol['pct_contra']:.0f}%), con una minoría que apoya ({pol['pct_favor']:.0f}%)."
                _tono = "critico"
        else:
            if pol["lado"] == "favor":
                _txt = f"Hay <strong>consenso a favor</strong>: el {pol['pct_favor']:.0f}% de quienes opinan apoyan."
                _tono = "favorable"
            else:
                _txt = f"Hay <strong>consenso crítico</strong>: el {pol['pct_contra']:.0f}% de quienes opinan critican."
                _tono = "critico"
        card_narrativa(_txt, tono=_tono)
    elif dist["n_total"] > 0:
        card_narrativa("La mayoría de los comentarios son <strong>neutrales</strong>; no hay una confrontación marcada entre posturas.", tono="neutral")
    card_explicativa(
        "Qué está ocurriendo: si la ciudadanía opina de forma parecida o está partida entre apoyo y crítica.",
        "Mientras más parejas sean las dos posturas, más dividida está la conversación; si una domina, hay consenso.",
    )
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
                col_nivel = "var(--red)"
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
    voces = _voces_influencia(plataforma, df_fb=df_fb, df_tk=df_tk)
    st.markdown('<div class="section-header"><div class="section-title">03 · Voces de Influencia</div></div>', unsafe_allow_html=True)
    if voces is not None and not voces.empty:
        _top = voces.iloc[0]
        card_narrativa(
            f"La página con más interacción es <strong>{_top['page_name']}</strong>, con {int(_top['engagement']):,} interacciones en {int(_top['posts'])} publicaciones.",
            tono="favorable",
        )
    card_explicativa(
        "Qué está ocurriendo: qué páginas oficiales concentran la mayor parte de la interacción ciudadana.",
        "La barra más larga es la página con más reacciones y comentarios en el período.",
    )
    if voces is not None and not voces.empty:
        max_eng = voces['engagement'].max() if not voces.empty else 1
        rows_html = ""
        for _, r in voces.iterrows():
            pct = (r['engagement'] / max_eng * 100) if max_eng > 0 else 0
            rows_html += f'<div class="bar-row"><div class="bar-row-label">{r["page_name"]}</div><div class="bar-track"><div class="bar-fill bar-fill-cy" style="width:{pct:.1f}%"></div></div><div class="bar-row-val">{int(r["engagement"]):,} · {int(r["posts"])}p</div></div>'
        st.markdown(f'<div class="panel"><div class="panel-head"><div class="panel-title">TOP 5 · PÁGINAS OFICIALES</div><div class="panel-meta">INTERACCIÓN · # PUBLICACIONES</div></div>{rows_html}</div>', unsafe_allow_html=True)
        referencias_publicaciones(limit=8, titulo="Enlaces de referencias bibliográficas", plataforma=plataforma)
    else:
        st.markdown('<div class="status-info">Sin datos de interacción para identificar voces en este período.</div>', unsafe_allow_html=True)

    # ── 4. TEMAS EMERGENTES ──
    # La deteccion de temas emergentes usa la clasificacion tematica de Facebook.
    # En la vista exclusiva de TikTok no se muestra para no exhibir datos de FB.
    if "tik" not in str(plataforma).lower():
        render_temas_emergentes(FACEBOOK_DB, ini, fin)
    else:
        st.markdown('<div class="section-header"><div class="section-title">04 · Temas Emergentes</div><div class="section-subtitle">Temas que ganan fuerza en la conversación.</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="status-info">Los temas emergentes se calculan a partir de la clasificación temática de Facebook; no están disponibles en la vista exclusiva de TikTok.</div>', unsafe_allow_html=True)
