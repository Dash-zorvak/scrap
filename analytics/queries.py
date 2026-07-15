"""Consultas SQL centralizadas.

Todas las queries que estaban dispersas en los modulos de dashboard se
consolidan aqui. Cada funcion recibe un db_path y devuelve los resultados
en una estructura simple (list of dicts o list of tuples).
"""
import sqlite3

from src.config import Config


def _conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_fb_comments_with_messages(db_path=None):
    """Fetch all non-empty FB comments for theme review."""
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT comment_id, message FROM fb_comments "
            "WHERE message IS NOT NULL AND message != ''"
        ).fetchall()
        return [(r["comment_id"], r["message"]) for r in rows]
    finally:
        conn.close()


def get_fb_post_signatures(db_path=None):
    """Load FB post signatures for dedup (post_id, firma)."""
    from dashboard._generar_id import firma_contenido
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT post_id, page_name, created_time, message FROM fb_posts"
        ).fetchall()
        return {firma_contenido(r["page_name"], r["created_time"], r["message"]): r["post_id"]
                for r in rows}
    finally:
        conn.close()


def get_tk_video_signatures(db_path=None):
    """Load TikTok video signatures for dedup (video_id, firma)."""
    from dashboard._generar_id import firma_contenido
    db_path = db_path or Config.TIKTOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT id, account_id, created_at, description FROM videos"
        ).fetchall()
        return {firma_contenido(r["account_id"], r["created_at"], r["description"]): r["id"]
                for r in rows}
    finally:
        conn.close()


def get_tk_videos_paginated(db_path=None, limit=50, offset=0):
    """Read TikTok videos with pagination."""
    db_path = db_path or Config.TIKTOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM videos ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_fb_post_by_id(post_id, db_path=None):
    """Read a single FB post by post_id."""
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM fb_posts WHERE post_id = ?", (post_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_fb_references_by_ids(post_ids, db_path=None):
    """Get FB post references (url, etc.) by post_id list."""
    if not post_ids:
        return []
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        placeholders = ",".join("?" for _ in post_ids)
        rows = conn.execute(
            f"SELECT post_id, page_name, created_time, post_url "
            f"FROM fb_posts WHERE post_id IN ({placeholders}) "
            f"AND post_url IS NOT NULL AND TRIM(post_url) != ''",
            post_ids,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_fb_recent_references(limit=10, db_path=None):
    """Get recent FB post references with URLs."""
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT post_id, page_name, created_time, post_url "
            "FROM fb_posts WHERE post_url IS NOT NULL AND TRIM(post_url) != '' "
            "ORDER BY created_time DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_tk_references_by_ids(video_ids, db_path=None):
    """Get TikTok video references by video id list."""
    if not video_ids:
        return []
    db_path = db_path or Config.TIKTOK_DB
    conn = _conn(db_path)
    try:
        placeholders = ",".join("?" for _ in video_ids)
        rows = conn.execute(
            f"SELECT id AS post_id, account_id, created_at, post_url "
            f"FROM videos WHERE id IN ({placeholders}) "
            f"AND post_url IS NOT NULL AND TRIM(post_url) != ''",
            video_ids,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_tk_recent_references(limit=10, db_path=None):
    """Get recent TikTok video references with URLs."""
    db_path = db_path or Config.TIKTOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT id AS post_id, account_id, created_at, post_url "
            "FROM videos WHERE post_url IS NOT NULL AND TRIM(post_url) != '' "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_external_pages(db_path=None):
    """List external pages."""
    db_path = db_path or Config.EXTERNOS_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM external_pages ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [r["name"] for r in rows]
    finally:
        conn.close()


def get_external_post_ids(db_path=None):
    """Get all external post IDs for dedup."""
    db_path = db_path or Config.EXTERNOS_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute("SELECT post_id FROM external_posts").fetchall()
        return {r["post_id"] for r in rows}
    finally:
        conn.close()


def get_tk_video_ids(db_path=None):
    """Get all TikTok video IDs for dedup."""
    db_path = db_path or Config.TIKTOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute("SELECT id FROM videos").fetchall()
        return {r["id"] for r in rows}
    finally:
        conn.close()


# ── §D-I: Aggregated stats for compute formulas ──

def get_fb_stats(db_path=None):
    """§D — Agrega métricas de Facebook para engagement/reacciones.

    Retorna dict con:
      - posts, comments: conteos
      - likes, loves, cares, hahas, wows, sads, angrys: sumatorias
      - shares, views: sumatorias
      - total_reacciones: suma de todas las reacciones
      - engagement: reacciones + comments + shares
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT "
            "  COUNT(*) as posts, "
            "  SUM(COALESCE(likes_count,0)) as likes, "
            "  SUM(COALESCE(loves_count,0)) as loves, "
            "  SUM(COALESCE(cares_count,0)) as cares, "
            "  SUM(COALESCE(hahas_count,0)) as hahas, "
            "  SUM(COALESCE(wows_count,0)) as wows, "
            "  SUM(COALESCE(sads_count,0)) as sads, "
            "  SUM(COALESCE(angrys_count,0)) as angrys, "
            "  SUM(COALESCE(comments_count,0)) as comments, "
            "  SUM(COALESCE(shares_count,0)) as shares, "
            "  SUM(COALESCE(views_count,0)) as views "
            "FROM fb_posts"
        ).fetchone()
        likes = row["likes"] or 0
        loves = row["loves"] or 0
        cares = row["cares"] or 0
        hahas = row["hahas"] or 0
        wows = row["wows"] or 0
        sads = row["sads"] or 0
        angrys = row["angrys"] or 0
        comments = row["comments"] or 0
        shares = row["shares"] or 0
        total_reacciones = likes + loves + cares + hahas + wows + sads + angrys
        engagement = total_reacciones + comments + shares
        return {
            "posts": row["posts"] or 0,
            "likes": likes, "loves": loves, "cares": cares,
            "hahas": hahas, "wows": wows, "sads": sads, "angrys": angrys,
            "comments": comments, "shares": shares,
            "views": row["views"] or 0,
            "total_reacciones": total_reacciones,
            "engagement": engagement,
        }
    finally:
        conn.close()


def get_tk_stats(db_path=None):
    """§D — Agrega métricas de TikTok para engagement.

    Retorna dict con:
      - videos, comments: conteos
      - views, likes, shares, favorites: sumatorias
      - engagement: likes + shares + favorites + comments
    """
    db_path = db_path or Config.TIKTOK_DB
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT "
            "  COUNT(*) as videos, "
            "  SUM(COALESCE(views,0)) as views, "
            "  SUM(COALESCE(likes,0)) as likes, "
            "  SUM(COALESCE(shares,0)) as shares, "
            "  SUM(COALESCE(favorites_count,0)) as favorites, "
            "  SUM(COALESCE(comments_count,0)) as comments "
            "FROM videos"
        ).fetchone()
        views = row["views"] or 0
        likes = row["likes"] or 0
        shares = row["shares"] or 0
        favorites = row["favorites"] or 0
        comments = row["comments"] or 0
        engagement = likes + shares + favorites + comments
        return {
            "videos": row["videos"] or 0,
            "views": views, "likes": likes, "shares": shares,
            "favorites": favorites, "comments": comments,
            "engagement": engagement,
        }
    finally:
        conn.close()


def get_fb_daily_volumes(db_path=None):
    """§I — Volumen diario de posts de Facebook para CV de autenticidad.

    Retorna lista de (fecha_str, conteo_posts).
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT DATE(created_time) as dia, COUNT(*) as n "
            "FROM fb_posts GROUP BY dia ORDER BY dia"
        ).fetchall()
        return [(r["dia"], r["n"]) for r in rows]
    finally:
        conn.close()


def get_tk_daily_volumes(db_path=None):
    """§I — Volumen diario de videos de TikTok para CV de autenticidad."""
    db_path = db_path or Config.TIKTOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT DATE(created_at) as dia, COUNT(*) as n "
            "FROM videos GROUP BY dia ORDER BY dia"
        ).fetchall()
        return [(r["dia"], r["n"]) for r in rows]
    finally:
        conn.close()


# ── §E/F/H: Historical data for formulas (Bloque 6.1) ──


def get_fb_monthly_sentiment(db_path=None):
    """§H — Promedio mensual de sentimiento (sentiment_score) de FB posts.

    Retorna lista de (mes_YYYY-MM, avg_sentiment_score, n_posts).
    Úsase para la dimensión 'consistencia' del Pulso IQ.
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT strftime('%Y-%m', created_time) as mes, "
            "AVG(COALESCE(sentiment_score, 0)) as avg_score, "
            "COUNT(*) as n "
            "FROM fb_posts GROUP BY mes ORDER BY mes"
        ).fetchall()
        return [(r["mes"], r["avg_score"], r["n"]) for r in rows]
    finally:
        conn.close()


def get_fb_per_theme_controversy(db_path=None):
    """§E — Controversia por tema (topic_category) de FB posts.

    Calcula: negativos / total por tema.
    negativos = angrys + sads + hahas (por post, acumulado).
    Retorna lista de dicts [{tema, n_posts, negativos, total_reacciones, controversy}].
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT "
            "  COALESCE(NULLIF(topic_category,''), 'sin_tema') as tema, "
            "  COUNT(*) as n_posts, "
            "  SUM(COALESCE(angrys_count,0) + COALESCE(sads_count,0) + COALESCE(hahas_count,0)) as negativos, "
            "  SUM(COALESCE(likes_count,0) + COALESCE(loves_count,0) + COALESCE(cares_count,0) "
            "    + COALESCE(hahas_count,0) + COALESCE(wows_count,0) "
            "    + COALESCE(sads_count,0) + COALESCE(angrys_count,0)) as total_reacciones "
            "FROM fb_posts "
            "GROUP BY tema"
        ).fetchall()
        result = []
        for r in rows:
            total_r = r["total_reacciones"] or 0
            neg = r["negativos"] or 0
            controversy = neg / total_r if total_r > 0 else 0.0
            result.append({
                "tema": r["tema"],
                "n_posts": r["n_posts"] or 0,
                "negativos": neg,
                "total_reacciones": total_r,
                "controversy": round(controversy, 4),
            })
        return result
    finally:
        conn.close()


def get_fb_references_for_alerts(post_ids=None, limit=20, db_path=None):
    """§F — Referencias (URLs) de posts FB para enlaces_referencia de alertas.

    Si post_ids se provee, filtra por esos IDs.
    Si no, retorna los posts más recientes con URL.
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        if post_ids:
            placeholders = ",".join("?" for _ in post_ids)
            rows = conn.execute(
                f"SELECT post_id, post_url, page_name, created_time "
                f"FROM fb_posts WHERE post_id IN ({placeholders}) "
                f"AND post_url IS NOT NULL AND TRIM(post_url) != ''",
                post_ids,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT post_id, post_url, page_name, created_time "
                "FROM fb_posts WHERE post_url IS NOT NULL AND TRIM(post_url) != '' "
                "ORDER BY created_time DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [r["post_url"] for r in rows if r["post_url"]]
    finally:
        conn.close()


def get_fb_controversial_posts(db_path=None):
    """§F — Posts FB con mayor proporción de reacciones negativas.

    Retorna lista de dicts [{post_id, post_url, negativos, total_reacciones,
        ratio, topic_category, zona}].
    Úsase para populate enlaces_referencia en alertas ICI/SDI/EFI/TAI.
    topic_category y zona permiten filtrar por tema o zona en TAI/ZDI.
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT "
            "  post_id, post_url, page_name, created_time, "
            "  COALESCE(NULLIF(topic_category,''), '') as topic_category, "
            "  COALESCE(zona, '') as zona, "
            "  (COALESCE(angrys_count,0) + COALESCE(sads_count,0) + COALESCE(hahas_count,0)) as negativos, "
            "  (COALESCE(likes_count,0) + COALESCE(loves_count,0) + COALESCE(cares_count,0) "
            "    + COALESCE(hahas_count,0) + COALESCE(wows_count,0) "
            "    + COALESCE(sads_count,0) + COALESCE(angrys_count,0)) as total_reacciones "
            "FROM fb_posts "
            "HAVING total_reacciones > 0 "
            "ORDER BY CAST(negativos AS FLOAT) / total_reacciones DESC "
            "LIMIT 20"
        ).fetchall()
        result = []
        for r in rows:
            total_r = r["total_reacciones"] or 0
            neg = r["negativos"] or 0
            ratio = neg / total_r if total_r > 0 else 0.0
            result.append({
                "post_id": r["post_id"],
                "post_url": r["post_url"] or "",
                "page_name": r["page_name"] or "",
                "created_time": r["created_time"] or "",
                "topic_category": r["topic_category"] or "",
                "zona": r["zona"] or "",
                "negativos": neg,
                "total_reacciones": total_r,
                "ratio": round(ratio, 4),
            })
        return result
    finally:
        conn.close()


def get_fb_posts_with_sentiment(db_path=None):
    """§H — Posts FB con sentiment_score para promedios mensuales.

    Retorna lista de dicts [{created_time, sentiment_score, topic_category, zona}].
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT created_time, "
            "  COALESCE(sentiment_score, 0) as sentiment_score, "
            "  COALESCE(NULLIF(topic_category,''), '') as topic_category, "
            "  COALESCE(zona, '') as zona "
            "FROM fb_posts ORDER BY created_time"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_fb_monthly_controversy(db_path=None):
    """§F — Controversia mensual de FB posts para historial ICI.

    Calcula, por mes (strftime('%Y-%m', created_time)):
        controversia = negativos / total_reacciones
    donde negativos = angrys + sads + hahas.

    Retorna lista de (mes_YYYY-MM, controversia, n_posts).
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT strftime('%Y-%m', created_time) as mes, "
            "SUM(COALESCE(angrys_count,0) + COALESCE(sads_count,0) "
            "  + COALESCE(hahas_count,0)) as negativos, "
            "SUM(COALESCE(likes_count,0) + COALESCE(loves_count,0) "
            "  + COALESCE(cares_count,0) + COALESCE(hahas_count,0) "
            "  + COALESCE(wows_count,0) + COALESCE(sads_count,0) "
            "  + COALESCE(angrys_count,0)) as total_reacciones, "
            "COUNT(*) as n "
            "FROM fb_posts GROUP BY mes ORDER BY mes"
        ).fetchall()
        result = []
        for r in rows:
            total_r = r["total_reacciones"] or 0
            neg = r["negativos"] or 0
            controversy = neg / total_r if total_r > 0 else 0.0
            result.append((r["mes"], round(controversy, 4), r["n"] or 0))
        return result
    finally:
        conn.close()


def get_fb_period_controversy(fecha_desde, fecha_hasta, db_path=None):
    """§F — Controversia de un período específico para ICI actual.

    Retorna (controversia, n_posts) para posts cuyo created_time
    está entre fecha_desde (inclusivo) y fecha_hasta (exclusivo).
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT "
            "SUM(COALESCE(angrys_count,0) + COALESCE(sads_count,0) "
            "  + COALESCE(hahas_count,0)) as negativos, "
            "SUM(COALESCE(likes_count,0) + COALESCE(loves_count,0) "
            "  + COALESCE(cares_count,0) + COALESCE(hahas_count,0) "
            "  + COALESCE(wows_count,0) + COALESCE(sads_count,0) "
            "  + COALESCE(angrys_count,0)) as total_reacciones, "
            "COUNT(*) as n "
            "FROM fb_posts WHERE created_time >= ? AND created_time < ?",
            (fecha_desde, fecha_hasta),
        ).fetchone()
        total_r = row["total_reacciones"] or 0
        neg = row["negativos"] or 0
        controversy = neg / total_r if total_r > 0 else 0.0
        return (round(controversy, 4), row["n"] or 0)
    finally:
        conn.close()


def get_fb_monthly_theme_controversy(db_path=None):
    """§F — Controversia mensual por tema para cv_28d y velocidad.

    Retorna lista de dicts [{mes, tema, controversy, n_posts}].
    Úsase para calcular la sensibilidad temática ajustada en TAI e ICI.
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT strftime('%Y-%m', created_time) as mes, "
            "COALESCE(NULLIF(topic_category,''), 'sin_tema') as tema, "
            "SUM(COALESCE(angrys_count,0) + COALESCE(sads_count,0) "
            "  + COALESCE(hahas_count,0)) as negativos, "
            "SUM(COALESCE(likes_count,0) + COALESCE(loves_count,0) "
            "  + COALESCE(cares_count,0) + COALESCE(hahas_count,0) "
            "  + COALESCE(wows_count,0) + COALESCE(sads_count,0) "
            "  + COALESCE(angrys_count,0)) as total_reacciones, "
            "COUNT(*) as n "
            "FROM fb_posts GROUP BY mes, tema ORDER BY mes, tema"
        ).fetchall()
        result = []
        for r in rows:
            total_r = r["total_reacciones"] or 0
            neg = r["negativos"] or 0
            controversy = neg / total_r if total_r > 0 else 0.0
            result.append({
                "mes": r["mes"],
                "tema": r["tema"],
                "controversy": round(controversy, 4),
                "n_posts": r["n"] or 0,
            })
        return result
    finally:
        conn.close()


def get_fb_posts_by_zone(zona, db_path=None):
    """§F — Posts FB de una zona específica para enlaces_referencia de ZDI.

    Retorna lista de dicts [{post_id, post_url, topic_category, created_time}].
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT post_id, post_url, topic_category, created_time "
            "FROM fb_posts WHERE zona = ? "
            "AND post_url IS NOT NULL AND TRIM(post_url) != '' "
            "ORDER BY created_time DESC LIMIT 10",
            (zona,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_fb_anger_by_zone(db_path=None):
    """§F — Ratio de enojo por zona para ZDI.

    Retorna lista de dicts [{zona, negativos, total, pct_negativos}].
    """
    db_path = db_path or Config.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT "
            "  COALESCE(NULLIF(zona,''), 'sin_zona') as zona, "
            "  SUM(COALESCE(angrys_count,0) + COALESCE(sads_count,0) + COALESCE(hahas_count,0)) as negativos, "
            "  COUNT(*) as total "
            "FROM fb_posts "
            "GROUP BY zona "
            "HAVING total >= 3"
        ).fetchall()
        result = []
        for r in rows:
            total = r["total"] or 0
            neg = r["negativos"] or 0
            pct = neg / total * 100 if total > 0 else 0.0
            result.append({
                "zona": r["zona"],
                "negativos": neg,
                "total": total,
                "pct_negativos": round(pct, 1),
            })
        return result
    finally:
        conn.close()
