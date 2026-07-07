"""Componentes de interfaz compartidos del dashboard.

Helpers de presentación reutilizados por los cuatro bloques: cabeceras, cards
explicativas («cómo leer esto»), avisos, notas metodológicas y, sobre todo, los
enlaces de referencia que permiten abrir la publicación de origen para verificar
que los datos no se inventan.

Estos helpers no dependen de los selectores globales del sidebar; cuando un
bloque necesita el período o la plataforma, los recibe como argumentos.

Nota sobre plataforma: las referencias de origen consultan publicaciones de
Facebook (tabla fb_posts). Cuando el filtro activo es solo TikTok, NO se muestran
esas referencias para no exhibir evidencia de una plataforma distinta a la
seleccionada. Las funciones aceptan `plataforma` y hacen early-return en ese caso.
"""

import os
import sqlite3

import pandas as pd

import streamlit as st

from dashboard.config import FACEBOOK_DB, TIKTOK_DB


def safe_query(query: str, db_path: str, params=None) -> pd.DataFrame:
    if not os.path.exists(db_path):
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception:
        return pd.DataFrame()


def _es_solo_tiktok(plataforma):
    """True si el filtro activo es exclusivamente TikTok."""
    return plataforma is not None and str(plataforma).strip().lower().startswith("tik")


def formato_fecha_espanol(fecha):
    dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
             'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    try:
        if pd.isna(fecha):
            return "Fecha no disponible"
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
            conn = sqlite3.connect(db)
            try:
                n = pd.read_sql(
                    f"SELECT COUNT(*) as c FROM {table} WHERE {col} IS NULL OR TRIM(CAST({col} AS TEXT)) = ''",
                    conn
                ).iloc[0]['c']
                if n > 0:
                    st.markdown(
                        f'<div class="status-info">Se descartaron {n} {label} sin fecha.</div>',
                        unsafe_allow_html=True
                    )
            finally:
                conn.close()
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
    """Card que traduce un cálculo: qué muestra, cómo leerlo y un aviso opcional."""
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


def card_narrativa(texto: str, tono: str = None):
    """Card breve con una lectura en lenguaje natural de lo que dice la gráfica.

    Sustituye a los subtítulos genéricos: en lugar de describir qué es la
    sección, resume en una frase lo que muestran los datos del período. `texto`
    admite HTML inline (por ejemplo <strong>). `tono` opcional ('favorable',
    'critico', 'neutral') ajusta el color del acento; por defecto usa el acento
    de la marca. La narrativa siempre debe derivarse de datos ya calculados,
    nunca inventarse.
    """
    t = (tono or "").strip().lower()
    if t in ("favorable", "positivo", "positiva", "verde", "apoyo"):
        color = "var(--green)"
    elif t in ("critico", "crítico", "negativo", "rojo", "critica", "crítica"):
        color = "var(--red)"
    elif t in ("neutral", "neutro", "amarillo", "mixto"):
        color = "var(--amber)"
    else:
        color = "var(--accent)"
    st.markdown(
        f'<div class="panel" style="border-left:3px solid {color};margin:4px 0 16px 0">'
        f'<p style="font-size:15px;color:var(--fg-primary);line-height:1.5;margin:0">{texto}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def que_ves_box(texto: str):
    st.markdown(
        f'<div class="wys-box"><span class="wys-label">QUÉ ESTÁS VIENDO</span>'
        f'<p class="wys-text">{texto}</p></div>',
        unsafe_allow_html=True,
    )


def bloom_caption(texto: str):
    st.markdown(f'<p class="exec-caption">{texto}</p>', unsafe_allow_html=True)


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


# ─── REFERENCIAS A PUBLICACIONES (verificación de origen) ──────────
# Permiten al lector abrir el post real en Facebook y comprobar de dónde salen
# los datos. La DB guarda post_url al cargar contenido. Solo aplican a Facebook,
# por lo que se ocultan cuando el filtro activo es exclusivamente TikTok.

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


def referencias_publicaciones(post_ids=None, limit=8, titulo="PUBLICACIONES DE ORIGEN", plataforma=None):
    """Renderiza enlaces clickeables a las publicaciones que sustentan un dato.

    Si post_ids viene dado, enlaza esas publicaciones; si no, las más recientes
    con enlace. No muestra nada si no hay URLs guardadas. Las referencias provienen
    de fb_posts (Facebook): en la vista de solo TikTok se omiten para no mostrar
    evidencia de otra plataforma.
    """
    if _es_solo_tiktok(plataforma):
        return
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
        'letter-spacing:1.5px;'
        'font-family:IBM Plex Mono,monospace;margin-bottom:4px">'
        + titulo + '</div>' + chips + '</div>',
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


def referencias_por_categoria(tema, limit=8, plataforma=None):
    if _es_solo_tiktok(plataforma):
        return
    ids = _post_ids_por_categoria(tema)
    if ids:
        referencias_publicaciones(post_ids=ids, limit=limit, titulo="Referencias a los post sobre " + str(tema).lower() + ", verifica el post", plataforma=plataforma)


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
