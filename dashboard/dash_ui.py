"""Cabecera ejecutiva compartida del panel de carga."""

import sqlite3

import pandas as pd
import streamlit as st

from config import FACEBOOK_DB, TIKTOK_DB, TK_ACCOUNTS


def _safe_query(query, db_path, params=None):
    try:
        conn = sqlite3.connect(db_path)
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        return None


def _post_links_html(filas, max_links=8):
    chips = []
    for r in filas[:max_links]:
        url = r.get("post_url") or ""
        label = r.get("page_name") or "Post"
        if url:
            chips.append(
                f'<a href="{url}" target="_blank" rel="noopener" '
                f'style="display:inline-block;font-family:IBM Plex Mono,monospace;'
                f'font-size:10px;color:var(--accent);background:var(--accent-soft);'
                f'padding:3px 10px;border-radius:3px;margin:2px 4px 2px 0;'
                f'text-decoration:none;white-space:nowrap">🔗 {label}</a>'
            )
    return "".join(chips)


def _page_head(overline: str, title: str, sub: str, stats: str = ""):
    stats_html = f'<div class="page-stats">{stats}</div>' if stats else ''
    st.markdown(f"""
    <div class="page-head">
        <div class="page-overline">{overline}</div>
        <div class="page-h">{title}</div>
        <div class="page-sub">{sub}</div>
        {stats_html}
    </div>
    """, unsafe_allow_html=True)


def _incluye_facebook(plataforma):
    p = str(plataforma or "").strip().lower()
    return p == "" or p.startswith("face") or p.startswith("amb")


def _incluye_tiktok(plataforma):
    p = str(plataforma or "").strip().lower()
    return p == "" or p.startswith("tik") or p.startswith("amb")


def _referencias_tiktok(post_ids=None, limit=8):
    """Enlaces de TikTok desde videos.post_url; page_name se resuelve vía TK_ACCOUNTS."""
    try:
        if post_ids is not None:
            ids = [str(p) for p in post_ids if p is not None and str(p) != ""]
            if not ids:
                return []
            marcadores = ",".join("?" for _ in ids)
            df = _safe_query(
                "SELECT id AS post_id, account_id, created_at, post_url FROM videos "
                "WHERE id IN (" + marcadores + ") "
                "AND post_url IS NOT NULL AND TRIM(post_url) != ''",
                TIKTOK_DB, params=ids,
            )
        else:
            df = _safe_query(
                "SELECT id AS post_id, account_id, created_at, post_url FROM videos "
                "WHERE post_url IS NOT NULL AND TRIM(post_url) != '' "
                "ORDER BY created_at DESC LIMIT ?",
                TIKTOK_DB, params=[int(limit)],
            )
    except Exception:
        return []
    if df is None or df.empty:
        return []
    rows = df.to_dict("records")
    for r in rows:
        r["page_name"] = TK_ACCOUNTS.get(r.get("account_id"), "TikTok")
        r["created_time"] = r.get("created_at")
    return rows


def referencias_publicaciones(post_ids=None, limit=8, titulo="PUBLICACIONES DE ORIGEN", plataforma=None):
    """Enlaces clickeables a publicaciones de origen, combinando Facebook y/o
    TikTok según el filtro activo (antes solo consultaba fb_posts)."""
    filas = []
    try:
        if _incluye_facebook(plataforma):
            if post_ids is not None:
                ids = [str(p) for p in post_ids if p is not None and str(p) != ""]
                if ids:
                    marcadores = ",".join("?" for _ in ids)
                    df = _safe_query(
                        "SELECT post_id, page_name, created_time, post_url FROM fb_posts "
                        "WHERE post_id IN (" + marcadores + ") "
                        "AND post_url IS NOT NULL AND TRIM(post_url) != ''",
                        FACEBOOK_DB, params=ids,
                    )
                    if df is not None and not df.empty:
                        filas.extend(df.to_dict("records"))
            else:
                df = _safe_query(
                    "SELECT post_id, page_name, created_time, post_url FROM fb_posts "
                    "WHERE post_url IS NOT NULL AND TRIM(post_url) != '' "
                    "ORDER BY created_time DESC LIMIT ?",
                    FACEBOOK_DB, params=[int(limit)],
                )
                if df is not None and not df.empty:
                    filas.extend(df.to_dict("records"))
        if _incluye_tiktok(plataforma):
            filas.extend(_referencias_tiktok(post_ids=post_ids, limit=limit))
    except Exception:
        pass
    if not filas:
        return
    chips = _post_links_html(filas, max_links=limit)
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
