import os

# Rutas relativas al proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Bases de datos
FACEBOOK_DB = os.path.join(BASE_DIR, "data", "facebook.db")
TIKTOK_DB   = os.path.join(BASE_DIR, "data", "tiktok.db")
EXTERNOS_DB = os.path.join(BASE_DIR, "data", "externos.db")
OUTPUT_DIR  = os.path.join(BASE_DIR, "dashboard", "outputs")

# Páginas oficiales a incluir (filtro para fb_posts)
FB_PAGES_OFICIALES = [
    "Jose Chicas",
    "Alcaldía de Santa Ana",
    "Alcaldia de Santa Ana",
    "Gustavo Acevedo"
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

# Cuentas TikTok
TK_ACCOUNTS = {
    1: "Alcaldía Santa Ana",
    3: "Gustavo Acevedo"
}

# Test DBs
FACEBOOK_TEST_DB = os.path.join(BASE_DIR, "data", "facebook_test.db")
TIKTOK_TEST_DB   = os.path.join(BASE_DIR, "data", "tiktok_test.db")
EXTERNOS_TEST_DB = os.path.join(BASE_DIR, "data", "externos_test.db")

# Crear carpeta outputs si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mínimo de comentarios analizados para considerar la muestra "suficiente" (Decisión #1)
MIN_COMENTARIOS_MUESTRA = 15
