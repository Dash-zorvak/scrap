"""Bloque II — Segmentación de Audiencia.

Estaciones del índice: Mapa de Públicos, Polarización y Voces de Influencia.
Se conservan además (por decisión del usuario) Cruce Tema × Zona, Perfil de
Audiencia (OCEAN) y Temas Emergentes. Recibe `periodo` y `plataforma` como
argumentos.
"""

import streamlit as st

from config import FACEBOOK_DB
from dashboard.muestra import evaluar_muestra
from dashboard.dash_metrics import cargar_comentarios_fb, cargar_fb_engagement
from dashboard.dash_audiencia import calcular_polarizacion
from dashboard.dash_inteligencia import cargar_cruce_tema_zona, cargar_perfil_ocean
from dashboard.dash_temas import render_temas_emergentes
from dashboard.dash_ui import (
    _page_head,
    hay_datos,
    card_explicativa,
    referencias_publicaciones,
)


def render_bloque2_audiencia(periodo, plataforma):
    _page_head(
        "SEGMENTACIÓN DE AUDIENCIA / ANÁLISIS DE PÚBLICOS",
        "Estructura de públicos y voces de influencia",
        "Composición emocional de quienes participan en la conversación: simpatizantes, neutrales y críticos; nivel de polarización y páginas que concentran la interacción.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    df_comentarios = cargar_comentarios_fb(FACEBOOK_DB)
    if not hay_datos(df_comentarios, "Aún no hay comentarios procesados."):
        return

    # ── 1. MAPA DE PÚBLICOS ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Mapa de Públicos</div><div class="section-subtitle">Composición de la audiencia según el tono de sus comentarios.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Cómo se divide la audiencia según el tono de sus comentarios: simpatizantes (positivos), neutrales y críticos (negativos).",
        "Cada porcentaje es la proporción de comentarios de ese tipo. La base son comentarios analizados, no personas únicas.",
    )
    df_tmp = df_comentarios.dropna(subset=['score_sentimiento'])
    if not df_tmp.empty:
        n_pos = (df_tmp['score_sentimiento'] > 0.1).sum()
        n_neg = (df_tmp['score_sentimiento'] < -0.1).sum()
        n_neu = len(df_tmp) - n_pos - n_neg
        total = n_pos + n_neg + n_neu
        p_pos = n_pos / total * 100 if total else 0
        p_neg = n_neg / total * 100 if total else 0
        p_neu = n_neu / total * 100 if total else 0

        st.markdown(f"""
        <div class="panel">
            <div class="panel-head">
                <div class="panel-title">DISTRIBUCIÓN DE PÚBLICOS</div>
                <div class="panel-meta">{int(total):,} COMENTARIOS ANALIZADOS</div>
            </div>
            <div class="bar-tri" style="height:14px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{p_pos:.1f}%"></span>
                <span class="bar-tri-neu" style="width:{p_neu:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{p_neg:.1f}%"></span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px">
                <div class="stat-card" style="border-top:2px solid var(--green);padding:14px"><div class="stat-value" style="color:var(--green)">{p_pos:.0f}%</div><div class="stat-label">SIMPATIZANTE</div></div>
                <div class="stat-card" style="border-top:2px solid var(--amber);padding:14px"><div class="stat-value" style="color:var(--amber)">{p_neu:.0f}%</div><div class="stat-label">NEUTRAL</div></div>
                <div class="stat-card" style="border-top:2px solid var(--red);padding:14px"><div class="stat-value" style="color:var(--red)">{p_neg:.0f}%</div><div class="stat-label">CRÍTICO</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:var(--fg-muted)">La base son los comentarios analizados, no personas individuales.</p>', unsafe_allow_html=True)

        m = evaluar_muestra(len(df_comentarios))
        st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">{m["etiqueta"]}</p>', unsafe_allow_html=True)
        referencias_publicaciones(limit=10, titulo="PUBLICACIONES ANALIZADAS")

    # ── 2. POLARIZACIÓN — consenso vs confrontación ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Polarización</div><div class="section-subtitle">Consenso vs. confrontación: si la conversación se parte en dos bandos enfrentados.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Si la conversación está en consenso o partida en dos bandos enfrentados (a favor vs. en contra).",
        "Mientras más parejos sean los dos lados, mayor la confrontación. Si un lado domina o casi todo es neutral, hay consenso.",
    )
    pol = calcular_polarizacion(df_tmp['score_sentimiento']) if not df_tmp.empty else None
    if pol:
        col_nivel = {'confrontacion': 'var(--red)', 'dividida': 'var(--amber)', 'consenso': 'var(--green)'}.get(pol['nivel'], 'var(--accent)')
        comprometidos = pol['n_favor'] + pol['n_contra']
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_nivel}">{pol['estado'].upper()}</div><div class="panel-meta">{comprometidos:,} TOMARON POSTURA · ÍNDICE {pol['indice']:.0f}/100</div></div>
            <div class="bar-tri" style="height:16px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{pol['pct_favor']:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{pol['pct_contra']:.1f}%"></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:12px">
                <span style="color:var(--green)">A favor {pol['pct_favor']:.0f}%</span>
                <span style="color:var(--red)">En contra {pol['pct_contra']:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">Confrontación alta = los dos bandos tienen tamaño parecido. Consenso = un lado domina o la mayoría es neutral. Índice {pol["indice"]:.0f}/100 (equilibrio de bandos × cuánta gente toma postura).</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes comentarios con postura definida para medir polarización.</div>', unsafe_allow_html=True)

    # ── 3. VOCES DE INFLUENCIA ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Voces de Influencia</div><div class="section-subtitle">Páginas oficiales con mayor concentración de interacción.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué páginas oficiales concentran la mayor parte de la interacción ciudadana.",
        "La barra más larga es la página con más reacciones y comentarios. Son páginas o cuentas, no personas.",
    )
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB)
    if not df_fb_raw.empty:
        top_pages = df_fb_raw.groupby('page_name').agg(
            engagement=('engagement_total', 'sum'),
            posts=('post_id', 'count')
        ).reset_index().sort_values('engagement', ascending=False).head(5)
        max_eng = top_pages['engagement'].max() if not top_pages.empty else 1
        rows_html = ""
        for _, r in top_pages.iterrows():
            pct = (r['engagement'] / max_eng * 100) if max_eng > 0 else 0
            rows_html += f'<div class="bar-row"><div class="bar-row-label">{r["page_name"]}</div><div class="bar-track"><div class="bar-fill bar-fill-cy" style="width:{pct:.1f}%"></div></div><div class="bar-row-val">{int(r["engagement"]):,} · {int(r["posts"])}p</div></div>'
        st.markdown(f'<div class="panel"><div class="panel-head"><div class="panel-title">TOP 5 · PÁGINAS OFICIALES</div><div class="panel-meta">ENGAGEMENT · # POSTS</div></div>{rows_html}</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:var(--fg-muted)">Son páginas y cuentas oficiales, no ciudadanos individuales.</p>', unsafe_allow_html=True)
        referencias_publicaciones(limit=8, titulo="PUBLICACIONES DE LAS PÁGINAS")
    else:
        st.markdown('<div class="status-info">Sin datos de engagement para identificar voces.</div>', unsafe_allow_html=True)

    # ── 4. CRUCE TEMA × ZONA ──
    st.markdown('<div class="section-header"><div class="section-title">04 · Cruce Tema × Zona</div><div class="section-subtitle">Combinaciones de tema y zona con mayor volumen de comentarios.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué combinaciones de tema y zona generan más comentarios.",
        "Cada fila es una zona y un tema; el número es cuántos comentarios hubo y el color su tono general.",
    )
    cruce = cargar_cruce_tema_zona(FACEBOOK_DB)
    if cruce:
        rows_html = ""
        for r in cruce[:10]:
            sent_emoji = {"positivo": "🟢", "negativo": "🔴", "neutral": "⚪", "muy_positivo": "🟢", "muy_negativo": "🔴", "mixto": "🟡"}.get(r["sentiment"], "⚪")
            rows_html += f'<div class="bar-row"><div class="bar-row-label">{r["zona"]} · {r["tema"]}</div><div class="bar-row-val" style="min-width:60px">{sent_emoji} {r["n"]:,}</div></div>'
        st.markdown(f'<div class="panel"><div class="panel-head"><div class="panel-title">TOP 10 · TEMA × ZONA</div><div class="panel-meta">COMENTARIOS</div></div>{rows_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">No hay suficientes datos georreferenciados para el cruce tema × zona.</div>', unsafe_allow_html=True)

    # ── 5. PERFIL DE AUDIENCIA (OCEAN) ──
    st.markdown('<div class="section-header"><div class="section-title">05 · Perfil de Audiencia</div><div class="section-subtitle">Segmentos de público identificados por su comportamiento narrativo.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Grupos de público que se comportan parecido al comentar (su tema y tono dominante).",
        "Cada segmento agrupa comentarios similares; se indica su tamaño, tono y tema más frecuente.",
    )
    perfil = cargar_perfil_ocean(FACEBOOK_DB)
    if perfil.get("has_sklearn") and perfil.get("clusters"):
        sent_map = {"positive": "🟢 positivo", "negative": "🔴 negativo", "neutral": "⚪ neutral"}
        for label, p in perfil["clusters"].items():
            sent = sent_map.get(p.get("dominant_sentiment", ""), "⚪")
            dom_topic = p.get("dominant_topic", "—")
            st.markdown(f"""
            <div class="kpi-card kpi-card-eff" style="max-width:100%">
                <div class="kpi-label">SEGMENTO {label}</div>
                <div style="display:flex;gap:16px;flex-wrap:wrap;margin:6px 0">
                    <span style="font-size:13px"><strong>{p.get("size", 0)}</strong> comentarios</span>
                    <span style="font-size:13px">{sent}</span>
                    <span style="font-size:13px">Tema: {dom_topic}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">El perfil de audiencia requiere scikit-learn y al menos 5 posts con datos completos.</div>', unsafe_allow_html=True)

    # ── 6. TEMAS EMERGENTES ──
    render_temas_emergentes(FACEBOOK_DB)
