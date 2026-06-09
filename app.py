import sqlite3
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import os
PIPELINE_DB = os.path.join(os.path.dirname(__file__), "data", "pipeline.db")

st.set_page_config(
    page_title="Dashboard Ejecutivo · Alcaldía de Santa Ana",
    page_icon="\u25ab",
    layout="wide",
)

st.markdown("""
<style>
    .stApp { background: #0a0a14; color: #d0d0e8; }
    .stTabs [data-baseweb="tab"] { font-family: 'JetBrains Mono', monospace; font-size: 10px; }
    .stTabs [aria-selected="true"] { color: #ff3355; }
    h1, h2, h3 { font-family: 'JetBrains Mono', monospace; color: #ff3355; }
    h4 { color: #00f0ff; }
    .card {
        background: #0e0e20; border: 1px solid #1a1a3e; border-radius: 6px;
        padding: 14px 18px; margin: 6px 0;
    }
    .card .label { font-size: 9px; text-transform: uppercase; color: #6b6b8a; letter-spacing: 1px; }
    .card .value { font-size: 28px; font-weight: 500; font-family: monospace; }
    .alert { border-left: 3px solid; border-radius: 4px; padding: 10px 14px; margin: 8px 0; }
    .alert.crisis { border-left-color: #ff3355; background: #1a0808; }
    .alert.warning { border-left-color: #ffb000; background: #1a1408; }
    .alert.ok { border-left-color: #00ff88; background: #081a10; }
    .footer { text-align: center; font-size: 10px; color: #3a3a5a; font-family: monospace; }
</style>
""", unsafe_allow_html=True)


def conectar():
    conn = sqlite3.connect(PIPELINE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def q(query):
    conn = conectar()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


st.sidebar.markdown(
    "<h1 style='font-size:13px;text-transform:uppercase;color:#ff3355;'>"
    "\u25ab PULSO CIUDADANO</h1>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    f"<p style='font-size:10px;color:#6b6b8a;font-family:monospace;'>"
    f"Alcaldía Santa Ana · {datetime.now().strftime('%d %b %Y')}</p>",
    unsafe_allow_html=True,
)

platforms = ["facebook", "tiktok"]
selected_platform = st.sidebar.selectbox("Plataforma", ["Ambas"] + platforms, index=0)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<p style='font-size:9px;color:#3a3a5a'>Metodología: Cambridge Analytica adaptada "
    "a datos agregados. Las reacciones son proxy emocional, no test psicológico.</p>",
    unsafe_allow_html=True,
)


def filtrar_plataforma(df, platform, col="plataforma"):
    if platform != "Ambas":
        return df[df[col] == platform]
    return df


# ─── LOAD ALL DATA ───────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_all():
    engagement = q("""
        SELECT e.*, c.etiqueta AS categoria_label
        FROM post_engagement e
        LEFT JOIN post_categorias c ON e.id = c.id AND e.plataforma = c.plataforma
    """)
    sentimiento = q("SELECT * FROM post_sentimiento")
    series = q("SELECT * FROM series_temporales")
    noticias = q("SELECT * FROM noticias_externas")
    eventos = q("SELECT * FROM eventos_correlacionados")
    return engagement, sentimiento, series, noticias, eventos


engagement, sentimiento, series, noticias, eventos = load_all()

# ─── TABS ─────────────────────────────────────────────────────────

tabs = st.tabs([
    "\u25ab Pulso Ciudadano",
    "\u25c9 Temas",
    "\u25b6 Tiempo",
    "\u25cc Comentarios",
    "\u25c8 Contexto",
])


# ═══════════════════════════════════════════════════════════════════
# TAB 1 — PULSO CIUDADANO
# ═══════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("<h3>\u25ab PULSO CIUDADANO</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:12px;color:#6b6b8a;margin-top:-8px'>"
        "¿Cómo está la ciudadanía hoy? Score emocional neto, controversia y tendencias.</p>",
        unsafe_allow_html=True,
    )

    eng_filtered = filtrar_plataforma(engagement, selected_platform)

    if eng_filtered.empty:
        st.warning("No hay datos de engagement para los filtros seleccionados.")
    else:
        # Score emocional neto promedio (últimos 30 días)
        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            score_neto = eng_filtered["score_emocional_neto"].mean()
            color = "#00ff88" if score_neto > 0.1 else ("#ffb000" if score_neto > -0.1 else "#ff3355")
            st.markdown(f"""
            <div class='card'><div class='label'>Score Emocional Neto</div>
            <div class='value' style='color:{color}'>{score_neto:.3f}</div></div>
            """, unsafe_allow_html=True)

        with col_b:
            controversy = eng_filtered["indice_controversia"].mean()
            c_color = "#ff3355" if controversy > 0.2 else ("#ffb000" if controversy > 0.1 else "#00ff88")
            st.markdown(f"""
            <div class='card'><div class='label'>Índice de Controversia</div>
            <div class='value' style='color:{c_color}'>{controversy:.1%}</div></div>
            """, unsafe_allow_html=True)

        with col_c:
            afecto = eng_filtered["indice_afecto_positivo"].mean()
            st.markdown(f"""
            <div class='card'><div class='label'>Afecto Positivo</div>
            <div class='value' style='color:#00f0ff'>{afecto:.1%}</div></div>
            """, unsafe_allow_html=True)

        with col_d:
            viral = eng_filtered["indice_viralidad"].mean()
            st.markdown(f"""
            <div class='card'><div class='label'>Viralidad</div>
            <div class='value' style='color:#8860ff'>{viral:.4f}</div></div>
            """, unsafe_allow_html=True)

        # Alerta
        if controversy > 0.20:
            st.markdown(f"""
            <div class='alert crisis'>
                <b>\u26a0 ALERTA:</b> La controversia supera el 20%. 
                Los temas de confrontación dominan la conversación pública.
            </div>
            """, unsafe_allow_html=True)
        elif controversy > 0.10:
            st.markdown(f"""
            <div class='alert warning'>
                <b>\u26a0 Atención:</b> La controversia está entre 10-20%.
                Monitorear tendencia.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='alert ok'>
                <b>\u2713</b> Controversia controlada. La conversación se mantiene en tono constructivo.
            </div>
            """, unsafe_allow_html=True)

        # Engagement rate distribution
        st.markdown("---")
        col_ch1, col_ch2 = st.columns(2)

        with col_ch1:
            top_cats = eng_filtered.groupby("categoria_label")["engagement_rate"].mean().sort_values(ascending=False).head(8)
            if not top_cats.empty:
                fig = px.bar(
                    x=top_cats.values, y=top_cats.index,
                    orientation="h",
                    labels={"x": "Engagement Rate Promedio", "y": ""},
                    title="Engagement Rate por Categoría",
                    color=top_cats.values,
                    color_continuous_scale=["#00f0ff", "#ff3355"],
                )
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#d0d0e8", height=300, showlegend=False)
                st.plotly_chart(fig, width='stretch')

        with col_ch2:
            sentiment_dist = eng_filtered["score_sentimiento"].dropna()
            if not sentiment_dist.empty:
                fig = px.histogram(
                    sentiment_dist, nbins=20,
                    labels={"value": "Score de Sentimiento"},
                    title="Distribución de Sentimiento en Posts",
                    color_discrete_sequence=["#00f0ff"],
                )
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#d0d0e8", height=300)
                fig.add_vline(x=0, line_dash="dash", line_color="#ff3355")
                st.plotly_chart(fig, width='stretch')

        st.markdown("---")
        st.markdown("<p style='font-size:10px;color:#3a3a5a'>"
                    "Score emocional neto = afecto positivo - controversia + (score sentimiento × 0.3). "
                    "Valores >0 indican clima favorable; <0 indican descontento.</p>",
                    unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# TAB 2 — TEMAS
# ═══════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("<h3>\u25c9 ¿QUÉ TEMAS RESUENAN?</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:12px;color:#6b6b8a;margin-top:-8px'>"
        "Categorías con más engagement, más controversia y carga emocional.</p>",
        unsafe_allow_html=True,
    )

    eng_f = filtrar_plataforma(engagement, selected_platform)

    if eng_f.empty or "categoria_label" not in eng_f.columns:
        st.warning("Ejecutá los módulos del pipeline primero.")
    else:
        cats_with_data = eng_f[eng_f["categoria_label"].notna() & (eng_f["categoria_label"] != "")]
        if cats_with_data.empty:
            st.info("No hay categorías asignadas aún. Corré el Módulo 1.")
        else:
            # Mapa de calor: categoría × métricas
            heatmap_data = cats_with_data.groupby("categoria_label").agg({
                "engagement_rate": "mean",
                "indice_controversia": "mean",
                "indice_afecto_positivo": "mean",
                "indice_humor": "mean",
                "indice_viralidad": "mean",
                "score_emocional_neto": "mean",
            }).reset_index()

            metrics_map = {
                "engagement_rate": "Engagement",
                "indice_controversia": "Controversia",
                "indice_afecto_positivo": "Afecto+",
                "indice_humor": "Humor",
                "indice_viralidad": "Viralidad",
                "score_emocional_neto": "Score Neto",
            }
            heatmap_long = heatmap_data.melt(
                id_vars=["categoria_label"],
                value_vars=list(metrics_map.keys()),
                var_name="metrica",
                value_name="valor",
            )
            heatmap_long["metrica_label"] = heatmap_long["metrica"].map(metrics_map)

            fig = px.density_heatmap(
                heatmap_long,
                x="metrica_label", y="categoria_label", z="valor",
                title="Mapa de Calor: Categoría × Emoción",
                color_continuous_scale=["#0a0a14", "#00f0ff", "#ff3355"],
                text_auto=".3f",
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#d0d0e8", height=400,
                              xaxis=dict(tickfont=dict(size=9)))
            st.plotly_chart(fig, width='stretch')

            # Ranking
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                top_engagement = heatmap_data.sort_values("engagement_rate", ascending=False).head(5)
                st.markdown("<h4>Más Engagement</h4>", unsafe_allow_html=True)
                for _, r in top_engagement.iterrows():
                    st.markdown(f"""
                    <div class='card' style='padding:8px 12px'>
                        <span style='color:#00f0ff;font-family:monospace'>{r['categoria_label']}</span>
                        <span style='float:right;color:#d0d0e8'>{r['engagement_rate']:.3f}</span>
                    </div>""", unsafe_allow_html=True)

            with col_r2:
                top_controversy = heatmap_data.sort_values("indice_controversia", ascending=False).head(5)
                st.markdown("<h4>Más Controversia</h4>", unsafe_allow_html=True)
                for _, r in top_controversy.iterrows():
                    st.markdown(f"""
                    <div class='card' style='padding:8px 12px'>
                        <span style='color:#ff3355;font-family:monospace'>{r['categoria_label']}</span>
                        <span style='float:right;color:#d0d0e8'>{r['indice_controversia']:.1%}</span>
                    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# TAB 3 — TIEMPO
# ═══════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("<h3>\u25b6 ¿CUÁNDO REACCIONA LA GENTE?</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:12px;color:#6b6b8a;margin-top:-8px'>"
        "Evolución del engagement en el tiempo con picos y anomalías marcados.</p>",
        unsafe_allow_html=True,
    )

    s_filtered = filtrar_plataforma(series, selected_platform)

    if s_filtered.empty:
        st.warning("No hay datos de series temporales. Corré el Módulo 4.")
    else:
        s_filtered = s_filtered.sort_values("periodo")
        s_filtered["semana_label"] = pd.to_datetime(s_filtered["semana_label"], errors="coerce")

        fig = go.Figure()

        for plat in s_filtered["plataforma"].unique():
            plat_data = s_filtered[s_filtered["plataforma"] == plat]
            fig.add_trace(go.Scatter(
                x=plat_data["semana_label"],
                y=plat_data["engagement_promedio"],
                mode="lines+markers",
                name=plat.capitalize(),
                line=dict(width=2),
                marker=dict(size=5),
            ))

            anomalias_plot = plat_data[plat_data["es_anomalia"] == True]
            if not anomalias_plot.empty:
                fig.add_trace(go.Scatter(
                    x=anomalias_plot["semana_label"],
                    y=anomalias_plot["engagement_promedio"],
                    mode="markers",
                    name=f"Anomalía {plat}",
                    marker=dict(
                        size=12, symbol="x",
                        color="#ff3355" if "negativo" in anomalias_plot["tipo_anomalia"].values[0] else "#00ff88",
                    ),
                ))

        fig.update_layout(
            title="Engagement Promedio Semanal",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#d0d0e8", height=400,
            hovermode="x unified",
            legend=dict(font=dict(size=10)),
        )
        st.plotly_chart(fig, width='stretch')

        # Stats
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            total_anomalies = s_filtered[s_filtered["es_anomalia"] == True]
            st.markdown(f"""
            <div class='card'><div class='label'>Anomalías Detectadas</div>
            <div class='value' style='color:#ff3355'>{len(total_anomalies)}</div></div>
            """, unsafe_allow_html=True)

        with col_s2:
            best_week = s_filtered.loc[s_filtered["engagement_total"].idxmax()] if not s_filtered.empty else {}
            if not best_week.empty:
                st.markdown(f"""
                <div class='card'><div class='label'>Mejor Semana</div>
                <div class='value' style='color:#00ff88'>{str(best_week.get('semana_label','-'))[:10]}</div>
                <div class='label'>{best_week.get('engagement_total',0):,} engagements</div></div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# TAB 4 — COMENTARIOS
# ═══════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("<h3>\u25cc ¿QUÉ DICE LA GENTE?</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:12px;color:#6b6b8a;margin-top:-8px'>"
        "Sentimiento en comentarios por tema y frases más repetidas.</p>",
        unsafe_allow_html=True,
    )

    s_filtered = filtrar_plataforma(sentimiento, selected_platform)

    if s_filtered.empty:
        st.warning("No hay datos de sentimiento. Corré el Módulo 2.")
    else:
        # Pie: distribución general de sentimiento en comentarios
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            total_pos = s_filtered["pct_positivo"].mean()
            total_neg = s_filtered["pct_negativo"].mean()
            total_neu = s_filtered["pct_neutral"].mean()
            fig = go.Figure(data=[go.Pie(
                labels=["Positivo", "Neutral", "Negativo"],
                values=[total_pos, total_neu, total_neg],
                marker=dict(colors=["#00ff88", "#ffb000", "#ff3355"]),
                textinfo="label+percent",
                hole=0.4,
            )])
            fig.update_layout(
                title="Sentimiento Global en Comentarios",
                paper_bgcolor="rgba(0,0,0,0)", font_color="#d0d0e8", height=300,
            )
            st.plotly_chart(fig, width='stretch')

        with col_p2:
            # Score de sentimiento promedio
            avg_score = s_filtered["score_sentimiento"].mean()
            st.markdown(f"""
            <div class='card'>
                <div class='label'>Score de Sentimiento Promedio</div>
                <div class='value' style='color:{"#00ff88" if avg_score > 0 else "#ff3355"}'>{avg_score:.3f}</div>
                <div style='font-size:10px;color:#6b6b8a;margin-top:4px'>
                Rango: -1 (todo negativo) a +1 (todo positivo)
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Nube de palabras (simplified — top words from engagement table categories)
            if not engagement.empty:
                all_scores = engagement["score_sentimiento"].dropna()
                pos_pct = (all_scores > 0).mean() * 100
                neg_pct = (all_scores < 0).mean() * 100
                neutral_pct = (all_scores == 0).mean() * 100
                st.markdown(f"""
                <div class='card'>
                    <div class='label'>Distribución de Posts</div>
                    <span style='color:#00ff88'>\u25cf Positivos {pos_pct:.0f}%</span><br>
                    <span style='color:#ffb000'>\u25cf Neutrales {neutral_pct:.0f}%</span><br>
                    <span style='color:#ff3355'>\u25cf Negativos {neg_pct:.0f}%</span>
                </div>
                """, unsafe_allow_html=True)

        # Sentimiento por categoría
        if "categoria" in engagement.columns:
            st.markdown("---")
            st.markdown("<h4>Sentimiento por Categoría</h4>", unsafe_allow_html=True)
            cat_sent = engagement[engagement["categoria"].notna() & (engagement["categoria"] != "")]
            if not cat_sent.empty:
                cat_sent_agg = cat_sent.groupby("categoria").agg(
                    score_promedio=("score_sentimiento", "mean"),
                    cantidad=("id", "count"),
                ).reset_index().sort_values("score_promedio")
                fig = px.bar(
                    cat_sent_agg, x="score_promedio", y="categoria", orientation="h",
                    labels={"score_promedio": "Score Sentimiento", "categoria": ""},
                    title="Score de Sentimiento Promedio por Categoría",
                    color="score_promedio",
                    color_continuous_scale=["#ff3355", "#ffb000", "#00ff88"],
                )
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font_color="#d0d0e8", height=350)
                fig.add_vline(x=0, line_dash="dash", line_color="#6b6b8a")
                st.plotly_chart(fig, width='stretch')

            # Comentarios negativos recientes (sample)
            st.markdown("---")
            st.markdown("<h4>Frases Más Repetidas (Comentarios Negativos)</h4>", unsafe_allow_html=True)
            try:
                conn = conectar()
                neg_comments = conn.execute("""
                    SELECT texto_comentario, autor, fecha
                    FROM facebook_comentarios
                    WHERE LENGTH(TRIM(texto_comentario)) > 10
                    ORDER BY RANDOM() LIMIT 10
                """).fetchall()
                conn.close()
                if neg_comments:
                    for c in neg_comments[:5]:
                        st.markdown(f"""
                        <div class='alert warning' style='padding:6px 10px;margin:4px 0'>
                            <span style='font-size:11px;font-style:italic'>"{c[0][:200]}"</span>
                            <span style='font-size:9px;color:#6b6b8a;display:block'>— {c[1] or 'Anónimo'}</span>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.info("No hay comentarios con texto suficiente.")
            except Exception as e:
                st.info(f"No se pudieron cargar comentarios: {e}")


# ═══════════════════════════════════════════════════════════════════
# TAB 5 — CONTEXTO
# ═══════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("<h3>\u25c8 ¿QUÉ PASÓ AFUERA?</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:12px;color:#6b6b8a;margin-top:-8px'>"
        "Correlación entre noticias externas y picos de engagement en redes.</p>",
        unsafe_allow_html=True,
    )

    col_n1, col_n2 = st.columns(2)

    with col_n1:
        st.markdown("<h4>Noticias Externas</h4>", unsafe_allow_html=True)
        if not noticias.empty:
            for _, n in noticias.iterrows():
                color_map = {"positiva": "#00ff88", "negativa": "#ff3355", "neutral": "#ffb000"}
                nc = color_map.get(n.get("clasificacion", "neutral"), "#6b6b8a")
                st.markdown(f"""
                <div class='card' style='padding:8px 12px'>
                    <span style='color:{nc};font-size:10px;text-transform:uppercase'>{n['clasificacion']}</span>
                    <span style='float:right;color:#6b6b8a;font-size:10px'>{n['fuente']}</span>
                    <div style='font-size:12px;margin:4px 0'>{n['titular']}</div>
                    <div style='font-size:10px;color:#6b6b8a'>{n['fecha']}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No hay noticias cargadas. Configurá fuentes en el Módulo 5.")

    with col_n2:
        st.markdown("<h4>Correlaciones Noticia → Pico</h4>", unsafe_allow_html=True)
        if not eventos.empty:
            for _, e in eventos.iterrows():
                st.markdown(f"""
                <div class='card' style='padding:8px 12px'>
                    <span style='color:#00f0ff;font-size:11px'>{e['noticia_titular'][:50]}...</span>
                    <div style='font-size:10px;color:#6b6b8a;margin-top:4px'>
                        {e['anomalia_tipo']} · {e['anomalia_plataforma']} ·
                        {e['dias_diferencia']} días de diferencia
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No hay correlaciones detectadas aún.")

    st.markdown("---")
    st.markdown("""
    <p style='font-size:10px;color:#3a3a5a'>
    ⚠ La correlación entre noticias y picos de engagement NO implica causalidad.
    Las noticias mostradas son datos de ejemplo. Para producción, conectar con fuentes reales.
    </p>
    """, unsafe_allow_html=True)


# ─── FOOTER ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p class='footer'>"
    "Dashboard Ejecutivo de Inteligencia Ciudadana · Alcaldía Santa Ana · "
    "Metodología inspirada en Cambridge Analytica (Kosinski et al. 2013) · "
    "Sin propuesta de campaña · Solo datos de la realidad</p>",
    unsafe_allow_html=True,
)
