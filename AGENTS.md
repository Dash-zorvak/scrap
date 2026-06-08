# scrapeo-social

Analítica de percepción pública para Facebook de Alcaldía de Santa Ana (página Jose Chicas).

## Meta

Extraer y analizar todos los posts, reacciones, vistas y comentarios de la página de Facebook Jose Chicas usando Graph API, almacenar en SQLite local, y presentar un dashboard ejecutivo en Streamlit con análisis de sentimiento, temas, zonas, NLP, alertas predictivas (Cambridge Index) e insights accionables.

## Stack

- **Scraping**: Facebook Graph API (`FB_ACCESS_TOKEN` con permisos `pages_read_engagement`, `pages_read_user_content`, `pages_manage_posts`, `read_insights`)
- **Almacenamiento**: SQLite local (`data/backup.db`) vía SQLAlchemy (7 tablas)
- **Análisis**: `SentimentAnalyzer` (español, 3 niveles + pysentimiento), Topic Detection (12 categorías), Zone Mapping (5 zonas), NLP pipeline (emociones, entidades, colocaciones, LDA)
- **Alertas Predictivas**: Cambridge Index — 5 detectores (ICI, SDI, EFI, TAI, ZDI) con supresión
- **Dashboard**: Streamlit (`dashboard/streamlit_app.py`) — 9 tabs: Ejecutivo, Emociones, Entidades, Tópicos, Cambridge, Colocaciones, Anomalías, Comentarios, Diagnóstico
- **Notificaciones**: Telegram bot para checkpoints de scraping
- **Tests**: 85 tests (pytest) — sentiment (6), topic detection (27), Cambridge Index (52)
- **Infra**: Python 3.11 venv

## Estado Actual

| Recurso | Cantidad |
|---------|----------|
| Posts FB | 444 |
| Comentarios FB | 3,490 |
| Views | 120+ posts con views |
| Sentimiento | 46% positivo, 10% negativo, 44% neutral |
| Tópicos detectados | 261/444 (59%) |
| Zonas detectadas | 64/444 (14%) |
| NLP emociones | 100% posts + 100% comentarios |
| NLP entidades | 100% posts + 100% comentarios |
| Problemáticas extraídas | 280 |
| Insights generados | 20 |
| Alertas Cambridge activas | 3 (TAI) |
| Tests | 85 pasando |

## Estructura del Proyecto

```
scrapeo-social/
├── src/
│   ├── main.py                    # CLI: 12 subcomandos
│   ├── config.py                  # Configuración desde .env
│   ├── intelligence/
│   │   └── cambridge_index.py    # Cambridge Index: TS, 5 alertas, supresión
│   ├── analyzer/
│   │   ├── sentiment.py          # Analizador español (3 niveles) + pysentimiento
│   │   ├── nlp_pipeline.py       # Pipeline NLP (emociones, entidades, colocaciones, LDA)
│   │   ├── topic_detection.py    # 12 tópicos, 5 zonas, emergencias, problemáticas
│   │   ├── executive_metrics.py  # NSI, CAI, insights, engagement
│   │   ├── anomaly_detector.py   # 5 alertas: controversia, sentimiento, engagement, topic, zona
│   │   ├── trends.py             # Análisis de tendencias
│   │   ├── reporting.py          # Generación de informes JSON/PNG
│   │   ├── latent_topics.py      # LDA topic modeling
│   │   ├── emotion_lexicon.py    # Léxico de emociones + colores
│   │   └── gazetteer.py          # Gazetteer de lugares, funcionarios
│   ├── fb_scraper/
│   │   ├── graph_api_scraper.py  # Scraper FB vía Graph API
│   │   ├── deep_scraper.py       # Scraper FB profundo (Playwright)
│   │   ├── phase3_resume.py      # Fase 3 extracción completa de comentarios
│   │   ├── models.py             # FBPostData, FBCommentData
│   │   └── bulk_scraper.py       # Scraping batch
│   └── storage/
│       ├── db.py                 # SQLite + SQLAlchemy (7 tablas)
│       └── supabase_client.py    # Thin wrapper de LocalStorage
├── tests/
│   ├── test_cambridge_index.py   # 52 tests
│   ├── test_sentiment.py         # 6 tests
│   └── test_topic_detection.py   # 27 tests
├── dashboard/
│   ├── streamlit_app.py          # Streamlit dashboard (9 tabs)
│   ├── data.js                   # Datos exportados desde SQLite
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
./scrapeo graph-scrape --max 500    # Scraping vía Graph API
./scrapeo deep-scrape --max 500     # Scraping profundo (Playwright)
./scrapeo analyze --reclassify     # Métricas, insights, problemáticas, Cambridge, export dashboard
./scrapeo cambridge                # Cambridge Index — alertas predictivas y sensibilidad por tópico
./scrapeo status                   # Estado de BD
./scrapeo export-dashboard         # Exportar SQLite → dashboard/data.js
./scrapeo nlp --batch 5000         # Pipeline NLP completo (emociones, entidades, colocaciones, tópicos)
./scrapeo phase3                   # Extraer comentarios pendientes (reanudable)
./scrapeo estimate N               # Proyectar tiempo para scrapear N posts

# Test:
pytest tests/                      # 85 tests

# Dashboard estático (abrir en navegador):
open dashboard/index.html

# Dashboard Streamlit:
streamlit run dashboard/streamlit_app.py
```

## Fases Ejecutadas

1. **Posts (Graph API)**: 387 posts scrapeados
2. **Views**: 120+ posts con views_count
3. **Comentarios**: 3,490 comentarios extraídos vía Phase 3
4. **Análisis**: Sentimiento, tópicos y zonas mapeados (59% topic, 14% zona)
5. **NLP Pipeline**: Emociones (6 categorías), entidades (spaCy + gazetteer), colocaciones (bigramas/trigramas), tópicos latentes (LDA) — 100% cobertura en posts + comentarios
6. **Dashboard Streamlit**: 9 tabs — Ejecutivo, Emociones, Entidades, Tópicos, Cambridge, Colocaciones, Anomalías, Comentarios, Diagnóstico
7. **Detección de anomalías**: Cambridge Index con 5 detectores predictivos y supresión
8. **Problemáticas**: 280 registros extraídos desde cmd_analyze
9. **Tests**: 85 tests (sentiment + topic detection + Cambridge Index)
10. **Deep-scraper**: Login corregido + exportador de cookies + 324 posts extraídos de SantaAnaAlcaldia
11. **Parsing numbers**: Fix bug `parseNum("44mil")` daba 44M — corregido distinguiendo M mayúscula de "mil"
12. **Keywords expansion**: Topic keywords ~70→~400, Zone keywords ~50→~200

## Decisiones Clave

1. **Solo Facebook**: TikTok eliminado completamente del proyecto
2. **3 fases secuenciales**: posts → views → comments, con checkpoints cada N items
3. **Comentarios con stickers/imágenes**: detectados via `attachment.type`, guardados como `[sticker]`/`[image]`/`[video]`
4. **Posts compartidos**: via `_get_post_metadata` → salta páginas que no son Jose Chicas
5. **Dashboard HTML estático**: genera `dashboard/data.js` desde SQLite via `./scrapeo analyze` o `./scrapeo export-dashboard`
6. **Solo SQLite local**: sin dependencia de Supabase

## Issues Conocidos

- **Graph API `from: null`**: Los comentarios de usuarios públicos no incluyen `from.name` por privacidad — se muestra "Anónimo"
- **NLP Pipeline timeout**: `process_pending` con batch >500 puede exceder 5 min por la carga de spaCy + pysentimiento por cada lote
- **Venv**: Python 3.11 venv en sistema 3.14 causa `ModuleNotFoundError` con pydantic-core, cryptography, numpy — requiere `pip install --force-reinstall` periódicamente
- **Graph API**: posts eliminados/borrados devuelven `(#100) Object does not exist` — se loggean y se saltan
- **Deep-scraper Phase 2 lento**: Visitar cada post individual para engagement toma ~50s/post. Facebook cambia DOM frecuentemente.
- **Página JoseMariaChicas restringida**: El deep-scraper no puede acceder. Solo SantaAnaAlcaldia es accesible.
- **Topic coverage 59%**: ~41% de posts son comentarios genéricos ("Bendiciones alcalde") sin tópico detectable por keywords.

## Bugs Fixed

- **Author name "Unknown"**: El API de Facebook devuelve `from: null` para comentarios públicos. Fix: mostrar "Anónimo" en lugar de "Unknown" en todos los scrapers + actualización retroactiva de 3,453 registros en DB.
- **Problematicas vacías**: `cmd_analyze` no llamaba `extract_problematicas`. Fix: agregado loop de extracción en `main.py` — genera 211 registros.
- **Author name "Unknown"**: El API de Facebook devuelve `from: null` para comentarios públicos. Fix: mostrar "Anónimo" en lugar de "Unknown" en todos los scrapers + actualización retroactiva de 3,453 registros en DB.
- **Problematicas vacías**: `cmd_analyze` no llamaba `extract_problematicas`. Fix: agregado loop de extracción en `main.py` — genera 211 registros (luego 280 con keywords expandidas).
- **Deep-scraper postId collision**: `new Uint8Array(8)` en JS crea array de ceros, no valores aleatorios → todos los posts tenían `postId = "deep_0000..."`. Fix: hash determinista del mensaje (`postIdFromMessage()`) con doble hash 32-bit para IDs únicos y estables entre scrolls (`deep_scraper.py:335-346`).
- **TimeoutGuard residual**: `guard.__exit__()` en bloque de autenticación referenciaba variable no definida (TimeoutGuard removido previamente). Fix: eliminar llamado huérfano (`deep_scraper.py:642`).
- **parseNum bug**: `parseNum("44mil")` detectaba la "m" de "mil" como "M" de millones → 44,000,000. Fix: `/M/i` case-insensitive reemplazado por matching exacto de "M" mayúscula en `deep_scraper.py`.
- **Deep-scraper login**: Facebook cambió `<button>` por `<div role="button">`. Fix: añadido `div[role="button"]:has-text(...)` al selector de login.

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

## Sesión Actual (1 Jun 2026)

### Goal
Build a hybrid Streamlit + HTML dashboard for Alcaldía Santa Ana (Jose Chicas) that processes raw FB and TikTok data into a brutally honest reputation analysis with Cambridge-style IQ indices, focused on re-election impact.

### Constraints & Preferences
- No campaign proposals — only display reality data
- Tono "cachetada en la cara" — brutally direct, comment-by-comment detail
- Sentiment: 5 niveles (muy_positivo → muy_negativo) instead of original 3
- Topics: 12 predefinidos + LDA emergent topics + NER entities for unlisted themes
- Zones: no hardcoded list; extract automatically via spaCy NER from real posts
- Gazetteer: strip all San Salvador entries; rebuild with Santa Ana–only data
- IQ Score: 7 dimensions (Aprobación, Conexión, Tranquilidad, Diversidad, Presencia, Consistencia, Atención)
- IQ display: combined headline (0-100) + radar chart + 2×2 matrix per platform
- Cross-platform: separate IQ FB / IQ TikTok + weighted General IQ (FB 55%, TT 45%)
- Periodicity: daily recalculation with 7-day rolling window
- Escenario A: clear analytical columns from FB DB (`backup.db`), move all processing to dashboard/analytics layer
- DB unified but raw: no sentiment/topic/zone stored; analysis is ephemeral in `analytics_cache.db`
- PDFs from Constanza & Asociados kept as reference of what NOT to deliver

### Progress
#### Done
- Explored both source databases (FB: 202 posts, 0 comments; TikTok: 1,552 videos, 3,172 comments, 163 non-empty)
- Cleaned FB analytical columns (SET sentiment=NULL, topic_category=NULL, zona=NULL) and deleted bogus 1659-date row
- Cleaned gazetteer: removed San Salvador entries, added Santa Ana–focused colonias, municipios, funcionarios, programas, lugares_emblemáticos
- Rewrote `sentiment.py` to 5-level rule‑based (muy_positivo/positivo/neutral/negativo/muy_negativo) with Unicode accent normalization via `unicodedata.normalize('NFKD')`
- Rewrote `topic_detection.py`:
  - Added accent normalization to `detect_topics`, `detect_zona`, `is_emergency`
  - Added `detect_zona_ner(text)` (spaCy GPE/LOC entities)
  - Added `detect_emerging_topics(texts)` (LDA wrapper)
  - Updated ZONA_KEYWORDS for Santa Ana with "colonia sur" fix
- Created `analytics_engine.py`:
  - Unified raw-data readers (`_get_fb_posts`, `_get_tt_posts`, `_get_fb_comments`, `_get_tt_comments`)
  - Processing pipeline with `analytics_cache.db` (processed_posts, processed_comments, daily_metrics, iq_scores)
  - `process_post()` runs sentiment + topic + zone + NER + emotions + entities + problemáticas
- Created `iq_engine.py`:
  - 7 dimension calculators (aprobacion, conexion, tranquilidad, diversidad_temas, presencia_zonas, consistencia, atencion)
  - `compute_iq_full()` returns `iq_general`, `iq_facebook`, `iq_tiktok`, radar data, matrix positions
  - `compute_cambridge_alerts()` wraps existing `run_all_detectors`
  - `compute_matrix_position()` returns quadrant labels
- Rewrote `dashboard/streamlit_app.py` (7 tabs):
  1. Ejecutivo (IQ headline + radar + matrix + re‑election alert)
  2. Reputación (5-level pie + cross-platform bar + per-dimension breakdown)
  3. IQ Score (7 dimension cards with bar + FB/TT split)
  4. Cambridge Index (NSI, Controversia, Riesgo, Aprobación gauges + alert cards)
  5. Tópicos y Zonas (keyword topic bar + LDA emergent + keyword zones + NER zones)
  6. Comentarios (filterable by platform/sentiment/topic + paginated comment feed)
  7. Problemáticas (detected issues + emergency Triage)
- Created `dashboard/generador_reporte.py` (print‑friendly HTML executive report)
- Updated tests: 86/86 pass (7 sentiment + 27 topic_detection + 52 cambridge_index)
- Fixed `conexion` dimension: handles FB posts with `views_count=0` by falling back to average reactions per post
- Full pipeline benchmark: FB 182 posts (6.7s) + TT 1,552 posts (84.6s) = ~91s total

### Current Status
- All 86 tests passing
- Analytics engine reads both DBs and processes posts successfully
- Cache DB (`analytics_cache.db`) created on first run (91s for full pipeline)
- Streamlit dashboard running at `http://localhost:8501`

### Key Decisions
- Unified schema but raw: FB and TikTok data stored in separate original DBs; analysis results cached in `analytics_cache.db` (processed_posts / processed_comments / daily_metrics / iq_scores tables)
- Sentiment 5‑level with rule‑based + pysentimiento + Transformers fallback chain; Unicode NFKD normalization to fix accent mismatches
- Topic detection: substring match with confidence scoring → if no keyword match, LDA (sklearn) + NER (spaCy) fill emergent topics
- Zone detection: keyword matching first → if empty, spaCy NER (GPE/LOC entities) as fallback
- IQ Score = weighted average of 7 dimensions (weights in `iq_engine.DIMENSION_WEIGHTS`) with separate per‑platform scores + combined weighted IQ
- Dashboard tone: red (#ff3355) as primary accent, crisis alerts, re‑election impact box on executive tab, "sin propuesta de campaña" footer
- Conexion dimension: when `views_count=0` (FB), use avg reactions per post instead of engagement rate

### Bugs Fixed in Diagnostic Run
- **Cache read crash**: `_get_cached_processed` tried `json.loads(cached["result_json"])` — the `processed_posts` table has no `result_json` column. Fixed in `process_post` and `process_comment` by reconstructing from individual columns with `None`-safe `json.loads()`.
- **Short-text posts not cached**: Empty/short text early-return paths skipped `_cache_processed()`, causing 5 TT + 20 FB posts to be reprocessed every run. Added cache calls to all return paths.
- **FB NULL-date posts filtered out**: `WHERE created_time > '2020-01-01'` excluded 20 FB posts with `created_time IS NULL`. Changed to `WHERE created_time IS NULL OR created_time > '2020-01-01'`.
- **Comment `post_id` lost**: `_cache_processed` for comments used `data.get("post_id", "")` but the `processed` dict didn't include `post_id`. Added `"post_id": comment.get("post_id", "")` to the processed dict.
- **Duplicate keywords**: `"exito"`, `"exitosa"`, `"exitoso"`, `"beneficio"`, `"beneficios"`, `"beneficiando"` appeared twice in `positive_words` (sentiment.py), inflating positive scores. Removed duplicate block.
- **Topic filter dead**: `topic_filter` selectbox in Tab 6 (Comentarios) was rendered but never applied to the filtered list. Added `if topic_filter != "Todos"` filter.
- **Cambridge alerts mixed platform data**: `compute_cambridge` received `all_posts_tuple` (FB + TT mixed), but Cambridge detectors expect FB reaction distributions. Fixed to pass only FB posts.
- **`is_emergency` no accent normalization**: Used `text.lower()` instead of NFKD normalization. Added normalization for both text and keywords.
- **Emotion lexicon normalization**: `_analyze_emotions_lexicon` skipped accent normalization and used substring matching. Added NFKD normalization and `\b` word boundaries.

### OCEAN-like Analysis Engine
New module `src/analyzer/ocean_engine.py` implements Cambridge-style techniques adapted to our data:
- **PCA**: Reduces 21+ dimensions per post to 3 principal components (explains ~30% variance)
- **K-Means**: Groups posts into 5 clusters by engagement pattern, sentiment, topic
- **Linear Regression**: Predicts engagement (reactions) from content features (MAE ~6,077 reactions)
- **Logistic Regression**: Classifies controversy risk (99.5% accuracy, 10 high-risk posts detected)
- Integration in dashboard as Tab 8 "Patrones"

### IQ Results (First Run)
| Dimension | FB | TT |
|-----------|-----|------|
| Aprobación | 61.1 | 62.5 |
| Conexión | 100.0 | 89.0 |
| Tranquilidad | 100.0 | 100.0 |
| Diversidad Temas | 46.7 | 83.7 |
| Presencia Zonas | 24.7 | 65.1 |
| Consistencia | 50.0 | 93.5 |
| Atención | 48.6 | 56.5 |
| **IQ Total** | **65.0** | **80.3** |
| **IQ General** | **71.9** | |

### Known Issues
- **TikTok comments**: Only 163/3,172 have non‑empty text; 3,009 are empty strings. Likely scraper couldn't extract text from those comments.
- **FB views**: All posts have `views_count = 0` — Conexion dimension uses avg reactions as fallback.
- **Topic coverage**: 46.7% FB (85/182), 83.7% TT (1,299/1,552). ~53% of FB posts have no keyword match.
- **Zone coverage (FB)**: 24.7% keyword + 27.5% NER. NER picks up false positives like "Responder", "KFC".
- **LDA topics**: Need ≥10 documents with ≥3 words each; not yet validated with full corpus.
- **Cache invalidation**: `analytics_cache.db` is append-only; no mechanism to detect stale data yet.
- **pysentimiento**: Not installed (missing from venv). Rule‑based fallback is the active code path.

### Relevant Files
- `data/backup.db`: Facebook raw data (202 posts, 0 comments, analytical columns NULL'd)
- `data/tiktok.db`: TikTok raw data (1,552 videos, 3,172 comments, 2 accounts)
- `data/analytics_cache.db`: Analysis results cache (created on first pipeline run)
- `src/analyzer/sentiment.py`: 5-level sentiment with rule‑based + accent normalization
- `src/analyzer/topic_detection.py`: keyword topic/zone detection + NER fallback + LDA emergent topics
- `src/analyzer/gazetteer.py`: Santa Ana–only gazetteer (colonias, municipios, funcionarios, programas, lugares_emblemáticos)
- `src/analyzer/analytics_engine.py`: unified reader, NLP pipeline processor, cache layer (writes to `analytics_cache.db`)
- `src/analyzer/iq_engine.py`: 7-dimension IQ calculator, radar, 2×2 matrix, Cambridge wrapper
- `dashboard/streamlit_app.py`: 7-tab Streamlit dashboard with brutal‑honesty design
- `dashboard/generador_reporte.py`: HTML executive‑report generator
- `dashboard/Social Listening *.pdf`: 3 reference PDFs from Constanza & Asociados (what NOT to deliver)
