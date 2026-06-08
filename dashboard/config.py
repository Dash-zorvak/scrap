import os

# Bases de datos
FACEBOOK_DB = "/Users/pro/Downloads/scrapeo-social/data/facebook.db"
TIKTOK_DB   = "/Users/pro/Downloads/scrapeo-social/data/tiktok.db"
EXTERNOS_DB = "/Users/pro/Downloads/scrapeo-social/data/externos.db"
OUTPUT_DIR  = "/Users/pro/Downloads/scrapeo-social/dashboard/outputs"

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

# Reacciones Facebook disponibles con datos reales
FB_REACTIONS = ["likes_count", "loves_count", "hahas_count", "sads_count"]

# Columnas TikTok
TK_ENGAGEMENT = ["views", "likes", "shares", "favorites_count", "comments_count"]

# Cuentas TikTok
TK_ACCOUNTS = {
    1: "Alcaldía Santa Ana",
    3: "Gustavo Acevedo"
}

# Bases de datos de PRUEBA (datos inventados, alta tasa de rechazo)
FACEBOOK_TEST_DB = "/Users/pro/Downloads/scrapeo-social/data/facebook_test.db"
TIKTOK_TEST_DB   = "/Users/pro/Downloads/scrapeo-social/data/tiktok_test.db"
EXTERNOS_TEST_DB = "/Users/pro/Downloads/scrapeo-social/data/externos_test.db"

# Crear carpeta outputs si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)
