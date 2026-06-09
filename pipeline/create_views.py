import sqlite3
from pipeline.config import FB_DB, TT_DB, PIPELINE_DB


def get_db():
    conn = sqlite3.connect(PIPELINE_DB)
    try:
        conn.execute(f"ATTACH DATABASE '{FB_DB}' AS fb")
    except Exception:
        pass
    try:
        conn.execute(f"ATTACH DATABASE '{TT_DB}' AS tt")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    return conn


FB_POSTS_QUERY = """
    SELECT
        post_id AS id, 'facebook' AS plataforma,
        COALESCE(message, '') AS texto,
        created_time AS fecha,
        COALESCE(likes_count, 0) AS me_gusta,
        COALESCE(loves_count, 0) AS me_encanta,
        COALESCE(hahas_count, 0) AS me_divierte,
        COALESCE(wows_count, 0) AS me_asombra,
        COALESCE(sads_count, 0) AS me_entristece,
        COALESCE(angrys_count, 0) AS me_enoja,
        COALESCE(comments_count, 0) AS comentarios_count,
        COALESCE(shares_count, 0) AS compartidos,
        COALESCE(views_count, 0) AS views,
        COALESCE(post_url, '') AS url
    FROM fb.fb_posts
    WHERE created_time IS NULL OR created_time > '2020-01-01'
"""

FB_COMMENTS_QUERY = """
    SELECT
        comment_id AS id, post_id, 'facebook' AS plataforma,
        COALESCE(message, '') AS texto,
        COALESCE(author_name, 'Anónimo') AS autor,
        created_time AS fecha
    FROM fb.fb_comments
    WHERE LENGTH(TRIM(COALESCE(message, ''))) > 2
"""

TT_POSTS_QUERY = """
    SELECT
        v.id AS id, 'tiktok' AS plataforma, a.display_name AS cuenta,
        COALESCE(v.description, '') AS texto,
        v.created_at AS fecha,
        COALESCE(v.likes, 0) AS me_gusta,
        0 AS me_encanta, 0 AS me_divierte, 0 AS me_asombra,
        0 AS me_entristece, 0 AS me_enoja,
        COALESCE(v.comments_count, 0) AS comentarios_count,
        COALESCE(v.shares, 0) AS compartidos,
        COALESCE(v.views, 0) AS views,
        v.url
    FROM tt.videos v
    JOIN tt.accounts a ON v.account_id = a.id
"""

TT_COMMENTS_QUERY = """
    SELECT
        c.id AS id, c.video_id AS post_id, 'tiktok' AS plataforma,
        COALESCE(c.text, '') AS texto,
        COALESCE(c.username, 'Anónimo') AS autor,
        c.created_at AS fecha
    FROM tt.comments c
    WHERE LENGTH(TRIM(COALESCE(c.text, ''))) > 2
"""


def setup():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS post_categorias (
            id TEXT, plataforma TEXT, cluster INTEGER,
            etiqueta TEXT, palabras_clave TEXT
        );
        CREATE TABLE IF NOT EXISTS post_sentimiento (
            post_id TEXT, plataforma TEXT, total_comentarios INTEGER,
            pct_positivo REAL, pct_negativo REAL, pct_neutral REAL,
            score_sentimiento REAL
        );
        CREATE TABLE IF NOT EXISTS post_engagement (
            id TEXT, plataforma TEXT, engagement_total INTEGER,
            engagement_rate REAL, indice_afecto_positivo REAL,
            indice_controversia REAL, indice_humor REAL,
            indice_viralidad REAL, score_emocional_neto REAL,
            score_sentimiento REAL, categoria TEXT
        );
        CREATE TABLE IF NOT EXISTS series_temporales (
            periodo TEXT, plataforma TEXT, semana_label TEXT,
            total_posts INTEGER, engagement_total INTEGER,
            engagement_promedio REAL, controversia_total INTEGER,
            viralidad_promedio REAL, media_movil REAL,
            es_anomalia INTEGER, tipo_anomalia TEXT
        );
        CREATE TABLE IF NOT EXISTS noticias_externas (
            noticia_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT, titular TEXT, texto TEXT, fuente TEXT,
            url TEXT, clasificacion TEXT, tema TEXT
        );
        CREATE TABLE IF NOT EXISTS eventos_correlacionados (
            noticia_titular TEXT, noticia_fuente TEXT,
            noticia_fecha TEXT, noticia_clasificacion TEXT,
            anomalia_periodo TEXT, anomalia_plataforma TEXT,
            anomalia_tipo TEXT, anomalia_engagement INTEGER,
            dias_diferencia INTEGER
        );
    """)
    conn.commit()
    return conn
