import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard"))

from config import (
    FACEBOOK_DB, TIKTOK_DB, EXTERNOS_DB,
    FACEBOOK_TEST_DB, TIKTOK_TEST_DB, EXTERNOS_TEST_DB,
    FB_PAGES_OFICIALES, FB_REACTIONS, TK_ENGAGEMENT,
    TK_ACCOUNTS, OUTPUT_DIR, MIN_COMENTARIOS_MUESTRA,
)
from dashboard.muestra import evaluar_muestra
from dashboard.sentimiento_engine import get_diagnostico_sentimiento
from dashboard.estilos import CSS
from dashboard.dash_ingesta import seccion_cargar_contenido
from dashboard.dash_metrics import (
    safe_query,
    get_fecha_inicio,
    filtrar_por_periodo_plataforma,
    calcular_semaforo,
    cargar_fb_engagement,
    cargar_tk_engagement,
    cargar_sentimiento_fb,
    cargar_comentarios_fb,
    cargar_comentarios_negativos,
    cargar_series,
    cargar_externos,
    calcular_contagio_emocional,
    generar_narrativa_ia,
    generar_interpretacion,
)

# ─── Estado de sesión (intacto) ─────────────────────────────
if "modo_prueba" not in st.session_state:
    st.session_state.modo_prueba = False

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
        'QUÉ ESTÁS VIENDO</p>{}</div>'
    ).format(items_html)


st.set_page_config(
    page_title="PANEL·SANTA ANA — Inteligencia Ciudadana",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(CSS, unsafe_allow_html=True)

# ─── Fecha de actualización (usada en topbar y sidebar) ─────
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
except Exception:
    fecha_str = "No disponible"

# ─── Topbar institucional ───────────────────────────────────
st.markdown(f"""
<div class="topbar">
    <div class="topbar-brand">PANEL <span class="sep">·</span> SANTA ANA <span class="sep">/</span> <span class="who">Inteligencia Ciudadana</span></div>
    <div class="topbar-meta">ACTUALIZADO <span class="acc">·</span> {fecha_str.upper()}</div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────

st.sidebar.markdown('<div class="sys-header"><div class="sys-brand">PANEL·SANTA ANA</div><div class="sys-brand-sub">Inteligencia Ciudadana</div></div>', unsafe_allow_html=True)

st.sidebar.markdown('<div class="sys-section-label">FILTROS</div>', unsafe_allow_html=True)

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

st.sidebar.markdown('<div class="sys-section-label">NAVEGACIÓN</div>', unsafe_allow_html=True)

vista = st.sidebar.radio("VISTA", [
    "Dashboard", "Cargar contenido", "Notas metodológicas"
])

st.sidebar.markdown('<hr class="sys-divider">')
st.sidebar.markdown('<div class="sys-section-label">SISTEMA</div>', unsafe_allow_html=True)

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
        '<div class="sys-footer" style="color:var(--amber);">MODO PRUEBA ACTIVO</div>',
        unsafe_allow_html=True
    )

st.sidebar.markdown(
    f'<div class="sys-footer">ACTUALIZADO: {fecha_str}</div>',
    unsafe_allow_html=True
)

st.sidebar.markdown('<hr class="sys-divider">')

with st.sidebar.expander("DIAGNÓSTICO DEL SISTEMA"):
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

# ─── HELPERS UI ─────────────────────────────────────────────

def formato_fecha_espanol(fecha):
    dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    try:
        if pd.isna(fecha): return "Fecha no disponible"
        d = pd.Timestamp(fecha)
        return f"{dias[d.weekday()]} {d.day} de {meses[d.month-1]}, {d.year}"
    except Exception:
        return str(fecha)


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
                    st.markdown(
                        f'<div class="status-info">Se descartaron {n} {label} sin fecha.</div>',
                        unsafe_allow_html=True
                    )
        except Exception:
            pass


def hay_datos(df, mensaje: str = "Aún no hay datos suficientes para esta sección.") -> bool:
    if df is None or len(df) == 0:
        st.markdown(
            f'<div class="status-info">{mensaje}</div>',
            unsafe_allow_html=True
        )
        return False
    return True


def card_explicativa(que_es: str, como_leerlo: str, ojo=None):
    ojo_html = (
        f'<div style="margin-top:8px;font-size:11px;color:var(--amber);font-family:\'Inter\',sans-serif;border-top:1px solid var(--border);padding-top:6px">'
        f'{ojo}</div>'
        if ojo else ""
    )
    st.markdown(
        f"""
        <div class="interpretation" style="margin:4px 0 16px 0">
            <div class="interpretation-label">CÓMO LEER ESTO</div>
            <div class="interpretation-texto">
                <strong style="color:var(--accent)">Qué muestra:</strong> {que_es}<br>
                <strong style="color:var(--accent)">Cómo leerlo:</strong> {como_leerlo}
            </div>
            {ojo_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def que_ves_box(texto: str):
    st.markdown(
        f'<div class="wys-box"><span class="wys-label">QUÉ ESTÁS VIENDO</span>'
        f'<p class="wys-text">{texto}</p></div>',
        unsafe_allow_html=True,
    )


def bloom_subheader(texto: str):
    st.markdown(f'<p class="exec-subheader">{texto}</p>', unsafe_allow_html=True)


def bloom_caption(texto: str):
    st.markdown(f'<p class="exec-caption">{texto}</p>', unsafe_allow_html=True)


def bloom_metric(label: str, value: str, delta=None, color=None):
    val_color = f'color:{color};' if color else ''
    delta_html = f'<div class="exec-card-sub">{delta}</div>' if delta else ''
    st.markdown(
        f'<div class="exec-card">'
        f'<div class="exec-card-title">{label}</div>'
        f'<div class="exec-card-value" style="{val_color}">{value}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )


def plotly_bloom_theme(bg: str = "var(--bg-card)", fg: str = "var(--fg-secondary)"):
    return dict(
        plot_bgcolor=bg, paper_bgcolor=bg,
        font=dict(color=fg, size=10, family='IBM Plex Mono, monospace'),
        xaxis=dict(gridcolor='var(--border)', showgrid=True, tickfont=dict(size=9)),
        yaxis=dict(gridcolor='var(--border)', showgrid=True, tickfont=dict(size=9)),
        margin=dict(l=0, r=0, t=10, b=0),
    )


def _page_head(overline: str, title: str, sub: str, stats: str = ""):
    """Cabecera ejecutiva de página (overline + título + subtítulo + meta)."""
    stats_html = f'<div class="page-stats">{stats}</div>' if stats else ''
    st.markdown(f"""
    <div class="page-head">
        <div class="page-overline">{overline}</div>
        <div class="page-h">{title}</div>
        <div class="page-sub">{sub}</div>
        {stats_html}
    </div>
    """, unsafe_allow_html=True)


def _docstrip(periodo_lbl: str, plataforma_lbl: str, fecha_lbl: str, modo_lbl: str = ""):
    """Pie ejecutivo con metadatos de la consulta."""
    modo_html = f'<span class="sep">·</span> <span class="acc">{modo_lbl}</span>' if modo_lbl else ''
    st.markdown(f"""
    <div class="docstrip-footer">
        <div>PANEL·SANTA ANA <span class="sep">·</span> INTELIGENCIA CIUDADANA</div>
        <div>PERÍODO <span class="acc">{periodo_lbl.upper()}</span> <span class="sep">·</span> FUENTE <span class="acc">{plataforma_lbl.upper()}</span> <span class="sep">·</span> {fecha_lbl.upper()} {modo_html}</div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════
# NOTAS METODOLÓGICAS
# ═══════════════════════════════════════════

def render_notas_metodologicas():
    _page_head(
        "REFERENCIA METODOLÓGICA / LÍMITES DEL SISTEMA",
        "Notas metodológicas",
        "Los supuestos, los proxys y los márgenes de error sobre los que se construye esta lectura. Léelos antes de tomar decisiones con estos datos."
    )
    st.markdown(
        "Este panel analiza contenido público (posts, reacciones y comentarios) de las "
        "páginas de la Alcaldía y el alcalde. Es una herramienta de lectura de percepción "
        "colectiva, no un oráculo. Sus límites:"
    )
    st.markdown(
        '<div class="status-warning"><span class="status-label status-label-warning">LIMITACIÓN</span> '
        'No predice votos individuales. Mide qué temas generan qué emociones en '
        'conjunto, no el comportamiento de personas concretas.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="status-info">Las reacciones son un proxy emocional, no un test psicológico validado. '
        'Úsalas como señal de tono colectivo, no como diagnóstico.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="status-info">El sentimiento de comentarios tiene ~85% de precisión en español. '
        'Alrededor de 1 de cada 7 comentarios puede estar mal clasificado.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="status-warning"><span class="status-label status-label-warning">LIMITACIÓN</span> '
        'Correlación no implica causalidad. Que un pico de engagement coincida con una noticia '
        'externa no prueba que una haya causado la otra; pueden influir terceros factores.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="status-info">TikTok no tiene reacciones diferenciadas (solo "me gusta"). Su lectura emocional '
        'depende 100% de los comentarios.</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="status-info">En Facebook, las reacciones con datos sólidos son "Me gusta", "Me encanta", '
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


# ═══════════════════════════════════════════
# Serie temporal helper
# ═══════════════════════════════════════════

def _build_serie_chart(df_fb_s, df_tk_s, periodo):
    if df_fb_s.empty and df_tk_s.empty:
        return None
    if plataforma == "Facebook":
        df = df_fb_s[['semana','engagement','es_anomalia']].copy()
    elif plataforma == "TikTok":
        df = df_tk_s[['semana','views_suma','es_anomalia']].copy()
        df = df.rename(columns={'views_suma':'engagement'})
    else:
        merged = pd.merge(
            df_fb_s[['semana','engagement']].rename(columns={'engagement':'fb'}),
            df_tk_s[['semana','views_suma','es_anomalia']].rename(columns={'views_suma':'tk'}),
            on='semana', how='outer'
        ).fillna(0)
        merged['engagement'] = merged['fb'] + merged['tk']
        df = merged[['semana','engagement','es_anomalia']].copy()
    fecha_inicio = get_fecha_inicio(periodo)
    df = df[df['semana'] >= fecha_inicio].copy()
    if df.empty:
        return None
    df['media_movil'] = df['engagement'].rolling(4, min_periods=1).mean()
    df['ratio'] = np.where(df['media_movil'] > 0, df['engagement'] / df['media_movil'], 1.0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['semana'], y=df['engagement'], mode='lines',
        line=dict(color='#22d3ee', width=2.5), name='Actividad ciudadana',
        customdata=df[['ratio']].values,
        hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y:,.0f} interacciones<extra></extra>"))
    anom = df[df['es_anomalia'] == True]
    if not anom.empty:
        fig.add_trace(go.Scatter(x=anom['semana'], y=anom['engagement'], mode='markers',
            marker=dict(color='#ef4444', size=12), name='Semana inusual',
            hovertemplate="<b>Semana inusual</b><br>%{x|%d %b %Y}<extra></extra>"))
    fig.update_layout(plot_bgcolor='var(--bg-card)', paper_bgcolor='var(--bg-card)',
        font=dict(color='var(--fg-secondary)', size=10, family='IBM Plex Mono, monospace'),
        xaxis=dict(gridcolor='var(--border)', tickformat='%d %b\n%Y', tickfont=dict(size=9)),
        yaxis=dict(gridcolor='var(--border)', tickformat=','),
        margin=dict(l=0,r=0,t=10,b=0), height=250, showlegend=False)
    return fig


# ═══════════════════════════════════════════
# BLOQUE I — PULSO GENERAL
# ═══════════════════════════════════════════

def render_bloque1_pulso():
    _warn_dropped_null_dates()
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    _page_head(
        "RESUMEN EJECUTIVO / LECTURA CIUDADANA",
        "Pulso general de la conversación pública",
        "Síntesis ejecutiva del clima narrativo, intensidad de la conversación y concentración temática observada en el período seleccionado.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos para este período.")
        return

    # ── 1. CLIMA NARRATIVO ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Clima Narrativo</div><div class="section-subtitle">Indicador agregado de tono de la conversación.</div></div>', unsafe_allow_html=True)
    color_sem, texto_sem = calcular_semaforo(df_fb)
    sem_class = {'verde':'positive','amarillo':'warning','rojo':'critical'}.get(color_sem, 'positive')
    st.markdown(f'<div class="indicator indicator-{sem_class}"><div class="indicator-dot"></div><div class="indicator-text">{texto_sem}</div></div>', unsafe_allow_html=True)

    df_sent = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
    score_val = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos_val = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0

    interp = generar_interpretacion("semaforo", {
        'score': score_val, 'pct_negativo': pct_neg_val,
        'pct_positivo': pct_pos_val, 'indice_enojo': enojo_val
    })
    st.markdown(f'<div class="interpretation"><div class="interpretation-label">LECTURA EJECUTIVA</div><div class="interpretation-texto">{interp}</div></div>', unsafe_allow_html=True)

    total_comentarios = df_sent['total_comentarios'].sum() if not df_sent.empty else 0
    m = evaluar_muestra(total_comentarios)
    st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">{m["etiqueta"]}</p>', unsafe_allow_html=True)

    # ── 2. INTENSIDAD ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Intensidad de la Conversación</div><div class="section-subtitle">Volumen de interacción ciudadana sobre el contenido oficial.</div></div>', unsafe_allow_html=True)
    total_eng = (int(df_fb['engagement_total'].sum()) if not df_fb.empty else 0) + (int(df_tk['engagement_total'].sum()) if not df_tk.empty else 0)
    total_posts = len(df_fb) + len(df_tk)
    total_reacciones = (int(df_fb['total_reacciones'].sum()) if not df_fb.empty else 0) + (int(df_tk['likes'].sum()) if not df_tk.empty else 0)

    # KPI row ejecutiva (bordes superiores codificados por color)
    st.markdown(f"""
    <div class="kpi-row" style="grid-template-columns:repeat(3,1fr)">
        <div class="kpi-card kpi-card-eng">
            <div class="kpi-label">INTERACCIONES TOTALES</div>
            <div class="kpi-value">{total_eng:,}</div>
            <div class="kpi-meta">Engagement agregado del período</div>
        </div>
        <div class="kpi-card kpi-card-eff">
            <div class="kpi-label">CONTENIDO PUBLICADO</div>
            <div class="kpi-value">{total_posts:,}</div>
            <div class="kpi-meta">Posts y videos en la ventana</div>
        </div>
        <div class="kpi-card kpi-card-sent">
            <div class="kpi-label">REACCIONES TOTALES</div>
            <div class="kpi-value">{total_reacciones:,}</div>
            <div class="kpi-meta">Respuesta emocional ciudadana</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_fb_s, df_tk_s = cargar_series(FACEBOOK_DB_ACTIVA, TIKTOK_DB_ACTIVA)
    fig = _build_serie_chart(df_fb_s, df_tk_s, periodo)
    if fig:
        card_explicativa("Qué tanto la gente reacciona, comenta y comparte.", "Más alto: más gente se involucra. Más bajo: la gente lo ve pero no responde.")
        st.plotly_chart(fig, width='stretch')

    # ── 3. CONCENTRACIÓN TEMÁTICA ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Concentración Temática</div><div class="section-subtitle">Distribución del contenido por categoría — concentración vs. diversidad.</div></div>', unsafe_allow_html=True)
    df_cat = safe_query("SELECT item_id, categoria_nombre FROM post_categorias", FACEBOOK_DB_ACTIVA)
    if not df_cat.empty:
        conteo = df_cat['categoria_nombre'].value_counts()
        total_cat = conteo.sum()
        top_tema = conteo.index[0]
        share_top = conteo.iloc[0] / total_cat * 100
        hhi = sum((c/total_cat*100)**2 for c in conteo) / 10000
        st.markdown(f'<div class="panel"><div class="panel-head"><div class="panel-title">TEMA PRINCIPAL</div><div class="panel-meta">HHI {hhi:.2f} · CONCENTRACIÓN {share_top:.0f}%</div></div><div style="font-size:18px;color:var(--fg-primary);font-weight:600;margin-bottom:10px">{top_tema}</div><div class="bar-track" style="height:8px"><div class="bar-fill bar-fill-cy" style="width:{share_top:.0f}%"></div></div></div>', unsafe_allow_html=True)
        otros = conteo.iloc[1:].index.tolist()[:5]
        if otros:
            st.markdown(f'<p style="font-size:11px;color:var(--fg-muted);margin-top:6px">Otros temas en circulación: {", ".join(str(t) for t in otros)}</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Clasificación de temas requiere sentence-transformers (no instalado).</div>', unsafe_allow_html=True)

    st.markdown('<div class="status-info">El análisis de sentimiento se basa en los comentarios capturados, no en el 100% de la conversación. Los porcentajes son un proxy, no una medición exhaustiva.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# BLOQUE II — SEGMENTACIÓN DE AUDIENCIA
# ═══════════════════════════════════════════

def render_bloque2_audiencia():
    _page_head(
        "SEGMENTACIÓN / ANÁLISIS DE AUDIENCIA",
        "Estructura de públicos y voces de influencia",
        "Lectura proxy de la composición emocional de quienes participan en la conversación: simpatizantes, neutrales, críticos; nivel de polarización y emisores que concentran interacción.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    df_comentarios = cargar_comentarios_fb(FACEBOOK_DB_ACTIVA)
    if not hay_datos(df_comentarios, "Aún no hay comentarios procesados."):
        return

    # ── 1. MAPA DE PÚBLICOS ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Mapa de Públicos</div><div class="section-subtitle">Composición de la audiencia según el tono de sus comentarios.</div></div>', unsafe_allow_html=True)
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
        st.markdown('<p style="font-size:11px;color:var(--fg-muted)">Proxy: la base son comentarios, no personas individuales.</p>', unsafe_allow_html=True)

        m = evaluar_muestra(len(df_comentarios))
        st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">{m["etiqueta"]}</p>', unsafe_allow_html=True)

    # ── 2. POLARIZACIÓN ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Polarización</div><div class="section-subtitle">Peso de las posiciones extremas frente al centro.</div></div>', unsafe_allow_html=True)
    if not df_tmp.empty:
        p_extremos = ((df_tmp['score_sentimiento'].abs() > 0.5).sum() / len(df_tmp) * 100)
        p_centro = 100 - p_extremos
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head">
                <div class="panel-title">CENTRO VS EXTREMOS</div>
                <div class="panel-meta">|SCORE| &gt; 0.5 = EXTREMO</div>
            </div>
            <div class="bar-row">
                <div class="bar-row-label">CENTRO</div>
                <div class="bar-track"><div class="bar-fill bar-fill-blu" style="width:{p_centro:.1f}%"></div></div>
                <div class="bar-row-val">{p_centro:.0f}%</div>
            </div>
            <div class="bar-row">
                <div class="bar-row-label">EXTREMOS</div>
                <div class="bar-track"><div class="bar-fill bar-fill-red" style="width:{p_extremos:.1f}%"></div></div>
                <div class="bar-row-val">{p_extremos:.0f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:var(--fg-muted)">Extremos = comentarios con |score| &gt; 0.5 (muy positivos o muy negativos). Alto % indica audiencia polarizada.</p>', unsafe_allow_html=True)

    # ── 3. VOCES DE INFLUENCIA ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Voces de Influencia (proxy)</div><div class="section-subtitle">Páginas oficiales con mayor concentración de interacción.</div></div>', unsafe_allow_html=True)
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
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
    else:
        st.markdown('<div class="status-info">Sin datos de engagement para identificar voces.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# BLOQUE III — RIESGO Y AUTENTICIDAD
# ═══════════════════════════════════════════

def render_bloque3_riesgo():
    _page_head(
        "ALERTAS / GESTIÓN DE RIESGO REPUTACIONAL",
        "Riesgo, autenticidad y velocidad de propagación",
        "Señales tempranas sobre la salud de la conversación: posibles patrones coordinados, nivel de alerta agregado, dinámica de propagación y puntos críticos de fricción.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)
    df_sent = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
    df_fb_s, df_tk_s = cargar_series(FACEBOOK_DB_ACTIVA, TIKTOK_DB_ACTIVA)

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos para este período.")
        return

    # ── 1. AUTENTICIDAD ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Índice de Autenticidad (heurística)</div><div class="section-subtitle">Estabilidad del volumen diario como proxy de comportamiento orgánico.</div></div>', unsafe_allow_html=True)
    if not df_fb.empty and 'created_time' in df_fb.columns:
        daily = df_fb.copy()
        daily['fecha'] = daily['created_time'].dt.date
        daily_vol = daily.groupby('fecha').size()
        cv = daily_vol.std() / daily_vol.mean() if daily_vol.mean() > 0 else 0
        if cv < 0.5:
            label_aut = "ESTABLE · perfil orgánico"
            cls_aut = "kpi-card-sent"
        elif cv < 1.0:
            label_aut = "MODERADA · picos puntuales"
            cls_aut = "kpi-card-ctrl"
        else:
            label_aut = "VOLÁTIL · posible coordinación"
            cls_aut = "kpi-card-risk"
        st.markdown(f'<div class="kpi-card {cls_aut}" style="max-width:520px"><div class="kpi-label">COEFICIENTE DE VARIACIÓN</div><div class="kpi-value">{cv:.2f}</div><div class="kpi-meta">{label_aut}</div></div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:var(--fg-muted);margin-top:8px">Heurística: CV bajo indica volumen diario estable (más orgánico). CV alto sugiere picos súbitos (posible coordinación). No es detección de bots.</p>', unsafe_allow_html=True)

    # ── 2. NIVEL DE ALERTA ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Nivel de Alerta</div><div class="section-subtitle">Lectura agregada del semáforo reputacional.</div></div>', unsafe_allow_html=True)
    color_sem, texto_sem = calcular_semaforo(df_fb)
    score_val = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos_val = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    interp = generar_interpretacion("semaforo", {
        'score': score_val, 'pct_negativo': pct_neg_val,
        'pct_positivo': pct_pos_val, 'indice_enojo': enojo_val
    })
    sem_class = {'verde':'positive','amarillo':'warning','rojo':'critical'}.get(color_sem, 'positive')
    st.markdown(f'<div class="indicator indicator-{sem_class}"><div class="indicator-dot"></div><div class="indicator-text">{texto_sem}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="interpretation"><div class="interpretation-label">CONTEXTO</div><div class="interpretation-texto">{interp}</div></div>', unsafe_allow_html=True)

    # ── 3. VELOCIDAD DE PROPAGACIÓN ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Velocidad de Propagación</div><div class="section-subtitle">Variación semana actual vs. semana anterior.</div></div>', unsafe_allow_html=True)
    df_series = pd.concat([df_fb_s, df_tk_s], ignore_index=True) if not df_fb_s.empty or not df_tk_s.empty else pd.DataFrame()
    if not df_series.empty and 'engagement' in df_series.columns:
        df_series = df_series.sort_values('semana')
        recent = df_series.tail(2)
        if len(recent) == 2:
            prev = recent.iloc[0]['engagement']
            curr = recent.iloc[1]['engagement']
            if prev > 0:
                cambio = (curr - prev) / prev * 100
            else:
                cambio = 0
            if cambio > 15:
                flecha, color_v, cls_v = "↑", "var(--red)", "kpi-card-risk"
                nota = f"La conversación creció {cambio:.0f}% vs la semana anterior."
            elif cambio < -15:
                flecha, color_v, cls_v = "↓", "var(--blue)", "kpi-card-eff"
                nota = f"La conversación cayó {abs(cambio):.0f}% vs la semana anterior."
            else:
                flecha, color_v, cls_v = "→", "var(--fg-secondary)", ""
                nota = "Volumen estable respecto a la semana anterior."
            st.markdown(f'<div class="kpi-card {cls_v}" style="max-width:520px;display:flex;align-items:center;gap:18px"><div style="font-size:36px;color:{color_v};font-weight:700;line-height:1">{flecha}</div><div><div class="kpi-label">VARIACIÓN SEMANAL</div><div style="font-size:13px;color:var(--fg-primary);margin-top:4px">{nota}</div></div></div>', unsafe_allow_html=True)

    # ── 4. PUNTOS DE FRICCIÓN ──
    st.markdown('<div class="section-header"><div class="section-title">04 · Puntos de Fricción</div><div class="section-subtitle">Comentarios con mayor carga crítica del período.</div></div>', unsafe_allow_html=True)
    df_neg = cargar_comentarios_negativos()
    if not df_neg.empty:
        top_neg = df_neg.nsmallest(3, 'sentiment_score') if 'sentiment_score' in df_neg.columns else df_neg.head(3)
        for _, r in top_neg.iterrows():
            msg = str(r.get('message', ''))[:160]
            st.markdown(f'<div class="pattern-card pattern-card-critical"><div style="font-family:var(--font-mono);font-size:9px;letter-spacing:1.4px;color:var(--red);font-weight:700;margin-bottom:6px">SEÑAL CRÍTICA</div><p style="font-size:13px;color:var(--fg-primary);line-height:1.55;margin:0">"{msg}"</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Sin comentarios negativos destacados.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# BLOQUE IV — MEMORIA E INTELIGENCIA APLICADA
# ═══════════════════════════════════════════

def _b4_header(num: int, titulo: str, subtitulo: str = ""):
    st.markdown(
        f'<div class="memo-section"><div class="memo-section-number">{num:02d}</div>'
        f'<div class="memo-section-title">{titulo}</div></div>',
        unsafe_allow_html=True,
    )


def _b4_card_ia(num: int, titulo: str, tipo: str, ctx: dict):
    _b4_header(num, titulo)
    with st.spinner(f"Generando {titulo}…"):
        narrativa = generar_narrativa_ia(tipo, ctx)
    st.markdown(f'<p class="memo-body">{narrativa}</p>', unsafe_allow_html=True)


def render_bloque4_inteligencia():
    _page_head(
        "MEMORÁNDUM / INTELIGENCIA APLICADA",
        "Memo estratégico para toma de decisiones",
        "Síntesis ejecutiva en formato briefing: eco histórico, brechas percepción-realidad, temas emergentes, proyección y recomendación estratégica.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    st.markdown("""
    <div class="memo-container">
        <div class="memo-header">
            <div class="memo-title">MEMORÁNDUM EJECUTIVO</div>
            <div class="memo-ref">PANEL·SANTA ANA · Inteligencia Ciudadana · Análisis Estratégico</div>
        </div>
    """, unsafe_allow_html=True)

    df_sent = cargar_sentimiento_fb(FACEBOOK_DB_ACTIVA)
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB_ACTIVA)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB_ACTIVA, FACEBOOK_DB_ACTIVA)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    score = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    total_eng = (int(df_fb['engagement_total'].sum()) if not df_fb.empty else 0) + (int(df_tk['engagement_total'].sum()) if not df_tk.empty else 0)

    ctx = {
        "score": round(float(score), 3),
        "pct_negativo": round(float(pct_neg), 1),
        "pct_positivo": round(float(pct_pos), 1),
        "indice_enojo": round(float(enojo), 3),
        "interacciones": int(total_eng),
        "periodo": periodo,
    }

    _b4_card_ia(1, "Eco Histórico", "eco_historico", ctx)
    _b4_card_ia(2, "Lección Aprendida", "leccion", ctx)
    _b4_card_ia(3, "Brecha Percepción-Realidad", "brecha", ctx)

    # ── 04 + 05 Temas ──
    emergentes, extintos = [], []
    temas_disponibles = False
    df_cat = safe_query(
        "SELECT item_id, categoria_nombre, created_time FROM fb_posts "
        "LEFT JOIN post_categorias ON fb_posts.post_id = post_categorias.item_id",
        FACEBOOK_DB_ACTIVA,
    )
    if not df_cat.empty and 'created_time' in df_cat.columns and 'categoria_nombre' in df_cat.columns:
        df_cat['created_time'] = pd.to_datetime(df_cat['created_time'], errors='coerce')
        df_cat['semana'] = df_cat['created_time'].dt.to_period('W').dt.start_time
        df_cat = df_cat.dropna(subset=['categoria_nombre', 'semana'])
        if not df_cat.empty:
            temas_disponibles = True
            ultima_sem = df_cat['semana'].max()
            sem_actual = df_cat[df_cat['semana'] == ultima_sem]
            sem_prev = df_cat[df_cat['semana'] == ultima_sem - pd.Timedelta(days=7)]
            freq_actual = sem_actual['categoria_nombre'].value_counts()
            freq_prev = sem_prev['categoria_nombre'].value_counts()
            emergentes = [c for c in freq_actual.index if c not in freq_prev.index]
            extintos = [c for c in freq_prev.index if c not in freq_actual.index]

    _b4_header(4, "Temas Emergentes")
    if temas_disponibles:
        if emergentes:
            html_e = "".join(
                f'<div class="memo-item memo-item-positivo">+ {t}</div>'
                for t in emergentes[:8]
            )
        else:
            html_e = '<div class="memo-item memo-item-neutral">Sin temas nuevos esta semana.</div>'
        st.markdown(html_e, unsafe_allow_html=True)
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Clasificación de temas requiere sentence-transformers.</div>', unsafe_allow_html=True)

    _b4_header(5, "Temas en Extinción")
    if temas_disponibles:
        if extintos:
            html_x = "".join(
                f'<div class="memo-item memo-item-negativo">- {t}</div>'
                for t in extintos[:8]
            )
        else:
            html_x = '<div class="memo-item memo-item-neutral">Sin temas en extinción esta semana.</div>'
        st.markdown(html_x, unsafe_allow_html=True)
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Clasificación de temas requiere sentence-transformers.</div>', unsafe_allow_html=True)

    _b4_card_ia(6, "Contexto No Visible", "contexto", ctx)

    _b4_header(7, "Correlación Contenido/Reacción")
    df_posts, conteo_tipos, distorsion_alta, _por_semana = calcular_contagio_emocional()
    if not df_posts.empty:
        resonancia_pos = int(conteo_tipos.get('resonancia_positiva', 0))
        rechazo = int(conteo_tipos.get('rechazo_a_positivo', 0))
        total_p = len(df_posts)
        st.markdown(
            f'<div class="memo-item memo-item-positivo">Resonancia positiva: {resonancia_pos}/{total_p}</div>'
            f'<div class="memo-item memo-item-negativo">Rechazo a positivo: {rechazo}/{total_p}</div>',
            unsafe_allow_html=True,
        )
        if not distorsion_alta.empty:
            st.markdown('<div class="memo-section-number" style="margin-top:8px">DISTORSIÓN ALTA</div>', unsafe_allow_html=True)
            for _, r in distorsion_alta.head(3).iterrows():
                msg = str(r.get('message', '') or '')[:100]
                st.markdown(
                    f'<div class="memo-item memo-item-negativo">"{msg}"</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Sin datos suficientes para correlación contenido-reacción.</div>', unsafe_allow_html=True)

    _b4_header(8, "Comparativa Sectorial")
    df_ext = cargar_externos(EXTERNOS_DB_ACTIVA)
    if df_ext is not None and not df_ext.empty:
        col_fuente = 'page_name' if 'page_name' in df_ext.columns else ('source' if 'source' in df_ext.columns else None)
        n_fuentes = int(df_ext[col_fuente].nunique()) if col_fuente else 0
        n_menciones = len(df_ext)
        score_ext = float(df_ext['score_sentimiento'].mean()) if 'score_sentimiento' in df_ext.columns else 0.0
        tono_ext = "POSITIVO" if score_ext > 0.1 else ("MIXTO" if score_ext > -0.1 else "CRÍTICO")
        color_t = "var(--green)" if score_ext > 0.1 else ("var(--amber)" if score_ext > -0.1 else "var(--red)")
        st.markdown(
            f'<div class="memo-item memo-item-neutral">Fuentes externas: {n_fuentes}</div>'
            f'<div class="memo-item memo-item-neutral">Menciones totales: {n_menciones}</div>'
            f'<div class="memo-item memo-item-positivo" style="border-left-color:{color_t};color:{color_t}">Tono externo: {tono_ext}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="memo-item memo-item-neutral">Sin datos externos para comparativa sectorial.</div>', unsafe_allow_html=True)

    _b4_card_ia(9, "Proyección de Escenario", "proyeccion", ctx)
    _b4_card_ia(10, "Recomendación Estratégica", "recomendacion", ctx)
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════
# DISPATCH PRINCIPAL
# ═══════════════════════════════════════════

if vista == "Dashboard":
    tab_pulso, tab_audiencia, tab_riesgo, tab_inteligencia = st.tabs([
        "RESUMEN EJECUTIVO", "AUDIENCIA",
        "ALERTAS", "MEMO ESTRATÉGICO"
    ])
    with tab_pulso:
        render_bloque1_pulso()
    with tab_audiencia:
        render_bloque2_audiencia()
    with tab_riesgo:
        render_bloque3_riesgo()
    with tab_inteligencia:
        render_bloque4_inteligencia()

    # Docstrip footer ejecutivo
    modo_lbl = "MODO PRUEBA" if st.session_state.modo_prueba else ""
    _docstrip(periodo, plataforma, fecha_str, modo_lbl)

elif vista == "Cargar contenido":
    _page_head(
        "OPERACIÓN / CARGA DE CONTENIDO",
        "Centro de ingesta de informes y evidencia",
        "Cargue informes consolidados, evidencia documental y briefings diarios. Cada documento se incorpora al pipeline de inteligencia."
    )
    st.markdown("""
    <div class="doc-center">
        <div class="doc-label">
            <div class="doc-icon-box">PDF</div>
            <div class="doc-info">
                <div class="doc-filename">Informe Consolidado del Día</div>
                <div class="doc-meta">CENTRO DE DOCUMENTACIÓN EJECUTIVA · BRIEFING DIARIO CORPORATIVO</div>
            </div>
        </div>
        <div class="doc-empty">
            <div class="doc-empty-label">Sin documento disponible. El informe consolidado se genera automáticamente al procesar los datos del día.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    seccion_cargar_contenido()

elif vista == "Notas metodológicas":
    render_notas_metodologicas()
