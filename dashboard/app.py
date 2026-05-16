import streamlit as st
import supabase
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict
import os

st.set_page_config(
    page_title="Santa Ana - Análisis de Percepción Social",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://hsflgjdvaemjqbcmaxvl.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhzZmxnamR2YWVtanFiY21heHZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg4MzIwOTUsImV4cCI6MjA5NDQwODA5NX0.lT7BTQ_gwPLX0nN8M8m3w3XB8dDx8UDXwsi10fZiwg4")

client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

COLORS = {
    "positive": "#2ecc71",
    "negative": "#e74c3c",
    "neutral": "#95a5a6"
}

TOPIC_COLORS = {
    "seguridad": "#e74c3c",
    "corrupcion": "#9b59b6",
    "obras_publicas": "#3498db",
    "servicios_publicos": "#f39c12",
    "empleo": "#1abc9c",
    "salud": "#e91e63",
    "educacion": "#00bcd4",
    "movilidad": "#795548",
    "medio_ambiente": "#4caf50",
    "transparencia": "#607d8b"
}


def get_data(query):
    try:
        result = query.execute()
        return result.data or []
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []


def get_executive_summary():
    try:
        fb_count = client.table("fb_posts").select("id", count="exact").execute().count
        tt_count = client.table("tt_posts").select("id", count="exact").execute().count
        fb_comments = client.table("fb_comments").select("id", count="exact").execute().count
        tt_comments = client.table("tt_comments").select("id", count="exact").execute().count

        fb_pos = client.table("fb_posts").select("id", count="exact").eq("sentiment", "positive").execute().count
        fb_neg = client.table("fb_posts").select("id", count="exact").eq("sentiment", "negative").execute().count
        
        tt_pos = client.table("tt_posts").select("id", count="exact").eq("sentiment", "positive").execute().count
        tt_neg = client.table("tt_posts").select("id", count="exact").eq("sentiment", "negative").execute().count

        fb_total = fb_pos + fb_neg
        tt_total = tt_pos + tt_neg

        fb_nsi = ((fb_pos - fb_neg) / fb_total * 100) if fb_total > 0 else 0
        tt_nsi = ((tt_pos - tt_neg) / tt_total * 100) if tt_total > 0 else 0

        return {
            "fb_posts": fb_count,
            "tt_posts": tt_count,
            "fb_comments": fb_comments,
            "tt_comments": tt_comments,
            "fb_positive": fb_pos,
            "fb_negative": fb_neg,
            "tt_positive": tt_pos,
            "tt_negative": tt_neg,
            "fb_nsi": round(fb_nsi, 1),
            "tt_nsi": round(tt_nsi, 1),
            "fb_sentiment": "positive" if fb_nsi > 0 else "negative" if fb_nsi < 0 else "neutral",
            "tt_sentiment": "positive" if tt_nsi > 0 else "negative" if tt_nsi < 0 else "neutral"
        }
    except Exception as e:
        st.error(f"Error: {e}")
        return {}


def get_problematicas_by_zone():
    try:
        fb_posts = get_data(client.table("fb_posts").select("*"))
        tt_posts = get_data(client.table("tt_posts").select("*"))
        
        zona_data = defaultdict(lambda: {"topics": defaultdict(int), "sentiment": {"positive": 0, "negative": 0, "neutral": 0}})
        
        for post in fb_posts + tt_posts:
            zona = post.get("zona") or "Sin zona específica"
            topic = post.get("topic_category")
            sentiment = post.get("sentiment")
            
            if topic:
                zona_data[zona]["topics"][topic] += 1
            if sentiment:
                zona_data[zona]["sentiment"][sentiment] += 1
        
        result = {}
        for zona, data in zona_data.items():
            total = sum(data["sentiment"].values())
            neg_pct = (data["sentiment"]["negative"] / total * 100) if total > 0 else 0
            result[zona] = {
                "topics": dict(data["topics"]),
                "total": total,
                "negative_pct": round(neg_pct, 1),
                "sentiment": data["sentiment"]
            }
        
        return result
    except Exception as e:
        return {}


def get_sentiment_trend(platform="facebook", days=30):
    try:
        data = get_data(
            client.table("daily_metrics")
            .select("*")
            .eq("platform", platform)
            .order("date", desc=True)
            .limit(days)
        )
        
        if not data:
            return {"labels": [], "positive": [], "negative": [], "neutral": []}
        
        data.reverse()
        
        return {
            "labels": [d.get("date", "") for d in data],
            "positive": [d.get("positive_pct", 0) for d in data],
            "negative": [d.get("negative_pct", 0) for d in data],
            "neutral": [d.get("neutral_pct", 0) for d in data],
            "nsi": [d.get("nsi", 0) for d in data],
            "cai": [d.get("cai", 0) for d in data]
        }
    except Exception as e:
        return {"labels": [], "positive": [], "negative": [], "neutral": []}


def get_top_posts(platform="facebook", limit=20):
    try:
        if platform == "facebook":
            data = get_data(client.table("fb_posts").select("*").order("comments_count", desc=True).limit(limit))
        else:
            data = get_data(client.table("tt_posts").select("*").order("comments_count", desc=True).limit(limit))
        return data
    except Exception as e:
        return []


def get_insights(limit=20):
    try:
        return get_data(
            client.table("insights")
            .select("*")
            .order("priority", desc=True)
            .limit(limit)
        )
    except Exception as e:
        return []


def render_executive_scorecard():
    summary = get_executive_summary()
    
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .metric-value {
        font-size: 42px;
        font-weight: bold;
        color: white;
    }
    .metric-label {
        font-size: 14px;
        color: #a0c4e8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-delta {
        font-size: 16px;
        color: #2ecc71;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        nsi_value = summary.get("fb_nsi", 0)
        nsi_color = "#2ecc71" if nsi_value > 0 else "#e74c3c" if nsi_value < 0 else "#95a5a6"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">NSI FACEBOOK</div>
            <div class="metric-value" style="color: {nsi_color}">{nsi_value}</div>
            <div class="metric-delta">Sentimiento Neto</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        tt_nsi = summary.get("tt_nsi", 0)
        tt_color = "#2ecc71" if tt_nsi > 0 else "#e74c3c" if tt_nsi < 0 else "#95a5a6"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">NSI TIKTOK</div>
            <div class="metric-value" style="color: {tt_color}">{tt_nsi}</div>
            <div class="metric-delta">Sentimiento Neto</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total_posts = summary.get("fb_posts", 0) + summary.get("tt_posts", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">TOTAL CONTENIDO</div>
            <div class="metric-value">{total_posts:,}</div>
            <div class="metric-delta">Posts + Videos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_comments = summary.get("fb_comments", 0) + summary.get("tt_comments", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">COMENTARIOS</div>
            <div class="metric-value">{total_comments:,}</div>
            <div class="metric-delta">Analizados</div>
        </div>
        """, unsafe_allow_html=True)


def render_platform_cards():
    summary = get_executive_summary()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📘 FACEBOOK")
        fb_pos = summary.get("fb_positive", 0)
        fb_neg = summary.get("fb_negative", 0)
        fb_total = fb_pos + fb_neg
        
        if fb_total > 0:
            pos_pct = fb_pos / fb_total * 100
            neg_pct = fb_neg / fb_total * 100
            
            fig = go.Figure(go.Bar(
                x=["Positivo", "Negativo"],
                y=[pos_pct, neg_pct],
                marker_color=["#2ecc71", "#e74c3c"],
                text=[f"{pos_pct:.1f}%", f"{neg_pct:.1f}%"],
                textposition="outside"
            ))
            fig.update_layout(
                title="Distribución de Sentimiento FB",
                height=250,
                showlegend=False,
                yaxis_title="Porcentaje"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.metric("Posts Totales", summary.get("fb_posts", 0))
        st.metric("Comentarios", summary.get("fb_comments", 0))
    
    with col2:
        st.markdown("### 🎵 TIKTOK")
        tt_pos = summary.get("tt_positive", 0)
        tt_neg = summary.get("tt_negative", 0)
        tt_total = tt_pos + tt_neg
        
        if tt_total > 0:
            pos_pct = tt_pos / tt_total * 100
            neg_pct = tt_neg / tt_total * 100
            
            fig = go.Figure(go.Bar(
                x=["Positivo", "Negativo"],
                y=[pos_pct, neg_pct],
                marker_color=["#2ecc71", "#e74c3c"],
                text=[f"{pos_pct:.1f}%", f"{neg_pct:.1f}%"],
                textposition="outside"
            ))
            fig.update_layout(
                title="Distribución de Sentimiento TT",
                height=250,
                showlegend=False,
                yaxis_title="Porcentaje"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.metric("Videos Totales", summary.get("tt_posts", 0))
        st.metric("Comentarios", summary.get("tt_comments", 0))


def render_problematicas_zone():
    zona_data = get_problematicas_by_zone()
    
    if not zona_data:
        st.info("No hay datos suficientes para mostrar problemáticas.")
        return
    
    st.markdown("## 📍 PROBLEMÁTICAS POR ZONA")
    
    zones = sorted(zona_data.keys(), key=lambda z: zona_data[z].get("negative_pct", 0), reverse=True)
    
    num_cols = min(len(zones), 5)
    cols = st.columns(num_cols)
    
    for i, zona in enumerate(zones[:5]):
        data = zona_data[zona]
        neg_pct = data.get("negative_pct", 0)
        
        color = "#e74c3c" if neg_pct > 30 else "#f39c12" if neg_pct > 15 else "#2ecc71"
        
        with cols[i]:
            st.markdown(f"""
            <div style="background: {color}20; border-left: 4px solid {color}; padding: 15px; border-radius: 5px; margin: 5px 0;">
                <h4 style="margin: 0; color: {color};">{zona}</h4>
                <p style="margin: 5px 0 0 0; font-size: 24px; font-weight: bold;">{neg_pct}%</p>
                <small style="color: #666;">negativo</small>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("### Temas por Zona")
    
    for zona in zones[:5]:
        data = zona_data[zona]
        topics = data.get("topics", {})
        
        if topics:
            sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
            
            st.markdown(f"**{zona}**")
            
            topic_df = pd.DataFrame(sorted_topics, columns=["Tema", "Menciones"])
            
            fig = px.bar(
                topic_df, 
                x="Menciones", 
                y="Tema", 
                orientation="h",
                color="Menciones",
                color_continuous_scale="RdYlGn_r"
            )
            fig.update_layout(height=250, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def render_sentiment_trend():
    st.markdown("## 📈 TENDENCIA DE SENTIMIENTO")
    
    tab1, tab2 = st.tabs(["Facebook", "TikTok"])
    
    with tab1:
        fb_trend = get_sentiment_trend("facebook")
        
        if fb_trend["labels"]:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=fb_trend["labels"],
                y=fb_trend["positive"],
                mode="lines+markers",
                name="Positivo",
                line=dict(color="#2ecc71", width=3),
                fill="tozeroy",
                fillcolor="rgba(46, 204, 113, 0.2)"
            ))
            
            fig.add_trace(go.Scatter(
                x=fb_trend["labels"],
                y=fb_trend["negative"],
                mode="lines+markers",
                name="Negativo",
                line=dict(color="#e74c3c", width=3),
                fill="tozeroy",
                fillcolor="rgba(231, 76, 60, 0.2)"
            ))
            
            fig.update_layout(
                title="Tendencia de Sentimiento - Facebook",
                xaxis_title="Fecha",
                yaxis_title="Porcentaje",
                height=400,
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar tendencia.")
    
    with tab2:
        tt_trend = get_sentiment_trend("tiktok")
        
        if tt_trend["labels"]:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=tt_trend["labels"],
                y=tt_trend["positive"],
                mode="lines+markers",
                name="Positivo",
                line=dict(color="#2ecc71", width=3),
                fill="tozeroy",
                fillcolor="rgba(46, 204, 113, 0.2)"
            ))
            
            fig.add_trace(go.Scatter(
                x=tt_trend["labels"],
                y=tt_trend["negative"],
                mode="lines+markers",
                name="Negativo",
                line=dict(color="#e74c3c", width=3),
                fill="tozeroy",
                fillcolor="rgba(231, 76, 60, 0.2)"
            ))
            
            fig.update_layout(
                title="Tendencia de Sentimiento - TikTok",
                xaxis_title="Fecha",
                yaxis_title="Porcentaje",
                height=400,
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar tendencia.")


def render_insights():
    st.markdown("## 💡 INSIGHTS GENERADOS")
    
    insights = get_insights(limit=15)
    
    if not insights:
        st.info("No hay insights disponibles aún. Ejecuta el scraping para generar datos.")
        return
    
    for insight in insights:
        priority = insight.get("priority", 0)
        sentiment = insight.get("sentiment", "")
        
        emoji = "🔴" if priority >= 4 else "🟡" if priority >= 3 else "🟢"
        border_color = "#e74c3c" if sentiment == "negative" else "#2ecc71" if sentiment == "positive" else "#95a5a6"
        
        st.markdown(f"""
        <div style="border-left: 4px solid {border_color}; padding: 15px; margin: 10px 0; background: #f8f9fa; border-radius: 5px;">
            <h4 style="margin: 0;">{emoji} {insight.get('title', '')}</h4>
            <p style="margin: 10px 0; color: #333;">{insight.get('description', '')}</p>
            <small style="color: #666;">
                Tema: {insight.get('topic', 'N/A')} | 
                Zona: {insight.get('zona', 'N/A')} |
                Prioridad: {priority}
            </small>
        </div>
        """, unsafe_allow_html=True)


def render_posts():
    st.markdown("## 📝 TOP POSTS")
    
    tab1, tab2 = st.tabs(["Facebook", "TikTok"])
    
    with tab1:
        posts = get_top_posts("facebook", limit=20)
        
        if posts:
            df = pd.DataFrame(posts)
            display_cols = ["post_id", "message", "likes_count", "comments_count", "sentiment", "topic_category", "zona"]
            
            for _, row in df.head(10).iterrows():
                sentiment_color = "#2ecc71" if row.get("sentiment") == "positive" else "#e74c3c" if row.get("sentiment") == "negative" else "#95a5a6"
                
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <div style="display: flex; justify-content: space-between;">
                        <strong>{row.get('topic_category', 'Sin tema')}</strong>
                        <span style="color: {sentiment_color}; font-weight: bold;">{row.get('sentiment', '')}</span>
                    </div>
                    <p style="color: #666; font-size: 14px;">{str(row.get('message', ''))[:200]}...</p>
                    <small>
                        👍 {row.get('likes_count', 0)} | 
                        💬 {row.get('comments_count', 0)} | 
                        📍 {row.get('zona', 'N/A')}
                    </small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay posts disponibles.")
    
    with tab2:
        videos = get_top_posts("tiktok", limit=20)
        
        if videos:
            for video in videos[:10]:
                sentiment_color = "#2ecc71" if video.get("sentiment") == "positive" else "#e74c3c" if video.get("sentiment") == "negative" else "#95a5a6"
                
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <div style="display: flex; justify-content: space-between;">
                        <strong>{video.get('topic_category', 'Sin tema')}</strong>
                        <span style="color: {sentiment_color}; font-weight: bold;">{video.get('sentiment', '')}</span>
                    </div>
                    <p style="color: #666; font-size: 14px;">{str(video.get('description', ''))[:200]}...</p>
                    <small>
                        ❤️ {video.get('likes_count', 0)} | 
                        💬 {video.get('comments_count', 0)} | 
                        👁️ {video.get('views_count', 0)}
                    </small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay videos disponibles.")


def main():
    st.markdown("""
    <style>
    .main-title {
        font-size: 36px;
        font-weight: bold;
        color: #1e3a5f;
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .subtitle {
        font-size: 18px;
        color: #666;
        text-align: center;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-title">🏛️ SANTA ANA - ANÁLISIS DE PERCEPCIÓN SOCIAL</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Dashboard Ejecutivo de Analítica de Redes Sociales</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    render_executive_scorecard()
    
    st.markdown("---")
    
    render_platform_cards()
    
    st.markdown("---")
    
    render_problematicas_zone()
    
    st.markdown("---")
    
    render_sentiment_trend()
    
    st.markdown("---")
    
    render_insights()
    
    st.markdown("---")
    
    render_posts()
    
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #999; font-size: 12px;">
        Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        <br>
        Powered by Scrapeo Social v2.0
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()