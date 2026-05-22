# scrapeo-social

Analítica de percepción pública para Facebook de Alcaldía de Santa Ana (página Jose Chicas).

## Meta

Extraer y analizar todos los posts, reacciones, vistas y comentarios de la página de Facebook Jose Chicas usando Graph API, almacenar en Supabase con backup SQLite local, y presentar un dashboard ejecutivo en Streamlit con análisis de sentimiento, temas, zonas e insights accionables.

## Stack

- **Scraping**: Facebook Graph API (`FB_ACCESS_TOKEN` con permisos `pages_read_engagement`, `pages_read_user_content`, `pages_manage_posts`, `read_insights`)
- **Almacenamiento**: SQLite local (`data/backup.db`) vía SQLAlchemy
- **Análisis**: `SentimentAnalyzer` (español, 3 niveles), Topic Detection (10 categorías), Zone Mapping (Centro/Norte/Sur/Este)
- **Dashboard**: Streamlit (`dashboard/app.py`) — 7 tabs: Ejecutivo, Zonas, Temas, Tendencia, Insights, Posts, Comentarios
- **Notificaciones**: Telegram bot para checkpoints de scraping
- **Infra**: Python 3.11 venv

## Estado Actual

| Recurso | Cantidad |
|---------|----------|
| Posts FB | 170 |
| Comentarios FB | 5,879 |
| Views | 170 posts con views |
| Sentimiento | 78.8% positivo, 14.7% neutral, 6.5% negativo |
| Dashboard | HTML estático con `data.js` generado desde SQLite |

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
│       └── supabase_client.py    # Wrapper de LocalStorage (compatibilidad)
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
./scrapeo analyze        # Generar métricas, insights y exportar dashboard/data.js
./scrapeo status         # Estado de BD
./scrapeo export-dashboard  # Exportar SQLite → dashboard/data.js
./scrapeo estimate N     # Proyectar tiempo para scrapear N posts (default: 20,000)

# Dashboard estático (abrir en navegador directamente):
open dashboard/index.html
```

## Fases Ejecutadas

1. **Posts (Graph API)**: 170 posts scrapeados (en progreso — target 500)
2. **Views**: 170 posts con views_count (completado)
3. **Comentarios**: 5,879 comentarios extraídos de los posts scrapeados
4. **Análisis**: Sentimiento, tópicos y zonas mapeados en los 170 posts

## Decisiones Clave

1. **Solo Facebook**: TikTok eliminado completamente del proyecto
2. **3 fases secuenciales**: posts → views → comments, con checkpoints cada N items
3. **Comentarios con stickers/imágenes**: detectados via `attachment.type`, guardados como `[sticker]`/`[image]`/`[video]`
4. **Posts compartidos**: via `_get_post_metadata` → salta páginas que no son Jose Chicas
5. **Dashboard HTML estático**: genera `dashboard/data.js` desde SQLite via `./scrapeo analyze` o `./scrapeo export-dashboard`
6. **Solo SQLite local**: sin dependencia de Supabase

## Issues Conocidos

- **Venv**: Python 3.11 venv en sistema 3.14 causa `ModuleNotFoundError` con pydantic-core, cryptography, numpy — requiere `pip install --force-reinstall` periódicamente
- **Graph API**: posts eliminados/borrados devuelven `(#100) Object does not exist` — se loggean y se saltan
- **Phase 3**: checkpoint en 350/4,763 (parada manual, datos reseteados para scrape nuevo)
- **Supabase eliminado**: ahora solo SQLite local. `SupabaseStorage` es un wrapper de `LocalStorage` por compatibilidad.

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
