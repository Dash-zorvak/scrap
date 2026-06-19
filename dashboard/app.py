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
import json
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard"))
from config import (
    FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB,
    FACEBOOK_TEST_DB, TIKTOK_TEST_DB, EXTERNOS_TEST_DB,
    FB_PAGES_OFICIALES, FB_REACTIONS, TK_ENGAGEMENT,
    TK_ACCOUNTS, OUTPUT_DIR, MIN_COMENTARIOS_MUESTRA,
)
from dashboard.guardar_lote import guardar_lote
from dashboard.externos_store import listar_paginas_externas, agregar_pagina_externa
from dashboard.estilos import CSS
from dashboard.procesar_lote import procesar_pipeline
from dashboard.muestra import evaluar_muestra
from dashboard.sentimiento_engine import get_diagnostico_sentimiento

# ── Toggle modo prueba — antes de cualquier función cacheada ──
if "modo_prueba" not in st.session_state:
    st.session_state.modo_prueba = False

# ── Estado del lote de ingreso (Fase 1: solo en memoria) ──
if "lote_ingreso" not in st.session_state:
    st.session_state["lote_ingreso"] = []

FACEBOOK_DB_ACTIVA = (
    FACEBOOK_TEST_DB if st.session_state.get("modo_prueba", False) else FACEBOOK_DB
)
TIKTOK_DB_ACTIVA = (
    TIKTOK_TEST_DB if st.session_state.get("modo_prueba", False) else TIKTOK_DB
)
EXTERNOS_DB_ACTIVA = (
    EXTERNOS_TEST_DB if st.session_state.get("modo_prueba", False) else EXTERNOS_DB
)

# ═══════════════════════════════
# CAPA DE IA — Groq (API compatible OpenAI)
# ════════════════════════════════

from dashboard.llm_groq import chat_texto, groq_disponible

@st.cache_data(ttl=3600, show_spinner=False)
def generar_narrativa_ia(tipo: str, contexto: dict) -> str:
    """
    Genera narrativa ejecutiva usando Groq (Llama 3.3 70B).
    Tipos: 'eco_historico', 'leccion', 'brecha', 'contexto',
           'correlacion', 'proyeccion', 'recomendacion'
    """
    if not groq_disponible():
        return "Análisis IA no disponible en este momento (falta GROQ_API_KEY en .streamlit/secrets.toml o variable de entorno)"
    
    prompts = {
        "eco_historico": (
            "Eres analista político senior para Alcaldía de Santa Ana. "
            "Dado el contexto de métricas de percepción de la semana, escribe un párrafo ejecutivo "
            "(máx 120 palabras) que explique qué patrón histórico o 'eco' del pasado "
            "resuena con la situación actual. Tono: directo, sin adjetivos vacíos, "
            "orientado a decisión de reelección. Español."
        ),
        "leccion": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sintetizando la lección operativa clara que deja esta semana de datos. "
            "Qué NO repetir, qué replicar. Tono: brutal honestidad, acción inmediata. Español."
        ),
        "brecha": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sobre la brecha entre lo que la ciudadanía PERCIBE (sentimiento, temas, enojo) "
            "y la GESTIÓN REAL (obras, servicios, indicadores municipales — dato no disponible en BD, "
            "asume que existe). Tono: confronta percepción vs realidad sin suavizar. Español."
        ),
        "contexto": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "explicando qué está pasando FUERA de las redes (eventos municipales, opositores, "
            "economía local, clima, noticias) que explica el sentimiento negativo detectado "
            "en comentarios. Usa solo el contexto implícito en los datos. Tono: discreto, informado. Español."
        ),
        "correlacion": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "sobre la correlación entre TIPO DE CONTENIDO publicado y REACCIÓN CIUDADANA "
            "(brecha reacción vs comentario). Qué contenido genera desconexión. Tono: diagnóstico preciso. Español."
        ),
        "proyeccion": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "proyectando el escenario a 2 semanas si la tendencia actual de sentimiento, "
            "engagement y narrativas se mantiene. Tono: alerta temprana, sin alarmismo. Español."
        ),
        "recomendacion": (
            "Eres analista político senior. Escribe un párrafo ejecutivo (máx 120 palabras) "
            "con LA recomendación estratégica única de la semana, sintetizando TODOS los indicadores: "
            "Pulso, Audiencia, Riesgo, Memoria. Qué hacer el lunes. Tono: orden directa, ejecutable. Español."
        ),
    }
    
    prompt_base = prompts.get(tipo, prompts["recomendacion"])
    ctx_str = json.dumps(contexto, ensure_ascii=False, default=str)[:3000]
    
    try:
        return chat_texto(
            f"{prompt_base}\n\nCONTEXTO (JSON):\n{ctx_str}",
            max_tokens=600,
            temperature=0.7,
            json=False,
        )
    except Exception:
        return "Análisis IA no disponible en este momento (error en llamada API)"

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
        '<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">'
        '<span style="font-size:14px;color:{};min-width:18px;font-weight:600;line-height:1.4;font-family:\'IBM Plex Mono\',monospace">'
        '{}</span>'
        '<div>'
        '<span style="font-size:11px;color:var(--fg-primary);font-weight:600;font-family:\'Inter\',sans-serif">'
        '{}</span>'
        '<span style="font-size:11px;color:var(--fg-muted);margin-left:4px;font-family:\'Inter\',sans-serif">'
        '— {}</span></div></div>'.format(
            e['color'], e['simbolo'], e['label'], e['descripcion']
        )
        for e in elementos
    )
    return (
        '<div style="background:var(--bg-card);border:1px solid var(--border);'
        'padding:12px 16px;margin-bottom:10px">'
        '<p style="font-size:9px;color:var(--fg-muted);margin:0 0 8px 0;'
        'font-weight:600;letter-spacing:1.5px;text-transform:uppercase;font-family:\'IBM Plex Mono\',monospace">'
        '◈ QUÉ ESTÁS VIENDO</p>{}</div>'
    ).format(items_html)

st.set_page_config(
    page_title="PANEL·SANTA ANA — Inteligencia Ciudadana",
    page_icon="\u2696",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(CSS, unsafe_allow_html=True)

# ── SIDEBAR ──

st.sidebar.markdown("""
<div style="border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:12px">
  <div style="font-size:9px;letter-spacing:2px;color:var(--accent);font-weight:600;font-family:'IBM Plex Mono',monospace;text-transform:uppercase">PANEL·SANTA ANA</div>
  <div style="font-size:11px;color:var(--fg-muted);margin-top:2px;font-family:'Inter',sans-serif">Inteligencia Ciudadana</div>
</div>
""", unsafe_allow_html=True)

periodo = st.sidebar.selectbox("PERÍODO", [
    "Esta semana",
    "Últimos 15 días",
    "Último mes",
    "Últimos 3 meses",
    "Todo el período"
])

plataforma = st.sidebar.selectbox("PLATAFORMA", [
    "Ambas", "Facebook", "TikTok"
])

vista = st.sidebar.radio("VISTA", [
    "📊 Dashboard", "📥 Cargar contenido", "📋 Notas metodológicas"
])

st.sidebar.markdown("---")
modo_prueba = st.sidebar.toggle(
    "MODO PRUEBA",
    value=st.session_state.modo_prueba,
    help="Activa datos de prueba con alta negatividad para testear el semáforo rojo"
)
if modo_prueba != st.session_state.modo_prueba:
    st.session_state.modo_prueba = modo_prueba
    st.cache_data.clear()
    st.rerun()

if st.session_state.modo_prueba:
    st.sidebar.markdown(
        '<p style="color:var(--amber);font-size:10px;font-family:\'IBM Plex Mono\',monospace;letter-spacing:0.5px">'
        'TEST MODE</p>',
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

st.sidebar.markdown(
    f'<p style="font-size:9px;color:var(--fg-muted);font-family:\'IBM Plex Mono\',monospace;letter-spacing:0.5px">'
    f'UPD: {fecha_str}</p>',
    unsafe_allow_html=True
)

st.sidebar.markdown("---")

with st.sidebar.expander("🔧 Diagnóstico"):
    st.caption("GROQ_API_KEY (visión + texto)")
    api_key_env = os.environ.get("GROQ_API_KEY")
    api_key_secrets = None
    try:
        api_key_secrets = st.secrets.get("GROQ_API_KEY")
    except Exception:
        pass
    if api_key_env:
        st.code("detectada (env)", language="text")
    elif api_key_secrets:
        st.code("detectada (secrets)", language="text")
    else:
        st.code("NO detectada", language="text")

    diag = get_diagnostico_sentimiento()
    st.caption("Motor de sentimiento")
    st.code(f"forzado: {diag['motor_forzado']}", language="text")
    st.code(f"bert_fallo: {diag['bert_fallo']}", language="text")
    if diag["ultimo_error_bert"]:
        st.code(f"último error BERT: {diag['ultimo_error_bert']}", language="text")
    if diag["ultimo_error_groq"]:
        st.code(f"último error Groq (sentimiento): {diag['ultimo_error_groq']}", language="text")

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

def _warn_dropped_null_dates():
    """Advierte si hay posts/videos sin fecha que serán descartados."""
    for table, col, label in [
        ("fb_posts", "created_time", "posts de Facebook"),
        ("videos", "created_at", "videos de TikTok"),
    ]:
        try:
            db = FACEBOOK_DB_ACTIVA if table == "fb_posts" else TIKTOK_DB_ACTIVA
            if not os.path.exists(db):
                continue
            with sqlite3.connect(db) as conn:
                n = pd.read_sql(
                    f"SELECT COUNT(*) as c FROM {table} WHERE {col} IS NULL OR TRIM(CAST({col} AS TEXT)) = ''",
                    conn
                ).iloc[0]['c']
                if n > 0:
                    st.warning(f"Se descartaron {n} {label} sin fecha.")
        except Exception:
            pass


def hay_datos(df, mensaje: str = "Aún no hay datos suficientes para esta sección.") -> bool:
    """Muestra un aviso elegante y devuelve False si el DataFrame está vacío."""
    if df is None or len(df) == 0:
        st.markdown(
            f'<div class="bloom-status-info"><span class="bloom-status-marker">●</span> {mensaje}</div>',
            unsafe_allow_html=True
        )
        return False
    return True


def card_explicativa(que_es: str, como_leerlo: str, ojo: str | None = None):
    """Tarjeta en lenguaje sencillo para explicar un gráfico al edil."""
    ojo_html = (
        f'<div style="margin-top:8px;font-size:11px;color:var(--amber);font-family:\'Inter\',sans-serif;border-top:1px solid var(--border);padding-top:6px">'
        f'<span style="font-weight:600">◈</span> {ojo}</div>'
        if ojo else ""
    )
    st.markdown(
        f"""
        <div class="interpretacion-box" style="margin:4px 0 16px 0">
            <div class="interpretacion-label">◈ CÓMO LEER ESTO</div>
            <div class="interpretacion-texto">
                <strong style="color:var(--accent)">Qué muestra:</strong> {que_es}<br>
                <strong style="color:var(--accent)">Cómo leerlo:</strong> {como_leerlo}
            </div>
            {ojo_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def que_ves_box(texto: str):
    """Caja QUÉ ESTÁS VIENDO en lenguaje ciudadano."""
    st.markdown(
        f'<div class="que-ves-box"><span class="que-ves-label">◈ QUÉ ESTÁS VIENDO</span>'
        f'<p class="que-ves-texto">{texto}</p></div>',
        unsafe_allow_html=True,
    )


def bloom_subheader(texto: str):
    """Reemplazo de st.subheader con estilo Bloomberg."""
    st.markdown(f'<p class="bloom-subheader">{texto}</p>', unsafe_allow_html=True)


def bloom_caption(texto: str):
    """Reemplazo de st.caption con estilo Bloomberg."""
    st.markdown(f'<p class="bloom-caption">{texto}</p>', unsafe_allow_html=True)


def bloom_metric(label: str, value: str, delta: str | None = None, color: str | None = None):
    """Tarjeta métrica compacta estilo Bloomberg."""
    val_color = f'color:{color};' if color else ''
    delta_html = f'<div class="bloom-card-sub">{delta}</div>' if delta else ''
    st.markdown(
        f'<div class="bloom-card { "bloom-border-accent" if color else "" }">'
        f'<div class="bloom-card-title">{label}</div>'
        f'<div class="bloom-card-value" style="{val_color}font-size:28px">{value}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )


def plotly_bloom_theme(bg: str = "var(--bg-card)", fg: str = "var(--fg-secondary)"):
    """Tema oscuro Bloomberg para gráficas Plotly."""
    return dict(
        plot_bgcolor=bg, paper_bgcolor=bg,
        font=dict(color=fg, size=10, family='IBM Plex Mono, monospace'),
        xaxis=dict(gridcolor='var(--border)', showgrid=True, tickfont=dict(size=9)),
        yaxis=dict(gridcolor='var(--border)', showgrid=True, tickfont=dict(size=9)),
        margin=dict(l=0, r=0, t=10, b=0),
    )


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
    if df_fb is not None and not df_fb.empty and 'created_time' in df_fb.columns:
        fb = df_fb[df_fb['created_time'] >= fecha_inicio].copy()
    else:
        fb = pd.DataFrame()
    if df_tk is not None and not df_tk.empty and 'created_at' in df_tk.columns:
        tk = df_tk[df_tk['created_at'] >= fecha_inicio].copy()
    else:
        tk = pd.DataFrame()
    if plataforma == "Facebook": return fb, pd.DataFrame()
    if plataforma == "TikTok": return pd.DataFrame(), tk
    return fb, tk

def calcular_semaforo(df_fb):
    if df_fb.empty: return "amarillo", "SIN DATOS — No hay suficientes datos esta semana"
    score = df_fb['score_emocional'].mean()
    if score >= 0.25: return "verde", "RESPALDO — La ciudadanía te respalda esta semana"
    elif score >= 0.10: return "amarillo", "MIXTO — Hay señales mixtas esta semana"
    else: return "rojo", "ALERTA — La ciudadanía está inquieta esta semana"

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
            'icono': '[ABANDONO]'
        },
        'promesas_incumplidas': {
            'nombre': 'Promesas incumplidas',
            'descripcion': 'Menciones de compromisos que el alcalde '
                          'hizo y que la ciudadanía percibe como no cumplidos',
            'keywords': ['prometio','prometieron','prometido','dijeron',
                        'para cuando','cuando van','siguen igual',
                        'nunca','años prometiendo','todavia'],
            'color': '#f59e0b',
            'icono': '[PROMESA]'
        },
        'narrativa_electoral': {
            'nombre': 'Narrativa electoral',
            'descripcion': 'La ciudadanía interpreta las acciones '
                          'del alcalde en clave de campaña electoral',
            'keywords': ['eleccion','voto','reeleccion','campaña',
                        'boto','votar','candidato','proximas',
                        'solo cuando hay','interesa el voto'],
            'color': '#8b5cf6',
            'icono': '[ELECTORAL]'
        },
        'corrupcion': {
            'nombre': 'Narrativa de corrupción',
            'descripcion': 'Señalamientos directos o indirectos '
                          'sobre manejo irregular de recursos',
            'keywords': ['corrupto','robo','ladron','dinero','fondos',
                        'recursos','licitacion','contrato','empleados',
                        'enchufado','nepotismo','millones'],
            'color': '#dc2626',
            'icono': '[CORRUPCIÓN]'
        },
        'reconocimiento': {
            'nombre': 'Reconocimiento ciudadano',
            'descripcion': 'Narrativa positiva — ciudadanos que '
                          'defienden y reconocen la gestión',
            'keywords': ['excelente','buen trabajo','gracias alcalde',
                        'sigan adelante','lo apoyamos','felicitaciones',
                        'bien hecho','orgullo','progreso','cambio'],
            'color': '#22c55e',
            'icono': '[RECONOCIMIENTO]'
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
        WHERE 1=1
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

def calcular_score_emocional_neto(min_reacciones: int = 0) -> pd.DataFrame:
    """Score emocional neto por post (Módulo 3 del blueprint).
    Lee fb_posts (reacciones/shares/views reales) + fb_sentimiento (sentimiento por post)."""
    posts = safe_query("""
        SELECT post_id, page_name, message, created_time,
               likes_count, loves_count, cares_count, hahas_count, wows_count,
               sads_count, angrys_count, shares_count, views_count,
               comments_count, topic_category, zona
        FROM fb_posts
    """, FACEBOOK_DB_ACTIVA)
    if posts.empty:
        return pd.DataFrame()

    num_cols = ["likes_count", "loves_count", "cares_count", "hahas_count", "wows_count",
                "sads_count", "angrys_count", "shares_count", "views_count", "comments_count"]
    for c in num_cols:
        posts[c] = pd.to_numeric(posts[c], errors="coerce").fillna(0)

    # engagement_total (blueprint): like + encanta + importa + divierte + asombra + entristece + enoja + compartidos
    posts["engagement_total"] = (
        posts["likes_count"] + posts["loves_count"] + posts["cares_count"] + posts["hahas_count"]
        + posts["wows_count"] + posts["sads_count"] + posts["angrys_count"]
        + posts["shares_count"]
    )
    # total reacciones (sin shares) para la regla de exclusión <10
    posts["total_reacciones"] = (
        posts["likes_count"] + posts["loves_count"] + posts["cares_count"] + posts["hahas_count"]
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

    return posts

def calcular_viralidad_tiktok(min_views: int = 0) -> pd.DataFrame:
    """Índice de viralidad de TikTok (Módulo 3, adaptado).
    TikTok no tiene reacciones diferenciadas → medimos ALCANCE/propagación, no emoción."""
    df = safe_query("SELECT * FROM videos", TIKTOK_DB_ACTIVA)
    if df.empty:
        return pd.DataFrame()
    for c in ["views", "likes", "shares", "comments_count", "favorites_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0) if c in df.columns else 0
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
        SELECT created_time, likes_count, loves_count, cares_count, hahas_count, wows_count,
               sads_count, angrys_count, shares_count, comments_count
        FROM fb_posts
        WHERE created_time IS NOT NULL AND TRIM(created_time) <> ''
    """, FACEBOOK_DB_ACTIVA)
    if posts.empty:
        return {}
    react = ["likes_count", "loves_count", "cares_count", "hahas_count", "wows_count",
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

# ════════════════════════════════
# SECCIÓN 1 — ESTADO GENERAL
# ════════════════════════════════

def render_notas_metodologicas():
    st.header("NOTAS METODOLÓGICAS")
    bloom_caption("Límites honestos del sistema — léelos antes de tomar decisiones con estos datos.")
    st.markdown(
        "Este panel analiza contenido público (posts, reacciones y comentarios) de las "
        "páginas de la Alcaldía y el alcalde. Es una herramienta de lectura de percepción "
        "colectiva, no un oráculo. Sus límites:"
    )
    st.markdown(
        '<div class="bloom-status-warning"><span class="bloom-status-label">LIMITACIÓN</span> '
        'No predice votos individuales. Mide qué temas generan qué emociones en '
        'conjunto, no el comportamiento de personas concretas.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-info">Las reacciones son un proxy emocional, no un test psicológico validado. '
        'Úsalas como señal de tono colectivo, no como diagnóstico.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-info">El sentimiento de comentarios tiene ~85% de precisión en español. '
        'Alrededor de 1 de cada 7 comentarios puede estar mal clasificado.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-warning"><span class="bloom-status-label">LIMITACIÓN</span> '
        'Correlación ≠ causalidad. Que un pico de engagement coincida con una noticia '
        'externa no prueba que una haya causado la otra; pueden influir terceros factores.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-info">TikTok no tiene reacciones diferenciadas (solo "me gusta"). Su lectura emocional '
        'depende 100% de los comentarios.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="bloom-status-info">En Facebook, las reacciones con datos sólidos son "Me gusta", "Me encanta", '
        '"Me divierte" y "Me enoja". "Me asombra" y "Me entristece" aparecen en volúmenes '
        'mínimos (decenas de casos), así que las métricas de afecto/controversia se apoyan '
        'sobre todo en las primeras.</div>',
        unsafe_allow_html=True
    )
    bloom_caption(
        "Metodología inspirada en Kosinski et al. (2013), adaptada a datos agregados por "
        "publicación (no a perfiles individuales) y con las limitaciones señaladas por "
        "Farina et al. (2025)."
    )


# ════════════════════════════════
# SECCIÓN — 📥 Cargar contenido (Fase 1)
# ════════════════════════════════

# ════════════════════════════════════
# Helpers de revisión (Fase 3)
# ════════════════════════════════════

def _campo_numero(label: str, dato_confianza: dict, key_suffix: str, id_temporal: str) -> None:
    """Renderiza st.number_input con resaltado por confianza.

    confianza 'seguro' → normal
    confianza 'dudoso' → 🟡 + "revisar: lectura dudosa"
    confianza 'no_detectado' → 🟡 + "no detectado — completa a mano"
    confianza 'manual' → 🟡 + "se teclea a mano (no se confía al OCR)"
    """
    confianza = dato_confianza.get("confianza", "no_detectado")
    valor = dato_confianza.get("valor")
    key = f"rev_{key_suffix}_{id_temporal}"

    label_display = f"🟡 {label}" if confianza != "seguro" else label
    initial = valor if valor is not None else 0

    st.number_input(label_display, min_value=0, value=initial, step=1, key=key)
    if confianza == "dudoso":
        st.caption("revisar: lectura dudosa")
    elif confianza == "no_detectado":
        st.caption("no detectado — completa a mano")
    elif confianza == "manual":
        st.caption("se teclea a mano (no se confía al OCR)")


def _contrato_vacio(plataforma: str) -> dict:
    """Contrato vacío para rellenar a mano cuando la IA falla.

    'externos' se trata igual que 'facebook' (misma extracción y campos).
    """
    vacio = {"valor": None, "confianza": "no_detectado"}
    if plataforma in ("facebook", "externos"):
        return {
            "plataforma": plataforma,
            "texto_post": "",
            "fecha": {"valor": None, "confianza": "no_detectado"},
            "autor_pagina": None,
            "reacciones": {k: dict(vacio) for k in (
                "likes", "loves", "cares", "hahas", "sads", "wows", "angrys", "total"
            )},
            "comentarios_count": dict(vacio),
            "compartidos": {"valor": None, "confianza": "manual"},
            "vistas": {"valor": None, "confianza": "manual"},
            "comentarios": [],
        }
    elif plataforma == "tiktok":
        return {
            "plataforma": "tiktok",
            "texto_post": "",
            "fecha": {"valor": None, "confianza": "no_detectado"},
            "autor_cuenta": None,
            "metricas": {k: dict(vacio) for k in (
                "likes", "favoritos", "comentarios_count"
            )} | {
                "compartidos": {"valor": None, "confianza": "manual"},
                "vistas": {"valor": None, "confianza": "manual"},
            },
            "comentarios": [],
        }


# ════════════════════════════════════
# Fase 3 — Revisión editable del lote
# ════════════════════════════════════

def seccion_revisar_lote() -> None:
    """Pantalla de revisión editable post-extracción (Fase 3).

    Dispara extracción con Groq (Llama 4 Scout), muestra tarjetas editables
    con resaltado por confianza, y produce datos_revisados.
    """
    lote = st.session_state["lote_ingreso"]
    pendientes = [p for p in lote if p["estado"] == "pendiente"]
    extraidos = [p for p in lote if p["estado"] in ("extraido", "revisado")]
    errores = [p for p in lote if p["estado"] == "error"]

    if not pendientes and not extraidos and not errores:
        return

    # ── Paso 1: Botón de extracción ──
    if pendientes:
        st.markdown("### 🔍 Extracción con IA")
        st.caption(
            "Groq (Llama 4 Scout) leerá las capturas y extraerá texto, fechas, "
            "reacciones y comentarios. Los números borrosos o no visibles "
            "quedarán marcados para que los completes."
        )
        if st.button("🔍 Extraer y revisar lote", width='stretch', type="primary"):
            from ingreso_extraccion import extraer_posts_desde_archivos
            import uuid

            n = len(pendientes)
            status = st.status(f"Extrayendo datos de los archivos… 0/{n}", expanded=True)
            nuevos_items = []
            for item in st.session_state["lote_ingreso"]:
                if item.get("estado") != "pendiente":
                    nuevos_items.append(item)
                    continue

                # 'externos' usa la misma extracción que Facebook
                plat_extraccion = "facebook" if item["plataforma"] == "externos" else item["plataforma"]
                resultado = extraer_posts_desde_archivos(item["imagenes"], plat_extraccion)

                if isinstance(resultado, dict) and resultado.get("error"):
                    item["estado"] = "error"
                    item["error_msg"] = resultado["error"]
                    nuevos_items.append(item)
                    continue

                posts = resultado.get("posts", [])
                if not posts:
                    item["estado"] = "error"
                    item["error_msg"] = "No se detectaron posts en el archivo"
                    nuevos_items.append(item)
                    continue

                for datos in posts:
                    enlace_au