import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
from collections import Counter
import logging
import os
import sys
sys.path.insert(0, "/Users/pro/Downloads/scrapeo-social/dashboard")
from config import (
    FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB,
    FACEBOOK_TEST_DB, TIKTOK_TEST_DB, EXTERNOS_TEST_DB,
    FB_PAGES_OFICIALES, FB_REACTIONS, TK_ENGAGEMENT,
    TK_ACCOUNTS, OUTPUT_DIR
)

# ── Toggle modo prueba — antes de cualquier función cacheada ──
if "modo_prueba" not in st.session_state:
    st.session_state.modo_prueba = False

FACEBOOK_DB_ACTIVA = (
    FACEBOOK_TEST_DB if st.session_state.get("modo_prueba", False) else FACEBOOK_DB
)
TIKTOK_DB_ACTIVA = (
    TIKTOK_TEST_DB if st.session_state.get("modo_prueba", False) else TIKTOK_DB
)
EXTERNOS_DB_ACTIVA = (
    EXTERNOS_TEST_DB if st.session_state.get("modo_prueba", False) else EXTERNOS_DB
)

def generar_interpretacion(tipo, datos):
    score = datos.get('score', 0)
    pct_neg = datos.get('pct_negativo', 0)
    pct_pos = datos.get('pct_positivo', 0)
    enojo = datos.get('indice_enojo', 0)

    if tipo == "semaforo":
        if score >= 0.25:
            return f"La ciudadanía te respalda. El {pct_pos:.0f}% de los comentarios son de apoyo — la gente está contenta con lo que ve en tus redes. Este es el momento de publicar más contenido de obras y logros."
        elif score >= 0.10:
            return f"Hay señales mixtas. Algunos te apoyan, otros empiezan a cuestionar. El {pct_neg:.0f}% de los comentarios son negativos — no es crisis todavía, pero la tendencia importa. Revisa qué temas generan más críticas esta semana."
        elif score >= 0:
            return f"Atención. El equilibrio entre apoyo y rechazo es frágil. El {pct_neg:.0f}% de los comentarios son negativos y el enojo representa el {enojo*100:.0f}% de las reacciones. La ciudadanía está observando — cualquier error se amplifica ahora."
        else:
            return f"ALERTA. La ciudadanía está en modo crítico. El enojo representa el {enojo*100:.0f}% de TODAS las reacciones — eso significa que por cada persona que apoya, hay varias que reaccionan con rechazo activo. El {pct_neg:.0f}% de los comentarios son negativos. Esto no es ruido — es una señal que históricamente precede pérdida de confianza electoral."

    elif tipo == "tema_critico":
        tema = datos.get('tema', '')
        reacciones = datos.get('reacciones', 0)
        return f"Aquí está el problema. '{tema}' concentra {reacciones:,} reacciones con {pct_neg:.0f}% de comentarios negativos. Cuando publicas sobre este tema, la ciudadanía responde principalmente con burla y enojo — no con apoyo. Esto indica una brecha entre lo que comunicas y lo que la gente experimenta en su colonia."

    elif tipo == "tema_positivo":
        tema = datos.get('tema', '')
        return f"'{tema}' es tu contenido más fuerte. El {pct_pos:.0f}% de comentarios son positivos — la gente comparte este tipo de contenido espontáneamente. Aquí la ciudadanía se identifica contigo, no solo consume lo que publicas."

    elif tipo == "anomalia":
        fecha = datos.get('fecha', '')
        views = datos.get('views', 0)
        tipo_pico = datos.get('tipo', 'positivo')
        if tipo_pico == 'positivo':
            return f"La semana del {fecha} fue inusual — {views:,} interacciones, muy por encima de tu promedio. Algo pasó esa semana que movilizó a la ciudadanía a tu favor. Identifica qué publicaste o qué evento ocurrió — ese es el tipo de contenido que debes replicar."
        else:
            return f"La semana del {fecha} tuvo una caída inusual. La ciudadanía reaccionó con más rechazo del habitual. Revisa qué comunicaste esa semana y qué pasó en el municipio en esas fechas."

    elif tipo == "patron_rechazo":
        nombre = datos.get('nombre', '')
        count = datos.get('count', 0)
        tendencia = datos.get('tendencia', '')
        return f"{count} personas expresaron este patrón con sus propias palabras. No es un comentario aislado — es una narrativa colectiva. Tendencia: {tendencia}. Cuando un patrón de rechazo crece semana a semana, eventualmente se convierte en el tema central que la oposición usará en campaña."

    elif tipo == "patron_respaldo":
        nombre = datos.get('nombre', '')
        count = datos.get('count', 0)
        return f"{count} personas expresaron apoyo genuino — no por obligación, sino porque algo resonó. Este es tu capital político real en redes. La diferencia entre apoyo genuino y apoyo vacío: el genuino se comparte, el vacío solo existe en el conteo."

    elif tipo == "microsegmentacion":
        tipo_contenido = datos.get('tipo', '')
        eng = datos.get('engagement', 0)
        patron = datos.get('patron', '')
        if patron == 'ALTO IMPACTO':
            return f"'{tipo_contenido}' es tu contenido más efectivo. Genera {eng:,.0f} interacciones en promedio — por encima del resto. Cuando publicas esto, la ciudadanía responde. Más de este contenido."
        elif patron == 'BAJO IMPACTO':
            return f"'{tipo_contenido}' no está funcionando. Solo {eng:,.0f} interacciones en promedio. La ciudadanía lo ignora o lo rechaza. Replantear cómo comunicas este tema."
        else:
            return f"'{tipo_contenido}' tiene impacto moderado. Hay potencial pero algo en el mensaje no termina de conectar con la ciudadanía."

    elif tipo == "contexto_externo":
        n_neg = datos.get('negativas', 0)
        n_total = datos.get('total', 0)
        fuente_top = datos.get('fuente_top', '')
        pct_neg_ext = (n_neg/n_total*100) if n_total > 0 else 0
        return f"Fuera de tus redes, {pct_neg_ext:.0f}% de las menciones sobre ti son negativas. La fuente más activa es '{fuente_top}'. Lo que dicen fuera de tus páginas es lo que la ciudadanía lee cuando busca tu nombre — no lo que tú publicas."

    return ""

def leyenda_grafica(elementos):
    items_html = "".join(
        '<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px">'
        '<span style="font-size:16px;color:{};min-width:20px;font-weight:700;line-height:1.4">'
        '{}</span>'
        '<div>'
        '<span style="font-size:12px;color:#e2e8f0;font-weight:600">'
        '{}</span>'
        '<span style="font-size:12px;color:#6b7280;margin-left:6px">'
        '— {}</span></div></div>'.format(
            e['color'], e['simbolo'], e['label'], e['descripcion']
        )
        for e in elementos
    )
    return (
        '<div style="background:#0f172a;border:1px solid #1f2937;'
        'border-radius:6px;padding:14px 18px;margin-bottom:12px">'
        '<p style="font-size:10px;color:#4b5563;margin:0 0 10px 0;'
        'font-weight:700;letter-spacing:1.5px;text-transform:uppercase">'
        'QUÉ ESTÁS VIENDO</p>{}</div>'
    ).format(items_html)

st.set_page_config(
    page_title="Panel de Inteligencia Ciudadana — Alcaldía Santa Ana",
    page_icon=":material/apartment:",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp { background-color: #0a0e1a; color: #e2e8f0; }
.stSidebar { background-color: #0d1117; border-right: 1px solid #21262d; }
.stSelectbox > div > div { background-color: #1f2937; color: #e2e8f0; border-color: #374151; }
.stRadio > div { color: #e2e8f0; }
.card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 12px;
}
.card-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 8px;
}
.card-value {
    font-size: 32px;
    font-weight: 700;
    color: #f9fafb;
    font-family: 'Courier New', monospace;
}
.card-sub {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 4px;
}
.semaforo-verde {
    background: linear-gradient(135deg, #052e16, #14532d);
    border: 1px solid #16a34a;
    border-left: 6px solid #22c55e;
    border-radius: 8px;
    padding: 28px 32px;
    text-align: center;
    margin-bottom: 20px;
}
.semaforo-amarillo {
    background: linear-gradient(135deg, #1c1407, #2d1f07);
    border: 1px solid #ca8a04;
    border-left: 6px solid #eab308;
    border-radius: 8px;
    padding: 28px 32px;
    text-align: center;
    margin-bottom: 20px;
}
.semaforo-rojo {
    background: linear-gradient(135deg, #1a0505, #2d0a0a);
    border: 1px solid #dc2626;
    border-left: 6px solid #ef4444;
    border-radius: 8px;
    padding: 28px 32px;
    text-align: center;
    margin-bottom: 20px;
}
.semaforo-texto {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin: 0;
}
.bullet-oro {
    font-size: 14px;
    color: #d1d5db;
    margin: 6px 0;
    padding-left: 8px;
}
.patron-rechazo {
    background: #1a0808;
    border: 1px solid #7f1d1d;
    border-left: 5px solid #ef4444;
    border-radius: 6px;
    padding: 24px 28px;
    margin-bottom: 16px;
}
.patron-respaldo {
    background: #071a0f;
    border: 1px solid #14532d;
    border-left: 5px solid #22c55e;
    border-radius: 6px;
    padding: 24px 28px;
    margin-bottom: 16px;
}
.patron-titulo {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.patron-meta {
    font-size: 13px;
    color: #9ca3af;
    margin-bottom: 12px;
}
.patron-count {
    font-size: 28px;
    font-weight: 700;
    font-family: 'Courier New', monospace;
}
.comentario-rep {
    background: #0f172a;
    border-left: 3px solid #374151;
    padding: 14px 18px;
    border-radius: 4px;
    font-size: 14px;
    font-style: italic;
    color: #d1d5db;
    margin: 8px 0;
    line-height: 1.5;
}
.comentario-lista {
    font-size: 12px;
    color: #9ca3af;
    margin: 4px 0;
    padding-left: 12px;
}
.badge-positivo {
    background: #14532d;
    color: #4ade80;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
.badge-mixto {
    background: #1c1407;
    color: #fbbf24;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
.badge-critico {
    background: #1a0505;
    color: #f87171;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
.riesgo-alto { color: #ef4444; font-weight: 700; font-size: 12px; }
.riesgo-medio { color: #f59e0b; font-weight: 700; font-size: 12px; }
.riesgo-bajo { color: #22c55e; font-weight: 700; font-size: 12px; }
.senal-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 6px;
    padding: 20px 24px;
    margin-bottom: 16px;
    font-size: 14px;
}
.senal-numero {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    color: #4b5563;
    text-transform: uppercase;
}
.senal-titulo {
    font-size: 15px;
    font-weight: 700;
    color: #f9fafb;
    margin: 4px 0 12px 0;
}
.seccion-header {
    border-bottom: 2px solid #1f2937;
    padding-bottom: 12px;
    margin-bottom: 24px;
}
.seccion-titulo {
    font-size: 20px;
    font-weight: 700;
    color: #f9fafb;
    letter-spacing: 0.3px;
}
.seccion-subtitulo {
    font-size: 12px;
    color: #6b7280;
    margin-top: 4px;
    font-style: italic;
}
.anomalia-item {
    background: #1a0808;
    border: 1px solid #7f1d1d;
    border-radius: 4px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 13px;
}

/* ===== Responsive mobile (≤640px) ===== */
@media (max-width: 640px) {
    /* Apilar TODAS las filas de columnas verticalmente */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 0.5rem !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    /* Métricas compactas para que no se corten los números */
    div[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    div[data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    /* Menos padding lateral en móvil */
    .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        padding-top: 1rem !important;
    }
    /* Títulos proporcionales a pantalla chica */
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.05rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──

st.sidebar.markdown("## 🏛 Alcaldía Santa Ana")
st.sidebar.markdown("*Panel de Inteligencia Ciudadana*")
st.sidebar.markdown("---")

periodo = st.sidebar.selectbox("📅 Período", [
    "Esta semana",
    "Últimos 15 días",
    "Último mes",
    "Últimos 3 meses",
    "Todo el período"
])

plataforma = st.sidebar.selectbox("📱 Plataforma", [
    "Ambas", "Facebook", "TikTok"
])

st.sidebar.markdown("---")
modo_prueba = st.sidebar.toggle(
    "🧪 Modo prueba",
    value=st.session_state.modo_prueba,
    help="Activa datos de prueba con alta negatividad para testear el semáforo rojo"
)
if modo_prueba != st.session_state.modo_prueba:
    st.session_state.modo_prueba = modo_prueba
    st.cache_data.clear()
    st.rerun()

if st.session_state.modo_prueba:
    st.sidebar.markdown(
        '<p style="color:#f59e0b;font-size:11px">'
        '⚠️ Datos de prueba activos</p>',
        unsafe_allow_html=True
    )

try:
    conn = sqlite3.connect(FACEBOOK_DB_ACTIVA)
    max_fb = pd.read_sql("SELECT MAX(created_time) as m FROM fb_engagement", conn).iloc[0]['m']
    conn.close()
    conn = sqlite3.connect(TIKTOK_DB_ACTIVA)
    max_tk = pd.read_sql("SELECT MAX(created_at) as m FROM tiktok_engagement", conn).iloc[0]['m']
    conn.close()
    fechas = []
    if max_fb: fechas.append(pd.Timestamp(max_fb))
    if max_tk: fechas.append(pd.Timestamp(max_tk))
    ultima_fecha = max(fechas) if fechas else datetime.now()
    dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    fecha_str = f"{dias[ultima_fecha.weekday()]} {ultima_fecha.day} de {meses[ultima_fecha.month-1]}, {ultima_fecha.year}"
except:
    fecha_str = "No disponible"

st.sidebar.caption(f"Última actualización: {fecha_str}")

st.sidebar.markdown("---")

seccion = st.sidebar.radio("", [
    "📊 Estado General",
    "🎯 Temas y Emociones",
    "📅 Línea del Tiempo",
    "💬 Voz Ciudadana",
    "🔬 Microsegmentación",
    "🤝 Confianza Institucional",
    "📡 Narrativas Activas",
    "🌊 Contagio Emocional",
    "🌐 Contexto Externo",
    "📋 Notas Metodológicas"
])

# ── HELPERS ──

def get_fecha_inicio(periodo):
    hoy = datetime.now()
    if periodo == "Esta semana": return hoy - timedelta(days=7)
    elif periodo == "Últimos 15 días": return hoy - timedelta(days=15)
    elif periodo == "Último mes": return hoy - timedelta(days=30)
    elif periodo == "Últimos 3 meses": return hoy - timedelta(days=90)
    else: return datetime(2020, 1, 1)

def formato_fecha_espanol(fecha):
    dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    try:
        if pd.isna(fecha): return "Fecha no disponible"
        d = pd.Timestamp(fecha)
        return f"{dias[d.weekday()]} {d.day} de {meses[d.month-1]}, {d.year}"
    except:
        return str(fecha)

def safe_query(query: str, db_path: str, params=None) -> pd.DataFrame:
    """Lee SQL devolviendo un DataFrame vacío si la DB/tabla no existe o la query falla."""
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        logging.warning(f"safe_query falló ({db_path}): {e}")
        return pd.DataFrame()

def hay_datos(df, mensaje: str = "Aún no hay datos suficientes para esta sección.") -> bool:
    """Muestra un aviso elegante y devuelve False si el DataFrame está vacío."""
    if df is None or len(df) == 0:
        st.info(f"📭 {mensaje}")
        return False
    return True

@st.cache_data(ttl=3600)
def cargar_fb_engagement(db_path):
    df = safe_query("""
        SELECT fe.*, pc.categoria_nombre
        FROM fb_engagement fe
        LEFT JOIN post_categorias pc ON fe.post_id = pc.item_id
    """, db_path)
    if df.empty:
        return df
    df['created_time'] = pd.to_datetime(df['created_time'], errors='coerce')
    df['categoria_nombre'] = df['categoria_nombre'].replace('Contenido promocional', 'Convocatorias y celebraciones')
    return df.dropna(subset=['created_time'])

@st.cache_data(ttl=3600)
def cargar_tk_engagement(tk_db_path, fb_db_path):
    df = safe_query("SELECT * FROM tiktok_engagement", tk_db_path)
    if df.empty:
        return df
    cats = safe_query("SELECT item_id, categoria_nombre FROM post_categorias", fb_db_path)
    if not cats.empty:
        cats['item_id'] = cats['item_id'].astype(str)
        df['id_str'] = df['id'].astype(str)
        df = df.merge(cats, left_on='id_str', right_on='item_id', how='left')
        df = df.drop(columns=['id_str','item_id'], errors='ignore')
    df['categoria_nombre'] = df.get('categoria_nombre', pd.Series(dtype=str))
    df['categoria_nombre'] = df['categoria_nombre'].replace('Contenido promocional', 'Convocatorias y celebraciones')
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    return df.dropna(subset=['created_at'])

@st.cache_data(ttl=3600)
def cargar_sentimiento_fb(db_path):
    df = safe_query("""
        SELECT fs.*, pc.categoria_nombre
        FROM fb_sentimiento fs
        LEFT JOIN post_categorias pc ON fs.post_id = pc.item_id
    """, db_path)
    return df

@st.cache_data(ttl=3600)
def cargar_comentarios_fb(db_path):
    df = safe_query("""
        SELECT fc.message, fc.post_id,
               fs.score_sentimiento,
               fs.pct_positivo, fs.pct_negativo,
               pc.categoria_nombre
        FROM fb_comments fc
        LEFT JOIN fb_sentimiento fs ON fc.post_id = fs.post_id
        LEFT JOIN post_categorias pc ON fc.post_id = pc.item_id
        WHERE fc.message IS NOT NULL
        AND fc.message != ''
        AND LENGTH(fc.message) > 10
    """, db_path)
    return df

def cargar_comentarios_negativos() -> pd.DataFrame:
    return safe_query("""
        SELECT comment_id, message, sentiment, sentiment_score, topic_category, zona
        FROM fb_comments
        WHERE sentiment IN ('negativo', 'muy_negativo')
        AND message IS NOT NULL AND TRIM(message) <> ''
    """, FACEBOOK_DB_ACTIVA)

@st.cache_data(ttl=3600)
def cargar_series(fb_db_path, tk_db_path):
    df_fb = safe_query("SELECT * FROM series_facebook", fb_db_path)
    df_tk = safe_query("SELECT * FROM series_tiktok", tk_db_path)
    if df_fb.empty and df_tk.empty:
        return pd.DataFrame(), pd.DataFrame()
    if not df_fb.empty:
        df_fb['semana'] = pd.to_datetime(df_fb['semana'])
        df_fb['engagement'] = df_fb['engagement_promedio'] * df_fb['total_posts']
        df_fb['plataforma'] = 'Facebook'
    if not df_tk.empty:
        df_tk['semana'] = pd.to_datetime(df_tk['semana'])
        df_tk['engagement'] = df_tk['views_suma']
        df_tk['plataforma'] = 'TikTok'
    return df_fb, df_tk

@st.cache_data(ttl=3600)
def cargar_externos(db_path):
    posts = safe_query("SELECT * FROM external_posts", db_path)
    if posts.empty:
        return posts
    posts['created_time'] = pd.to_datetime(posts['created_time'], errors='coerce')
    sent = safe_query("SELECT * FROM external_sentimiento", db_path)
    if not sent.empty:
        return posts.merge(sent, on='post_id', how='left')
    posts['score_sentimiento'] = 0.0
    posts['comentario_mas_negativo'] = ''
    return posts

def filtrar_por_periodo_plataforma(df_fb, df_tk, periodo, plataforma):
    fecha_inicio = get_fecha_inicio(periodo)
    fb = df_fb[df_fb['created_time'] >= fecha_inicio].copy()
    tk = df_tk[df_tk['created_at'] >= fecha_inicio].copy()
    if plataforma == "Facebook": return fb, pd.DataFrame()
    if plataforma == "TikTok": return pd.DataFrame(), tk
    return fb, tk

def calcular_semaforo(df_fb):
    if df_fb.empty: return "amarillo", "🟡 Sin datos suficientes esta semana"
    score = df_fb['score_emocional'].mean()
    if score >= 0.25: return "verde", "🟢 La ciudadanía te respalda esta semana"
    elif score >= 0.10: return "amarillo", "🟡 Hay señales mixtas esta semana"
    else: return "rojo", "🔴 La ciudadanía está inquieta esta semana"

def detectar_patrones_comentarios(df_comentarios):
    patrones_rechazo = {
        'abandono_territorial': {
            'keywords': ['calle', 'colonia', 'barrio', 'paviment',
                        'abandon', 'olvidado', 'espera', 'nunca vienen'],
            'nombre': 'Abandono territorial',
            'descripcion': 'Colonias y comunidades que se sienten ignoradas'
        },
        'desconfianza': {
            'keywords': ['corrupto', 'mentira', 'robo', 'ladron',
                        'nefasto', 'inutil', 'pura propaganda'],
            'nombre': 'Desconfianza institucional',
            'descripcion': 'Ciudadanos que cuestionan la honestidad de la gestion'
        },
        'narrativa_electoral': {
            'keywords': ['eleccion', 'voto', 'reeleccion', 'campana',
                        'boto', 'votar', 'elecciones', 'proximas'],
            'nombre': 'Narrativa electoral activa',
            'descripcion': 'Ciudadanos que leen las acciones en clave electoral'
        },
        'servicios_basicos': {
            'keywords': ['basura', 'alumbrado', 'lampara', 'luz',
                        'agua', 'telefono', 'atencion'],
            'nombre': 'Falla en servicios basicos',
            'descripcion': 'Quejas sobre servicios municipales sin respuesta'
        }
    }
    patrones_respaldo = {
        'reconocimiento_obras': {
            'keywords': ['excelente', 'buen trabajo', 'gracias',
                        'bendicion', 'felicitaciones', 'sigan'],
            'nombre': 'Reconocimiento de obras visibles',
            'descripcion': 'Ciudadanos que valoran los resultados concretos'
        },
        'identidad_local': {
            'keywords': ['orgulloso', 'santa ana', 'santaneco',
                        'fas', 'deporte', 'cultura', 'identidad'],
            'nombre': 'Conexion con identidad local',
            'descripcion': 'Ciudadanos que se identifican con el municipio'
        }
    }
    resultados_rechazo = []
    resultados_respaldo = []

    df_neg = df_comentarios[
        df_comentarios['score_sentimiento'].notna() &
        (df_comentarios['score_sentimiento'] < -0.1)
    ].copy()

    df_pos = df_comentarios[
        df_comentarios['score_sentimiento'].notna() &
        (df_comentarios['score_sentimiento'] > 0.1)
    ].copy()

    for key, patron in patrones_rechazo.items():
        mask = df_neg['message'].str.lower().str.contains(
            '|'.join(patron['keywords']), na=False
        )
        comentarios_patron = df_neg[mask]
        if len(comentarios_patron) > 0:
            rep = str(comentarios_patron.iloc[0]['message'])
            otros = [str(x) for x in comentarios_patron.iloc[1:4]['message'].tolist()]
            cat = comentarios_patron['categoria_nombre'].mode()
            categoria = cat.iloc[0] if len(cat) > 0 else "General"
            resultados_rechazo.append({
                'nombre': patron['nombre'],
                'descripcion': patron['descripcion'],
                'count': len(comentarios_patron),
                'representativo': rep,
                'otros': otros,
                'categoria': categoria,
                'tendencia': 'Creciendo' if len(comentarios_patron) > 20
                            else 'Estable'
            })

    for key, patron in patrones_respaldo.items():
        mask = df_pos['message'].str.lower().str.contains(
            '|'.join(patron['keywords']), na=False
        )
        comentarios_patron = df_pos[mask]
        if len(comentarios_patron) > 0:
            rep = str(comentarios_patron.iloc[0]['message'])
            otros = [str(x) for x in comentarios_patron.iloc[1:4]['message'].tolist()]
            cat = comentarios_patron['categoria_nombre'].mode()
            categoria = cat.iloc[0] if len(cat) > 0 else "General"
            resultados_respaldo.append({
                'nombre': patron['nombre'],
                'descripcion': patron['descripcion'],
                'count': len(comentarios_patron),
                'representativo': rep,
                'otros': otros,
                'categoria': categoria,
                'tendencia': 'Estable' if len(comentarios_patron) > 50
                            else 'Creciendo'
            })

    return resultados_rechazo, resultados_respaldo

@st.cache_data(ttl=3600)
def calcular_confianza_institucional():
    df = safe_query("""
        SELECT fc.message, fc.post_id,
               fs.score_sentimiento,
               pc.categoria_nombre
        FROM fb_comments fc
        LEFT JOIN fb_sentimiento fs ON fc.post_id = fs.post_id
        LEFT JOIN post_categorias pc ON fc.post_id = pc.item_id
        WHERE fc.message IS NOT NULL
        AND LENGTH(fc.message) > 10
    """, FACEBOOK_DB_ACTIVA)
    if df.empty:
        return {}, 0, ("", {"score": 0})

    dimensiones = {
        'honestidad': {
            'trust': ['honesto','transparente','cumple','palabra',
                     'verdad','confiable','serio','responsable'],
            'distrust': ['corrupto','mentira','roba','ladron',
                        'trampa','engaño','deshonesto','fraude',
                        'corrucion','corrupto']
        },
        'competencia': {
            'trust': ['capaz','eficiente','trabaja','logro',
                     'resultado','avance','progreso','gestiona',
                     'resuelve','soluciona'],
            'distrust': ['inutil','incapaz','incompetente','nefasto',
                        'no sirve','mal trabajo','pésimo','fracaso',
                        'no hace nada','abandono']
        },
        'presencia': {
            'trust': ['presente','cercano','visita','recorre',
                     'atiende','responde','llega','aparece'],
            'distrust': ['ausente','no aparece','no viene',
                        'desaparecido','no atiende','ignoramos',
                        'olvidados','no llega']
        },
        'integridad': {
            'trust': ['justo','equitativo','todos','comunidades',
                     'igual','imparcial','beneficia'],
            'distrust': ['favoritismo','solo algunos','donde conviene',
                        'preferidos','discrimina','desigual',
                        'olvidadas','nada mas']
        }
    }

    resultados = {}
    for dim, palabras in dimensiones.items():
        trust_mask = df['message'].str.lower().str.contains(
            '|'.join(palabras['trust']), na=False
        )
        distrust_mask = df['message'].str.lower().str.contains(
            '|'.join(palabras['distrust']), na=False
        )
        n_trust = trust_mask.sum()
        n_distrust = distrust_mask.sum()
        total = n_trust + n_distrust
        if total > 0:
            score = (n_trust - n_distrust) / total
        else:
            score = 0
        ejemplos_raw = df[distrust_mask]['message'].tolist()
        ejemplos_dedup = list(dict.fromkeys(ejemplos_raw))[:3]
        resultados[dim] = {
            'trust': int(n_trust),
            'distrust': int(n_distrust),
            'score': float(score),
            'comentarios_distrust': ejemplos_dedup
        }

    total_trust_global = sum(d['trust'] for d in resultados.values())
    total_distrust_global = sum(d['distrust'] for d in resultados.values())

    if total_distrust_global > 0:
        ratio_global = total_trust_global / total_distrust_global
    else:
        ratio_global = total_trust_global  # sin desconfianza → confianza perfecta

    if ratio_global >= 2.0:
        score_global = 1.0
    elif ratio_global >= 1.0:
        score_global = 0.5
    elif ratio_global >= 0.5:
        score_global = 0.0
    else:
        score_global = -0.5

    dim_riesgo = min(resultados.items(), key=lambda x: x[1]['score'])

    return resultados, score_global, dim_riesgo

@st.cache_data(ttl=3600)
def calcular_narrativas_activas():
    df = safe_query("""
        SELECT fc.message, fc.post_id,
               fe.created_time,
               fs.score_sentimiento,
               pc.categoria_nombre
        FROM fb_comments fc
        LEFT JOIN fb_engagement fe ON fc.post_id = fe.post_id
        LEFT JOIN fb_sentimiento fs ON fc.post_id = fs.post_id
        LEFT JOIN post_categorias pc ON fc.post_id = pc.item_id
        WHERE fc.message IS NOT NULL
        AND LENGTH(fc.message) > 10
    """, FACEBOOK_DB_ACTIVA)
    if df.empty:
        return {}

    df['created_time'] = pd.to_datetime(df['created_time'], errors='coerce')
    df['semana'] = df['created_time'].dt.to_period('W').dt.start_time

    narrativas = {
        'abandono_territorial': {
            'nombre': 'Abandono territorial',
            'descripcion': 'La ciudadanía siente que ciertas zonas o '
                          'colonias son ignoradas sistemáticamente',
            'keywords': ['colonia','barrio','calle','canton','comunidad',
                        'abandon','olvidado','nunca vienen','no llegan',
                        'esperando','años esperando'],
            'color': '#ef4444',
            'icono': '🏚️'
        },
        'promesas_incumplidas': {
            'nombre': 'Promesas incumplidas',
            'descripcion': 'Menciones de compromisos que el alcalde '
                          'hizo y que la ciudadanía percibe como no cumplidos',
            'keywords': ['prometio','prometieron','prometido','dijeron',
                        'para cuando','cuando van','siguen igual',
                        'nunca','años prometiendo','todavia'],
            'color': '#f59e0b',
            'icono': '📋'
        },
        'narrativa_electoral': {
            'nombre': 'Narrativa electoral',
            'descripcion': 'La ciudadanía interpreta las acciones '
                          'del alcalde en clave de campaña electoral',
            'keywords': ['eleccion','voto','reeleccion','campaña',
                        'boto','votar','candidato','proximas',
                        'solo cuando hay','interesa el voto'],
            'color': '#8b5cf6',
            'icono': '🗳️'
        },
        'corrupcion': {
            'nombre': 'Narrativa de corrupción',
            'descripcion': 'Señalamientos directos o indirectos '
                          'sobre manejo irregular de recursos',
            'keywords': ['corrupto','robo','ladron','dinero','fondos',
                        'recursos','licitacion','contrato','empleados',
                        'enchufado','nepotismo','millones'],
            'color': '#dc2626',
            'icono': '⚠️'
        },
        'reconocimiento': {
            'nombre': 'Reconocimiento ciudadano',
            'descripcion': 'Narrativa positiva — ciudadanos que '
                          'defienden y reconocen la gestión',
            'keywords': ['excelente','buen trabajo','gracias alcalde',
                        'sigan adelante','lo apoyamos','felicitaciones',
                        'bien hecho','orgullo','progreso','cambio'],
            'color': '#22c55e',
            'icono': '👏'
        }
    }

    resultados = {}
    for key, narr in narrativas.items():
        mask = df['message'].str.lower().str.contains(
            '|'.join(narr['keywords']), na=False
        )
        df_narr = df[mask].copy()

        if not df_narr.empty and 'semana' in df_narr.columns:
            por_semana = df_narr.groupby('semana').size().reset_index(
                name='count'
            ).sort_values('semana')

            if len(por_semana) >= 4:
                recientes = por_semana.tail(4)['count'].mean()
                anteriores = por_semana.iloc[-8:-4]['count'].mean() if len(por_semana) >= 8 else por_semana.head(4)['count'].mean()
                if anteriores > 0:
                    cambio_pct = ((recientes - anteriores) / anteriores) * 100
                else:
                    cambio_pct = 0
            else:
                cambio_pct = 0
                por_semana = pd.DataFrame({'semana':[],'count':[]})
        else:
            cambio_pct = 0
            por_semana = pd.DataFrame({'semana':[],'count':[]})

        if cambio_pct > 20:
            tendencia = '↑ Creciendo'
            tend_color = '#ef4444' if key != 'reconocimiento' else '#22c55e'
        elif cambio_pct < -20:
            tendencia = '↓ Bajando'
            tend_color = '#22c55e' if key != 'reconocimiento' else '#ef4444'
        else:
            tendencia = '→ Estable'
            tend_color = '#6b7280'

        resultados[key] = {
            **narr,
            'total': len(df_narr),
            'cambio_pct': cambio_pct,
            'tendencia': tendencia,
            'tend_color': tend_color,
            'por_semana': por_semana,
            'ejemplos': list(dict.fromkeys(df_narr['message'].tolist()))[:3]
        }

    return resultados

@st.cache_data(ttl=3600)
def calcular_contagio_emocional():
    df_posts = safe_query("""
        SELECT fe.post_id,
               fe.created_time,
               fe.score_emocional,
               fe.indice_amor,
               fe.indice_humor,
               fe.indice_tristeza,
               fe.total_reacciones,
               fe.message,
               pc.categoria_nombre,
               fs.score_sentimiento as sent_comentarios,
               fs.pct_positivo,
               fs.pct_negativo
        FROM fb_engagement fe
        LEFT JOIN post_categorias pc ON fe.post_id = pc.item_id
        LEFT JOIN fb_sentimiento fs ON fe.post_id = fs.post_id
        WHERE fe.total_reacciones >= 10
    """, FACEBOOK_DB_ACTIVA)
    if df_posts.empty:
        return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

    df_posts['created_time'] = pd.to_datetime(
        df_posts['created_time'], errors='coerce'
    )
    df_posts['semana'] = df_posts['created_time'].dt.to_period('W').dt.start_time

    df_posts['distorsion'] = (
        df_posts['score_emocional'] - df_posts['sent_comentarios']
    )

    umbral_pos = df_posts['score_emocional'].quantile(0.75)
    umbral_neg = df_posts['score_emocional'].quantile(0.25)

    def clasificar_contagio(row):
        em = row.get('score_emocional', 0) or 0
        sent = row.get('sent_comentarios', 0) or 0
        dist = row.get('distorsion', 0) or 0

        if pd.isna(em) or pd.isna(sent):
            return 'sin_datos', 'Sin datos suficientes'

        if em >= umbral_pos and sent >= umbral_pos:
            return 'resonancia_positiva', 'Resonancia positiva'
        elif em >= umbral_pos and sent <= umbral_neg:
            return 'rechazo_a_positivo', 'Rechazo a mensaje positivo'
        elif em <= umbral_neg and sent <= umbral_neg:
            return 'resonancia_negativa', 'Resonancia negativa'
        elif em <= umbral_neg and sent >= umbral_pos:
            return 'inversion_positiva', 'Inversión positiva'
        elif abs(dist) > 0.3:
            return 'distorsion_alta', 'Alta distorsión narrativa'
        else:
            return 'neutral', 'Respuesta neutral'

    df_posts['tipo_contagio'] = df_posts.apply(
        lambda r: clasificar_contagio(r)[0], axis=1
    )
    df_posts['label_contagio'] = df_posts.apply(
        lambda r: clasificar_contagio(r)[1], axis=1
    )

    conteo_tipos = df_posts['tipo_contagio'].value_counts().to_dict()

    distorsion_alta = df_posts[
        df_posts['tipo_contagio'] == 'rechazo_a_positivo'
    ].nlargest(5, 'distorsion')[
        ['post_id','created_time','message',
         'score_emocional','sent_comentarios',
         'distorsion','categoria_nombre']
    ]

    por_semana = df_posts.groupby('semana').agg(
        score_post=('score_emocional','mean'),
        score_comentarios=('sent_comentarios','mean'),
        distorsion_prom=('distorsion','mean')
    ).reset_index().dropna()

    return df_posts, conteo_tipos, distorsion_alta, por_semana

def calcular_score_emocional_neto(min_reacciones: int = 10) -> pd.DataFrame:
    """Score emocional neto por post (Módulo 3 del blueprint).
    Lee fb_posts (reacciones/shares/views reales) + fb_sentimiento (sentimiento por post)."""
    posts = safe_query("""
        SELECT post_id, page_name, message, created_time,
               likes_count, loves_count, hahas_count, wows_count,
               sads_count, angrys_count, shares_count, views_count,
               comments_count, topic_category, zona
        FROM fb_posts
    """, FACEBOOK_DB_ACTIVA)
    if posts.empty:
        return pd.DataFrame()

    num_cols = ["likes_count", "loves_count", "hahas_count", "wows_count",
                "sads_count", "angrys_count", "shares_count", "views_count", "comments_count"]
    for c in num_cols:
        posts[c] = pd.to_numeric(posts[c], errors="coerce").fillna(0)

    # engagement_total (blueprint): like + encanta + divierte + asombra + entristece + enoja + compartidos
    posts["engagement_total"] = (
        posts["likes_count"] + posts["loves_count"] + posts["hahas_count"]
        + posts["wows_count"] + posts["sads_count"] + posts["angrys_count"]
        + posts["shares_count"]
    )
    # total reacciones (sin shares) para la regla de exclusión <10
    posts["total_reacciones"] = (
        posts["likes_count"] + posts["loves_count"] + posts["hahas_count"]
        + posts["wows_count"] + posts["sads_count"] + posts["angrys_count"]
    )

    base = posts["engagement_total"].replace(0, pd.NA)
    # afecto positivo = encanta(loves) + asombra(wows) ; controversia = enoja(angrys) + entristece(sads)
    posts["afecto_positivo"] = ((posts["loves_count"] + posts["wows_count"]) / base).fillna(0.0)
    posts["controversia"]    = ((posts["angrys_count"] + posts["sads_count"]) / base).fillna(0.0)

    # score_sentimiento por post desde fb_sentimiento, normalizado a [-1, 1]
    sent = safe_query("""
        SELECT post_id, pct_positivo, pct_negativo, total_comentarios
        FROM fb_sentimiento
    """, FACEBOOK_DB_ACTIVA)
    if not sent.empty:
        for c in ["pct_positivo", "pct_negativo", "total_comentarios"]:
            sent[c] = pd.to_numeric(sent[c], errors="coerce").fillna(0)
        # detecta si los pct vienen en 0-100 o ya en 0-1
        denom = 100.0 if sent[["pct_positivo", "pct_negativo"]].max().max() > 1.5 else 1.0
        sent["score_sent_norm"] = (sent["pct_positivo"] - sent["pct_negativo"]) / denom
        posts = posts.merge(sent[["post_id", "score_sent_norm", "total_comentarios"]],
                            on="post_id", how="left")
    else:
        posts["score_sent_norm"] = 0.0
        posts["total_comentarios"] = 0
    posts["score_sent_norm"] = posts["score_sent_norm"].fillna(0.0)
    posts["total_comentarios"] = posts["total_comentarios"].fillna(0)

    # SCORE EMOCIONAL NETO (blueprint M3)
    posts["score_emocional_neto"] = (
        posts["afecto_positivo"] - posts["controversia"] + (posts["score_sent_norm"] * 0.3)
    )

    # regla del blueprint: solo posts con >= min_reacciones cuentan para proporciones
    posts["incluido_proporciones"] = posts["total_reacciones"] >= min_reacciones
    return posts

def calcular_viralidad_tiktok(min_views: int = 100) -> pd.DataFrame:
    """Índice de viralidad de TikTok (Módulo 3, adaptado).
    TikTok no tiene reacciones diferenciadas → medimos ALCANCE/propagación, no emoción."""
    df = safe_query("SELECT * FROM videos", TIKTOK_DB_ACTIVA)
    if df.empty:
        return pd.DataFrame()
    for c in ["views", "likes", "shares", "comments_count", "favorites_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0) if c in df.columns else 0
    df = df[df["views"] >= min_views].copy()
    if df.empty:
        return df
    v = df["views"].replace(0, pd.NA)
    df["indice_viralidad"] = (df["shares"] / v).fillna(0.0)
    df["engagement_rate"]  = ((df["likes"] + df["comments_count"] + df["shares"]) / v).fillna(0.0)
    label_col = next((c for c in ["descripcion", "description", "caption", "desc",
                                   "titulo", "title", "video_url", "url"] if c in df.columns), None)
    if label_col:
        df["video"] = df[label_col].astype(str).str.replace("\n", " ").str.slice(0, 80)
    else:
        df["video"] = "video " + df.index.astype(str)
    return df.sort_values("indice_viralidad", ascending=False)

def calcular_correlacion_noticias_picos(z_umbral: float = 1.0, ventana_dias: int = 3) -> dict:
    """Cruza picos de engagement de FB (alcaldía) con noticias externas que coinciden en el tiempo.
    Es correlación TEMPORAL, no causalidad."""
    posts = safe_query("""
        SELECT created_time, likes_count, loves_count, hahas_count, wows_count,
               sads_count, angrys_count, shares_count, comments_count
        FROM fb_posts
        WHERE created_time IS NOT NULL AND TRIM(created_time) <> ''
    """, FACEBOOK_DB_ACTIVA)
    if posts.empty:
        return {}
    react = ["likes_count", "loves_count", "hahas_count", "wows_count",
             "sads_count", "angrys_count", "shares_count", "comments_count"]
    for c in react:
        posts[c] = pd.to_numeric(posts[c], errors="coerce").fillna(0)
    posts["engagement"] = posts[react].sum(axis=1)
    posts["fecha"] = pd.to_datetime(posts["created_time"], errors="coerce", utc=True).dt.tz_localize(None)
    posts = posts.dropna(subset=["fecha"])
    if posts.empty:
        return {}
    posts["semana"] = posts["fecha"].dt.to_period("W-SUN").dt.start_time
    serie = posts.groupby("semana", as_index=False)["engagement"].sum().sort_values("semana")
    mu = serie["engagement"].mean()
    sd = serie["engagement"].std(ddof=0)
    serie["z"] = (serie["engagement"] - mu) / (sd if sd and sd > 0 else 1)
    serie["es_pico"] = serie["z"] >= z_umbral
    noticias = safe_query("""
        SELECT created_time, source, message, total_reactions, comments_count, post_url
        FROM external_posts
        WHERE created_time IS NOT NULL AND TRIM(created_time) <> ''
    """, EXTERNOS_DB_ACTIVA)
    if not noticias.empty:
        noticias["fecha"] = pd.to_datetime(noticias["created_time"], errors="coerce", utc=True).dt.tz_localize(None)
        noticias = noticias.dropna(subset=["fecha"])
    coincidencias = []
    for _, pk in serie[serie["es_pico"]].iterrows():
        wk = pk["semana"]
        if noticias is not None and not noticias.empty:
            mask = (noticias["fecha"] >= wk - pd.Timedelta(days=ventana_dias)) & \
                   (noticias["fecha"] <= wk + pd.Timedelta(days=7 + ventana_dias))
            for _, nt in noticias[mask].iterrows():
                coincidencias.append({
                    "semana_pico": wk.date().isoformat(),
                    "engagement": int(pk["engagement"]),
                    "z": round(float(pk["z"]), 2),
                    "fuente": str(nt.get("source", "") or ""),
                    "noticia": (str(nt.get("message", "") or ""))[:120],
                    "fecha_noticia": nt["fecha"].date().isoformat(),
                })
    return {"serie": serie, "coincidencias": pd.DataFrame(coincidencias),
            "n_picos": int(serie["es_pico"].sum())}

# ═══════════════════════════════════════════
# SECCIÓN 1 — ESTADO GENERAL
# ═══════════════════════════════════════════

def render_notas_metodologicas():
    st.header("📋 Notas Metodológicas")
    st.caption("Límites honestos del sistema — léelos antes de tomar decisiones con estos datos.")
    st.markdown(
        "Este panel analiza contenido público (posts, reacciones y comentarios) de las "
        "páginas de la Alcaldía y el alcalde. Es una herramienta de lectura de percepción "
        "colectiva, no un oráculo. Sus límites:"
    )
    st.warning(
        "No predice votos individuales. Mide qué temas generan qué *emociones en "
        "conjunto*, no el comportamiento de personas concretas."
    )
    st.info(
        "Las reacciones son un proxy emocional, no un test psicológico validado. "
        "Úsalas como señal de tono colectivo, no como diagnóstico."
    )
    st.info(
        "El sentimiento de comentarios tiene ~85% de precisión en español. "
        "Alrededor de 1 de cada 7 comentarios puede estar mal clasificado."
    )
    st.warning(
        "Correlación ≠ causalidad. Que un pico de engagement coincida con una noticia "
        "externa no prueba que una haya causado la otra; pueden influir terceros factores."
    )
    st.info(
        "TikTok no tiene reacciones diferenciadas (solo 'me gusta'). Su lectura emocional "
        "depende 100% de los comentarios."
    )
    st.info(
        "En Facebook, las reacciones con datos sólidos son 'Me gusta', 'Me encanta', "
        "'Me divierte' y 'Me enoja'. 'Me asombra' y 'Me entristece' aparecen en volúmenes "
        "mínimos (decenas de casos), así que las métricas de afecto/controversia se apoyan "
        "sobre todo en las primeras."
    )
    st.caption(
        "Metodología inspirada en Kosinski et al. (2013), adaptada a datos agregados por "
        "publicación (no a perfiles individuales) y con las limitaciones señaladas por "
        "Farina et al. (2025)."
    )

if seccion == "📊 Estado General":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">📊 Estado General</div>
        <div class="seccion-subtitulo">
            Un vistazo — panorama completo en 30 segundos
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos de Facebook ni TikTok para este periodo.")
        st.stop()

    color_sem, texto_sem = calcular_semaforo(df_fb)

    # Bullets
    df_cat = safe_query("SELECT item_id, categoria_nombre FROM post_categorias", FACEBOOK_DB_ACTIVA)

    df_sent = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
    pct_positivo = df_sent['pct_positivo'].mean() if not df_sent.empty else 0

    df_tema_neg = safe_query("""
        SELECT pc.categoria_nombre,
               AVG(fs.pct_negativo) as pct_neg
        FROM fb_sentimiento fs
        LEFT JOIN post_categorias pc ON fs.post_id = pc.item_id
        WHERE pc.categoria_nombre IS NOT NULL
        AND pc.categoria_nombre != ''
        GROUP BY pc.categoria_nombre
        ORDER BY pct_neg DESC
        LIMIT 1
    """, FACEBOOK_DB_ACTIVA)
    tema_top_neg = df_tema_neg.iloc[0]['categoria_nombre'] if not df_tema_neg.empty else "Sin datos"

    df_fb_s, df_tk_s = cargar_series(FACEBOOK_DB_ACTIVA, TIKTOK_DB_ACTIVA)
    semana_anomalia = "sin anomalias recientes"
    anomalias_tk = df_tk_s[df_tk_s['es_anomalia'] == True].sort_values('semana', ascending=False)
    if not anomalias_tk.empty:
        semana_anomalia = formato_fecha_espanol(anomalias_tk.iloc[0]['semana'])

    clase_sem = f"semaforo-{color_sem}"
    st.markdown(f"""
    <div class="{clase_sem}">
        <p class="semaforo-texto">{texto_sem}</p>
    </div>
    """, unsafe_allow_html=True)

    # Interpretación
    score_sent_val = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos_val = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0

    interpretacion_sem = generar_interpretacion("semaforo", {
        'score': score_sent_val,
        'pct_negativo': pct_neg_val,
        'pct_positivo': pct_pos_val,
        'indice_enojo': enojo_val
    })

    st.markdown(f"""
    <div style="background:#0f172a;border-left:4px solid #3b82f6;
         padding:16px 20px;border-radius:4px;margin-bottom:16px">
        <p style="font-size:13px;color:#6b7280;margin:0 0 4px 0;
           font-weight:600;letter-spacing:1px;text-transform:uppercase">
            LO QUE ESTO SIGNIFICA
        </p>
        <p style="font-size:15px;color:#e2e8f0;margin:0;line-height:1.7">
            {interpretacion_sem}
        </p>
    </div>
    """, unsafe_allow_html=True)

    total_reacciones = 0
    if not df_fb.empty:
        total_reacciones += df_fb['total_reacciones'].sum()
    if not df_tk.empty:
        total_reacciones += df_tk['likes'].sum()

    st.markdown(f"""
    <div class="card">
        <p class="bullet-oro">
            📊 En este período recibiste
            <strong>{total_reacciones:,.0f}</strong>
            reacciones en total
        </p>
        <p class="bullet-oro">
            🎯 El tema con mayor rechazo ciudadano:
            <strong>{tema_top_neg}</strong>
        </p>
        <p class="bullet-oro">
            💬 El <strong>{pct_positivo:.1f}%</strong>
            de los comentarios son de apoyo
        </p>
        <p class="bullet-oro">
            ⚡ Semana con actividad inusual más reciente:
            <strong>{semana_anomalia}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 4 metricas
    total_eng = 0
    total_posts = 0
    if not df_fb.empty:
        total_eng += int(df_fb['engagement_total'].sum())
        total_posts += len(df_fb)
    if not df_tk.empty:
        total_eng += int(df_tk['engagement_total'].sum())
        total_posts += len(df_tk)

    n_comments = 0
    df_nc = safe_query("SELECT COUNT(*) as n FROM fb_comments WHERE message != ''", FACEBOOK_DB_ACTIVA)
    if not df_nc.empty:
        n_comments = int(df_nc.iloc[0]['n'])

    sent_fb = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
    score_sent = sent_fb['score_sentimiento'].mean() if not sent_fb.empty else 0
    if score_sent > 0.2:
        tono_txt, tono_color = "POSITIVO", "#22c55e"
    elif score_sent > 0:
        tono_txt, tono_color = "MIXTO", "#eab308"
    else:
        tono_txt, tono_color = "CRITICO", "#ef4444"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Personas que reaccionaron</div>
            <div class="card-value">{total_eng:,}</div>
            <div class="card-sub">reacciones totales</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Comentarios recibidos</div>
            <div class="card-value">{int(n_comments):,}</div>
            <div class="card-sub">con texto analizable</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Contenido publicado</div>
            <div class="card-value">{total_posts:,}</div>
            <div class="card-sub">posts y videos</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Tono ciudadano</div>
            <div class="card-value" style="color:{tono_color};font-size:24px">{tono_txt}</div>
            <div class="card-sub">basado en comentarios</div>
        </div>""", unsafe_allow_html=True)

    # Grafico tendencia
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Cada punto en esta línea es una semana. Cuando la línea sube, más gente interactuó con tu contenido. Los puntos rojos son semanas donde la actividad fue inusualmente alta o baja — algo ocurrió esa semana que movilizó a la ciudadanía.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### ¿Cuanto esta hablando la gente de ti?")

    if plataforma == "Facebook":
        df_serie = df_fb_s[['semana','engagement','es_anomalia']].copy()
    elif plataforma == "TikTok":
        df_serie = df_tk_s[['semana','views_suma','es_anomalia']].copy()
        df_serie = df_serie.rename(columns={'views_suma':'engagement'})
    else:
        df_merged = pd.merge(
            df_fb_s[['semana','engagement']].rename(columns={'engagement':'fb'}),
            df_tk_s[['semana','views_suma','es_anomalia']].rename(columns={'views_suma':'tk'}),
            on='semana', how='outer'
        ).fillna(0)
        df_merged['engagement'] = df_merged['fb'] + df_merged['tk']
        df_serie = df_merged[['semana','engagement','es_anomalia']].copy()

    fecha_inicio_plot = get_fecha_inicio(periodo)
    df_serie = df_serie[df_serie['semana'] >= fecha_inicio_plot]

    if not df_serie.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_serie['semana'], y=df_serie['engagement'],
            mode='lines',
            line=dict(color='#3b82f6', width=2.5),
            name='Actividad ciudadana',
            hovertemplate='<b>%{x|%d %b %Y}</b><br>%{y:,.0f} interacciones<extra></extra>'
        ))
        anomalias = df_serie[df_serie['es_anomalia'] == True]
        if not anomalias.empty:
            fig.add_trace(go.Scatter(
                x=anomalias['semana'], y=anomalias['engagement'],
                mode='markers',
                marker=dict(color='#ef4444', size=12, symbol='circle'),
                name='Semana inusual',
                hovertemplate='<b>Semana inusual</b><br>%{x|%d %b %Y}<br>%{y:,.0f} interacciones<extra></extra>'
            ))
        fig.update_layout(
            plot_bgcolor='#111827', paper_bgcolor='#111827',
            font=dict(color='#9ca3af', size=11),
            xaxis=dict(gridcolor='#1f2937', showgrid=True, tickformat='%d %b\n%Y'),
            yaxis=dict(gridcolor='#1f2937', showgrid=True, tickformat=','),
            legend=dict(bgcolor='#111827', bordercolor='#1f2937'),
            margin=dict(l=0, r=0, t=10, b=0), height=280
        )
        st.plotly_chart(fig, use_container_width=True)

    # Comparativa FB vs TK
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Comparación directa entre tus dos plataformas principales. Facebook mide reacciones y comentarios. TikTok mide visualizaciones y engagement — cuántas personas no solo vieron sino interactuaron.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### ¿Como se compara cada plataforma?")
    col_fb, col_tk = st.columns(2)

    with col_fb:
        if not df_fb.empty:
            reac_fb = int(df_fb['total_reacciones'].sum())
            sent_fb2 = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
            tono_fb = "Positivo" if sent_fb2['score_sentimiento'].mean() > 0.1 else "Mixto"
            amor = df_fb['indice_amor'].mean()
            humor = df_fb['indice_humor'].mean()
            tristeza = df_fb['indice_tristeza'].mean()
            enojo = df_fb['indice_enojo'].mean() if 'indice_enojo' in df_fb.columns else 0
            reac_max = max([
                (amor,    '❤️ Amor'),
                (humor,   '😆 Humor'),
                (tristeza,'😢 Tristeza'),
                (enojo,   '😡 Enojo')
            ], key=lambda x: x[0] if not pd.isna(x[0]) else 0)[1]
            st.markdown(f"""
            <div class="card">
                <div class="card-title">FACEBOOK</div>
                <p style="font-size:13px;margin:6px 0">
                    <strong>Reacciones totales:</strong> {reac_fb:,}
                </p>
                <p style="font-size:13px;margin:6px 0">
                    <strong>Comentarios totales:</strong> {int(n_comments):,}
                </p>
                <p style="font-size:13px;margin:6px 0">
                    <strong>Tono predominante:</strong> {tono_fb}
                </p>
                <p style="font-size:13px;margin:6px 0">
                    <strong>Reacción más usada:</strong> {reac_max}
                </p>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="card"><p>Sin datos de Facebook para este periodo</p></div>', unsafe_allow_html=True)

    with col_tk:
        if not df_tk.empty:
            views_tk = int(df_tk['views'].sum())
            likes_tk = int(df_tk['likes'].sum())
            shares_prom = df_tk['shares'].mean() if not df_tk.empty else 0
            eng_rate = df_tk['engagement_rate'].mean() * 100
            st.markdown(f"""
            <div class="card">
                <div class="card-title">TIKTOK</div>
                <p style="font-size:13px;margin:6px 0">
                    <strong>Views totales:</strong> {views_tk:,}
                </p>
                <p style="font-size:13px;margin:6px 0">
                    <strong>Likes totales:</strong> {likes_tk:,}
                </p>
                <p style="font-size:13px;margin:6px 0">
                    <strong>Compartidos promedio:</strong> {shares_prom:.1f}
                </p>
                <p style="font-size:13px;margin:6px 0">
                    <strong>Engagement promedio:</strong> {eng_rate:.2f}%
                </p>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="card"><p>Sin datos de TikTok para este periodo</p></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# SECCIÓN 2 — TEMAS Y EMOCIONES
# ═══════════════════════════════════════════

elif seccion == "🎯 Temas y Emociones":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">🎯 Temas y Emociones</div>
        <div class="seccion-subtitulo">
            ¿De que habla la gente y como se siente segun el tema?
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos en este periodo para Temas y Emociones.")
        st.stop()

    df_sent = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)

    for df in [df_fb, df_tk, df_fb_raw, df_tk_raw]:
        if 'categoria_nombre' in df.columns:
            df['categoria_nombre'] = df['categoria_nombre'].replace(
                'Contenido promocional',
                'Convocatorias y celebraciones'
            )

    dfs = []
    if not df_fb.empty and 'categoria_nombre' in df_fb.columns:
        fb_cat = df_fb.groupby('categoria_nombre').agg(
            reacciones=('total_reacciones','sum'),
            comentarios=('engagement_total','sum'),
            amor=('indice_amor','mean'),
            humor=('indice_humor','mean'),
            tristeza=('indice_tristeza','mean')
        ).reset_index()
        fb_cat['plataforma'] = 'Facebook'
        dfs.append(fb_cat)

    if not df_tk.empty and 'categoria_nombre' in df_tk.columns:
        tk_cat = df_tk.groupby('categoria_nombre').agg(
            reacciones=('likes','sum'),
            comentarios=('comments_count','sum')
        ).reset_index()
        tk_cat['amor'] = 0
        tk_cat['humor'] = 0
        tk_cat['tristeza'] = 0
        tk_cat['plataforma'] = 'TikTok'
        dfs.append(tk_cat)

    if dfs:
        df_temas = pd.concat(dfs).groupby('categoria_nombre').agg(
            reacciones=('reacciones','sum'),
            comentarios=('comentarios','sum'),
            amor=('amor','mean'),
            humor=('humor','mean'),
            tristeza=('tristeza','mean')
        ).reset_index().sort_values('reacciones', ascending=False)

        df_sent_cat = safe_query("""
            SELECT pc.categoria_nombre,
                   AVG(fs.pct_positivo) as pct_pos,
                   AVG(fs.pct_negativo) as pct_neg,
                   AVG(fs.score_sentimiento) as score
            FROM fb_sentimiento fs
            LEFT JOIN post_categorias pc ON fs.post_id = pc.item_id
            WHERE pc.categoria_nombre IS NOT NULL
            GROUP BY pc.categoria_nombre
        """, FACEBOOK_DB_ACTIVA)
        df_sent_cat['categoria_nombre'] = df_sent_cat['categoria_nombre'].replace(
            'Contenido promocional', 'Convocatorias y celebraciones'
        )
        df_temas = df_temas.merge(df_sent_cat, on='categoria_nombre', how='left')

        def get_tono_badge(score):
            if pd.isna(score): return '<span class="badge-mixto">MIXTO</span>'
            if score > 0.15: return '<span class="badge-positivo">POSITIVO</span>'
            if score > 0: return '<span class="badge-mixto">MIXTO</span>'
            return '<span class="badge-critico">CRITICO</span>'

        def get_riesgo(pct_neg, reacciones):
            if pd.isna(pct_neg): return '<span class="riesgo-medio">MEDIO</span>'
            if pct_neg > 8: return '<span class="riesgo-alto">ALTO</span>'
            if pct_neg > 4: return '<span class="riesgo-medio">MEDIO</span>'
            return '<span class="riesgo-bajo">BAJO</span>'

        def get_emocion(amor, humor, tristeza):
            if pd.isna(amor): return "—"
            vals = [(amor,'Amor'),(humor,'Humor'),(tristeza,'Tristeza')]
            return max(vals, key=lambda x: x[0] if not pd.isna(x[0]) else 0)[1]

        # Interpretación temas
        if not df_temas.empty and 'pct_neg' in df_temas.columns:
            tema_mas_critico = df_temas.nlargest(1, 'pct_neg').iloc[0]
            tema_mas_positivo = df_temas.nsmallest(1, 'pct_neg').iloc[0]

            texto_critico = generar_interpretacion("tema_critico", {
                'tema': str(tema_mas_critico['categoria_nombre']).replace('\n',' ')[:40],
                'pct_negativo': tema_mas_critico.get('pct_neg', 0),
                'reacciones': int(tema_mas_critico['reacciones'])
            })

            texto_positivo = generar_interpretacion("tema_positivo", {
                'tema': str(tema_mas_positivo['categoria_nombre']).replace('\n',' ')[:40],
                'pct_positivo': tema_mas_positivo.get('pct_pos', 0)
            })

            st.markdown(f"""
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px">
                <div style="background:#1a0808;border-left:4px solid #ef4444;padding:16px 20px;border-radius:4px">
                    <p style="font-size:11px;color:#ef4444;margin:0 0 6px 0;font-weight:600;letter-spacing:1px;text-transform:uppercase">⚠️ TEMA EN ZONA DE RIESGO</p>
                    <p style="font-size:14px;color:#e2e8f0;margin:0;line-height:1.6">{texto_critico}</p>
                </div>
                <div style="background:#071a0f;border-left:4px solid #22c55e;padding:16px 20px;border-radius:4px">
                    <p style="font-size:11px;color:#22c55e;margin:0 0 6px 0;font-weight:600;letter-spacing:1px;text-transform:uppercase">✅ TEMA MÁS SÓLIDO</p>
                    <p style="font-size:14px;color:#e2e8f0;margin:0;line-height:1.6">{texto_positivo}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#0d1117;border-left:3px solid #374151;
             padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
            <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
                  color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
            <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
               line-height:1.5">Cada fila es un tema de tu contenido. TONO indica si los comentarios sobre ese tema son positivos, mixtos o críticos. EMOCIÓN es la reacción predominante. RIESGO señala los temas donde la ciudadanía está más molesta.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr;
             padding:10px 16px;border-bottom:2px solid #374151;
             font-size:11px;font-weight:600;letter-spacing:1px;
             color:#6b7280;text-transform:uppercase;">
            <span>TEMA</span>
            <span style="text-align:right">REACCIONES</span>
            <span style="text-align:center">TONO</span>
            <span style="text-align:center">EMOCION</span>
            <span style="text-align:right">COMENTARIOS</span>
            <span style="text-align:center">RIESGO</span>
        </div>
        """, unsafe_allow_html=True)

        for _, row in df_temas.iterrows():
            nombre = str(row['categoria_nombre']).replace('\n',' ')
            reac = f"{int(row['reacciones']):,}"
            tono = get_tono_badge(row.get('score'))
            emocion = get_emocion(row['amor'], row['humor'], row['tristeza'])
            comentarios = f"{int(row['comentarios']):,}"
            riesgo = get_riesgo(row.get('pct_neg'), row['reacciones'])

            st.markdown(f"""
            <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr;
                 padding:14px 16px;border-bottom:1px solid #1f2937;
                 font-size:13px;align-items:center;">
                <span style="font-weight:600;color:#f9fafb">{nombre}</span>
                <span style="text-align:right;font-family:'Courier New';
                      color:#60a5fa;font-weight:700">{reac}</span>
                <span style="text-align:center">{tono}</span>
                <span style="text-align:center">{emocion}</span>
                <span style="text-align:right;color:#9ca3af">{comentarios}</span>
                <span style="text-align:center">{riesgo}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Mapa de calor
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Cuanto más azul e intenso el color, más fuerte es esa emoción en ese tema. Blanco o gris = poca emoción. Azul brillante = tema que genera reacción emocional fuerte.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### ¿Que emocion genera cada tema?")

    if dfs and not df_temas.empty:
        df_heat = df_temas[['categoria_nombre','amor','humor','tristeza']].copy()
        df_heat = df_heat.fillna(0)
        df_heat = df_heat[
            (df_heat['amor'] > 0) |
            (df_heat['humor'] > 0) |
            (df_heat['tristeza'] > 0)
        ]
        df_heat['categoria_nombre'] = df_heat['categoria_nombre'].str.replace('\n',' ')
        df_heat_melt = df_heat.melt(
            id_vars='categoria_nombre',
            value_vars=['amor','humor','tristeza'],
            var_name='emocion', value_name='intensidad'
        )
        df_heat_melt['emocion'] = df_heat_melt['emocion'].map({
            'amor': 'Amor', 'humor': 'Humor', 'tristeza': 'Tristeza'
        })
        fig_heat = px.density_heatmap(
            df_heat_melt, x='emocion', y='categoria_nombre', z='intensidad',
            color_continuous_scale=[[0,'#111827'],[0.3,'#1e3a5f'],[0.7,'#2563eb'],[1,'#60a5fa']],
            labels={'intensidad':'Intensidad','emocion':'Emocion','categoria_nombre':'Tema'}
        )
        fig_heat.update_layout(
            plot_bgcolor='#111827', paper_bgcolor='#111827',
            font=dict(color='#9ca3af', size=11),
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=10, b=0), height=300
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # Top 5 posts
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Los 5 contenidos que más movieron a la ciudadanía en el período seleccionado, medidos por interacciones totales (reacciones + comentarios + compartidos).</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### El contenido que mas movio a la ciudadania")

    dfs_top = []
    if not df_fb.empty:
        fb_top = df_fb.nlargest(5, 'engagement_total')[
            ['post_id','created_time','message','engagement_total',
             'total_reacciones','indice_amor','indice_humor',
             'indice_tristeza','categoria_nombre']
        ].copy()
        fb_top['plataforma'] = 'Facebook'
        fb_top['fecha'] = fb_top['created_time']
        fb_top['texto'] = fb_top['message']
        dfs_top.append(fb_top.rename(columns={'engagement_total':'total','total_reacciones':'reacciones'}))

    if not df_tk.empty:
        tk_top = df_tk.nlargest(5, 'engagement_total')[
            ['id','created_at','description','engagement_total','likes','categoria_nombre']
        ].copy()
        tk_top['plataforma'] = 'TikTok'
        tk_top['fecha'] = tk_top['created_at']
        tk_top['texto'] = tk_top['description']
        tk_top['reacciones'] = tk_top['likes']
        tk_top['indice_amor'] = 0
        tk_top['indice_humor'] = 0
        tk_top['indice_tristeza'] = 0
        dfs_top.append(tk_top.rename(columns={'engagement_total':'total'}))

    if dfs_top:
        df_top = pd.concat(dfs_top).nlargest(5, 'total')
        for _, row in df_top.iterrows():
            plat = row['plataforma']
            plat_color = "#1877f2" if plat == "Facebook" else "#ff0050"
            plat_badge = f'<span style="background:{plat_color};color:white;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700">{plat.upper()}</span>'
            fecha = formato_fecha_espanol(row['fecha'])
            texto = str(row['texto'])[:120] + "..." if len(str(row['texto'])) > 120 else str(row['texto'])
            categoria = str(row.get('categoria_nombre',''))[:40]
            total = int(row['total'])

            ia_val = float(row.get('indice_amor',0) or 0)
            ih_val = float(row.get('indice_humor',0) or 0)
            it_val = float(row.get('indice_tristeza',0) or 0)
            reac_val = float(row.get('reacciones',0) or 0)
            amor_n = int(ia_val * reac_val) if pd.notna(reac_val) else 0
            humor_n = int(ih_val * reac_val) if pd.notna(reac_val) else 0
            trist_n = int(it_val * reac_val) if pd.notna(reac_val) else 0

            st.markdown(f"""
            <div class="card" style="border-left:4px solid #3b82f6">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-size:11px;color:#6b7280">{fecha}</span>
                    <div style="display:flex;gap:8px;align-items:center">
                        {plat_badge}
                        <span style="font-size:11px;color:#4b5563;background:#1f2937;padding:2px 8px;border-radius:4px">{categoria}</span>
                    </div>
                </div>
                <p style="font-size:14px;color:#e2e8f0;margin:8px 0;line-height:1.5">{texto}</p>
                <div style="display:flex;gap:16px;margin-top:10px;align-items:center">
                    <span style="font-size:12px;color:#9ca3af">
                        Amor {amor_n:,} &nbsp;·&nbsp; Humor {humor_n:,} &nbsp;·&nbsp; Tristeza {trist_n:,}
                    </span>
                    <span style="margin-left:auto;font-size:18px;font-weight:700;color:#60a5fa;font-family:'Courier New'">
                        {total:,} interacciones
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader("❤️‍🔥 Score Emocional Neto por post")
    st.caption(
        "Combina afecto vs. controversia (reacciones) y el sentimiento de los comentarios. "
        "Rango ~[-1, 1]: positivo = post querido; negativo = post que genera rechazo."
    )
    df_sen = calcular_score_emocional_neto(min_reacciones=10)
    if hay_datos(df_sen, "Aún no hay posts para el score emocional."):
        df_val = df_sen[df_sen["incluido_proporciones"]].copy()
        if hay_datos(df_val, "Ningún post supera el mínimo de 10 reacciones para el análisis de proporciones."):
            df_val = df_val.sort_values("score_emocional_neto", ascending=False)

            c1, c2, c3 = st.columns(3)
            c1.metric("Score neto promedio", f"{df_val['score_emocional_neto'].mean():+.2f}")
            c2.metric("Post más querido", f"{df_val['score_emocional_neto'].max():+.2f}")
            c3.metric("Post más controversial", f"{df_val['score_emocional_neto'].min():+.2f}")

            def _resumen(m):
                m = (str(m) if m is not None else "").replace("\n", " ").strip()
                return (m[:90] + "…") if len(m) > 90 else (m or "(sin texto)")
            df_val["post"] = df_val["message"].apply(_resumen)

            cols_show = ["post", "score_emocional_neto", "afecto_positivo",
                         "controversia", "score_sent_norm", "total_reacciones"]
            ren = {"post": "Post", "score_emocional_neto": "Score neto",
                   "afecto_positivo": "Afecto", "controversia": "Controversia",
                   "score_sent_norm": "Sent. coment.", "total_reacciones": "Reacciones"}
            fmt = {"Score neto": "{:+.2f}", "Afecto": "{:.2f}",
                   "Controversia": "{:.2f}", "Sent. coment.": "{:+.2f}"}

            st.markdown("**🟢 Top 10 — más queridos**")
            st.dataframe(df_val.head(10)[cols_show].rename(columns=ren).style.format(fmt),
                         use_container_width=True, hide_index=True)

            st.markdown("**🔴 Bottom 10 — más controversiales**")
            st.dataframe(df_val.tail(10).sort_values("score_emocional_neto")[cols_show].rename(columns=ren).style.format(fmt),
                         use_container_width=True, hide_index=True)

            fig_sen = px.bar(
                df_val.head(15), x="score_emocional_neto", y="post", orientation="h",
                color="score_emocional_neto", color_continuous_scale="RdYlGn",
                labels={"score_emocional_neto": "Score emocional neto", "post": ""},
            )
            fig_sen.update_layout(height=520, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_sen, use_container_width=True)

    st.divider()
    st.subheader("🚀 Índice de Viralidad — TikTok")
    st.caption(
        "Viralidad = compartidos / views (qué tanto se propaga). TikTok no tiene reacciones "
        "diferenciadas, así que esto mide ALCANCE, no emoción (esa vive en los comentarios)."
    )
    df_vir = calcular_viralidad_tiktok(min_views=100)
    if hay_datos(df_vir, "Aún no hay videos de TikTok con views suficientes."):
        c1, c2, c3 = st.columns(3)
        c1.metric("Viralidad promedio", f"{df_vir['indice_viralidad'].mean()*100:.2f}%")
        c2.metric("Video más viral", f"{df_vir['indice_viralidad'].max()*100:.2f}%")
        c3.metric("Engagement rate prom.", f"{df_vir['engagement_rate'].mean()*100:.2f}%")

        top = df_vir.head(10)[["video", "indice_viralidad", "engagement_rate", "views", "shares", "likes"]].copy()
        top["indice_viralidad"] = (top["indice_viralidad"] * 100).round(2)
        top["engagement_rate"] = (top["engagement_rate"] * 100).round(2)
        st.markdown("**🔥 Top 10 videos más virales**")
        st.dataframe(top.rename(columns={
            "video": "Video", "indice_viralidad": "Viralidad %", "engagement_rate": "Engagement %",
            "views": "Views", "shares": "Shares", "likes": "Likes",
        }), use_container_width=True, hide_index=True)

        fig_vir = px.scatter(
            df_vir, x="views", y="shares", size="likes", color="indice_viralidad",
            color_continuous_scale="Plasma", hover_data=["video"],
            labels={"views": "Views", "shares": "Compartidos", "indice_viralidad": "Viralidad"},
        )
        fig_vir.update_layout(height=480)
        st.plotly_chart(fig_vir, use_container_width=True)

# ═══════════════════════════════════════════
# SECCIÓN 3 — LÍNEA DEL TIEMPO
# ═══════════════════════════════════════════

elif seccion == "📅 Línea del Tiempo":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">📅 Linea del Tiempo</div>
        <div class="seccion-subtitulo">
            ¿Cuando explota la conversacion y que la causo?
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_fb_s, df_tk_s = cargar_series(FACEBOOK_DB_ACTIVA, TIKTOK_DB_ACTIVA)

    if df_fb_s.empty and df_tk_s.empty:
        hay_datos(df_fb_s, "No hay datos de series temporales.")
        st.stop()

    plat_sel = st.radio("Seleccionar plataforma:", ["Ambas","Facebook","TikTok"], horizontal=True)

    if plat_sel == "Facebook":
        df_plot = df_fb_s[['semana','engagement_promedio','es_anomalia','total_posts','score_emocional_promedio']].copy()
        df_plot = df_plot.rename(columns={'engagement_promedio':'engagement','score_emocional_promedio':'score'})
        ylabel = "Engagement promedio"
    elif plat_sel == "TikTok":
        df_plot = df_tk_s[['semana','views_suma','es_anomalia','engagement_rate_promedio']].copy()
        df_plot = df_plot.rename(columns={'views_suma':'engagement','engagement_rate_promedio':'score'})
        df_plot['score'] = df_plot.get('score', 0)
        ylabel = "Views totales"
    else:
        df_fb_m = df_fb_s[['semana','engagement_promedio','es_anomalia']].copy()
        df_fb_m['eng'] = df_fb_m['engagement_promedio']
        df_tk_m = df_tk_s[['semana','views_suma','es_anomalia']].copy()
        df_tk_m['eng'] = df_tk_m['views_suma']
        df_both = pd.merge(
            df_fb_m[['semana','eng']].rename(columns={'eng':'fb'}),
            df_tk_m[['semana','eng','es_anomalia']].rename(columns={'eng':'tk'}),
            on='semana', how='outer'
        ).fillna(0)
        df_both['engagement'] = df_both['fb'] + df_both['tk']
        df_both['score'] = 0
        df_plot = df_both[['semana','engagement','es_anomalia','score']].copy()
        ylabel = "Actividad total"

    fecha_inicio_plot = get_fecha_inicio(periodo)
    df_plot = df_plot[df_plot['semana'] >= fecha_inicio_plot].copy()

    if not df_plot.empty:
        df_plot = df_plot.sort_values('semana')
        df_plot['media_movil'] = df_plot['engagement'].rolling(4, min_periods=1).mean()

        st.markdown(leyenda_grafica([
            {'simbolo': '—', 'color': '#3b82f6',
             'label': 'Actividad semanal',
             'descripcion': 'Total de reacciones y comentarios sumados cada 7 días. Cada punto = una semana completa.'},
            {'simbolo': '····', 'color': '#f97316',
             'label': 'Promedio móvil 4 semanas',
             'descripcion': 'El nivel "normal" de actividad calculado sobre el último mes. Si la línea azul está muy por encima o abajo de esta → semana inusual.'},
            {'simbolo': '●', 'color': '#ef4444',
             'label': 'Anomalía detectada',
             'descripcion': 'Semana donde la actividad fue 2 veces mayor o menor que el promedio histórico. Algo pasó esa semana — busca qué publicaste o qué ocurrió en el municipio.'},
        ]), unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_plot['semana'], y=df_plot['engagement'],
            mode='lines', line=dict(color='#3b82f6', width=2),
            name='Actividad semanal',
            fill='tozeroy', fillcolor='rgba(59,130,246,0.08)',
            hovertemplate='<b>Semana del %{x|%d %b %Y}</b><br>%{y:,.0f}<extra></extra>'
        ))
        fig.add_trace(go.Scatter(
            x=df_plot['semana'], y=df_plot['media_movil'],
            mode='lines', line=dict(color='#f59e0b', width=1.5, dash='dot'),
            name='Promedio 4 semanas',
            hovertemplate='Promedio: %{y:,.0f}<extra></extra>'
        ))
        anom = df_plot[df_plot['es_anomalia'] == True]
        if not anom.empty:
            fig.add_trace(go.Scatter(
                x=anom['semana'], y=anom['engagement'],
                mode='markers',
                marker=dict(color='#ef4444', size=14, symbol='circle', line=dict(color='#fca5a5', width=2)),
                name='Semana inusual',
                hovertemplate='<b>SEMANA INUSUAL</b><br>%{x|%d %b %Y}<br>%{y:,.0f}<extra></extra>'
            ))
        fig.update_layout(
            plot_bgcolor='#111827', paper_bgcolor='#111827',
            font=dict(color='#9ca3af', size=11),
            xaxis=dict(gridcolor='#1f2937', tickformat='%d %b\n%Y', showgrid=True),
            yaxis=dict(gridcolor='#1f2937', showgrid=True, tickformat=',', title=ylabel),
            legend=dict(bgcolor='rgba(17,24,39,0.8)', bordercolor='#1f2937', x=0, y=1),
            margin=dict(l=0, r=0, t=10, b=0), height=350
        )
        st.plotly_chart(fig, use_container_width=True)

    # Anomalias
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Estas son las semanas donde la conversación ciudadana explotó. No significa que fue bueno o malo — significa que algo captó masivamente la atención. Identifica qué pasó esa semana para entender por qué.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Semanas con actividad inusual")
    st.markdown("*Estas semanas tuvieron una actividad significativamente mayor a lo normal — algo ocurrio que movilizo a la ciudadania.*")

    anom_fb = df_fb_s[df_fb_s['es_anomalia']==True].sort_values('semana', ascending=False)
    anom_tk = df_tk_s[df_tk_s['es_anomalia']==True].sort_values('semana', ascending=False)

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown("**Facebook**")
        if anom_fb.empty:
            st.markdown('<div class="card"><p style="color:#6b7280">Sin anomalias detectadas</p></div>', unsafe_allow_html=True)
        else:
            for _, row in anom_fb.head(5).iterrows():
                fecha = formato_fecha_espanol(row['semana'])
                eng = int(row['engagement_promedio'])
                score = row.get('score_emocional_promedio', 0)
                tipo_pico = 'positivo' if score > 0 else 'negativo'
                interp_anom = generar_interpretacion("anomalia", {
                    'fecha': fecha, 'views': eng, 'tipo': tipo_pico
                })
                st.markdown(f"""
                <div class="anomalia-item">
                    <strong style="color:#f87171"> {fecha}</strong><br>
                    <span style="font-size:12px;color:#9ca3af">
                        Engagement: <strong style="color:#60a5fa">{eng:,}</strong>
                    </span>
                    <p style="font-size:12px;color:#d1d5db;margin:6px 0 0 0;line-height:1.5;font-style:italic">{interp_anom}</p>
                </div>
                """, unsafe_allow_html=True)
    with col_a2:
        st.markdown("**TikTok**")
        if anom_tk.empty:
            st.markdown('<div class="card"><p style="color:#6b7280">Sin anomalias detectadas</p></div>', unsafe_allow_html=True)
        else:
            for _, row in anom_tk.head(5).iterrows():
                fecha = formato_fecha_espanol(row['semana'])
                views = int(row['views_suma'])
                rate = float(row.get('engagement_rate_promedio', 0)) * 100
                interp_anom = generar_interpretacion("anomalia", {
                    'fecha': fecha, 'views': views, 'tipo': 'negativo'
                })
                st.markdown(f"""
                <div class="anomalia-item">
                    <strong style="color:#f87171"> {fecha}</strong><br>
                    <span style="font-size:12px;color:#9ca3af">
                        Views: <strong style="color:#60a5fa">{views:,}</strong>
                        &nbsp;·&nbsp; Engagement: {rate:.2f}%
                    </span>
                    <p style="font-size:12px;color:#d1d5db;margin:6px 0 0 0;line-height:1.5;font-style:italic">{interp_anom}</p>
                </div>
                """, unsafe_allow_html=True)

    # Heatmap dia de semana
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Cuándo reacciona más la gente según el día de la semana. Azul oscuro = más actividad. Útil para saber qué días publicar para maximizar el alcance.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### ¿Cuando reacciona mas la gente?")

    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)

    dfs_dias = []
    if not df_fb_raw.empty:
        df_fb_wk = df_fb_raw.copy()
        df_fb_wk['dia'] = df_fb_wk['created_time'].dt.dayofweek
        dfs_dias.append(df_fb_wk[['dia','total_reacciones']].rename(columns={'total_reacciones':'valor'}))
    if not df_tk_raw.empty:
        df_tk_wk = df_tk_raw.copy()
        df_tk_wk['dia'] = df_tk_wk['created_at'].dt.dayofweek
        dfs_dias.append(df_tk_wk[['dia','likes']].rename(columns={'likes':'valor'}))

    if dfs_dias:
        df_dias = pd.concat(dfs_dias).groupby('dia')['valor'].sum().reset_index()
        dias_nombres = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom']
        df_dias['nombre'] = df_dias['dia'].map(lambda x: dias_nombres[x] if x < 7 else '?')
        dia_pico = df_dias.loc[df_dias['valor'].idxmax()]

        fig_dias = go.Figure(go.Bar(
            x=df_dias['nombre'], y=df_dias['valor'],
            marker=dict(color=df_dias['valor'], colorscale=[[0,'#1f2937'],[0.5,'#1d4ed8'],[1,'#60a5fa']]),
            hovertemplate='%{x}: %{y:,} reacciones<extra></extra>'
        ))
        fig_dias.update_layout(
            plot_bgcolor='#111827', paper_bgcolor='#111827',
            font=dict(color='#9ca3af', size=12),
            xaxis=dict(gridcolor='#1f2937'), yaxis=dict(gridcolor='#1f2937', tickformat=','),
            showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=200
        )
        st.plotly_chart(fig_dias, use_container_width=True)
        st.markdown(
            f'<p style="font-size:13px;color:#9ca3af">📌 El dia que mas reacciona '
            f'la gente en promedio: <strong style="color:#f9fafb">{dia_pico["nombre"]}</strong> '
            f'({int(dia_pico["valor"]):,} reacciones totales)</p>',
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════
# SECCIÓN 4 — VOZ CIUDADANA
# ═══════════════════════════════════════════

elif seccion == "💬 Voz Ciudadana":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">💬 Voz Ciudadana</div>
        <div class="seccion-subtitulo">
            Señales de comportamiento colectivo — metodologia Kosinski adaptada
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_comentarios = cargar_comentarios_fb(FACEBOOK_DB_ACTIVA)

    if not hay_datos(df_comentarios, "Aún no hay comentarios procesados."):
        st.stop()

    # Senal 1
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Diferencia entre los likes que la gente da por inercia (apoyo vacío) y los temas donde los comentarios confirman que el apoyo es real (apoyo genuino). Basado en metodología Kosinski 2013: el comportamiento real revela más que las reacciones superficiales.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="senal-card">
        <div class="senal-numero">SEÑAL 01</div>
        <div class="senal-titulo">
            ¿Que temas generan apoyo genuino vs. apoyo vacio?
        </div>
    """, unsafe_allow_html=True)

    df_s1 = safe_query("""
        SELECT pc.categoria_nombre,
               AVG(fe.indice_amor) as amor_promedio,
               AVG(fe.total_reacciones) as reacciones_promedio,
               AVG(fs.pct_positivo) as pct_positivo,
               AVG(fs.pct_negativo) as pct_negativo,
               AVG(fs.score_sentimiento) as score_sent
        FROM fb_engagement fe
        LEFT JOIN post_categorias pc ON fe.post_id = pc.item_id
        LEFT JOIN fb_sentimiento fs ON fe.post_id = fs.post_id
        WHERE pc.categoria_nombre IS NOT NULL
        GROUP BY pc.categoria_nombre
    """, FACEBOOK_DB_ACTIVA)

    score_sent = df_s1['score_sent']
    genuino = df_s1.nlargest(3, 'score_sent')[
        ['categoria_nombre','amor_promedio','pct_positivo','score_sent']
    ].copy()

    vacio = df_s1.nsmallest(3, 'score_sent')[
        ['categoria_nombre','amor_promedio','pct_negativo','score_sent']
    ].copy()

    col_g, col_v = st.columns(2)
    with col_g:
        st.markdown('<p style="color:#22c55e;font-weight:600;font-size:12px;letter-spacing:1px">Temas con menor rechazo (relativo)</p>', unsafe_allow_html=True)
        st.markdown('<p style="color:#6b7280;font-size:11px">Mejor balance comentarios vs. reacciones</p>', unsafe_allow_html=True)
        for _, r in genuino.iterrows():
            nombre = str(r['categoria_nombre']).replace('\n',' ')[:35]
            st.markdown(f'<p style="font-size:13px;color:#d1d5db;padding:4px 0">→ <strong>{nombre}</strong>: {r["pct_positivo"]:.1f}% comentarios positivos</p>', unsafe_allow_html=True)
    with col_v:
        st.markdown('<p style="color:#f59e0b;font-weight:600;font-size:12px;letter-spacing:1px">APOYO VACIO</p>', unsafe_allow_html=True)
        st.markdown('<p style="color:#6b7280;font-size:11px">Reacciones altas pero comentarios criticos</p>', unsafe_allow_html=True)
        for _, r in vacio.iterrows():
            nombre = str(r['categoria_nombre']).replace('\n',' ')[:35]
            st.markdown(f'<p style="font-size:13px;color:#d1d5db;padding:4px 0">→ <strong>{nombre}</strong>: {r["pct_negativo"]:.1f}% comentarios negativos</p>', unsafe_allow_html=True)

    nota = "📌 Todos los temas tienen rechazo predominante. Estos son los menos críticos." if score_sent.max() < 0 else "📌 La gente da 'me gusta' por inercia en eventos pero en comentarios dice lo que realmente piensa."
    st.markdown(f"""
        <p style="font-size:12px;color:#6b7280;margin-top:12px;border-top:1px solid #1f2937;padding-top:10px">
            {nota}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Senal 2
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Intensidad emocional por tema. Alta intensidad positiva = temas que movilizan al ciudadano a favor. Alta intensidad negativa = temas que generan indignación. Baja intensidad = temas que la gente ignora emocionalmente.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="senal-card">
        <div class="senal-numero">SEÑAL 02</div>
        <div class="senal-titulo">
            ¿Que temas generan reaccion emocional fuerte?
        </div>
    """, unsafe_allow_html=True)

    if not df_s1.empty:
        df_s1_sort = df_s1.sort_values('amor_promedio', ascending=False)
        alta_pos = df_s1_sort[df_s1_sort['score_sent'] > 0.15].head(2)
        alta_neg = df_s1_sort[df_s1_sort['score_sent'] < 0].head(2)
        baja = df_s1_sort[
            (df_s1_sort['amor_promedio'] < df_s1_sort['amor_promedio'].median()) &
            (df_s1_sort['score_sent'].abs() < 0.1)
        ].head(2)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<p style="color:#22c55e;font-weight:600;font-size:11px;letter-spacing:1px">ALTA INTENSIDAD POSITIVA</p>', unsafe_allow_html=True)
            if alta_pos.empty:
                st.markdown('<p style="font-size:12px;color:#6b7280">Sin datos positivos significativos</p>', unsafe_allow_html=True)
            for _, r in alta_pos.iterrows():
                nombre = str(r['categoria_nombre']).replace('\n',' ')[:30]
                st.markdown(f'<p style="font-size:13px;color:#d1d5db;padding:4px 0">🏆 <strong>{nombre}</strong><br><span style="font-size:11px;color:#6b7280">La ciudadania comparte espontaneamente</span></p>', unsafe_allow_html=True)
        with col2:
            st.markdown('<p style="color:#ef4444;font-weight:600;font-size:11px;letter-spacing:1px">ALTA INTENSIDAD NEGATIVA</p>', unsafe_allow_html=True)
            if alta_neg.empty:
                st.markdown('<p style="font-size:12px;color:#6b7280">Sin datos negativos significativos</p>', unsafe_allow_html=True)
            for _, r in alta_neg.iterrows():
                nombre = str(r['categoria_nombre']).replace('\n',' ')[:30]
                st.markdown(f'<p style="font-size:13px;color:#d1d5db;padding:4px 0">🚧 <strong>{nombre}</strong><br><span style="font-size:11px;color:#6b7280">Comentarios de denuncia y queja</span></p>', unsafe_allow_html=True)
        with col3:
            st.markdown('<p style="color:#6b7280;font-weight:600;font-size:11px;letter-spacing:1px">BAJA INTENSIDAD</p>', unsafe_allow_html=True)
            if baja.empty:
                st.markdown('<p style="font-size:12px;color:#6b7280">Sin datos de baja intensidad</p>', unsafe_allow_html=True)
            for _, r in baja.iterrows():
                nombre = str(r['categoria_nombre']).replace('\n',' ')[:30]
                st.markdown(f'<p style="font-size:13px;color:#d1d5db;padding:4px 0">📋 <strong>{nombre}</strong><br><span style="font-size:11px;color:#6b7280">No conecta emocionalmente</span></p>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#6b7280;padding:16px">Sin datos suficientes para analizar intensidad emocional</p>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Senal 3
    palabras_electorales = ['eleccion','voto','reeleccion','campana','boto','votar','elecciones','proximas','candidato','partido']
    df_electoral = df_comentarios[
        df_comentarios['message'].str.lower().str.contains('|'.join(palabras_electorales), na=False)
    ]

    pct_neg_electoral = 0
    if len(df_electoral) > 0 and 'score_sentimiento' in df_electoral.columns:
        pct_neg_electoral = (df_electoral['score_sentimiento'] < -0.1).mean() * 100

    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Comentarios donde la ciudadanía interpreta tus acciones en clave electoral. Cuántos son, qué tono tienen, y si están creciendo. Este patrón predice percepción electoral antes de que aparezca en encuestas.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="senal-card">
        <div class="senal-numero">SEÑAL 03</div>
        <div class="senal-titulo">
            Narrativa electoral activa en tiempo real
        </div>
        <p style="font-size:13px;color:#9ca3af;margin-bottom:16px">
            Comentarios donde la ciudadania lee las acciones en clave electoral:
            <strong style="color:#f9fafb">{len(df_electoral)}</strong> comentarios detectados
            &nbsp;·&nbsp;
            <strong style="color:#ef4444">{pct_neg_electoral:.0f}%</strong> negativos
        </p>
    """, unsafe_allow_html=True)

    if not df_electoral.empty:
        for _, row in df_electoral.head(4).iterrows():
            msg = str(row['message'])[:150]
            score = row.get('score_sentimiento', 0)
            color = "#ef4444" if score < -0.1 else "#22c55e"
            st.markdown(f'<div class="comentario-rep" style="border-left-color:{color}">"{msg}"</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Patrones de comportamiento
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Cada bloque representa un patrón compartido por múltiples ciudadanos que expresaron lo mismo con palabras distintas. El número grande es cuántas personas expresaron ese patrón. La flecha indica si ese patrón está creciendo o estable.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Lo que dice la ciudadania — cada comentario es un patron")
    st.markdown("*Cada comentario mostrado aqui representa un patron compartido por multiples ciudadanos que expresaron lo mismo con palabras distintas.*")

    patrones_rechazo, patrones_respaldo = detectar_patrones_comentarios(df_comentarios)

    col_rec, col_res = st.columns(2)

    with col_rec:
        st.markdown('<p style="color:#ef4444;font-weight:700;font-size:13px;letter-spacing:1px;margin-bottom:12px">PATRONES DE RECHAZO</p>', unsafe_allow_html=True)
        if not patrones_rechazo:
            st.markdown('<p style="color:#6b7280;font-size:12px">Sin patrones de rechazo detectados</p>', unsafe_allow_html=True)
        for p in patrones_rechazo:
            otros_html = ''.join([f'<p class="comentario-lista">• "{c[:80]}..."</p>' for c in p['otros']])
            tend_class = "tendencia-subiendo" if "Creciendo" in p['tendencia'] else "tendencia-estable"
            st.markdown(f"""
            <div class="patron-rechazo">
                <div class="patron-titulo" style="color:#f87171">{p['nombre']}</div>
                <div class="patron-meta">
                    <span class="patron-count" style="color:#ef4444;font-size:22px">{p['count']}</span>
                    personas expresaron esto &nbsp;·&nbsp;
                    <span>{p['tendencia']}</span>
                    <br><span style="font-size:11px">Tema: {p['categoria']}</span>
                </div>
                <div class="comentario-rep">"{p['representativo'][:140]}"</div>
                {otros_html}
                <p style="font-size:12px;color:#fca5a5;margin-top:10px;font-style:italic;border-top:1px solid #7f1d1d;padding-top:8px">{generar_interpretacion("patron_rechazo", {'nombre': p['nombre'], 'count': p['count'], 'tendencia': p['tendencia']})}</p>
            </div>
            """, unsafe_allow_html=True)

    with col_res:
        st.markdown('<p style="color:#22c55e;font-weight:700;font-size:13px;letter-spacing:1px;margin-bottom:12px">PATRONES DE RESPALDO</p>', unsafe_allow_html=True)
        if not patrones_respaldo:
            st.markdown('<p style="color:#6b7280;font-size:12px">Sin patrones de respaldo detectados</p>', unsafe_allow_html=True)
        for p in patrones_respaldo:
            otros_html = ''.join([f'<p class="comentario-lista">• "{c[:80]}..."</p>' for c in p['otros']])
            tend_class = "tendencia-subiendo" if "Creciendo" in p['tendencia'] else "tendencia-estable"
            st.markdown(f"""
            <div class="patron-respaldo">
                <div class="patron-titulo" style="color:#4ade80">{p['nombre']}</div>
                <div class="patron-meta">
                    <span class="patron-count" style="color:#22c55e;font-size:22px">{p['count']}</span>
                    personas expresaron esto &nbsp;·&nbsp;
                    <span>{p['tendencia']}</span>
                    <br><span style="font-size:11px">Tema: {p['categoria']}</span>
                </div>
                <div class="comentario-rep">"{p['representativo'][:140]}"</div>
                {otros_html}
                <p style="font-size:12px;color:#86efac;margin-top:10px;font-style:italic;border-top:1px solid #14532d;padding-top:8px">{generar_interpretacion("patron_respaldo", {'nombre': p['nombre'], 'count': p['count'], 'tendencia': p['tendencia']})}</p>
            </div>
            """, unsafe_allow_html=True)

    # Sentimiento por tema
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Para cada tema, cómo se distribuye la opinión ciudadana entre positivo (verde), neutral (gris) y negativo (rojo). Una barra mayormente verde = tema bien recibido. Mucho rojo = tema que genera rechazo activo.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### ¿Como reacciona la gente segun el tema?")
    df_sent_tema = safe_query("""
        SELECT pc.categoria_nombre,
               AVG(fs.pct_positivo) as positivo,
               AVG(fs.pct_negativo) as negativo,
               AVG(100 - fs.pct_positivo - fs.pct_negativo) as neutral
        FROM fb_sentimiento fs
        LEFT JOIN post_categorias pc ON fs.post_id = pc.item_id
        WHERE pc.categoria_nombre IS NOT NULL AND pc.categoria_nombre != ''
        GROUP BY pc.categoria_nombre
        ORDER BY positivo DESC
    """, FACEBOOK_DB_ACTIVA)
    df_sent_tema['categoria_nombre'] = df_sent_tema['categoria_nombre'].str.replace('\n',' ')

    if not df_sent_tema.empty:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name='Positivo', y=df_sent_tema['categoria_nombre'], x=df_sent_tema['positivo'],
            orientation='h', marker_color='#16a34a',
            text=df_sent_tema['positivo'].apply(lambda x: f'{x:.1f}%'),
            textposition='inside', textfont=dict(size=10, color='white')
        ))
        fig_bar.add_trace(go.Bar(
            name='Neutral', y=df_sent_tema['categoria_nombre'], x=df_sent_tema['neutral'],
            orientation='h', marker_color='#374151',
            text=df_sent_tema['neutral'].apply(lambda x: f'{x:.1f}%'),
            textposition='inside', textfont=dict(size=10, color='#9ca3af')
        ))
        fig_bar.add_trace(go.Bar(
            name='Negativo', y=df_sent_tema['categoria_nombre'], x=df_sent_tema['negativo'],
            orientation='h', marker_color='#dc2626',
            text=df_sent_tema['negativo'].apply(lambda x: f'{x:.1f}%'),
            textposition='inside', textfont=dict(size=10, color='white')
        ))
        fig_bar.update_layout(
            barmode='stack',
            plot_bgcolor='#111827', paper_bgcolor='#111827',
            font=dict(color='#9ca3af', size=11),
            xaxis=dict(gridcolor='#1f2937', ticksuffix='%', range=[0,100]),
            yaxis=dict(gridcolor='#1f2937'),
            legend=dict(bgcolor='rgba(17,24,39,0.8)', bordercolor='#1f2937', orientation='h', y=1.05),
            margin=dict(l=0, r=0, t=30, b=0), height=320
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()
    st.subheader("☁️ Nube de palabras — comentarios negativos")
    st.caption("Términos más frecuentes en comentarios clasificados como negativos / muy negativos.")
    df_neg = cargar_comentarios_negativos()
    if hay_datos(df_neg, "Aún no hay comentarios negativos analizados. (Corré el re-análisis de sentimiento.)"):
        import re
        import matplotlib.pyplot as plt
        from wordcloud import WordCloud, STOPWORDS
        stop_es = set(STOPWORDS) | {
            "que", "de", "la", "el", "los", "las", "un", "una", "y", "o", "a", "en", "es", "se",
            "no", "con", "por", "para", "su", "sus", "lo", "le", "les", "mas", "más", "como",
            "pero", "ya", "si", "sí", "del", "al", "me", "mi", "tu", "te", "yo", "muy", "esta",
            "este", "eso", "esa", "ese", "son", "fue", "han", "hay", "ha", "va", "van", "ser",
            "porque", "cuando", "donde", "quien", "cual", "nos", "sino", "tan", "todo", "toda",
            "todos", "todas", "the", "https", "http", "com", "www", "ni", "ese", "esos", "esas",
        }
        texto = " ".join(df_neg["message"].astype(str).tolist()).lower()
        texto = re.sub(r"http\S+|www\S+", " ", texto)
        texto = re.sub(r"@\w+", " ", texto)
        try:
            wc = WordCloud(width=1000, height=500, background_color="white",
                           stopwords=stop_es, colormap="Reds", collocations=False).generate(texto)
            fig_wc, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig_wc)
            st.caption(f"Basado en {len(df_neg):,} comentarios negativos.")
        except ValueError:
            st.info("No hay suficientes palabras para generar la nube.")

# ═══════════════════════════════════════════
# SECCIÓN 5 — MICROSEGMENTACIÓN
# ═══════════════════════════════════════════

elif seccion == "🔬 Microsegmentación":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">🔬 Microsegmentacion de Contenido</div>
        <div class="seccion-subtitulo">
            ¿Que tipo de contenido funciona, cual no, y que patron emocional genera cada uno?
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos en este periodo para Microsegmentación.")
        st.stop()

    st.markdown("### Patrones de contenido detectados")
    st.markdown("*Cada fila es un tipo de contenido agrupado automaticamente por similitud semantica y patron de reaccion.*")

    dfs_micro = []
    if not df_fb.empty and 'categoria_nombre' in df_fb.columns:
        fb_micro = df_fb.groupby('categoria_nombre').agg(
            posts=('post_id','count'),
            eng_prom=('engagement_total','mean'),
            reac_prom=('total_reacciones','mean'),
            amor=('indice_amor','mean'),
            humor=('indice_humor','mean'),
            tristeza=('indice_tristeza','mean')
        ).reset_index()
        fb_micro['plataforma'] = 'FB'
        dfs_micro.append(fb_micro)

    if not df_tk.empty and 'categoria_nombre' in df_tk.columns:
        tk_micro = df_tk.groupby('categoria_nombre').agg(
            posts=('id','count'),
            eng_prom=('engagement_total','mean'),
            reac_prom=('likes','mean'),
            viral_prom=('indice_viralidad','mean')
        ).reset_index()
        tk_micro['amor'] = 0
        tk_micro['humor'] = 0
        tk_micro['tristeza'] = 0
        tk_micro['plataforma'] = 'TK'
        dfs_micro.append(tk_micro)

    if dfs_micro:
        df_micro = pd.concat(dfs_micro).groupby('categoria_nombre').agg(
            posts=('posts','sum'),
            eng_prom=('eng_prom','mean'),
            amor=('amor','mean'),
            humor=('humor','mean'),
            tristeza=('tristeza','mean')
        ).reset_index().sort_values('eng_prom', ascending=False)

        if not df_tk.empty and 'categoria_nombre' in df_tk.columns:
            tk_viral = df_tk.groupby('categoria_nombre')['indice_viralidad'].mean().reset_index().rename(columns={'indice_viralidad':'viral'})
            df_micro = df_micro.merge(tk_viral, on='categoria_nombre', how='left')
        else:
            df_micro['viral'] = 0

        df_micro['categoria_nombre'] = df_micro['categoria_nombre'].str.replace('\n',' ')
        df_micro['viral'] = df_micro['viral'].fillna(0)

        st.markdown("""
        <div style="background:#0d1117;border-left:3px solid #374151;
             padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
            <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
                  color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
            <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
               line-height:1.5">Cada fila es un tipo de contenido agrupado automáticamente por similitud. ENG. PROM. es el promedio de interacciones por post. VIRALIDAD es cuánto comparte la gente ese tipo de contenido vs cuánto lo ve. PATRÓN indica si ese tipo de contenido tiene alto, medio o bajo impacto comparado con el resto.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="display:grid;grid-template-columns:2fr 0.7fr 1fr 1fr 1fr 1.2fr;
             padding:10px 16px;border-bottom:2px solid #374151;
             font-size:11px;font-weight:600;letter-spacing:1px;
             color:#6b7280;text-transform:uppercase;">
            <span>TIPO DE CONTENIDO</span>
            <span style="text-align:center">POSTS</span>
            <span style="text-align:right">ENG. PROM.</span>
            <span style="text-align:right">VIRALIDAD</span>
            <span style="text-align:center">EMOCION</span>
            <span style="text-align:center">PATRON</span>
        </div>
        """, unsafe_allow_html=True)

        for _, row in df_micro.iterrows():
            nombre = str(row['categoria_nombre'])[:40]
            posts = int(row['posts'])
            eng_val = float(row['eng_prom'])
            eng = f"{int(eng_val):,}"
            viral = f"{float(row['viral'])*100:.1f}%"

            amor = float(row['amor']) if not pd.isna(row['amor']) else 0
            humor = float(row['humor']) if not pd.isna(row['humor']) else 0
            tristeza = float(row['tristeza']) if not pd.isna(row['tristeza']) else 0

            emo_max = max([(amor,'Amor'),(humor,'Humor'),(tristeza,'Tristeza')], key=lambda x: x[0])[1]

            all_med = df_micro['eng_prom'].median()
            if eng_val > all_med * 1.5:
                patron_str = 'ALTO IMPACTO'
                patron = '<span style="color:#22c55e;font-weight:600">ALTO IMPACTO</span>'
            elif eng_val > all_med:
                patron_str = 'MODERADO'
                patron = '<span style="color:#f59e0b;font-weight:600">MODERADO</span>'
            else:
                patron_str = 'BAJO IMPACTO'
                patron = '<span style="color:#6b7280;font-weight:600">BAJO IMPACTO</span>'

            interp_micro = generar_interpretacion("microsegmentacion", {
                'tipo': nombre, 'engagement': eng_val, 'patron': patron_str
            })

            st.markdown(f"""
            <div style="display:grid;grid-template-columns:2fr 0.7fr 1fr 1fr 1fr 1.2fr;
                 padding:14px 16px;border-bottom:1px solid #1f2937;
                 font-size:13px;align-items:center;">
                <span style="font-weight:600;color:#f9fafb;display:block;line-height:1.3">{nombre}<br><span style="font-size:10px;color:#6b7280;font-weight:400">{interp_micro[:80]}...</span></span>
                <span style="text-align:center;color:#9ca3af">{posts}</span>
                <span style="text-align:right;font-family:'Courier New';color:#60a5fa;font-weight:700">{eng}</span>
                <span style="text-align:right;color:#9ca3af">{viral}</span>
                <span style="text-align:center">{emo_max}</span>
                <span style="text-align:center">{patron}</span>
            </div>
            """, unsafe_allow_html=True)

    # Top 5
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">Los 5 posts y videos más impactantes del período. El número grande a la derecha son las interacciones totales. Las cifras pequeñas abajo son el desglose por tipo de reacción.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Los 5 contenidos mas impactantes")

    dfs_top5 = []
    if not df_fb.empty:
        fb5 = df_fb.nlargest(10, 'engagement_total').copy()
        fb5['plataforma'] = 'Facebook'
        fb5['fecha'] = fb5['created_time']
        fb5['texto'] = fb5['message']
        fb5['total'] = fb5['engagement_total']
        fb5['reac'] = fb5['total_reacciones']
        dfs_top5.append(fb5)
    if not df_tk.empty:
        tk5 = df_tk.nlargest(10, 'engagement_total').copy()
        tk5['plataforma'] = 'TikTok'
        tk5['fecha'] = tk5['created_at']
        tk5['texto'] = tk5['description']
        tk5['total'] = tk5['engagement_total']
        tk5['reac'] = tk5['likes']
        dfs_top5.append(tk5)

    if dfs_top5:
        df_top5 = pd.concat(dfs_top5).nlargest(5, 'total')
        for i, (_, row) in enumerate(df_top5.iterrows(), 1):
            plat = row['plataforma']
            plat_color = "#1877f2" if plat == "Facebook" else "#ff0050"
            fecha = formato_fecha_espanol(row['fecha'])
            texto = str(row['texto'])[:120]
            cat = str(row.get('categoria_nombre','—'))[:35].replace('\n',' ')
            total = int(row['total'])

            amor_v = float(row.get('indice_amor',0) or 0)
            humor_v = float(row.get('indice_humor',0) or 0)
            trist_v = float(row.get('indice_tristeza',0) or 0)
            reac_v = float(row.get('reac',0) or 0)

            amor_n = int(amor_v * reac_v) if pd.notna(amor_v) and pd.notna(reac_v) else 0
            humor_n = int(humor_v * reac_v) if pd.notna(humor_v) and pd.notna(reac_v) else 0
            trist_n = int(trist_v * reac_v) if pd.notna(trist_v) and pd.notna(reac_v) else 0

            st.markdown(f"""
            <div class="card" style="border-left:4px solid #3b82f6">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;align-items:center">
                    <span style="font-size:22px;font-weight:800;color:#1f2937;font-family:'Courier New'">#{i}</span>
                    <div style="display:flex;gap:8px">
                        <span style="background:{plat_color};color:white;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700">{plat.upper()}</span>
                        <span style="background:#1f2937;color:#9ca3af;padding:2px 8px;border-radius:4px;font-size:10px">{cat}</span>
                    </div>
                </div>
                <p style="font-size:11px;color:#6b7280;margin:4px 0">{fecha}</p>
                <p style="font-size:14px;color:#e2e8f0;margin:8px 0;line-height:1.5">{texto}...</p>
                <div style="display:flex;justify-content:space-between;margin-top:10px;align-items:center">
                    <span style="font-size:12px;color:#9ca3af">
                        Amor {amor_n:,} &nbsp;·&nbsp; Humor {humor_n:,} &nbsp;·&nbsp; Tristeza {trist_n:,}
                    </span>
                    <span style="font-size:20px;font-weight:700;color:#60a5fa;font-family:'Courier New'">{total:,}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Día de semana
    st.markdown("### ¿Cuándo reacciona más la gente?")

    dfs_dias = []
    if not df_fb.empty:
        df_fb['dia'] = df_fb['created_time'].dt.dayofweek
        dfs_dias.append(df_fb[['dia','total_reacciones']].rename(
            columns={'total_reacciones':'valor'}
        ))
    if not df_tk.empty:
        df_tk['dia'] = df_tk['created_at'].dt.dayofweek
        dfs_dias.append(df_tk[['dia','likes']].rename(
            columns={'likes':'valor'}
        ))

    if dfs_dias:
        df_dias = pd.concat(dfs_dias).groupby('dia')['valor'].sum().reset_index()
        dias_nombres = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']
        df_dias['nombre'] = df_dias['dia'].map(
            lambda x: dias_nombres[x] if x < 7 else '?'
        )
        dia_pico = df_dias.loc[df_dias['valor'].idxmax()]

        fig_dias = go.Figure(go.Bar(
            x=df_dias['nombre'],
            y=df_dias['valor'],
            marker=dict(
                color=df_dias['valor'],
                colorscale=[[0,'#1f2937'],[0.5,'#1d4ed8'],[1,'#60a5fa']]
            ),
            hovertemplate='%{x}: %{y:,} reacciones<extra></extra>'
        ))
        fig_dias.update_layout(
            plot_bgcolor='#111827',
            paper_bgcolor='#111827',
            font=dict(color='#9ca3af', size=12),
            xaxis=dict(gridcolor='#1f2937'),
            yaxis=dict(gridcolor='#1f2937', tickformat=','),
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0),
            height=200
        )
        st.plotly_chart(fig_dias, use_container_width=True)
        st.markdown(
            f'<p style="font-size:13px;color:#9ca3af">'
            f'📌 El día que más reacciona la gente en promedio: '
            f'<strong style="color:#f9fafb">{dia_pico["nombre"]}</strong> '
            f'({int(dia_pico["valor"]):,} reacciones totales)</p>',
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════
# SECCIÓN 6 — CONTEXTO EXTERNO
# ═══════════════════════════════════════════

elif seccion == "🌐 Contexto Externo":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">🌐 Contexto Externo</div>
        <div class="seccion-subtitulo">
            ¿Que dicen de ti fuera de tus redes oficiales?
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#1c1407;border:1px solid #ca8a04;border-left:5px solid #eab308;border-radius:6px;padding:12px 16px;margin-bottom:20px">
        <span style="color:#fbbf24;font-size:12px;font-weight:600">DATOS SIMULADOS</span>
        <span style="color:#9ca3af;font-size:12px"> &nbsp;— Esta seccion se activara automaticamente cuando lleguen las URLs de paginas externas reales a monitorear.</span>
    </div>
    """, unsafe_allow_html=True)

    df_ext = cargar_externos(EXTERNOS_DB_ACTIVA)

    if df_ext.empty:
        st.markdown('<div class="card"><p style="color:#6b7280;text-align:center">Sin datos externos disponibles</p></div>', unsafe_allow_html=True)
    else:
        n_fuentes = df_ext['page_name'].nunique()
        n_menciones = len(df_ext)
        score_ext = df_ext['score_sentimiento'].mean() if 'score_sentimiento' in df_ext.columns else 0
        n_neg = int((df_ext['score_sentimiento'] < -0.2).sum()) if 'score_sentimiento' in df_ext.columns else 0
        fuente_top = df_ext['page_name'].value_counts().idxmax() if not df_ext.empty else '—'

        ctx = generar_interpretacion("contexto_externo", {
            'negativas': n_neg, 'total': n_menciones, 'fuente_top': fuente_top
        })
        st.markdown(f"""
        <div style="background:#111827;border-left:4px solid #eab308;padding:16px 20px;border-radius:4px;margin-bottom:24px">
            <p style="font-size:11px;color:#eab308;margin:0 0 6px 0;font-weight:600;letter-spacing:1px;text-transform:uppercase">🔍 LO QUE DICEN FUERA DE TUS REDES</p>
            <p style="font-size:14px;color:#e2e8f0;margin:0;line-height:1.6">{ctx}</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="card"><div class="card-title">Fuentes monitoreadas</div><div class="card-value">{n_fuentes}</div><div class="card-sub">paginas externas</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="card"><div class="card-title">Menciones externas</div><div class="card-value">{n_menciones}</div><div class="card-sub">publicaciones sobre el alcalde</div></div>""", unsafe_allow_html=True)
        with col3:
            tono_ext = "POSITIVO" if score_ext > 0.1 else "MIXTO" if score_ext > -0.1 else "CRITICO"
            color_ext = "#22c55e" if score_ext > 0.1 else "#eab308" if score_ext > -0.1 else "#ef4444"
            st.markdown(f"""
            <div class="card"><div class="card-title">Tono externo</div><div class="card-value" style="color:{color_ext};font-size:22px">{tono_ext}</div><div class="card-sub">percepcion fuera de tus redes</div></div>""", unsafe_allow_html=True)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown("**¿Quien habla de ti?**")
            fuentes = df_ext.groupby('page_name').size().reset_index(name='menciones').sort_values('menciones', ascending=True)
            fig_f = go.Figure(go.Bar(
                x=fuentes['menciones'], y=fuentes['page_name'], orientation='h',
                marker_color='#3b82f6', hovertemplate='%{y}: %{x} menciones<extra></extra>'
            ))
            fig_f.update_layout(plot_bgcolor='#111827', paper_bgcolor='#111827', font=dict(color='#9ca3af',size=10), xaxis=dict(gridcolor='#1f2937'), yaxis=dict(gridcolor='#1f2937'), margin=dict(l=0,r=0,t=10,b=0), height=300)
            st.plotly_chart(fig_f, use_container_width=True)
        with col_b2:
            st.markdown("**¿Como hablan de ti?**")
            if 'score_sentimiento' in df_ext.columns:
                pos = (df_ext['score_sentimiento'] > 0.2).sum()
                neg = (df_ext['score_sentimiento'] < -0.2).sum()
                neu = len(df_ext) - pos - neg
                fig_dona = go.Figure(go.Pie(labels=['Positivo','Negativo','Neutral'], values=[pos, neg, neu], hole=0.6, marker=dict(colors=['#16a34a','#dc2626','#374151'])))
                fig_dona.update_layout(plot_bgcolor='#111827', paper_bgcolor='#111827', font=dict(color='#9ca3af'), showlegend=True, legend=dict(bgcolor='rgba(0,0,0,0)'), margin=dict(l=0,r=0,t=10,b=0), height=300)
                st.plotly_chart(fig_dona, use_container_width=True)

        st.markdown("""
        <div style="background:#0d1117;border-left:3px solid #374151;
             padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
            <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
                  color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
            <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
               line-height:1.5">Publicaciones de fuentes externas que hablan del alcalde con tono negativo. El número es el pulso — más negativo significa mayor rechazo en esa publicación externa.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### Alertas — menciones mas criticas")
        if 'score_sentimiento' in df_ext.columns:
            df_criticas = df_ext.nsmallest(10, 'score_sentimiento')[['created_time','page_name','message','score_sentimiento','comentario_mas_negativo']]
            for _, row in df_criticas.iterrows():
                fecha = formato_fecha_espanol(row['created_time'])
                fuente = str(row['page_name'])
                msg = str(row['message'])[:100]
                score = float(row['score_sentimiento'])
                coment = str(row.get('comentario_mas_negativo',''))[:80]
                st.markdown(f"""
                <div class="patron-rechazo">
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                        <span style="font-size:11px;color:#6b7280">{fecha}</span>
                        <span style="font-size:11px;color:#f87171;font-weight:600">{fuente}</span>
                    </div>
                    <p style="font-size:13px;color:#d1d5db;margin:4px 0">{msg}...</p>
                    <p style="font-size:11px;color:#9ca3af;margin-top:6px">Pulso: <strong style="color:#ef4444">{score:.2f}</strong> &nbsp;·&nbsp; Comentario: "{coment}"</p>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📈 Correlación: picos de engagement ↔ noticias externas")
    st.warning("⚠️ La coincidencia temporal NO implica causalidad (ver Notas Metodológicas).")
    corr = calcular_correlacion_noticias_picos(z_umbral=1.0, ventana_dias=3)
    if not corr:
        st.info("📭 No hay datos de FB suficientes para detectar picos.")
    else:
        serie = corr["serie"]
        fig_c = px.line(serie, x="semana", y="engagement", markers=True,
                        labels={"semana": "Semana", "engagement": "Engagement semanal"})
        picos = serie[serie["es_pico"]]
        if not picos.empty:
            fig_c.add_scatter(x=picos["semana"], y=picos["engagement"], mode="markers",
                              marker=dict(size=13, color="red", symbol="star"), name="Pico")
        fig_c.update_layout(height=420)
        st.plotly_chart(fig_c, use_container_width=True)
        st.metric("Semanas con pico de engagement", corr["n_picos"])

        coinc = corr["coincidencias"]
        st.markdown("**Noticias externas que coinciden con semanas de pico**")
        if hay_datos(coinc, "No se encontraron noticias externas en las semanas de pico."):
            st.dataframe(coinc.rename(columns={
                "semana_pico": "Semana pico", "engagement": "Engagement", "z": "z",
                "fuente": "Fuente", "noticia": "Titular / Texto", "fecha_noticia": "Fecha noticia",
            }), use_container_width=True, hide_index=True)

elif seccion == "🤝 Confianza Institucional":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">🤝 Confianza Institucional</div>
        <div class="seccion-subtitulo">
            ¿La ciudadanía confía en el alcalde como persona e institución?
            Basado en Trust Analytics — Budzynska 2025
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:20px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;line-height:1.5">
            Esta sección mide algo diferente al sentimiento general.
            No es si la gente está contenta o enojada con un servicio —
            es si la ciudadanía confía en el alcalde como persona:
            si lo percibe honesto, competente, presente y justo.
            Estas son las 4 dimensiones que determinan si alguien
            merece reelección según la ciudadanía.
        </p>
    </div>
    """, unsafe_allow_html=True)

    resultados, score_global, dim_riesgo = calcular_confianza_institucional()

    if score_global > 0.3:
        color_conf = "#22c55e"
        texto_conf = "CONFIANZA ALTA"
        desc_conf = "La ciudadanía tiene una percepción favorable del alcalde como persona"
    elif score_global > 0:
        color_conf = "#eab308"
        texto_conf = "CONFIANZA MODERADA"
        desc_conf = "Hay señales mixtas — algunas dimensiones están en riesgo"
    else:
        color_conf = "#ef4444"
        texto_conf = "CONFIANZA EROSIONADA"
        desc_conf = "La ciudadanía cuestiona el carácter del alcalde en múltiples dimensiones"

    st.markdown(f"""
    <div class="card" style="border-left:5px solid {color_conf};
         text-align:center;padding:24px">
        <div style="font-size:28px;font-weight:800;color:{color_conf};
             font-family:'Courier New';letter-spacing:2px">
            {texto_conf}
        </div>
        <div style="font-size:13px;color:#9ca3af;margin-top:8px">
            {desc_conf}
        </div>
        <div style="font-size:13px;color:#6b7280;margin-top:4px">
            Dimensión más en riesgo:
            <strong style="color:#ef4444">
                {dim_riesgo[0].upper()}
            </strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Las 4 dimensiones de confianza")

    nombres = {
        'honestidad': ('Honestidad',
                      '¿La ciudadanía percibe al alcalde como honesto?'),
        'competencia': ('Competencia',
                       '¿Lo perciben como capaz de hacer el trabajo?'),
        'presencia': ('Presencia territorial',
                     '¿Siente la gente que el alcalde está cerca?'),
        'integridad': ('Integridad / Equidad',
                      '¿Perciben que actúa igual para todos?')
    }

    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2]

    for i, (dim, datos) in enumerate(resultados.items()):
        nombre, descripcion = nombres[dim]
        trust = datos['trust']
        distrust = datos['distrust']
        score = datos['score']
        total = trust + distrust

        pct_trust = (trust / total * 100) if total > 0 else 50
        pct_distrust = (distrust / total * 100) if total > 0 else 50

        if score > 0.3:
            color_d = "#22c55e"
            estado = "✅ CONFIABLE"
        elif score > 0:
            color_d = "#eab308"
            estado = "⚠️ EN RIESGO"
        else:
            color_d = "#ef4444"
            estado = "🔴 EROSIONADA"

        barra_trust = int(pct_trust)
        barra_distrust = int(pct_distrust)

        comentarios_html = ''
        for c in datos['comentarios_distrust'][:2]:
            comentarios_html += f'<p class="comentario-lista">• "{c[:80]}"</p>'

        with cols[i]:
            st.markdown(f"""
            <div class="card" style="border-top:3px solid {color_d}">
                <div style="display:flex;justify-content:space-between;
                     align-items:center;margin-bottom:6px">
                    <span style="font-weight:700;font-size:14px;
                          color:#f9fafb">{nombre}</span>
                    <span style="font-size:11px;font-weight:600;
                          color:{color_d}">{estado}</span>
                </div>
                <p style="font-size:11px;color:#6b7280;margin-bottom:12px">
                    {descripcion}
                </p>
                <div style="display:flex;margin-bottom:8px;
                     border-radius:3px;overflow:hidden;height:8px">
                    <div style="width:{barra_trust}%;background:#16a34a"></div>
                    <div style="width:{barra_distrust}%;background:#dc2626"></div>
                </div>
                <div style="display:flex;justify-content:space-between;
                     font-size:11px;margin-bottom:12px">
                    <span style="color:#22c55e">
                        ✓ {trust} menciones de confianza
                    </span>
                    <span style="color:#ef4444">
                        ✗ {distrust} menciones de desconfianza
                    </span>
                </div>
                {comentarios_html}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### Radar de confianza institucional")
    st.markdown(leyenda_grafica([
        {'simbolo': '◆', 'color': '#3b82f6',
         'label': 'Confianza actual',
         'descripcion': 'Qué tan lleno está cada eje según lo que dice la ciudadanía. Más lleno = más confianza en esa dimensión.'},
        {'simbolo': '◇', 'color': '#4b5563',
         'label': 'Referencia neutral',
         'descripcion': 'El punto de equilibrio. Si la forma azul está por dentro de este hexágono, hay déficit de confianza en esa dimensión.'},
        {'simbolo': '■', 'color': '#22c55e',
         'label': 'Eje verde (confiable)',
         'descripcion': 'Dimensión donde la ciudadanía expresa más confianza que desconfianza.'},
        {'simbolo': '■', 'color': '#ef4444',
         'label': 'Eje rojo (en riesgo)',
         'descripcion': 'Dimensión donde las menciones de desconfianza superan a las de confianza.'},
    ]), unsafe_allow_html=True)

    categorias = [nombres[d][0] for d in resultados.keys()]
    valores = [max(0, (v['score'] + 1) / 2) for v in resultados.values()]
    valores_norm = [v * 100 for v in valores]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=valores_norm + [valores_norm[0]],
        theta=categorias + [categorias[0]],
        fill='toself',
        fillcolor='rgba(59,130,246,0.15)',
        line=dict(color='#3b82f6', width=2),
        name='Confianza actual'
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=[50,50,50,50,50],
        theta=categorias + [categorias[0]],
        mode='lines',
        line=dict(color='#374151', width=1, dash='dot'),
        name='Referencia neutral'
    ))
    fig_radar.update_layout(
        polar=dict(
            bgcolor='#111827',
            radialaxis=dict(
                visible=True,
                range=[0,100],
                gridcolor='#1f2937',
                tickfont=dict(color='#6b7280', size=9),
                ticksuffix='%'
            ),
            angularaxis=dict(
                gridcolor='#1f2937',
                tickfont=dict(color='#9ca3af', size=11)
            )
        ),
        paper_bgcolor='#111827',
        font=dict(color='#9ca3af'),
        legend=dict(
            bgcolor='rgba(17,24,39,0.8)',
            bordercolor='#1f2937'
        ),
        margin=dict(l=40,r=40,t=20,b=20),
        height=380
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    dims_en_riesgo = [
        (d, v) for d, v in resultados.items() if v['score'] < 0
    ]
    if dims_en_riesgo:
        st.markdown("### ⚠️ Dimensiones con erosión de confianza")
        for dim, datos in dims_en_riesgo:
            nombre = nombres[dim][0]
            for comentario in datos['comentarios_distrust'][:3]:
                st.markdown(f"""
                <div class="patron-rechazo">
                    <div class="patron-titulo" style="color:#f87171">
                        {nombre} — señal de desconfianza
                    </div>
                    <div class="comentario-rep">"{comentario[:160]}"</div>
                </div>
                """, unsafe_allow_html=True)

elif seccion == "📡 Narrativas Activas":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">📡 Narrativas Activas</div>
        <div class="seccion-subtitulo">
            ¿Qué historias colectivas está construyendo
            la ciudadanía sobre el alcalde?
            Basado en Framing Theory — McCombs & Shaw 1972
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:20px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">
            Una narrativa es una historia que la ciudadanía repite
            colectivamente. No es un comentario aislado — es un patrón
            que se forma cuando muchas personas dicen lo mismo
            con palabras distintas. Lo peligroso no es que exista
            una narrativa negativa — es cuando está creciendo
            semana a semana sin respuesta.
        </p>
    </div>
    """, unsafe_allow_html=True)

    narrativas_data = calcular_narrativas_activas()

    orden = sorted(
        narrativas_data.items(),
        key=lambda x: (
            0 if (x[1]['cambio_pct'] > 20 and x[0] != 'reconocimiento') else
            1 if x[0] != 'reconocimiento' else 2
        )
    )

    for key, narr in orden:
        es_positiva = key == 'reconocimiento'
        borde_color = narr['color']

        ejemplos_html = ''.join([
            f'<p class="comentario-lista">• "{e[:90]}"</p>'
            for e in narr['ejemplos'][:2]
        ])

        sparkline_html = ''
        if not narr['por_semana'].empty and len(narr['por_semana']) > 1:
            max_val = narr['por_semana']['count'].max()
            if max_val > 0:
                bars = []
                for _, row in narr['por_semana'].tail(8).iterrows():
                    height = int((row['count'] / max_val) * 24)
                    height = max(2, height)
                    bars.append(
                        f'<div style="width:6px;height:{height}px;'
                        f'background:{borde_color};opacity:0.7;'
                        f'border-radius:1px;margin:0 1px;'
                        f'align-self:flex-end"></div>'
                    )
                sparkline_html = (
                    f'<div style="display:flex;align-items:flex-end;'
                    f'height:28px;margin-top:8px">{"".join(bars)}</div>'
                )

        cambio_abs = abs(narr['cambio_pct'])
        cambio_str = (
            f"+{cambio_abs:.0f}%" if narr['cambio_pct'] > 0
            else f"-{cambio_abs:.0f}%"
        )

        st.markdown(f"""
        <div class="card" style="border-left:5px solid {borde_color}">
            <div style="display:flex;justify-content:space-between;
                 align-items:flex-start;margin-bottom:8px">
                <div>
                    <span style="font-size:18px">{narr['icono']}</span>
                    <span style="font-size:15px;font-weight:700;
                          color:#f9fafb;margin-left:8px">
                        {narr['nombre']}
                    </span>
                </div>
                <div style="text-align:right">
                    <div style="font-size:28px;font-weight:800;
                          color:{borde_color};font-family:'Courier New'">
                        {narr['total']}
                    </div>
                    <div style="font-size:11px;
                          color:{narr['tend_color']};font-weight:600">
                        {narr['tendencia']} {cambio_str}
                    </div>
                </div>
            </div>
            <p style="font-size:12px;color:#6b7280;margin-bottom:10px">
                {narr['descripcion']}
            </p>
            {sparkline_html}
            <div style="margin-top:10px;border-top:1px solid #1f2937;
                 padding-top:8px">
                {ejemplos_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Evolución de todas las narrativas")
    st.markdown(leyenda_grafica([
        {'simbolo': '—', 'color': '#ef4444',
         'label': 'Abandono territorial',
         'descripcion': 'Menciones donde la ciudadanía siente que su colonia o zona es ignorada.'},
        {'simbolo': '—', 'color': '#f59e0b',
         'label': 'Promesas incumplidas',
         'descripcion': 'Comentarios que hacen referencia a compromisos no cumplidos.'},
        {'simbolo': '—', 'color': '#a855f7',
         'label': 'Narrativa electoral',
         'descripcion': 'La ciudadanía interpreta las acciones del alcalde como movimientos de campaña, no de gestión.'},
        {'simbolo': '—', 'color': '#ec4899',
         'label': 'Narrativa de corrupción',
         'descripcion': 'Señalamientos sobre uso irregular de recursos públicos.'},
        {'simbolo': '—', 'color': '#22c55e',
         'label': 'Reconocimiento ciudadano',
         'descripcion': 'Narrativa positiva — ciudadanos que defienden y reconocen la gestión espontáneamente.'},
        {'simbolo': '↑', 'color': '#9ca3af',
         'label': 'Una línea que sube',
         'descripcion': 'Esa narrativa está ganando fuerza en la conversación ciudadana semana a semana.'},
    ]), unsafe_allow_html=True)

    fig_narr = go.Figure()
    for key, narr in narrativas_data.items():
        if not narr['por_semana'].empty:
            fig_narr.add_trace(go.Scatter(
                x=narr['por_semana']['semana'],
                y=narr['por_semana']['count'],
                mode='lines+markers',
                name=f"{narr['icono']} {narr['nombre']}",
                line=dict(color=narr['color'], width=2),
                marker=dict(size=5),
                hovertemplate=(
                    f"<b>{narr['nombre']}</b><br>"
                    "%{x|%d %b %Y}<br>"
                    "%{y} menciones<extra></extra>"
                )
            ))

    fig_narr.update_layout(
        plot_bgcolor='#111827',
        paper_bgcolor='#111827',
        font=dict(color='#9ca3af', size=11),
        xaxis=dict(
            gridcolor='#1f2937',
            tickformat='%d %b\n%Y'
        ),
        yaxis=dict(
            gridcolor='#1f2937',
            title='Menciones por semana'
        ),
        legend=dict(
            bgcolor='rgba(17,24,39,0.8)',
            bordercolor='#1f2937',
            orientation='h',
            y=-0.2
        ),
        margin=dict(l=0,r=0,t=10,b=60),
        height=350
    )
    st.plotly_chart(fig_narr, use_container_width=True)

elif seccion == "🌊 Contagio Emocional":

    st.markdown("""
    <div class="seccion-header">
        <div class="seccion-titulo">🌊 Contagio Emocional</div>
        <div class="seccion-subtitulo">
            ¿Las emociones que publicas llegan como las envías,
            o la ciudadanía las recibe diferente?
            Basado en Affective Agenda Setting — Nature 2023
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:20px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">
            Cuando publicas un post positivo, ¿la gente responde
            positivamente? ¿O hay posts donde publicas algo positivo
            y la ciudadanía responde con enojo? Eso se llama distorsión
            narrativa — y es la señal más temprana de una crisis
            de comunicación antes de que explote.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df_posts, conteo_tipos, distorsion_alta, por_semana = calcular_contagio_emocional()

    total_posts = len(df_posts)
    resonancia_pos = conteo_tipos.get('resonancia_positiva', 0)
    rechazo = conteo_tipos.get('rechazo_a_positivo', 0)
    distorsion = conteo_tipos.get('distorsion_alta', 0)

    pct_resonancia = (resonancia_pos / total_posts * 100) if total_posts > 0 else 0
    pct_rechazo = (rechazo / total_posts * 100) if total_posts > 0 else 0
    pct_distorsion = (distorsion / total_posts * 100) if total_posts > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="card" style="border-top:3px solid #22c55e">
            <div class="card-title">Resonancia positiva</div>
            <div class="card-value" style="color:#22c55e">
                {pct_resonancia:.0f}%
            </div>
            <div class="card-sub">
                {resonancia_pos} posts donde el mensaje llegó bien
            </div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card" style="border-top:3px solid #ef4444">
            <div class="card-title">Rechazo a positivo</div>
            <div class="card-value" style="color:#ef4444">
                {pct_rechazo:.0f}%
            </div>
            <div class="card-sub">
                {rechazo} posts positivos que generaron rechazo
            </div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="card" style="border-top:3px solid #f59e0b">
            <div class="card-title">Alta distorsión</div>
            <div class="card-value" style="color:#f59e0b">
                {pct_distorsion:.0f}%
            </div>
            <div class="card-sub">
                {distorsion} posts con brecha emocional alta
            </div>
        </div>""", unsafe_allow_html=True)

    if df_posts['score_emocional'].max() < 0:
        st.markdown("""
        <p style="font-size:11px;color:#6b7280;margin-top:4px">
        * Clasificación relativa — todos los posts tienen tono negativo;
        estos son los comparativamente menos negativos.
        </p>
        """, unsafe_allow_html=True)

    st.markdown("### Emoción publicada vs emoción recibida por la ciudadanía")
    st.markdown(leyenda_grafica([
        {'simbolo': '—', 'color': '#3b82f6',
         'label': 'Tono de tus posts',
         'descripcion': 'Emoción promedio de lo que publica el alcalde cada semana. Valores positivos = contenido con tono positivo. Negativos = contenido con tono de urgencia o problema.'},
        {'simbolo': '—', 'color': '#f97316',
         'label': 'Tono de los comentarios',
         'descripcion': 'Cómo responde emocionalmente la ciudadanía a esos mismos posts esa semana.'},
        {'simbolo': '▓', 'color': '#7f1d1d',
         'label': 'Zona de distorsión',
         'descripcion': 'Área donde ambas líneas se separan. Cuando esta zona es grande, el mensaje que publicas llega diferente a como lo pensaste — la ciudadanía recibe otra cosa.'},
        {'simbolo': '- -', 'color': '#4b5563',
         'label': 'Línea neutral (0)',
         'descripcion': 'El punto de equilibrio. Por encima = tono positivo. Por debajo = tono negativo.'},
    ]), unsafe_allow_html=True)

    if not por_semana.empty:
        fig_contagio = go.Figure()

        fig_contagio.add_trace(go.Scatter(
            x=por_semana['semana'],
            y=por_semana['score_post'],
            mode='lines+markers',
            name='Tono de tus posts',
            line=dict(color='#3b82f6', width=2.5),
            marker=dict(size=6),
            hovertemplate=(
                '<b>Tono publicado</b><br>'
                '%{x|%d %b %Y}<br>'
                'Score: %{y:.2f}<extra></extra>'
            )
        ))

        fig_contagio.add_trace(go.Scatter(
            x=por_semana['semana'],
            y=por_semana['score_comentarios'],
            mode='lines+markers',
            name='Tono de los comentarios',
            line=dict(color='#f59e0b', width=2.5),
            marker=dict(size=6),
            hovertemplate=(
                '<b>Tono recibido</b><br>'
                '%{x|%d %b %Y}<br>'
                'Score: %{y:.2f}<extra></extra>'
            )
        ))

        fig_contagio.add_trace(go.Scatter(
            x=pd.concat([por_semana['semana'],
                         por_semana['semana'][::-1]]),
            y=pd.concat([por_semana['score_post'],
                         por_semana['score_comentarios'][::-1]]),
            fill='toself',
            fillcolor='rgba(239,68,68,0.08)',
            line=dict(color='rgba(0,0,0,0)'),
            name='Zona de distorsión',
            hoverinfo='skip'
        ))

        fig_contagio.add_hline(
            y=0,
            line_dash='dot',
            line_color='#374151',
            annotation_text='Neutral',
            annotation_font_color='#6b7280',
            annotation_font_size=10
        )

        fig_contagio.update_layout(
            plot_bgcolor='#111827',
            paper_bgcolor='#111827',
            font=dict(color='#9ca3af', size=11),
            xaxis=dict(
                gridcolor='#1f2937',
                tickformat='%d %b\n%Y'
            ),
            yaxis=dict(
                gridcolor='#1f2937',
                title='Score emocional',
                range=[-1, 1]
            ),
            legend=dict(
                bgcolor='rgba(17,24,39,0.8)',
                bordercolor='#1f2937'
            ),
            margin=dict(l=0,r=0,t=10,b=0),
            height=320
        )
        st.plotly_chart(fig_contagio, use_container_width=True)

    st.markdown("### Posts donde el mensaje positivo generó rechazo")
    st.markdown("""
    <div style="background:#0d1117;border-left:3px solid #374151;
         padding:10px 14px;margin-bottom:12px;border-radius:0 4px 4px 0">
        <span style="font-size:10px;font-weight:600;letter-spacing:1.5px;
              color:#4b5563;text-transform:uppercase">QUÉ ESTÁS VIENDO</span>
        <p style="font-size:12px;color:#9ca3af;margin:4px 0 0 0;
           line-height:1.5">
            Estos son los posts donde más brecha hubo entre
            lo que publicaste y cómo respondió la ciudadanía.
            Son señales de alerta temprana — el tema tocó
            una fibra sensible que las reacciones no reflejan
            pero los comentarios sí revelan.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if distorsion_alta.empty:
        st.markdown("""
        <div class="card">
            <p style="color:#22c55e;text-align:center">
                ✅ Sin casos de distorsión alta en este período
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for _, row in distorsion_alta.iterrows():
            fecha = formato_fecha_espanol(row['created_time'])
            msg = str(row['message'])[:100]
            score_post = float(row.get('score_emocional', 0) or 0)
            score_coment = float(row.get('sent_comentarios', 0) or 0)
            cat = str(row.get('categoria_nombre','—'))[:30].replace('\n',' ')

            color_post = '#22c55e' if score_post > 0 else '#ef4444'
            color_coment = '#22c55e' if score_coment > 0 else '#ef4444'

            st.markdown(f"""
            <div class="patron-rechazo">
                <div style="display:flex;justify-content:space-between;
                     margin-bottom:8px">
                    <span style="font-size:11px;color:#6b7280">{fecha}</span>
                    <span style="font-size:11px;color:#9ca3af;
                          background:#1f2937;padding:2px 8px;
                          border-radius:4px">{cat}</span>
                </div>
                <p style="font-size:13px;color:#d1d5db;
                          margin-bottom:10px;line-height:1.5">
                    {msg}...
                </p>
                <div style="display:flex;gap:24px">
                    <div>
                        <span style="font-size:10px;color:#6b7280;
                              text-transform:uppercase;
                              letter-spacing:1px">
                            Tono publicado
                        </span>
                        <div style="font-size:18px;font-weight:700;
                              color:{color_post};
                              font-family:'Courier New'">
                            {score_post:+.2f}
                        </div>
                    </div>
                    <div style="font-size:20px;color:#374151;
                          align-self:center">→</div>
                    <div>
                        <span style="font-size:10px;color:#6b7280;
                              text-transform:uppercase;
                              letter-spacing:1px">
                            Tono recibido
                        </span>
                        <div style="font-size:18px;font-weight:700;
                              color:{color_coment};
                              font-family:'Courier New'">
                            {score_coment:+.2f}
                        </div>
                    </div>
                    <div style="margin-left:auto;text-align:right">
                        <span style="font-size:10px;color:#6b7280;
                              text-transform:uppercase;
                              letter-spacing:1px">
                            Distorsión
                        </span>
                        <div style="font-size:18px;font-weight:700;
                              color:#ef4444;font-family:'Courier New'">
                            {abs(float(row.get('distorsion',0) or 0)):.2f}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### ¿Cómo responde la ciudadanía a tus posts?")

    labels_map = {
        'resonancia_positiva': '✅ Resonancia positiva',
        'rechazo_a_positivo': '🔴 Rechazo a mensaje positivo',
        'resonancia_negativa': '⚠️ Resonancia negativa',
        'inversion_positiva': '🔄 Inversión positiva',
        'distorsion_alta': '📊 Alta distorsión',
        'neutral': '⚪ Respuesta neutral',
        'sin_datos': '— Sin datos'
    }
    colors_map = {
        'resonancia_positiva': '#16a34a',
        'rechazo_a_positivo': '#dc2626',
        'resonancia_negativa': '#ca8a04',
        'inversion_positiva': '#2563eb',
        'distorsion_alta': '#9333ea',
        'neutral': '#374151',
        'sin_datos': '#1f2937'
    }

    tipos_validos = {
        k: v for k, v in conteo_tipos.items()
        if k != 'sin_datos' and v > 0
    }

    if tipos_validos:
        st.markdown(leyenda_grafica([
            {'simbolo': '■', 'color': '#f59e0b',
             'label': 'Resonancia negativa',
             'descripcion': 'Posts donde tanto el contenido como los comentarios tienen tono negativo. La ciudadanía y el alcalde coinciden en que hay un problema.'},
            {'simbolo': '■', 'color': '#a855f7',
             'label': 'Alta distorsión',
             'descripcion': 'Posts donde el alcalde publica algo con un tono y la ciudadanía responde con el opuesto. La señal más temprana de una crisis de comunicación.'},
            {'simbolo': '■', 'color': '#3b82f6',
             'label': 'Inversión positiva',
             'descripcion': 'Posts donde el alcalde publicó algo negativo o neutro pero la ciudadanía respondió positivamente. Contenido que conecta más de lo esperado.'},
            {'simbolo': '■', 'color': '#374151',
             'label': 'Respuesta neutral',
             'descripcion': 'Posts que no generaron reacción emocional clara en ninguna dirección.'},
        ]), unsafe_allow_html=True)
        fig_dist = go.Figure(go.Pie(
            labels=[labels_map.get(k, k) for k in tipos_validos.keys()],
            values=list(tipos_validos.values()),
            hole=0.55,
            marker=dict(
                colors=[colors_map.get(k,'#374151') for k in tipos_validos.keys()],
                line=dict(color='#111827', width=2)
            ),
            textfont=dict(size=11, color='white'),
            hovertemplate='%{label}<br>%{value} posts (%{percent})<extra></extra>'
        ))
        fig_dist.update_layout(
            plot_bgcolor='#111827',
            paper_bgcolor='#111827',
            font=dict(color='#9ca3af'),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(17,24,39,0.8)',
                bordercolor='#1f2937',
                font=dict(size=11)
            ),
            margin=dict(l=0,r=0,t=10,b=0),
            height=320
        )
        st.plotly_chart(fig_dist, use_container_width=True)

elif seccion == "📋 Notas Metodológicas":
    render_notas_metodologicas()
