"""Consultas SQL centralizadas.

Todas las queries que estaban dispersas en los modulos de dashboard se
consolidan aqui. Cada funcion recibe un db_path y devuelve los resultados
en una estructura simple (list of dicts o list of tuples).
"""
import sqlite3

from src.config import Config

_cfg = Config()


def _conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_fb_comments_with_messages(db_path=None):
    """Fetch all non-empty FB comments for theme review."""
    db_path = db_path or _cfg.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT comment_id, message FROM fb_comments "
            "WHERE message IS NOT NULL AND message != ''"
        ).fetchall()
        return [(r["comment_id"], r["message"]) for r in rows]
    finally:
        conn.close()


def get_fb_comments_with_context(db_path=None):
    """Fetch non-empty FB comments with their parent post_id for evidence tracing.

    Returns list of dicts: {"id": comment_id, "texto": message,
    "post_id": post_id, "plataforma": "facebook"}.
    """
    db_path = db_path or _cfg.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT comment_id, message, post_id FROM fb_comments "
            "WHERE message IS NOT NULL AND message != ''"
        ).fetchall()
        return [
            {"id": r["comment_id"], "texto": r["message"],
             "post_id": r["post_id"], "plataforma": "facebook"}
            for r in rows
        ]
    finally:
        conn.close()


def get_tk_comments_with_messages(db_path=None):
    """Fetch all non-empty TikTok comments for theme review."""
    db_path = db_path or _cfg.TIKTOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT id, text FROM comments "
            "WHERE text IS NOT NULL AND text != ''"
        ).fetchall()
        return [(r["id"], r["text"]) for r in rows]
    finally:
        conn.close()


def get_tk_comments_with_context(db_path=None):
    """Fetch non-empty TikTok comments with their parent video_id for evidence tracing.

    Returns list of dicts: {"id": comment_id, "texto": text,
    "post_id": video_id, "plataforma": "tiktok"}.
    """
    db_path = db_path or _cfg.TIKTOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT id, text, video_id FROM comments "
            "WHERE text IS NOT NULL AND text != ''"
        ).fetchall()
        return [
            {"id": r["id"], "texto": r["text"],
             "post_id": r["video_id"], "plataforma": "tiktok"}
            for r in rows
        ]
    finally:
        conn.close()


def get_ext_comments_with_messages(db_path=None):
    """Fetch all non-empty Externos comments for theme review."""
    db_path = db_path or _cfg.EXTERNOS_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT comment_id, message FROM external_comments "
            "WHERE message IS NOT NULL AND message != ''"
        ).fetchall()
        return [(r["comment_id"], r["message"]) for r in rows]
    finally:
        conn.close()


def get_ext_comments_with_context(db_path=None):
    """Fetch non-empty Externos comments with their parent post_id for evidence tracing.

    Returns list of dicts: {"id": comment_id, "texto": message,
    "post_id": post_id, "plataforma": "externos"}.
    """
    db_path = db_path or _cfg.EXTERNOS_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT comment_id, message, post_id FROM external_comments "
            "WHERE message IS NOT NULL AND message != ''"
        ).fetchall()
        return [
            {"id": r["comment_id"], "texto": r["message"],
             "post_id": r["post_id"], "plataforma": "externos"}
            for r in rows
        ]
    finally:
        conn.close()


def get_fb_post_signatures(db_path=None):
    """Load FB post signatures for dedup (post_id, firma)."""
    from dashboard._generar_id import firma_contenido
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.TIKTOK_DB
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
    db_path = db_path or _cfg.TIKTOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.TIKTOK_DB
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
    db_path = db_path or _cfg.TIKTOK_DB
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
    db_path = db_path or _cfg.EXTERNOS_DB
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
    db_path = db_path or _cfg.EXTERNOS_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute("SELECT post_id FROM external_posts").fetchall()
        return {r["post_id"] for r in rows}
    finally:
        conn.close()


def get_tk_video_ids(db_path=None):
    """Get all TikTok video IDs for dedup."""
    db_path = db_path or _cfg.TIKTOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.TIKTOK_DB
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


def get_externos_stats(db_path=None):
    """§D — Agrega metricas de Externos para engagement.

    Retorna dict con:
      - posts, comments: conteos
      - total_reactions: suma de reacciones
      - engagement: total_reactions + comments (sin shares, Externos no los tiene)
    """
    db_path = db_path or _cfg.EXTERNOS_DB
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT "
            "  COUNT(*) as posts, "
            "  SUM(COALESCE(total_reactions,0)) as total_reactions, "
            "  SUM(COALESCE(comments_count,0)) as comments "
            "FROM external_posts"
        ).fetchone()
        total_reactions = row["total_reactions"] or 0
        comments = row["comments"] or 0
        engagement = total_reactions + comments
        return {
            "posts": row["posts"] or 0,
            "total_reactions": total_reactions,
            "comments": comments,
            "engagement": engagement,
        }
    finally:
        conn.close()


def get_external_page_engagement(db_path=None):
    """Retorna engagement por pagina externa desde external_pages + external_posts.

    Retorna lista de dicts: [{page_name, posts, total_reactions, comments_count, engagement}].
    """
    db_path = db_path or _cfg.EXTERNOS_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT p.name, "
            "  COUNT(DISTINCT po.post_id) as posts, "
            "  SUM(COALESCE(po.total_reactions,0)) as total_reactions, "
            "  SUM(COALESCE(po.comments_count,0)) as comments_count "
            "FROM external_pages p "
            "LEFT JOIN external_posts po ON po.page_name = p.name "
            "GROUP BY p.name "
            "ORDER BY total_reactions + comments_count DESC"
        ).fetchall()
        result = []
        for r in rows:
            tr = r["total_reactions"] or 0
            cc = r["comments_count"] or 0
            result.append({
                "page_name": r["name"],
                "posts": r["posts"] or 0,
                "total_reactions": tr,
                "comments_count": cc,
                "engagement": tr + cc,
            })
        return result
    finally:
        conn.close()


def cargar_temas_aprobados():
    """Combina aprobaciones de las 3 DBs con el mismo peso.

    Retorna lista de dicts ordenada por doc_count descendente, donde cada
    tema incluye la plataforma de origen. Los conteos por categoría se
    suman entre plataformas (sin duplicar IDs entre DBs distintas).
    """
    from dashboard.tema_aprobaciones import agregar_por_tema
    combinados = {}
    for label, db in [("facebook", _cfg.FACEBOOK_DB),
                      ("tiktok", _cfg.TIKTOK_DB),
                      ("externos", _cfg.EXTERNOS_DB)]:
        try:
            parcial = agregar_por_tema(db)
            for tema in parcial:
                cat = tema["categoria"]
                if cat not in combinados:
                    combinados[cat] = {
                        "id": 0,
                        "categoria": cat,
                        "label": tema["label"],
                        "doc_count": 0,
                        "apoyo": 0,
                        "critica": 0,
                        "neutral": 0,
                        "ejemplo": "",
                        "ejemplo_critica": "",
                        "emociones": {},
                        "emocion_dominante": "calma",
                        "plataformas": [],
                    }
                entry = combinados[cat]
                entry["doc_count"] += tema["doc_count"]
                entry["apoyo"] += tema.get("apoyo", 0)
                entry["critica"] += tema.get("critica", 0)
                entry["neutral"] += tema.get("neutral", 0)
                if label not in entry["plataformas"]:
                    entry["plataformas"].append(label)
                if tema.get("ejemplo") and (
                    not entry["ejemplo"] or len(tema["ejemplo"]) < len(entry["ejemplo"])
                ):
                    entry["ejemplo"] = tema["ejemplo"]
                if tema.get("ejemplo_critica") and (
                    not entry["ejemplo_critica"]
                    or len(tema["ejemplo_critica"]) < len(entry["ejemplo_critica"])
                ):
                    entry["ejemplo_critica"] = tema["ejemplo_critica"]
                emo_counts = tema.get("emociones", {})
                if isinstance(emo_counts, dict):
                    for emo_key, emo_info in emo_counts.items():
                        if isinstance(emo_info, dict):
                            entry["emociones"][emo_key] = {
                                "count": entry["emociones"].get(emo_key, {}).get("count", 0)
                                         + emo_info.get("count", 0),
                                "pct": 0,
                            }
        except Exception:
            pass
    total = sum(t["doc_count"] for t in combinados.values()) or 1
    result = []
    for i, (cat, entry) in enumerate(sorted(combinados.items(),
                                              key=lambda x: -x[1]["doc_count"])):
        entry["id"] = i + 1
        entry["pct"] = round(entry["doc_count"] / total * 100, 1)
        emo_total = sum(v.get("count", 0) for v in entry["emociones"].values()) or 1
        for emo_key in entry["emociones"]:
            entry["emociones"][emo_key]["pct"] = round(
                entry["emociones"][emo_key]["count"] / emo_total * 100, 1
            )
        if entry["emociones"]:
            entry["emocion_dominante"] = max(
                entry["emociones"], key=lambda e: entry["emociones"][e].get("count", 0)
            )
        entry["pct_apoyo"] = round(entry["apoyo"] / entry["doc_count"] * 100, 1) if entry["doc_count"] else 0
        entry["pct_critica"] = round(entry["critica"] / entry["doc_count"] * 100, 1) if entry["doc_count"] else 0
        entry["pct_neutral"] = round(entry["neutral"] / entry["doc_count"] * 100, 1) if entry["doc_count"] else 0
        entry["saldo"] = entry["apoyo"] - entry["critica"]
        result.append(entry)
    return result


def calcular_correlacion_noticias_picos(z_umbral=1.0, ventana_dias=3, db_path=None):
    """Calcula correlacion temporal entre picos de engagement y noticias externas.

    Retorna dict con:
      - semana: str con la semana analizada
      - engagement: float engagement promedio de la semana
      - fuente: str fuente externa con mayor actividad
      - noticia: str titulo/mensaje de la noticia mas reciente
      - fecha: str fecha de la noticia
      - n_picos: int numero de picos detectados
      - coincidencias: int picos que coinciden con noticias externas
      - indice_correlacion: float entre 0 y 1
    """
    from datetime import datetime, timedelta
    import statistics

    db_externos = db_path or _cfg.EXTERNOS_DB
    db_fb = _cfg.FACEBOOK_DB

    # Obtener engagement semanal de Facebook
    conn_fb = _conn(db_fb)
    try:
        rows_fb = conn_fb.execute(
            "SELECT DATE(created_time) as dia, "
            "  SUM(likes_count + loves_count + cares_count + hahas_count "
            "      + wows_count + sads_count + angrys_count + comments_count "
            "      + shares_count) as engagement "
            "FROM fb_posts "
            "WHERE created_time IS NOT NULL "
            "GROUP BY dia ORDER BY dia"
        ).fetchall()
    except Exception:
        rows_fb = []
    finally:
        conn_fb.close()

    if not rows_fb:
        return {
            "semana": "", "engagement": 0, "fuente": "", "noticia": "",
            "fecha": "", "n_picos": 0, "coincidencias": 0,
            "indice_correlacion": 0.0,
        }

    # Calcular engagement promedio y desviacion
    eng_vals = [r["engagement"] or 0 for r in rows_fb]
    if len(eng_vals) < 3:
        return {
            "semana": "", "engagement": 0, "fuente": "", "noticia": "",
            "fecha": "", "n_picos": 0, "coincidencias": 0,
            "indice_correlacion": 0.0,
        }

    media = statistics.mean(eng_vals)
    desv = statistics.stdev(eng_vals) if len(eng_vals) > 1 else 1.0
    if desv == 0:
        desv = 1.0

    # Detectar picos (z-score > umbral)
    picos = []
    for i, r in enumerate(rows_fb):
        eng = r["engagement"] or 0
        z = (eng - media) / desv
        if z > z_umbral:
            picos.append({
                "fecha": r["dia"],
                "engagement": eng,
                "z_score": round(z, 2),
            })

    # Obtener noticias externas
    conn_ext = _conn(db_externos)
    try:
        rows_ext = conn_ext.execute(
            "SELECT page_name, message, created_time "
            "FROM external_posts "
            "WHERE created_time IS NOT NULL "
            "ORDER BY created_time DESC"
        ).fetchall()
    except Exception:
        rows_ext = []
    finally:
        conn_ext.close()

    # Contar coincidencias dentro de la ventana
    coincidencias = 0
    fuente_top = ""
    noticia_top = ""
    fecha_top = ""
    for pico in picos:
        try:
            fecha_pico = datetime.strptime(pico["fecha"], "%Y-%m-%d")
        except (ValueError, TypeError):
            continue
        for ext in rows_ext:
            try:
                ext_date = datetime.strptime(ext["created_time"][:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                continue
            diff = abs((fecha_pico - ext_date).days)
            if diff <= ventana_dias:
                coincidencias += 1
                if not fuente_top:
                    fuente_top = ext["page_name"] or ""
                    noticia_top = (ext["message"] or "")[:200]
                    fecha_top = ext["created_time"][:10]
                break

    n_picos = len(picos)
    indice = round(coincidencias / n_picos, 2) if n_picos > 0 else 0.0

    semana = ""
    if rows_fb:
        semana = rows_fb[-1]["dia"] or ""

    return {
        "semana": semana,
        "engagement": round(media, 1),
        "fuente": fuente_top,
        "noticia": noticia_top,
        "fecha": fecha_top,
        "n_picos": n_picos,
        "coincidencias": coincidencias,
        "indice_correlacion": indice,
    }


def get_fb_daily_volumes(db_path=None):
    """§I — Volumen diario de posts de Facebook para CV de autenticidad.

    Retorna lista de (fecha_str, conteo_posts).
    """
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.TIKTOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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


def get_fb_monthly_er(db_path=None):
    """ER mensual de FB: retorna lista de (mes, er, total_engagement, n_posts).

    ER = total_engagement / n_posts * 100, donde engagement incluye
    reacciones + comments + shares.
    """
    db_path = db_path or _cfg.FACEBOOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT strftime('%Y-%m', created_time) as mes, "
            "COUNT(*) as n_posts, "
            "SUM(COALESCE(likes_count,0) + COALESCE(loves_count,0) "
            "  + COALESCE(cares_count,0) + COALESCE(hahas_count,0) "
            "  + COALESCE(wows_count,0) + COALESCE(sads_count,0) "
            "  + COALESCE(angrys_count,0) + COALESCE(comments_count,0) "
            "  + COALESCE(shares_count,0)) as total_eng "
            "FROM fb_posts GROUP BY mes ORDER BY mes"
        ).fetchall()
        result = []
        for r in rows:
            er = round(r["total_eng"] / r["n_posts"] * 100, 2) if r["n_posts"] else 0
            result.append((r["mes"], er, r["total_eng"], r["n_posts"]))
        return result
    finally:
        conn.close()


def get_tk_monthly_er(db_path=None):
    """ER mensual de TikTok: retorna lista de (mes, er, total_engagement, n_videos).

    ER = total_engagement / n_videos * 100, donde engagement incluye
    likes + comments + shares + favorites.
    """
    db_path = db_path or _cfg.TIKTOK_DB
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT strftime('%Y-%m', created_at) as mes, "
            "COUNT(*) as n_videos, "
            "SUM(COALESCE(likes,0) + COALESCE(comments_count,0) "
            "  + COALESCE(shares,0) + COALESCE(favorites_count,0)) as total_eng "
            "FROM videos GROUP BY mes ORDER BY mes"
        ).fetchall()
        result = []
        for r in rows:
            er = round(r["total_eng"] / r["n_videos"] * 100, 2) if r["n_videos"] else 0
            result.append((r["mes"], er, r["total_eng"], r["n_videos"]))
        return result
    finally:
        conn.close()


def get_fb_per_theme_controversy(db_path=None):
    """§E — Controversia por tema (topic_category) de FB posts.

    Calcula: negativos / total por tema.
    negativos = angrys + sads + hahas (por post, acumulado).
    Retorna lista de dicts [{tema, n_posts, negativos, total_reacciones, controversy}].
    """
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
    db_path = db_path or _cfg.FACEBOOK_DB
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
