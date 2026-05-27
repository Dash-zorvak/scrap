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
│   ├── intelligence/
│   │   └── cambridge_index.py    # Cambridge Index: TS, 5 alertas predictivas, supresión
│   ├── analyzer/
│   │   ├── sentiment.py          # Analizador español (3 niveles)
│   │   ├── anomaly_detector.py   # 5 alertas: controversia, sentimiento, engagement, topic, zona
│   │   ├── trends.py             # Análisis de tendencias
│   │   └── reporting.py          # Generación de informes JSON/PNG
│   ├── fb_scraper/
│   │   ├── graph_api_scraper.py  # Scraper FB vía Graph API
│   │   ├── deep_scraper.py       # Scraper FB profundo
│   │   └── models.py             # FBPostData, FBCommentData
│   └── storage/
│       ├── db.py                 # SQLite + SQLAlchemy
│       └── supabase_client.py    # Wrapper de LocalStorage (compatibilidad)
├── tests/
│   └── test_cambridge_index.py   # 52 tests: TS, alerts, supresión, integración
├── dashboard/
│   ├── streamlit_app.py          # Streamlit dashboard (7 tabs)
│   ├── dashboard.html            # Panel ejecutivo HTML estático
│   ├── indices.html              # Índices compuestos
│   ├── sentiment.html            # Sentimiento por tópico/zona
│   ├── insights.html             # Explorador de insights
│   └── index.html                # Landing page
├── data/                         # SQLite database
├── outputs/                      # Informes JSON y gráficos
├── .env                          # Credenciales y configuración
└── scrapeo                       # Wrapper: activa venv y ejecuta main
```

## Comandos

```bash
./scrapeo graph-scrape   # Scraping vía Graph API
./scrapeo deep-scrape --search "Jose Chicas" --max 500 --headless  # Deep scraping búsqueda
./scrapeo deep-search "Jose Chicas" 500   # Atajo para deep-scrape con search + headless
./scrapeo analyze        # Generar métricas, insights y exportar dashboard/data.js
./scrapeo status         # Estado de BD
./scrapeo export-dashboard  # Exportar SQLite → dashboard/data.js
./scrapeo nlp            # Pipeline NLP (emociones, entidades, colocaciones, tópicos)
./scrapeo nlp --batch 1000 --no-collocations --no-topics  # Solo emociones+entidades
./scrapeo nlp --n-topics 10   # Extraer 10 tópicos latentes
./scrapeo estimate N     # Proyectar tiempo para scrapear N posts (default: 20,000)
./scrapeo bulk-scrape 500 "Jose Chicas"  # Graph API + Deep Search combinado

# Dashboard estático (abrir en navegador directamente):
open dashboard/index.html

# Dashboard ciencia de datos (Streamlit):
streamlit run dashboard/streamlit_app.py
```

## Fases Ejecutadas

1. **Posts (Graph API)**: 170 posts scrapeados (en progreso — target 500)
2. **Views**: 170 posts con views_count (completado)
3. **Comentarios**: 5,879 comentarios extraídos de los posts scrapeados
4. **Análisis**: Sentimiento, tópicos y zonas mapeados en los 170 posts
5. **NLP Pipeline (nuevo)**: Emociones (6 categorías), entidades (spaCy + gazetteer), colocaciones (bigramas/trigramas), tópicos latentes (LDA)
6. **Dashboard Streamlit (nuevo)**: 7 tabs — Ejecutivo, Emociones, Entidades, Tópicos Latentes, Colocaciones, Anomalías, Diagnóstico
7. **Detección de anomalías**: Picos de controversia, disonancia entidad-sentimiento, caída de engagement, tópicos con rechazo inusual
8. **Cambridge Index (nuevo)**: Topic Sensitivity (11 topics, base 0.6–1.6, ajuste trimestral), 5 alertas predictivas (ICI, SDI, EFI, TAI, ZDI) con supresión (cooldown, deadband, sample mínimos)

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

## Bugs Fixed

- **Deep-scraper postId collision**: `new Uint8Array(8)` en JS crea array de ceros, no valores aleatorios → todos los posts tenían `postId = "deep_0000..."`. Fix: usar hash determinista del mensaje (`postIdFromMessage()`) con doble hash 32-bit para IDs únicos y estables entre scrolls (`deep_scraper.py:335-346`).
- **TimeoutGuard residual**: `guard.__exit__()` en bloque de autenticación referenciaba variable no definida (TimeoutGuard removido previamente). Fix: eliminar llamado huérfano (`deep_scraper.py:642`).

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
