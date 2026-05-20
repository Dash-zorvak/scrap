# scrapeo-social

Analítica de percepción pública para Facebook de Alcaldía de Santa Ana (página Jose Chicas).

## Meta

Extraer y analizar todos los posts, reacciones, vistas y comentarios de la página de Facebook Jose Chicas usando Graph API, almacenar en Supabase con backup SQLite local, y presentar un dashboard ejecutivo en Streamlit con análisis de sentimiento, temas, zonas e insights accionables.

## Stack

- **Scraping**: Facebook Graph API (`FB_ACCESS_TOKEN` con permisos `pages_read_engagement`, `pages_read_user_content`, `pages_manage_posts`, `read_insights`)
- **Almacenamiento**: Supabase (PostgreSQL cloud) + SQLite local (`data/backup.db`) como backup de verificación
- **Análisis**: `SentimentAnalyzer` (español, 3 niveles), Topic Detection (10 categorías), Zone Mapping (Centro/Norte/Sur/Este)
- **Dashboard**: Streamlit (`dashboard/app.py`) — 7 tabs: Ejecutivo, Zonas, Temas, Tendencia, Insights, Posts, Comentarios
- **Notificaciones**: Telegram bot para checkpoints de scraping
- **Infra**: Python 3.11 venv

## Estado Actual

| Recurso | Cantidad |
|---------|----------|
| Posts FB | 4,763 |
| Comentarios FB | 20,951 |
| Likes | ~95K |
| Loves | ~36K |
| Hahas | ~6K |
| Sads | ~1.4K |
| Angrys | ~2.2K |
| Shares | ~15K |
| Vistas | ~3.9M (3,822 posts con views > 0) |
| Sentimiento (posts) | 2,696 positive · 301 negative · 1,766 neutral → NSI ~79.9% |
| Sentimiento (comentarios) | 9,082 positive · 1,414 negative · 5,627 neutral → NSI ~73% |

## Estructura del Proyecto

```
scrapeo-social/
├── src/
│   ├── main.py                    # CLI: scrape, analyze, status
│   ├── config.py                 # Configuración desde .env
│   ├── analyzer/
│   │   ├── sentiment.py          # Analizador español (3 niveles)
│   │   ├── trends.py             # Análisis de tendencias
│   │   └── reporting.py          # Generación de informes JSON/PNG
│   ├── fb_scraper/
│   │   ├── graph_api_scraper.py  # Scraper FB vía Graph API
│   │   ├── deep_scraper.py       # Scraper FB profundo
│   │   └── models.py             # FBPostData, FBCommentData
│   └── storage/
│       ├── db.py                 # SQLite + SQLAlchemy
│       └── supabase_client.py    # Supabase storage
├── dashboard/
│   └── app.py                    # Streamlit dashboard (7 tabs)
├── data/                         # SQLite database
├── outputs/                      # Informes JSON y gráficos
├── .env                          # Credenciales y configuración
└── scrapeo                       # Wrapper: activa venv y ejecuta main
```

## Comandos

```bash
./scrapeo graph-scrape   # Scraping vía Graph API
./scrapeo deep-scrape    # Deep scraping alternativo
./scrapeo analyze        # Generar métricas e insights
./scrapeo status         # Estado de BD
./scrapeo verify         # Comparar Supabase vs backup local
./scrapeo sync           # Sincronizar Supabase → local
./scrapeo estimate N     # Proyectar tiempo para scrapear N posts (default: 20,000)
streamlit run dashboard/app.py  # Dashboard ejecutivo (Bloomberg-style, 8 tabs)
```

## Fases Ejecutadas

1. **Posts**: 4,763 posts scrapeados vía Graph API, ~96 min, ~0.8 posts/s
2. **Views**: 3,822 posts actualizados con views_count, 54 min
3. **Comentarios**: procesados 1,100/4,763 posts, 20,951 comentarios en Supabase + SQLite

## Decisiones Clave

1. **Solo Facebook**: TikTok eliminado completamente del proyecto
2. **3 fases secuenciales**: posts → views → comments, con checkpoints cada N items
3. **Comentarios con stickers/imágenes**: detectados via `attachment.type`, guardados como `[sticker]`/`[image]`/`[video]`
4. **Posts compartidos**: via `_get_post_metadata` → salta páginas que no son Jose Chicas
5. **Dashboard todo-en-uno**: una sola app Streamlit con todas las vistas
6. **Backup dual**: Supabase (primario) + SQLite local (verificación vía `./scrapeo verify`)

## Issues Conocidos

- **Venv**: Python 3.11 venv en sistema 3.14 causa `ModuleNotFoundError` con pydantic-core, cryptography, numpy — requiere `pip install --force-reinstall` periódicamente
- **Graph API**: posts eliminados/borrados devuelven `(#100) Object does not exist` — se loggean y se saltan
- **Phase 3**: checkpoint en 1,100/4,763 (parada manual)

## Entorno de Ejecución

```bash
./scrapeo status
# O manualmente:
source venv/bin/activate
python -m src.main status
```

## Notas Importantes

1. **Sin propuesta de campaña**: El entregable es solo análisis de datos para presentar al edil
2. **Graph API** con `FB_ACCESS_TOKEN` requiere permisos: `pages_read_engagement`, `pages_read_user_content`, `pages_manage_posts`, `read_insights`
