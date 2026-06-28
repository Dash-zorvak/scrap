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
    FB_PAGES_OFICIALES, FB_REACTIONS, TK_ENGAGEMENT,
    TK_ACCOUNTS, OUTPUT_DIR, MIN_COMENTARIOS_MUESTRA,
)
from dashboard.muestra import evaluar_muestra
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
from dashboard.dash_inteligencia import (
    cargar_iq,
    cargar_zonas_resumen,
    cargar_alertas_cambridge,
    traducir_alerta,
    cargar_cruce_tema_zona,
    cargar_perfil_ocean,
    cargar_temas_latentes,
)
from dashboard.dash_temas import render_temas_emergentes
from dashboard.dash_pulso import (
    calcular_clima_diario,
    calcular_intensidad_vs_promedio,
    calcular_concentracion,
)
from dashboard.dash_audiencia import calcular_polarizacion
from dashboard.dash_riesgo import (
    calcular_autenticidad,
    calcular_nivel_alerta,
    calcular_propagacion_24_48,
    agrupar_fricciones,
)
from dashboard.dash_memoria import (
    clasificar_evolucion_temas,
    comparar_sectorial,
)

# ─── Estado de sesión ───────────────────
if "lote_ingreso" not in st.session_state:
    st.session_state["lote_ingreso"] = []


def leyenda_grafica(elementos):
    items_html = "".join(
        '<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">'
        '<span style="font-size:14px;color:{};min-width:18px;font-weight:600;line-height:1.4;font-family:IBM Plex Mono,monospace">'
        '{}</span>'
        '<div>'
        '<span style="font-size:11px;color:var(--fg-primary);font-weight:600;font-family:Inter,sans-serif">'
        '{}</span>'
        '<span style="font-size:11px;color:var(--fg-muted);margin-left:4px;font-family:Inter,sans-serif">'
        '— {}</span></div></div>'.format(
            e['color'], e['simbolo'], e['label'], e['descripcion']
        )
        for e in elementos
    )
    return (
        '<div style="background:var(--bg-card);border:1px solid var(--border);'
        'padding:12px 16px;margin-bottom:10px">'
        '<p style="font-size:9px;color:var(--fg-muted);margin:0 0 8px 0;'
        'font-weight:600;letter-spacing:1.5px;text-transform:uppercase;font-family:IBM Plex Mono,monospace">'
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
    conn = sqlite3.connect(FACEBOOK_DB)
    max_fb = pd.read_sql("SELECT MAX(created_time) as m FROM fb_engagement", conn).iloc[0]['m']
    conn.close()
    conn = sqlite3.connect(TIKTOK_DB)
    max_tk = pd.read_sql("SELECT MAX(created_at) as m FROM tiktok_engagement", conn).iloc[0]['m']
    conn.close()
    fechas = []
    if max_fb: fechas.append(pd.Timestamp(max_fb))
    if max_tk: fechas.append(pd.Timestamp(max_tk))
    ultima_fecha = max(fechas) if fechas else datetime.now()
    dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    meses_short = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
    fecha_str = f"{dias[ultima_fecha.weekday()]} {ultima_fecha.day} de {meses[ultima_fecha.month-1]}, {ultima_fecha.year}"
    fecha_corta = f"{ultima_fecha.day:02d} {meses_short[ultima_fecha.month-1]} {ultima_fecha.year}"
except Exception:
    fecha_str = "No disponible"
    fecha_corta = "N/D"

# ─── Topbar institucional ──────────────────
st.markdown(f"""
<div class="topbar">
    <div class="topbar-brand">PANEL <span class="sep">·</span> SANTA ANA <span class="sep">/</span> <span class="who">Inteligencia Ciudadana</span></div>
    <div class="topbar-meta">ACTUALIZADO <span class="acc">·</span> {fecha_str.upper()}</div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR · CONSOLA EJECUTIVA ─────────────

# Header institucional
st.sidebar.markdown("""
<div class="sys-header">
    <div class="sys-brand">PANEL·SANTA ANA</div>
    <div class="sys-brand-sub">INTELIGENCIA CIUDADANA</div>
</div>
""", unsafe_allow_html=True)

# Ticker de sistema · estado operacional + feed
st.sidebar.markdown(f"""
<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--r-sm);padding:11px 13px;margin-bottom:18px">
    <div style="display:flex;align-items:center;justify-content:space-between;font-family:var(--font-mono);font-size:9px;letter-spacing:1.4px;color:var(--fg-muted);font-weight:600;text-transform:uppercase">
        <span>SYS</span>
        <span style="display:flex;align-items:center;gap:6px">
            <span style="width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 0 3px rgba(34,197,94,0.18);display:inline-block"></span>
            <span style="color:var(--green);letter-spacing:1.2px">OPERACIONAL</span>
        </span>
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;font-family:var(--font-mono);font-size:9px;letter-spacing:1.2px;color:var(--fg-muted);font-weight:600;margin-top:9px;text-transform:uppercase">
        <span>FEED</span>
        <span style="color:var(--accent)">{fecha_corta}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sección · Parámetros
st.sidebar.markdown('<div class="sys-section-label" style="color:var(--accent);display:flex;align-items:center;gap:6px"><span style="font-size:8px">▣</span><span>PARÁMETROS</span></div>', unsafe_allow_html=True)

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

# Sección · Consola
st.sidebar.markdown('<div class="sys-section-label" style="color:var(--accent);margin-top:18px;display:flex;align-items:center;gap:6px"><span style="font-size:8px">▣</span><span>CONSOLA</span></div>', unsafe_allow_html=True)

vista = st.sidebar.radio("VISTA", [
    "Dashboard", "Cargar contenido", "Notas metodológicas"
])

# Footer institucional
st.sidebar.markdown(f"""
<div style="margin-top:26px;padding-top:14px;border-top:1px solid var(--border);font-family:var(--font-mono);color:var(--fg-muted);letter-spacing:0.4px;line-height:1.6">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;font-size:9px;text-transform:uppercase;letter-spacing:1.4px;font-weight:600">
        <span>ACTUALIZADO</span>
        <span style="color:var(--accent)">{fecha_corta}</span>
    </div>
    <div style="color:var(--fg-secondary);font-size:9px;line-height:1.5">{fecha_str}</div>
    <div style="color:var(--fg-dim);font-size:8.5px;margin-top:12px;letter-spacing:1px;text-transform:uppercase;border-top:1px solid var(--border-soft);padding-top:8px">PANEL·SANTA ANA <span style="color:var(--accent-2)">·</span> v1.0 <span style="color:var(--accent-2)">·</span> CONFIDENCIAL</div>
</div>
""", unsafe_allow_html=True)

# ─── HELPERS UI ────────────────

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
            db = FACEBOOK_DB if table == "fb_posts" else TIKTOK_DB
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
        f'<div style="margin-top:8px;font-size:11px;color:var(--amber);font-family:Inter,sans-serif;border-top:1px solid var(--border);padding-top:6px">'
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


# ─── REFERENCIAS A PUBLICACIONES (verificación de origen) ──────────
# Permiten al lector abrir el post real en Facebook y comprobar de dónde salen
# los datos (que no se inventan). La DB guarda post_url al cargar contenido.

def _post_links_html(rows, max_links=8):
    chips = ""
    vistos = set()
    for r in rows:
        try:
            url = str((r.get("post_url") if hasattr(r, "get") else r["post_url"]) or "").strip()
        except Exception:
            url = ""
        if not url or url in vistos:
            continue
        vistos.add(url)
        try:
            page = str((r.get("page_name") if hasattr(r, "get") else r["page_name"]) or "Publicación")
        except Exception:
            page = "Publicación"
        try:
            ft = r.get("created_time") if hasattr(r, "get") else r["created_time"]
        except Exception:
            ft = None
        etiqueta = page[:32]
        if ft is not None and str(ft) not in ("", "NaT", "None"):
            try:
                etiqueta += " · " + pd.Timestamp(ft).strftime("%d %b")
            except Exception:
                pass
        chips += (
            '<a href="' + url + '" target="_blank" rel="noopener" '
            'style="display:inline-block;font-size:11px;padding:3px 9px;margin:3px 4px 0 0;'
            'background:var(--bg-elevated);border:1px solid var(--border);border-radius:12px;'
            'color:var(--accent);text-decoration:none;font-family:Inter,sans-serif">'
            '🔗 ' + etiqueta + '</a>'
        )
        if chips.count("<a ") >= max_links:
            break
    return chips


def referencias_publicaciones(post_ids=None, limit=8, titulo="PUBLICACIONES DE ORIGEN"):
    """Renderiza enlaces clickeables a las publicaciones que sustentan un dato.

    Si post_ids viene dado, enlaza esas publicaciones; si no, las más recientes
    con enlace. No muestra nada si no hay URLs guardadas.
    """
    try:
        if post_ids is not None:
            ids = [str(p) for p in post_ids if p is not None and str(p) != ""]
            if not ids:
                return
            ids = list(dict.fromkeys(ids))[:limit]
            marcadores = ",".join("?" for _ in ids)
            df = safe_query(
                "SELECT post_id, page_name, created_time, post_url FROM fb_posts "
                "WHERE post_id IN (" + marcadores + ") "
                "AND post_url IS NOT NULL AND TRIM(post_url) != ''",
                FACEBOOK_DB, params=ids,
            )
        else:
            df = safe_query(
                "SELECT post_id, page_name, created_time, post_url FROM fb_posts "
                "WHERE post_url IS NOT NULL AND TRIM(post_url) != '' "
                "ORDER BY created_time DESC LIMIT ?",
                FACEBOOK_DB, params=[int(limit)],
            )
    except Exception:
        df = None
    if df is None or len(df) == 0:
        return
    chips = _post_links_html(df.to_dict("records"), max_links=limit)
    if not chips:
        return
    st.markdown(
        '<div style="margin:2px 0 16px 0">'
        '<div style="font-size:9px;color:var(--fg-muted);font-weight:600;'
        'letter-spacing:1.5px;text-transform:uppercase;'
        'font-family:IBM Plex Mono,monospace;margin-bottom:4px">'
        + titulo + ' — abrí el post para verificar</div>' + chips + '</div>',
        unsafe_allow_html=True,
    )


def _post_ids_por_categoria(tema):
    try:
        df = safe_query(
            "SELECT item_id FROM post_categorias WHERE categoria_nombre = ?",
            FACEBOOK_DB, params=[str(tema)],
        )
        return df["item_id"].tolist() if df is not None and not df.empty else []
    except Exception:
        return []


def _post_ids_por_tema_comentarios(tema):
    try:
        df = safe_query(
            "SELECT DISTINCT post_id FROM fb_comments WHERE topic_category = ?",
            FACEBOOK_DB, params=[str(tema)],
        )
        return df["post_id"].tolist() if df is not None and not df.empty else []
    except Exception:
        return []


def referencias_por_categoria(tema, limit=8):
    ids = _post_ids_por_categoria(tema)
    if ids:
        referencias_publicaciones(post_ids=ids, limit=limit, titulo="PUBLICACIONES SOBRE «" + str(tema) + "»")


def referencias_por_tema_comentarios(tema, limit=6):
    ids = _post_ids_por_tema_comentarios(tema)
    if ids:
        referencias_publicaciones(post_ids=ids, limit=limit, titulo="PUBLICACIONES DE «" + str(tema) + "»")


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


def _docstrip(periodo_lbl: str, plataforma_lbl: str, fecha_lbl: str):
    """Pie ejecutivo con metadatos de la consulta."""
    st.markdown(f"""
    <div class="docstrip-footer">
        <div>PANEL·SANTA ANA <span class="sep">·</span> INTELIGENCIA CIUDADANA</div>
        <div>PERÍODO <span class="acc">{periodo_lbl.upper()}</span> <span class="sep">·</span> FUENTE <span class="acc">{plataforma_lbl.upper()}</span> <span class="sep">·</span> {fecha_lbl.upper()}</div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════
# NOTAS METODOLÓGICAS
# ════════════════════════════════════════════════════════════════════

def render_notas_metodologicas():
    _page_head(
        "REFERENCIA METODOLÓGICA / LÍMITES DEL SISTEMA",
        "Notas metodológicas",
        "Los supuestos, las simplificaciones y los márgenes de error sobre los que se construye esta lectura. Léelos antes de tomar decisiones con estos datos."
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
        '<div class="status-info">Las reacciones son una señal del tono emocional, no un test psicológico validado. '
        'Léelas como pulso del ánimo colectivo, no como diagnóstico.</div>',
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


# ════════════════════════════════════════════════════════════════════
# Serie temporal helper
# ════════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════════
# BLOQUE I — PULSO GENERAL
# ════════════════════════════════════════════════════════════════════

def render_bloque1_pulso():
    _warn_dropped_null_dates()
    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB, FACEBOOK_DB)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)

    _page_head(
        "PULSO GENERAL / LECTURA CIUDADANA",
        "Pulso general de la conversación pública",
        "Síntesis ejecutiva del clima narrativo, intensidad de la conversación y concentración temática observada en el período seleccionado.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos para este período.")
        return

    # Métricas de sentimiento (alimentan el cierre factual).
    df_sent = cargar_sentimiento_fb(FACEBOOK_DB)
    score_val = df_sent['score_sentimiento'].mean() if not df_sent.empty else 0
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    pct_pos_val = df_sent['pct_positivo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    total_comentarios = df_sent['total_comentarios'].sum() if not df_sent.empty else 0

    # ── 1. CLIMA NARRATIVO — tono dominante del día + tendencia vs ayer ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Clima Narrativo</div><div class="section-subtitle">Tono dominante del día y su tendencia frente al día anterior.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "El tono (favorable, neutro o adverso) de los comentarios del último día con datos, y si mejoró o empeoró frente al día anterior.",
        "La barra reparte los comentarios en favorables, neutros y adversos. La flecha dice si lo favorable subió o bajó respecto al día previo.",
        "Se pondera por la cantidad de comentarios de cada publicación, no por número de publicaciones.",
    )
    clima = calcular_clima_diario(safe_query(
        "SELECT fs.pct_positivo, fs.pct_negativo, fs.total_comentarios, fe.created_time "
        "FROM fb_sentimiento fs JOIN fb_engagement fe ON fs.post_id = fe.post_id",
        FACEBOOK_DB,
    ))
    if clima:
        fav = clima['pct_favorable']; neu = clima['pct_neutro']; adv = clima['pct_adverso']
        dom = max((fav, 'Favorable'), (neu, 'Neutro'), (adv, 'Adverso'), key=lambda x: x[0])[1]
        delta = clima.get('delta_favorable')
        if delta is None:
            trend = '<span style="color:var(--fg-muted)">Sin día previo para comparar.</span>'
        elif delta > 1:
            trend = f'<span style="color:var(--green)">▲ +{delta:.1f} pts favorables respecto al día anterior.</span>'
        elif delta < -1:
            trend = f'<span style="color:var(--red)">▼ {delta:.1f} pts favorables respecto al día anterior.</span>'
        else:
            trend = f'<span style="color:var(--fg-secondary)">→ Estable respecto al día anterior ({delta:+.1f} pts).</span>'
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title">TONO DOMINANTE · {dom.upper()}</div><div class="panel-meta">{clima['n_comentarios']:,} COMENTARIOS · {clima['fecha']}</div></div>
            <div class="bar-tri" style="height:16px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{fav:.1f}%"></span>
                <span class="bar-tri-neu" style="width:{neu:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{adv:.1f}%"></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:12px">
                <span style="color:var(--green)">Favorable {fav:.0f}%</span>
                <span style="color:var(--amber)">Neutro {neu:.0f}%</span>
                <span style="color:var(--red)">Adverso {adv:.0f}%</span>
            </div>
            <div style="margin-top:10px;font-size:13px">{trend}</div>
        </div>
        """, unsafe_allow_html=True)
        m = evaluar_muestra(clima['n_comentarios'])
        st.markdown(f'<p style="font-size:11px;color:var(--fg-muted)">{m["etiqueta"]}</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes comentarios con fecha para calcular el clima del día.</div>', unsafe_allow_html=True)

    # ── 2. INTENSIDAD — volumen del último día vs promedio diario de la semana ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Intensidad de la Conversación</div><div class="section-subtitle">Volumen de interacción del último día frente al promedio diario de la semana.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Cuánta interacción (reacciones, comentarios, compartidos) generó el último día frente al promedio diario de la semana.",
        "Si la barra del último día es más larga que la del promedio, hubo más movimiento de lo habitual; si es más corta, hubo menos.",
    )
    intens = calcular_intensidad_vs_promedio(df_fb, df_tk)
    if intens:
        vol_hoy = intens['vol_hoy']; prom = intens['promedio']; pct = intens['pct_dif']
        maxv = max(vol_hoy, prom, 1)
        if pct > 15:
            col_hoy = 'var(--red)'; lectura = f'El último día registró {pct:.0f}% más interacción que el promedio de la semana.'
        elif pct < -15:
            col_hoy = 'var(--blue)'; lectura = f'El último día registró {abs(pct):.0f}% menos interacción que el promedio de la semana.'
        else:
            col_hoy = 'var(--accent)'; lectura = 'El último día se mantiene en línea con el promedio de la semana.'
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title">ÚLTIMO DÍA VS PROMEDIO SEMANAL</div><div class="panel-meta">{intens['fecha_hoy']} · {intens['n_ref']} DÍAS DE REFERENCIA</div></div>
            <div class="bar-row"><div class="bar-row-label">ÚLTIMO DÍA</div><div class="bar-track"><div class="bar-fill" style="width:{vol_hoy / maxv * 100:.1f}%;background:{col_hoy}"></div></div><div class="bar-row-val">{vol_hoy:,.0f}</div></div>
            <div class="bar-row"><div class="bar-row-label">PROMEDIO</div><div class="bar-track"><div class="bar-fill bar-fill-blu" style="width:{prom / maxv * 100:.1f}%"></div></div><div class="bar-row-val">{prom:,.0f}</div></div>
            <div style="margin-top:10px;font-size:13px;color:var(--fg-primary)">{lectura}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes días con interacción para comparar contra el promedio semanal.</div>', unsafe_allow_html=True)

    # ── 3. CONCENTRACIÓN TEMÁTICA — desglose completo de todos los temas ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Concentración Temática</div><div class="section-subtitle">Cómo se reparte la conversación entre todos los temas, no solo el principal.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Si la conversación gira en torno a un solo tema o está repartida entre varios.",
        "Cada color es un tema y su porcentaje es la parte de la conversación que ocupa. Mientras más repartidos los colores, más diversa es la conversación.",
        "HHI alto = un tema concentra casi todo; HHI bajo = conversación fragmentada.",
    )
    df_cat = safe_query("SELECT item_id, categoria_nombre FROM post_categorias", FACEBOOK_DB)
    conc = calcular_concentracion(df_cat['categoria_nombre'].value_counts().to_dict()) if not df_cat.empty else None
    if conc:
        col_estado = {'dominado': 'var(--red)', 'liderado': 'var(--amber)', 'fragmentado': 'var(--green)'}.get(conc['nivel'], 'var(--accent)')
        ramas = conc.get('ramas', [])
        paleta = ['var(--accent)', '#a78bfa', '#f59e0b', '#34d399', '#f472b6', '#60a5fa', '#fbbf24', '#4ade80', '#fb7185', '#818cf8']
        segmentos = ""
        filas = ""
        for i, rama in enumerate(ramas):
            c = paleta[i % len(paleta)]
            segmentos += f'<span title="{rama["tema"]} {rama["share"]:.0f}%" style="display:inline-block;height:100%;background:{c};width:{rama["share"]:.1f}%"></span>'
            filas += (
                '<div style="display:flex;align-items:center;gap:8px;margin-top:6px;font-size:12px">'
                f'<span style="width:10px;height:10px;border-radius:2px;background:{c};display:inline-block;flex:none"></span>'
                f'<span style="flex:1;color:var(--fg-primary)">{rama["tema"]}</span>'
                f'<span style="color:var(--fg-secondary)">{rama["n"]} publicaciones · {rama["share"]:.0f}%</span>'
                '</div>'
            )
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_estado}">{conc['estado'].upper()}</div><div class="panel-meta">{conc['n_temas']} TEMAS · HHI {conc['hhi']:.2f}</div></div>
            <div class="bar-tri" style="height:16px;border-radius:3px">{segmentos}</div>
            <div style="margin-top:12px">{filas}</div>
        </div>
        """, unsafe_allow_html=True)
        referencias_por_categoria(conc['top_tema'])
    else:
        st.markdown('<div class="status-info">Clasificación de temas no disponible para este período.</div>', unsafe_allow_html=True)

    st.markdown('<div class="status-info">Este análisis está basado al 100% en los comentarios extraídos y analizados de las publicaciones revisadas.</div>', unsafe_allow_html=True)

    # ── CIERRE FACTUAL — lectura en una frase ──
    interp_cierre = generar_interpretacion("semaforo", {
        'score': score_val, 'pct_negativo': pct_neg_val,
        'pct_positivo': pct_pos_val, 'indice_enojo': enojo_val,
        'total_comentarios': int(total_comentarios),
    })
    st.markdown(f'<div class="interpretation" style="margin-top:16px"><div class="interpretation-label">🔎 En una frase:</div><div class="interpretation-texto">{interp_cierre}</div></div>', unsafe_allow_html=True)
    referencias_publicaciones(limit=10, titulo="PUBLICACIONES ANALIZADAS")


# ════════════════════════════════════════════════════════════════════
# BLOQUE II — SEGMENTACIÓN DE AUDIENCIA
# ════════════════════════════════════════════════════════════════════

def render_bloque2_audiencia():
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


# ════════════════════════════════════════════════════════════════════
# BLOQUE III — RIESGO Y AUTENTICIDAD
# ════════════════════════════════════════════════════════════════════

def render_bloque3_riesgo():
    _page_head(
        "RIESGO Y AUTENTICIDAD / GESTIÓN DE RIESGO REPUTACIONAL",
        "Riesgo, autenticidad y velocidad de propagación",
        "Señales tempranas sobre la salud de la conversación: patrones coordinados, necesidad de respuesta institucional, proyección a 24-48h y puntos críticos de fricción.",
        f'PERÍODO <span class="acc">{periodo.upper()}</span> <span class="sep">·</span> PLATAFORMA <span class="acc">{plataforma.upper()}</span>'
    )

    df_fb_raw = cargar_fb_engagement(FACEBOOK_DB)
    df_tk_raw = cargar_tk_engagement(TIKTOK_DB, FACEBOOK_DB)
    df_fb, df_tk = filtrar_por_periodo_plataforma(df_fb_raw, df_tk_raw, periodo, plataforma)
    df_sent = cargar_sentimiento_fb(FACEBOOK_DB)
    df_coment = cargar_comentarios_fb(FACEBOOK_DB)
    df_coment_raw = safe_query("SELECT message, sentiment, sentiment_score, topic_category FROM fb_comments", FACEBOOK_DB)

    if df_fb.empty and df_tk.empty:
        hay_datos(df_fb, "No hay datos para este período.")
        return

    # ── 1. AUTENTICIDAD — orgánico vs coordinado/sospechoso ──
    st.markdown('<div class="section-header"><div class="section-title">01 · Índice de Autenticidad</div><div class="section-subtitle">Proporción de conversación orgánica frente a patrones coordinados o sospechosos (mensajes repetidos).</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué parte de la conversación parece orgánica y qué parte parece copia-pega coordinado (mensajes idénticos repetidos).",
        "La barra verde es lo orgánico; la roja, lo sospechoso. Abajo se listan los mensajes que más se repiten.",
        "No detecta bots: solo mide repetición de texto idéntico.",
    )
    aut = calcular_autenticidad(df_coment_raw['message']) if not df_coment_raw.empty and 'message' in df_coment_raw.columns else None
    if aut:
        col_aut = {'organico': 'var(--green)', 'mixto': 'var(--amber)', 'coordinado': 'var(--red)'}.get(aut['nivel'], 'var(--accent)')
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_aut}">{aut['estado'].upper()}</div><div class="panel-meta">{aut['n_total']:,} COMENTARIOS · {aut['n_grupos']} GRUPOS REPETIDOS</div></div>
            <div class="bar-tri" style="height:16px;border-radius:3px">
                <span class="bar-tri-pos" style="width:{aut['pct_organico']:.1f}%"></span>
                <span class="bar-tri-neg" style="width:{aut['pct_sospechoso']:.1f}%"></span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:10px;font-size:12px">
                <span style="color:var(--green)">Orgánico {aut['pct_organico']:.0f}%</span>
                <span style="color:var(--red)">Sospechoso {aut['pct_sospechoso']:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if aut['ejemplos']:
            ej_html = "".join(f'<div class="bar-row"><div class="bar-row-label">\"{e["texto"][:80]}\"</div><div class="bar-row-val">×{e["veces"]}</div></div>' for e in aut['ejemplos'])
            st.markdown(f'<div class="panel" style="margin-top:8px"><div class="panel-head"><div class="panel-title">MENSAJES MÁS REPETIDOS</div></div>{ej_html}</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:var(--fg-muted)">Sospechoso = mensajes idénticos repetidos (posible copia-pega coordinado). No es detección de bots.</p>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">Aún no hay suficientes comentarios para evaluar autenticidad.</div>', unsafe_allow_html=True)

    # ── 2. NIVEL DE ALERTA — necesidad de respuesta institucional ──
    st.markdown('<div class="section-header"><div class="section-title">02 · Nivel de Alerta</div><div class="section-subtitle">Qué tan urgente es responder y, sobre todo, a qué responder.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Qué tan urgente es que la institución responda, en semáforo: verde (tranquilo), amarillo (preparar) o rojo (responder ya).",
        "El color resume el nivel de molestia. Abajo se nombran los temas concretos a los que habría que responder y qué podría crecer.",
    )
    pct_neg_val = df_sent['pct_negativo'].mean() if not df_sent.empty else 0
    enojo_val = df_fb['indice_enojo'].mean() if not df_fb.empty and 'indice_enojo' in df_fb.columns else 0
    pol_b3 = calcular_polarizacion(df_coment['score_sentimiento']) if not df_coment.empty and 'score_sentimiento' in df_coment.columns else None
    balance_b3 = pol_b3['balance'] if pol_b3 else None
    fricciones = agrupar_fricciones(df_coment_raw)
    alerta = calcular_nivel_alerta(pct_negativo=pct_neg_val, indice_enojo=enojo_val, balance_confrontacion=balance_b3, n_fricciones=len(fricciones), temas_friccion=fricciones)
    sem_class = {'verde': 'positive', 'amarillo': 'warning', 'rojo': 'critical'}.get(alerta['color'], 'positive')
    emoji_sem = {'verde': '🟢', 'amarillo': '🟡', 'rojo': '🔴'}.get(alerta['color'], '⚪')
    st.markdown(f'<div class="indicator indicator-{sem_class}"><div class="indicator-dot"></div><div style="flex:1"><div style="font-weight:600;font-size:14px;margin-bottom:2px">{emoji_sem} {alerta["titular"]}</div><div style="font-size:13px;color:var(--fg-secondary)">{alerta["accion"]}</div></div></div>', unsafe_allow_html=True)
    if alerta.get("detalle"):
        st.markdown(f'<div class="interpretation" style="margin-top:10px"><div class="interpretation-label">QUÉ SIGNIFICA</div><div class="interpretation-texto">{alerta["detalle"]}</div></div>', unsafe_allow_html=True)
    factores = alerta.get("factores", [])
    if factores:
        chips = "".join(f'<span style="font-size:11px;padding:3px 9px;margin:3px 4px 0 0;display:inline-block;background:var(--bg-elevated);border:1px solid var(--border);border-radius:12px;color:var(--fg-secondary)">{f}</span>' for f in factores)
        st.markdown(f'<div style="margin-top:8px"><div style="font-size:9px;color:var(--fg-muted);font-weight:600;letter-spacing:1.5px;text-transform:uppercase;font-family:IBM Plex Mono,monospace;margin-bottom:4px">POR QUÉ ESTE NIVEL</div>{chips}</div>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:11px;color:var(--fg-muted);margin-top:8px">Índice de necesidad de respuesta: {alerta["riesgo"]:.0f}/100 — combina cuántos comentarios son negativos, el enojo en las reacciones, la confrontación y los temas de fricción.</p>', unsafe_allow_html=True)
    if fricciones:
        ids_alerta = []
        for fr in fricciones[:3]:
            ids_alerta.extend(_post_ids_por_tema_comentarios(fr["tema"]))
        referencias_publicaciones(post_ids=ids_alerta, limit=8, titulo="PUBLICACIONES DETRÁS DE LA ALERTA")

    alertas = cargar_alertas_cambridge(FACEBOOK_DB)
    if alertas:
        st.markdown('<p style="font-size:11px;color:var(--fg-muted);margin-top:10px;font-weight:600">SEÑALES DE COMPORTAMIENTO DETECTADAS</p>', unsafe_allow_html=True)
        for a in alertas:
            ta = traducir_alerta(a)
            color_class = {"🟢": "positive", "🟡": "warning", "🔴": "critical"}.get(ta["color"], "warning")
            st.markdown(f'<div class="indicator indicator-{color_class}" style="margin-bottom:8px"><div class="indicator-dot"></div><div style="flex:1"><div style="font-weight:600;font-size:13px">{ta["color"]} {ta["titular"]}</div><div style="font-size:12px;color:var(--fg-secondary)">{ta["lectura"]}</div></div></div>', unsafe_allow_html=True)

    # ── 3. VELOCIDAD DE PROPAGACIÓN — proyección 24-48h ──
    st.markdown('<div class="section-header"><div class="section-title">03 · Velocidad de Propagación</div><div class="section-subtitle">Hacia dónde va la conversación en las próximas 24 a 48 horas.</div></div>', unsafe_allow_html=True)
    card_explicativa(
        "Hacia dónde va la interacción en las próximas 24 a 48 horas si sigue la tendencia actual.",
        "Compara hoy con la proyección a 24h y 48h. Es una estimación por tendencia, no una certeza.",
    )
    prop = calcular_propagacion_24_48(df_fb)
    if prop:
        col_p = {'acelerando': 'var(--red)', 'desacelerando': 'var(--blue)', 'estable': 'var(--fg-secondary)'}.get(prop['tendencia'], 'var(--accent)')
        maxv = max(prop['hoy'], prop['proy_24h'], prop['proy_48h'], 1)
        st.markdown(f"""
        <div class="panel">
            <div class="panel-head"><div class="panel-title" style="color:{col_p}">{prop['flecha']} {prop['tendencia'].upper()}</div><div class="panel-meta">{prop['n_dias']} DÍAS DE TENDENCIA</div></div>
            <div class="bar-row"><div class="bar-row-label">HOY</div><div class="bar-track"><div class="bar-fill bar-fill-cy" style="width:{prop['hoy'] / maxv * 100:.1f}%"></div></div><div class="bar-row-val">{prop['hoy']:,.0f}</div></div>
            <div class="bar-row"><div class="bar-row-label">PROY. +24H</div><div class="bar-track"><div class="bar-fill" style="width:{prop['proy_24h'] / maxv * 100:.1f}%;background:{col_p}"></div></div><div class="bar-row-val">{prop['proy_24h']:,.0f} ({prop['pct_24h']:+.0f}%)</div></div>
            <div class="bar-row"><div class="bar-row-label">PROY. +