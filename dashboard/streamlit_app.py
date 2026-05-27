import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.storage.supabase_client import SupabaseStorage
from src.analyzer.nlp_pipeline import analyze_emotions, analyze_entities
from src.analyzer.emotion_lexicon import EMOTION_COLORS
from src.analyzer.gazetteer import GAZETTEER
from src.intelligence.cambridge_index import run_all_detectors, SuppressionEngine, TOPIC_DEFAULT_SENSITIVITY

st.set_page_config(
    page_title="Jose Chicas · Panel de Ciencia de Datos",
    page_icon="⬥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background: #050510; color: #c8c8e0; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { 
        font-family: 'JetBrains Mono', monospace; 
        font-size: 11px; 
        text-transform: uppercase; 
        letter-spacing: 0.8px;
        color: #6b6b8a;
    }
    .stTabs [aria-selected="true"] { color: #00f0ff; }
    h1, h2, h3 { font-family: 'JetBrains Mono', monospace; color: #00f0ff; }
    .metric-card {
        background: #0b0b1a; border: 1px solid #1a1a3e; border-radius: 6px;
        padding: 14px 16px; text-align: center;
    }
    .metric-card .label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.8px; color: #6b6b8a; }
    .metric-card .value { font-size: 28px; font-weight: 500; font-family: monospace; }
    .alert-card {
        background: #0b0b1a; border-left: 3px solid; border-radius: 6px;
        padding: 12px 16px; margin-bottom: 8px;
    }
    .alert-card.crisis { border-left-color: #ff3355; }
    .alert-card.warning { border-left-color: #ffb000; }
    .alert-card.info { border-left-color: #00f0ff; }
    .alert-card .title { font-family: monospace; font-size: 12px; font-weight: 500; }
    .alert-card .desc { font-size: 11px; color: #6b6b8a; margin-top: 4px; }
    .ts-table { font-family: 'JetBrains Mono', monospace; font-size: 11px; width: 100%; border-collapse: collapse; }
    .ts-table th { text-align: left; padding: 6px 10px; border-bottom: 1px solid #1a1a3e; color: #6b6b8a; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 400; }
    .ts-table td { padding: 5px 10px; border-bottom: 1px solid rgba(26,26,62,.5); }
    .ts-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
    .severity-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
    footer { display: none; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown(
    "<h1 style='font-size:13px;letter-spacing:1px;text-transform:uppercase;color:#00f0ff;'>"
    "⬥ PANEL DE CIENCIA DE DATOS</h1>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    "<p style='font-size:10px;color:#6b6b8a;font-family:monospace;'>"
    "Alcaldía de Santa Ana · Gustavo Acevedo<br>"
    f"{datetime.now().strftime('%d %b %Y')}</p>",
    unsafe_allow_html=True,
)

storage = SupabaseStorage()
posts_raw = storage.get_fb_posts(limit=10000)
comments_raw = storage.get_fb_comments(limit=50000)

posts_df = pd.DataFrame(posts_raw) if posts_raw else pd.DataFrame()
comments_df = pd.DataFrame(comments_raw) if comments_raw else pd.DataFrame()

nlp_results = storage.get_nlp_results(limit=50000)
emotions_by_item = {}
entities_by_item = {}
for nr in nlp_results:
    key = (nr["item_type"], nr["item_id"])
    if nr["analysis_type"] == "emotions":
        emotions_by_item[key] = nr["result_json"]
    elif nr["analysis_type"] == "entities":
        entities_by_item[key] = nr["result_json"]

collocation_results = storage.get_nlp_results(item_type="global", analysis_type="collocations", limit=1)

def fmt(n):
    try:
        return f"{int(n):,}"
    except:
        return str(n)

def short(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)

def emotion_color(e):
    return EMOTION_COLORS.get(e, "#6b6b8a")

def safe_div(a, b):
    return a / b if b else 0

latent_topic_results = storage.get_nlp_results(item_type="global", analysis_type="latent_topic", limit=1)

intelligence = run_all_detectors(posts_raw, SuppressionEngine()) if posts_raw else {"alerts": [], "indices": {}, "topic_sensitivity": {}, "alert_summary": {}}

tabs = st.tabs([
    "⬥ Ejecutivo", "◈ Emociones", "◎ Entidades",
    "⬡ Tópicos", "◈ Cambridge", "▣ Colocaciones", "⚠ Anomalías", "◉ Comentarios", "◉ Diagnóstico"
])

with tabs[0]:
    st.markdown("## Panel Ejecutivo")
    total_posts = len(posts_df)
    total_comments = len(comments_df)
    total_reactions = int(posts_df[[c for c in posts_df.columns if c.endswith('_count') and c != 'comments_count' and c != 'shares_count' and c != 'views_count']].sum().sum()) if total_posts > 0 else 0
    total_views = int(posts_df['views_count'].sum()) if total_posts > 0 and 'views_count' in posts_df.columns else 0
    total_shares = int(posts_df['shares_count'].sum()) if total_posts > 0 and 'shares_count' in posts_df.columns else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"<div class='metric-card'><div class='label'>Publicaciones</div><div class='value' style='color:#00f0ff'>{fmt(total_posts)}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><div class='label'>Visualizaciones</div><div class='value' style='color:#00f0ff'>{short(total_views)}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><div class='label'>Reacciones</div><div class='value' style='color:#00ff88'>{fmt(total_reactions)}</div></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-card'><div class='label'>Comentarios</div><div class='value' style='color:#ffb000'>{fmt(total_comments)}</div></div>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<div class='metric-card'><div class='label'>Compartidos</div><div class='value' style='color:#8860ff'>{fmt(total_shares)}</div></div>", unsafe_allow_html=True)

    st.markdown("### Resumen de Ciencia de Datos")
    if total_posts == 0:
        st.info("No hay datos cargados. El scraping está en progreso.")
    else:
        st.markdown(f"""
        <div style='background:#0b0b1a;border:1px solid #1a1a3e;border-radius:6px;padding:16px;font-size:12px;line-height:1.7'>
        <p><strong style='color:#00f0ff'>Estado del Pipeline NLP:</strong>
        {len(emotions_by_item)} análisis de emociones · {len(entities_by_item)} análisis de entidades</p>
        <p><strong style='color:#00f0ff'>Cobertura:</strong>
        {len([k for k in emotions_by_item if k[0]=='post'])} posts con emociones de {total_posts} totales ·
        {len([k for k in emotions_by_item if k[0]=='comment'])} comments con emociones de {total_comments} totales</p>
        </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            sentiment_data = posts_df['sentiment'].value_counts() if 'sentiment' in posts_df.columns else pd.Series()
            if not sentiment_data.empty:
                fig = px.pie(
                    values=sentiment_data.values, names=sentiment_data.index,
                    color=sentiment_data.index,
                    color_discrete_map={'positive': '#00ff88', 'neutral': '#ffb000', 'negative': '#ff3355'},
                    title="Distribución de Sentimiento (Posts)"
                )
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            topic_data = posts_df['topic_category'].value_counts() if 'topic_category' in posts_df.columns else pd.Series()
            if not topic_data.empty:
                fig = px.bar(
                    x=topic_data.values, y=topic_data.index,
                    orientation='h', title="Posts por Tópico",
                    color=topic_data.values,
                    color_continuous_scale=['#00f0ff', '#8860ff'],
                )
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver Dashboard HTML Estático"):
        html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
        if os.path.exists(html_path):
            with open(html_path) as f:
                st.components.v1.html(f.read(), height=800, scrolling=True)
        else:
            st.warning("dashboard.html no encontrado")

with tabs[1]:
    st.markdown("## Análisis de Emociones")
    if not emotions_by_item:
        st.info("Ejecutá `./scrapeo nlp` para procesar emociones.")
    else:
        emotion_items = []
        for (itype, iid), emo in emotions_by_item.items():
            if emo:
                emotion_items.append({"type": itype, "id": iid, **emo})
        emo_df = pd.DataFrame(emotion_items) if emotion_items else pd.DataFrame()
        if not emo_df.empty:
            emotion_cols = [c for c in emo_df.columns if c in EMOTION_COLORS or c in ("joy", "anger", "sadness", "fear", "disgust", "surprise", "neutral")]
            if emotion_cols:
                avg_emotions = emo_df[emotion_cols].mean().sort_values(ascending=False)
                fig = px.bar(
                    x=avg_emotions.values, y=avg_emotions.index,
                    orientation='h',
                    title="Perfil Emocional Promedio",
                    color=avg_emotions.index,
                    color_discrete_map={e: EMOTION_COLORS.get(e, "#6b6b8a") for e in avg_emotions.index},
                )
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0', showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("### Mapa de Calor: Co-ocurrencia de Emociones")
                corr = emo_df[emotion_cols].corr()
                fig = px.imshow(corr, text_auto='.2f', color_continuous_scale=['#ff3355', '#0b0b1a', '#00ff88'],
                                aspect='auto', title="Correlación entre Emociones")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.markdown("## Explorador de Entidades")
    if not entities_by_item:
        st.info("Ejecutá `./scrapeo nlp` para extraer entidades.")
    else:
        loc_counter = Counter()
        person_counter = Counter()
        org_counter = Counter()
        gazetteer_counter = Counter()
        entity_sentiment = defaultdict(lambda: {"pos": 0, "neg": 0, "neu": 0, "count": 0})
        for (itype, iid), ent in entities_by_item.items():
            for loc in ent.get("locations", []):
                loc_counter[loc] += 1
            for person in ent.get("people", []):
                person_counter[person] += 1
            for org in ent.get("organizations", []):
                org_counter[org] += 1
            for gm in ent.get("gazetteer_matches", []):
                val = gm.get("value", "")
                gazetteer_counter[val] += 1
                if itype == "post":
                    post = posts_df[posts_df['post_id'] == iid]
                    if not post.empty:
                        s = post.iloc[0].get('sentiment', '')
                        sent_key = {"positive": "pos", "negative": "neg", "neutral": "neu"}.get(s, "neu")
                        entity_sentiment[val][sent_key] += 1
                        entity_sentiment[val]["count"] += 1
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Lugares Detectados (spaCy)")
            if loc_counter:
                loc_df = pd.DataFrame(loc_counter.most_common(20), columns=["Lugar", "Menciones"])
                fig = px.bar(loc_df.head(15), x="Menciones", y="Lugar", orientation='h',
                             color="Menciones", color_continuous_scale=['#00f0ff', '#8860ff'],
                             title="Top 15 Lugares")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.markdown("### Gazetter: Colonias y Zonas")
            if gazetteer_counter:
                gaz_df = pd.DataFrame(gazetteer_counter.most_common(20), columns=["Zona/Colonia", "Menciones"])
                fig = px.bar(gaz_df.head(15), x="Menciones", y="Zona/Colonia", orientation='h',
                             color="Menciones", color_continuous_scale=['#00ff88', '#ffb000'],
                             title="Top 15 Menciones del Gazetteer")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig, use_container_width=True)
        st.markdown("### Sentimiento por Entidad")
        if entity_sentiment:
            rows = []
            for ent, s in sorted(entity_sentiment.items(), key=lambda x: x[1]["count"], reverse=True)[:30]:
                total = s["pos"] + s["neg"] + s["neu"]
                if total > 0:
                    rows.append({"Entidad": ent, "Positivo": s["pos"]/total, "Negativo": s["neg"]/total,
                                 "Neutral": s["neu"]/total, "Menciones": s["count"]})
            if rows:
                ent_sent_df = pd.DataFrame(rows).sort_values("Negativo", ascending=False)
                fig = px.bar(ent_sent_df.head(15), x="Negativo", y="Entidad", orientation='h',
                             title="Entidades con Mayor Sentimiento Negativo",
                             color="Negativo", color_continuous_scale=['#ffb000', '#ff3355'],
                             text_auto='.0%')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig, use_container_width=True)

with tabs[3]:
    st.markdown("## Tópicos Latentes")
    if latent_topic_results:
        lt = latent_topic_results[0]["result_json"]
        topics = lt.get("topics", [])
        if topics:
            st.markdown(f"<p style='font-size:11px;color:#6b6b8a;font-family:monospace;'>{lt.get('n_docs', 0)} documentos · {len(topics)} tópicos · vocab: {lt.get('vocabulary_size', 0)} términos</p>", unsafe_allow_html=True)
            for t in topics:
                words = ", ".join(t.get("words", []))
                st.markdown(
                    f"<div style='background:#0b0b1a;border:1px solid #1a1a3e;border-radius:6px;padding:12px;margin-bottom:8px'>"
                    f"<div style='display:flex;justify-content:space-between'>"
                    f"<span style='font-family:monospace;font-size:12px;color:#00f0ff'>Tópico {t['id']+1}</span>"
                    f"<span style='font-family:monospace;font-size:10px;color:#6b6b8a'>{fmt(t['doc_count'])} docs ({t['pct']}%)</span>"
                    f"</div>"
                    f"<div style='font-size:11px;margin-top:4px;color:#c8c8e0'>{words}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            topic_df = pd.DataFrame([{"id": t['id']+1, "words": ", ".join(t['words'][:5]), "docs": t['doc_count'], "pct": t['pct']} for t in topics])
            fig = px.bar(topic_df, x='docs', y='id', orientation='h', text='words',
                         title="Distribución de Tópicos", labels={'id': '', 'docs': 'Documentos'},
                         color='docs', color_continuous_scale=['#00f0ff', '#8860ff'])
            fig.update_traces(textposition='outside')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0', showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No se encontraron tópicos latentes.")
    else:
        st.info("Ejecutá `./scrapeo nlp` con `--topics` para generar tópicos latentes.")

with tabs[4]:
    st.markdown("## Cambridge Index — Alertas Predictivas")

    if not posts_raw or len(posts_raw) < 5:
        st.info("Datos insuficientes para generar alertas (mínimo 5 posts).")
    else:
        alerts = intelligence["alerts"]
        ts = intelligence["topic_sensitivity"]
        alert_summary = intelligence["alert_summary"]

        col1, col2, col3 = st.columns(3)
        with col1:
            total_alerts = alert_summary.get("total", 0)
            color = "#ff3355" if total_alerts > 0 else "#00ff88"
            st.markdown(f"<div class='metric-card'><div class='label'>Alertas Activas</div><div class='value' style='color:{color}'>{total_alerts}</div></div>", unsafe_allow_html=True)
        with col2:
            by_sev = alert_summary.get("by_severity", {})
            criticas = by_sev.get("critico", 0) + by_sev.get("alto", 0)
            st.markdown(f"<div class='metric-card'><div class='label'>Críticas / Altas</div><div class='value' style='color:#ff3355'>{criticas}</div></div>", unsafe_allow_html=True)
        with col3:
            by_type = alert_summary.get("by_type", {})
            st.markdown(f"<div class='metric-card'><div class='label'>Tipos Detectados</div><div class='value' style='color:#00f0ff'>{len(by_type)}</div></div>", unsafe_allow_html=True)

        if alerts:
            st.markdown("### Alertas del Sistema Predictivo")
            for a in alerts:
                sev_color = {4: "#ff0044", 3: "#ff3355", 2: "#ffb000", 1: "#6b6b8a"}.get(a["severity"], "#6b6b8a")
                sev_label = a["severity_label"].upper()
                st.markdown(
                    f"<div class='alert-card' style='border-left-color:{sev_color}'>"
                    f"<div class='title'><span class='severity-dot' style='background:{sev_color}'></span>"
                    f"[{a['type'].upper()}] {a['title']}</div>"
                    f"<div class='desc'>{a['description']}</div>"
                    f"<div style='font-size:9px;color:#6b6b8a;font-family:monospace;margin-top:4px'>"
                    f"Score: {a['score']} · {sev_label}"
                    f"{' · ' + a['topic'].replace('_',' ').title() if a.get('topic') else ''}"
                    f"{' · Zona: ' + a['zona'] if a.get('zona') else ''}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("No se detectaron anomalías. El sistema de alertas está en verde.")

        st.markdown("### Sensibilidad por Tópico (Cambridge Index)")
        if ts:
            ts_html = '<table class="ts-table"><thead><tr><th>Tópico</th><th>Sensibilidad Base</th><th>Posts</th><th>Indicador</th></tr></thead><tbody>'
            for topic, data in sorted(ts.items(), key=lambda x: x[1]["base"], reverse=True):
                base = data["base"]
                color = "#ff3355" if base >= 1.4 else "#ffb000" if base >= 1.2 else "#00f0ff"
                bars = '<span style="color:' + color + '">' + "█" * max(1, int(base * 5)) + "</span>"
                ts_html += f"<tr><td>{topic.replace('_',' ').title()}</td><td style='color:{color}'>{base}</td><td>{data['posts']}</td><td>{bars}</td></tr>"
            ts_html += "</tbody></table>"
            st.markdown(ts_html, unsafe_allow_html=True)

        if alerts:
            st.markdown("### Distribución de Alertas")
            alert_df = pd.DataFrame(alerts)
            if not alert_df.empty and 'type' in alert_df.columns:
                type_counts = alert_df['type'].value_counts()
                fig = px.bar(
                    x=type_counts.values, y=type_counts.index, orientation='h',
                    title="Alertas por Tipo",
                    color=type_counts.index,
                    color_discrete_map={"ici": "#ff3355", "sdi": "#ffb000", "efi": "#00f0ff",
                                        "tai": "#8860ff", "zdi": "#5599ff"},
                )
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font_color='#c8c8e0', showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown(
            "<p style='font-size:10px;color:#6b6b8a;font-family:monospace;'>"
            "FÓRMULAS: ICI = z-score controversia (2σ) · SDI = caída relativa sentimiento (>20%) · "
            "EFI = caída engagement (>30%) · TAI = ratio enojo tópico (>2x) · ZDI = negatividad zona (>25%)<br>"
            "Supresión: cooldown 3-7d según tipo · sample mínimos · priorización por severidad + score</p>",
            unsafe_allow_html=True,
        )

with tabs[5]:
    st.markdown("## Colocaciones del Discurso")
    if collocation_results:
        coll = collocation_results[0]["result_json"]
        bigrams = coll.get("bigrams", {}).get("ngrams", {})
        trigrams = coll.get("trigrams", {}).get("ngrams", {})
        if bigrams:
            st.markdown("### Bigramas Más Frecuentes")
            bg_df = pd.DataFrame(list(bigrams.items()), columns=["Bigrama", "Frecuencia"]).sort_values("Frecuencia", ascending=False).head(30)
            fig = px.bar(bg_df.head(20), x="Frecuencia", y="Bigrama", orientation='h',
                         color="Frecuencia", color_continuous_scale=['#00f0ff', '#00ff88'],
                         title="Top 20 Bigramas")
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
            st.plotly_chart(fig, use_container_width=True)
        if trigrams:
            st.markdown("### Trigramas Más Frecuentes")
            tg_df = pd.DataFrame(list(trigrams.items()), columns=["Trigrama", "Frecuencia"]).sort_values("Frecuencia", ascending=False).head(20)
            st.dataframe(tg_df, use_container_width=True, hide_index=True)
        st.markdown(f"<p style='font-size:10px;color:#6b6b8a;font-family:monospace;'>Corpus: {coll.get('bigrams', {}).get('total_docs', 0)} documentos</p>", unsafe_allow_html=True)
    else:
        st.info("Ejecutá `./scrapeo nlp` para extraer colocaciones del corpus.")

with tabs[6]:
    st.markdown("## Detección de Anomalías — Serie Temporal")
    if total_posts < 10:
        st.info("Se necesitan más datos para detectar anomalías.")
    else:
        if 'created_time' in posts_df.columns and total_posts > 5:
            posts_df['created_date'] = pd.to_datetime(posts_df['created_time'], errors='coerce')
            posts_df['month'] = posts_df['created_date'].dt.to_period('M').astype(str)
            monthly = posts_df.groupby('month').agg(
                posts=('post_id', 'count'),
                angrys=('angrys_count', 'sum'),
                sads=('sads_count', 'sum'),
                likes=('likes_count', 'sum'),
                loves=('loves_count', 'sum'),
                hahas=('hahas_count', 'sum'),
                wows=('wows_count', 'sum'),
                views=('views_count', 'sum'),
                comments=('comments_count', 'sum'),
                shares=('shares_count', 'sum'),
            ).reset_index()
        else:
            monthly = pd.DataFrame()

        if not monthly.empty:
            monthly['controversy'] = (monthly['angrys'] + monthly['sads']) / (monthly['likes'] + monthly['loves'] + monthly['hahas'] + monthly['wows'] + monthly['angrys'] + monthly['sads'] + 1)
            monthly['engagement_rate'] = (monthly['likes'] + monthly['loves'] + monthly['comments'] + monthly['shares']) / (monthly['views'] + 1) * 100
            monthly['net_sentiment'] = (monthly['likes'] + monthly['loves'] - monthly['angrys'] - monthly['sads']) / (monthly['likes'] + monthly['loves'] + monthly['angrys'] + monthly['sads'] + 1)

        alerts = intelligence["alerts"]
        if alerts:
            st.markdown("### Alertas del Cambridge Index")
            for a in alerts[:5]:
                sev_color = {4: "#ff0044", 3: "#ff3355", 2: "#ffb000", 1: "#6b6b8a"}.get(a["severity"], "#6b6b8a")
                st.markdown(
                    f"<div class='alert-card' style='border-left-color:{sev_color}'>"
                    f"<div class='title'>[{a['type'].upper()}] {a['title']}</div>"
                    f"<div class='desc'>{a['description']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("No se detectaron anomalías significativas en el período actual.")

        if not monthly.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.line(monthly, x='month', y='controversy', markers=True,
                              title="Índice de Controversia Mensual",
                              labels={'controversy': 'Controversia', 'month': ''})
                if len(monthly) > 2:
                    mean_val = monthly['controversy'].mean()
                    std_val = monthly['controversy'].std()
                    fig.add_hline(y=mean_val, line_dash="dash", line_color="#6b6b8a", annotation_text="Media")
                    fig.add_hline(y=mean_val + 2*std_val, line_dash="dot", line_color="#ff3355", annotation_text="+2σ")
                    fig.add_hline(y=max(mean_val - 2*std_val, 0), line_dash="dot", line_color="#00ff88", annotation_text="-2σ")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig2 = px.line(monthly, x='month', y='engagement_rate', markers=True,
                               title="Engagement Rate Mensual",
                               labels={'engagement_rate': 'Engagement %', 'month': ''})
                if len(monthly) > 2:
                    mean_er = monthly['engagement_rate'].mean()
                    fig2.add_hline(y=mean_er, line_dash="dash", line_color="#6b6b8a", annotation_text="Media")
                    fig2.add_hline(y=mean_er * 0.7, line_dash="dot", line_color="#ff3355", annotation_text="-30%")
                fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig2, use_container_width=True)

            if 'net_sentiment' in monthly.columns:
                fig3 = px.line(monthly, x='month', y='net_sentiment', markers=True,
                               title="Sentimiento Neto Mensual",
                               labels={'net_sentiment': 'Net Sentiment', 'month': ''})
                fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig3, use_container_width=True)

with tabs[7]:
    st.markdown("## Explorador de Comentarios")
    if comments_df.empty:
        st.info("No hay comentarios extraídos aún. Usá `./scrapeo phase3` para extraerlos.")
    else:
        st.markdown(f"**{len(comments_df)}** comentarios extraídos de **{posts_df['post_id'].nunique()}** posts.")
        post_filter = st.selectbox("Filtrar por post:", ["Todos"] + posts_df['post_id'].tolist())
        if post_filter != "Todos":
            filtered = comments_df[comments_df['post_id'] == post_filter]
        else:
            filtered = comments_df
        st.dataframe(
            filtered[['author_name', 'message', 'sentiment', 'topic_category', 'zona', 'like_count']]
            .rename(columns={'author_name': 'Autor', 'message': 'Comentario', 'sentiment': 'Sentimiento',
                             'topic_category': 'Tópico', 'zona': 'Zona', 'like_count': 'Likes'}),
            use_container_width=True, height=500,
            column_config={"Comentario": st.column_config.TextColumn(width="large")}
        )

with tabs[8]:
    st.markdown("## Diagnóstico para el Edil")
    st.markdown("### Accountability: ¿Dónde hemos fallado?")

    if total_posts < 5:
        st.info("Datos insuficientes para generar diagnóstico.")
    else:
        issues = []
        if 'sentiment' in posts_df.columns:
            neg_posts = posts_df[posts_df['sentiment'] == 'negative']
            neg_rate = len(neg_posts) / total_posts if total_posts > 0 else 0
            if neg_rate > 0.1:
                issues.append({
                    "severity": "alta",
                    "area": "Sentimiento General",
                    "finding": f"{neg_rate:.1%} de las publicaciones tienen sentimiento negativo.",
                    "recommendation": "Revisar la estrategia de comunicación. Alto nivel de descontento."
                })

        if 'topic_category' in posts_df.columns:
            topic_neg = posts_df[posts_df['sentiment'] == 'negative'].groupby('topic_category').size().reset_index(name='count')
            topic_neg = topic_neg.sort_values('count', ascending=False)
            if not topic_neg.empty:
                worst_topic = topic_neg.iloc[0]
                issues.append({
                    "severity": "media",
                    "area": f"Tópico: {worst_topic['topic_category']}",
                    "finding": f"{fmt(worst_topic['count'])} publicaciones negativas en esta categoría.",
                    "recommendation": "Auditar el contenido y la ejecución de este tópico."
                })

        for zona in ["Norte", "Sur", "Este", "Centro", "Oeste"]:
            if 'zona' in posts_df.columns:
                zona_posts = posts_df[posts_df['zona'] == zona]
                if len(zona_posts) > 3:
                    zona_neg = zona_posts[zona_posts['sentiment'] == 'negative']
                    zona_neg_rate = len(zona_neg) / len(zona_posts)
                    if zona_neg_rate > 0.2:
                        issues.append({
                            "severity": "alta",
                            "area": f"Zona: {zona}",
                            "finding": f"{zona_neg_rate:.0%} de sentimiento negativo en {fmt(len(zona_posts))} publicaciones.",
                            "recommendation": "Investigación de campo necesaria en esta zona."
                        })

        if issues:
            for issue in sorted(issues, key=lambda x: 0 if x['severity'] == 'alta' else 1):
                color = '#ff3355' if issue['severity'] == 'alta' else '#ffb000'
                st.markdown(
                    f"<div class='alert-card' style='border-left-color:{color}'>"
                    f"<div class='title' style='color:{color}'>{'🔴' if issue['severity']=='alta' else '🟡'} {issue['area']}</div>"
                    f"<div class='desc'><strong>Hallazgo:</strong> {issue['finding']}</div>"
                    f"<div class='desc'><strong>Recomendación:</strong> {issue['recommendation']}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.success("No se detectaron fallas significativas. La gestión muestra resultados positivos.")

        st.markdown("### Distribución de Responsabilidad por Zona")
        if 'zona' in posts_df.columns and 'sentiment' in posts_df.columns:
            zona_sent = posts_df.groupby(['zona', 'sentiment']).size().reset_index(name='count')
            if not zona_sent.empty:
                fig = px.bar(zona_sent, x='zona', y='count', color='sentiment',
                             color_discrete_map={'positive': '#00ff88', 'neutral': '#ffb000', 'negative': '#ff3355'},
                             title="Posts por Zona y Sentimiento",
                             labels={'zona': 'Zona', 'count': 'Posts', 'sentiment': ''})
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Mapa de Riesgo")
        risk_data = []
        for zona in ["Norte", "Sur", "Este", "Centro", "Oeste"]:
            if 'zona' in posts_df.columns:
                zp = posts_df[posts_df['zona'] == zona]
                if len(zp) > 0:
                    likes = int(zp['likes_count'].sum())
                    angrys = int(zp['angrys_count'].sum())
                    risk_data.append({"Zona": zona, "Aprobación": likes, "Rechazo": angrys,
                                      "Ratio": safe_div(angrys, likes + angrys)})
        if risk_data:
            risk_df = pd.DataFrame(risk_data)
            fig = px.scatter(risk_df, x='Aprobación', y='Rechazo', size='Ratio', text='Zona',
                             color='Ratio', color_continuous_scale=['#00ff88', '#ffb000', '#ff3355'],
                             title="Riesgo por Zona (Aprobación vs Rechazo)")
            fig.update_traces(textposition='top center')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#c8c8e0')
            st.plotly_chart(fig, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<p style='font-size:9px;color:#6b6b8a;font-family:monospace;'>"
    f"Posts: {fmt(total_posts)} · Comentarios: {fmt(total_comments)}<br>"
    f"NLP: {len(emotions_by_item)} análisis · {len(entities_by_item)} entidades<br>"
    f"Modelo: v1.0 · Lexicon-based</p>",
    unsafe_allow_html=True,
)
