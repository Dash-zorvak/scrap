# TikTok Scraper V2

Scrapeo de videos, comentarios e hilos de 2 cuentas de TikTok.
Sin browser. Con checkpoints para reanudar si se interrumpe.

## Requisitos previos

- Python 3.11+
- PostgreSQL corriendo localmente

## Setup rápido

```bash
# 1. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear la base de datos
createdb tiktok_scraper

# 4. Verificar conexión
python run.py --status
```

## Ejecución por fases

```bash
# FASE 1: Scrapear todos los videos (~2-4 horas)
python run.py --phase 1

# FASE 2: Scrapear comentarios de cada video (~15-30 horas)
python run.py --phase 2

# FASE 3: Scrapear hilos de respuestas (~35-55 horas)
python run.py --phase 3

# Todo en secuencia (recomendado dejar corriendo)
python run.py --phase all
```

## Monitoreo

```bash
# Ver cuántos datos se han recolectado
python run.py --status

# Revisar logs del día
tail -f scraper_$(date +%Y%m%d).log
```

## Si se interrumpe

No hay problema. Cada fase guarda un checkpoint.
Al volver a ejecutar el mismo comando, continúa desde donde quedó.

## Cambiar URL de base de datos

```bash
export TIKTOK_DB_URL="postgresql://usuario:password@localhost/tiktok_scraper"
python run.py --phase all
```

## Estructura de datos

### tt_videos
- video_id, username, description, create_time
- likes_count, comments_count, shares_count, views_count, favorites_count
- hashtags (JSON), thumbnail_url, video_url

### tt_comments
- comment_id, video_id, text, author_name, create_time, likes_count
- parent_comment_id (NULL = raíz), is_reply, reply_count