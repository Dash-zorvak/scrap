import os

# Rutas relativas al proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# DATA_DIR configurable via env var (Railway: montar volumen persistente aquí)
# Por defecto = BASE_DIR/data (comportamiento actual)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))

# Bases de datos — todas derivadas de DATA_DIR
FACEBOOK_DB = os.path.join(DATA_DIR, "facebook.db")
TIKTOK_DB   = os.path.join(DATA_DIR, "tiktok.db")
EXTERNOS_DB = os.path.join(DATA_DIR, "externos.db")

OUTPUT_DIR  = os.environ.get("OUTPUT_DIR", os.path.join(BASE_DIR, "dashboard", "outputs"))

# Páginas oficiales del sujeto del dashboard (filtro/origen para fb_posts).
# El tablero analiza al alcalde de Santa Ana (Gustavo Acevedo) y a la Alcaldía:
# son las dos fuentes oficiales que se monitorean para saber qué dice la gente de él.
# Las páginas de terceros que hablan del alcalde se analizan aparte como EXTERNOS.
FB_PAGES_OFICIALES = [
    "Alcaldía de Santa Ana",
    "Gustavo Acevedo",
]

# Tablas
FB_POSTS_TABLE    = "fb_posts"
FB_COMMENTS_TABLE = "fb_comments"
TK_VIDEOS_TABLE   = "videos"
TK_COMMENTS_TABLE = "comments"

# Reacciones Facebook: las 7 reacciones completas (ninguna queda fuera)
FB_REACTIONS = [
    "likes_count",
    "loves_count",
    "cares_count",
    "hahas_count",
    "wows_count",
    "sads_count",
    "angrys_count"
]

# Columnas TikTok
TK_ENGAGEMENT = ["views", "likes", "shares", "favorites_count", "comments_count"]

# Cuentas TikTok (account_id -> etiqueta de UI). Nombres alineados con FB.
TK_ACCOUNTS = {
    1: "Alcaldía de Santa Ana",
    3: "Gustavo Acevedo"
}

# Crear carpetas necesarias si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mínimo de comentarios analizados para considerar la muestra "suficiente" (Decisión #1)
MIN_COMENTARIOS_MUESTRA = 15

# ─── Sincronización opcional con Hugging Face Dataset (HF Spaces) ───
# El disco de HF Spaces es efímero. Si se definen HF_DATASET_REPO y HF_TOKEN,
# se descargan las bases persistidas al arrancar. En local/Railway es un no-op.
try:
    from dashboard.hf_sync import pull_dbs as _hf_pull_dbs
    _hf_pull_dbs()
except Exception:
    pass
