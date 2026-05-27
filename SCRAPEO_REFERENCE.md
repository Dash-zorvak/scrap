# Scrapeo Social — Referencia Completa

Proyecto: `~/Downloads/scrapeo-social` (NO en iCloud — evita corrupción de .so)
Última actualización: Mayo 2026

---

## 1. COMANDOS

### Wrapper `./scrapeo` (bash)

| Comando | Qué hace |
|---|---|
| `./scrapeo full-scrape [N]` | Scrapea N posts de TODAS las páginas en FB_PAGES. Usa Graph API si tiene `id`, Deep Scraper si tiene `url`. Al final corre `analyze` para actualizar el dashboard. |
| `./scrapeo bulk-scrape [N]` | Exactamente igual que full-scrape (alias). |
| `./scrapeo graph-scrape [--page N]` | Scrapea vía Graph API (página individual). Pasa --page para índice en FB_PAGES. |
| `./scrapeo deep-scrape [--page-url URL] [--page-name NAME] [--max N]` | Deep scraping con Playwright para páginas sin ID numérico. |
| `./scrapeo analyze` | Genera métricas (NSI, CAI, insights) y exporta dashboard/data.js |
| `./scrapeo status` | Muestra estado de la DB (posts, comentarios, sentimiento) |
| `./scrapeo pages` | Lista páginas configuradas con indicador 🔑 Graph API / 🌐 Playwright/Deep |
| `./scrapeo phase3 [--page N]` | Reanuda extracción de comentarios desde checkpoint |
| `./scrapeo estimate [N]` | Estima tiempo para scrapear N posts (default: 20,000) |
| `./scrapeo export-dashboard` | Exporta SQLite → dashboard/data.js |
| `./scrapeo reset` | Purga TODOS los datos de la DB |
| `./scrapeo scrape` | (Legacy) Scraper con Playwright base |

### Argumentos comunes para subcomandos de main.py

| Flag | Aplica a | Qué hace |
|---|---|---|
| `--page N` | graph-scrape, deep-scrape, phase3 | Selecciona página por índice en FB_PAGES |
| `--page-id ID` | graph-scrape, deep-scrape, phase3 | ID numérico de la página (sobreescribe FB_PAGES) |
| `--page-name NAME` | graph-scrape, deep-scrape, phase3 | Nombre visible de la página |
| `--page-url URL` | deep-scrape | URL completa de página pública (ej: https://facebook.com/PaginaX) |
| `--max N` | graph-scrape, deep-scrape | Posts objetivo |
| `--headless` | deep-scrape | Modo headless (sin ventana) |
| `--cookies-file PATH` | deep-scrape | Ruta a cookies.json |
| `--checkpoint-every N` | deep-scrape, phase3 | Checkpoint cada N posts |
| `--token TOKEN` | graph-scrape | Access token (o usa FB_ACCESS_TOKEN en .env) |
| `--no-comments` | graph-scrape | Saltar extracción de comentarios |
| `--no-replies` | graph-scrape, phase3 | Saltar replies/hilos |
| `--log-level {debug,info,warning,error}` | todos | Nivel de logging |

---

## 2. ESTRUCTURA DETALLADA DEL PROYECTO

```
~/Downloads/scrapeo-social/
│
├── scrapeo                          # Entry point CLI (bash wrapper)
│   ├── full-scrape / bulk-scrape    # Itera FB_PAGES, elige scraper según id/url
│   ├── pages                        # Lista páginas con emoji método
│   ├── estimate                     # Delega a src/analyzer/estimation.py
│   └── *                            # Todo lo demás delega a src.main
│
├── .env                             # Config: tokens, FB_PAGES, credenciales, proxy
├── .env.example                     # Template documentado
│
├── requirements.txt                 # Dependencias Python
├── setup.sh                         # Script único de instalación
├── cookies.json                     # Cookies de sesión Facebook (autogenerado)
│
├── AGENTS.md                        # Memoria del proyecto (para IA)
├── supabase_schema.sql              # DDL (legacy, ya no se usa)
├── supabase_insert_policies.sql     # RLS policies (legacy)
│
├── src/                             # ★ LÓGICA PRINCIPAL ★
│   │
│   ├── main.py                      # CLI argparse: 11 subcomandos
│   │   ├── main()                   # Parser principal + dispatch
│   │   ├── _resolve_page()          # Unifica args + .env → dict con has_id
│   │   ├── cmd_graph_scrape()       # Graph API handler (salta si no hay has_id)
│   │   ├── cmd_deep_scrape()        # Deep Scraper handler (acepta page_url)
│   │   ├── cmd_scrape()             # Playwright legacy handler
│   │   ├── cmd_analyze()            # Métricas + export dashboard
│   │   ├── cmd_status()             # Estado de DB
│   │   ├── cmd_phase3()             # Reanudación de comentarios
│   │   ├── cmd_reset()              # Purga completa
│   │   ├── cmd_estimate()           # Estimación de tiempo
│   │   ├── _export_dashboard_data() # SQLite → dashboard/data.js
│   │   └── analyze_and_save_posts() # Sentimiento + tópico + zona por post
│   │
│   ├── config.py                    # Clase Config
│   │   ├── pages (property)         # Parsea FB_PAGES (JSON), fallback a vars individuales
│   │   ├── get_page(index)          # Retorna página específica + has_id
│   │   └── resolve_page()           # Unifica fuente de página (args/env)
│   │
│   ├── fb_scraper/                  # ★ SCRAPERS ★
│   │   ├── __init__.py
│   │   ├── models.py                # FBPostData, FBCommentData (dataclasses)
│   │   │
│   │   ├── graph_api_scraper.py     # GraphAPIScraper (553 líneas)
│   │   │   └── GraphAPIScraper
│   │   │       ├── __init__(token, page_id, page_name)
│   │   │       ├── scrape(max_posts, get_comments, get_replies)
│   │   │       │   ├── Fase 1: Posts (FB Graph API /me/feed)
│   │   │       │   ├── Fase 1b: Vistas (/{post}/insights)
│   │   │       │   └── Fase 2: Comentarios + replies
│   │   │       ├── _get_post_metadata()       # Salta posts compartidos
│   │   │       ├── _get_post_insights()       # Views count
│   │   │       ├── _get_comments()            # Comentarios con paginación
│   │   │       ├── _get_replies()             # Replies/hilos
│   │   │       └── _analyze_comment()         # Sentimiento + tópico + zona
│   │   │
│   │   ├── bulk_scraper.py          # BulkFacebookScraper (orquestador 3 fases)
│   │   │   └── BulkFacebookScraper
│   │   │       ├── __init__(phase, max_posts)
│   │   │       ├── run()            # Ejecuta fases secuencialmente
│   │   │       ├── phase1_posts()   # Posts batch con checkpoint
│   │   │       ├── phase2_views()   # Views batch con checkpoint
│   │   │       ├── phase3_comments()# Comentarios batch con checkpoint
│   │   │       └── main()           # Entry point CLI
│   │   │
│   │   ├── phase3_resume.py         # Phase3Resumer (268 líneas)
│   │   │   └── Phase3Resumer
│   │   │       ├── __init__(token, page_id)
│   │   │       ├── run()            # Loop sobre posts sin comentarios
│   │   │       ├── _load_pending_posts()  # Posts que faltan comentar
│   │   │       ├── _save_checkpoint()
│   │   │       └── _process_post_comments()
│   │   │
│   │   ├── deep_scraper.py          # FacebookDeepScraper
│   │   │   └── FacebookDeepScraper
│   │   │       ├── __init__(cookies_file, page_id, page_name, page_url, ...)
│   │   │       ├── _init_browser()  # Playwright + stealth
│   │   │       ├── _login()         # Carga cookies de sesión
│   │   │       ├── scrape(max_posts, checkpoint_every)
│   │   │       │   ├── Navegación URL-aware (page_url o page_id)
│   │   │       │   ├── Scroll infinito con anti-ban
│   │   │       │   ├── Extracción de posts + texto
│   │   │       │   └── Checkpoint cada N posts
│   │   │       ├── _scrape_page_posts()
│   │   │       ├── _extract_post_text()
│   │   │       └── _detect_ban()    # Anti-detección
│   │   │
│   │   └── playwright_scraper.py    # FacebookPlaywright (475 líneas)
│   │       └── FacebookPlaywright
│   │           ├── __init__(email, password, proxy, headless, cookies)
│   │           ├── _init_session()  # Login por cookies o email/password
│   │           ├── scrape_page_posts(page_name, max_posts)  # Scroll + extracción
│   │           ├── _login_with_cookies()
│   │           ├── _login_with_credentials()
│   │           └── _has_more_posts()
│   │
│   ├── storage/                     # ★ ALMACENAMIENTO ★
│   │   ├── __init__.py
│   │   ├── db.py                    # LocalStorage (SQLite + SQLAlchemy)
│   │   │   └── LocalStorage
│   │   │       ├── __init__(db_path, backup)
│   │   │       ├── _init_db()       # Crea tablas si no existen
│   │   │       ├── insert_fb_post(post)    # UNIQUE on post_id
│   │   │       ├── insert_fb_comment(comment)  # UNIQUE on comment_id
│   │   │       ├── insert_problematica()
│   │   │       ├── insert_insight()
│   │   │       ├── insert_daily_metric()
│   │   │       ├── get_fb_posts(limit, offset)  # + filtros por page_id, date
│   │   │       ├── get_fb_post(post_id)
│   │   │       ├── get_fb_comments(limit, offset, post_id)
│   │   │       ├── get_posts_without_comments()
│   │   │       ├── get_executive_summary()    # Conteos + sentimiento
│   │   │       ├── purge_all()
│   │   │       └── _backup()        # Backup antes de purge
│   │   │
│   │   └── supabase_client.py       # SupabaseStorage → wrapper de LocalStorage
│   │       └── SupabaseStorage
│   │           ├── __init__()       # Instancia LocalStorage
│   │           └── (delega todo a .local)
│   │
│   ├── analyzer/                    # ★ ANÁLISIS ★
│   │   ├── __init__.py
│   │   ├── sentiment.py             # SentimentAnalyzer (261 líneas)
│   │   │   └── SentimentAnalyzer
│   │   │       ├── analyze(text)    # Retorna (label, score)
│   │   │       ├── _analyze_pysentimiento()  # NLP español
│   │   │       └── _analyze_fallback()       # Léxico (300+ palabras)
│   │   │
│   │   ├── topic_detection.py       # Topic + Zona Detection (196 líneas)
│   │   │   ├── TOPIC_KEYWORDS       # 10 categorías con keywords
│   │   │   ├── get_main_topic(text) # Retorna topic key
│   │   │   ├── detect_zona(text)    # Retorna zona geográfica
│   │   │   ├── extract_problematicas(text, sentiment)  # Problemas detectados
│   │   │   ├── get_top_keywords(texts, n)   # Keywords más frecuentes
│   │   │   └── get_top_bigrams(texts, n)    # Bigramas más frecuentes
│   │   │
│   │   ├── executive_metrics.py     # ExecutiveMetrics
│   │   │   └── ExecutiveMetrics
│   │   │       ├── __init__(storage)
│   │   │       ├── generate_daily_metrics(platform)  # NSI, CAI, engagement, etc.
│   │   │       └── generate_insights(platform)       # Insights accionables
│   │   │
│   │   ├── reporting.py             # Reportes visuales (matplotlib)
│   │   │   └── generate_report(posts, output_dir)
│   │   │
│   │   ├── trends.py                # TrendAnalyzer
│   │   │   └── TrendAnalyzer
│   │   │       ├── analyze(posts)   # Picos, correlaciones, patrones
│   │   │       └── detect_trends(monthly_data)
│   │   │
│   │   └── estimation.py            # Estimación de tiempo de scrape
│   │       └── calc_metrics(target)   # Basado en benchmarks reales
│   │
│   ├── notifications/               # ★ NOTIFICACIONES ★
│   │   ├── __init__.py
│   │   └── telegram.py              # TelegramNotifier
│   │       └── TelegramNotifier
│   │           ├── __init__()       # Se auto-habilita si hay token+chat_id
│   │           ├── send(message)    # Mensaje individual
│   │           ├── send_batch(messages)  # Batch de mensajes
│   │           └── send_alert(message, type)  # Alertas con emoji
│   │
│   ├── scraper_pipeline.py          # ScraperPipeline (legacy, no activo)
│   └── scraper_resilient.py         # ResilientScraper (legacy, no activo)
│
├── dashboard/                       # ★ FRONTEND HTML ★
│   ├── dashboard.html               # Dashboard principal con KPIs
│   ├── index.html                   # Landing page
│   ├── sentiment.html               # Vista de sentimiento
│   ├── indices.html                 # Vista de índices ejecutivos
│   ├── insights.html                # Vista de insights
│   ├── data.js                      # OUTPUT: ~30KB JSON con todos los datos
│   └── .env                         # Config del dashboard (raro)
│
├── data/                            # ★ DATOS PERSISTENTES ★
│   ├── backup.db                    # SQLite con posts, comentarios, métricas
│   └── phase3_checkpoint.json       # Checkpoint de Phase 3
│
└── SKILLS/                          # Skills de opencode (no del proyecto)
    ├── caveman.md
    ├── diagnose.md
    └── grill-me.md
```

---

## 3. CONFIGURACIÓN DE PÁGINAS (.env)

### Formato FB_PAGES (recomendado — multi-página)

```env
# Mezcla de páginas admin (con id) y públicas (solo url):
FB_PAGES=[{"id":"123456789","name":"PaginaAdmin"},{"url":"https://facebook.com/PaginaPublica","name":"PaginaPublica"}]

# Solo páginas admin:
FB_PAGES=[{"id":"111","name":"Pag1"},{"id":"222","name":"Pag2"}]

# Solo páginas públicas:
FB_PAGES=[{"url":"https://facebook.com/Pub1","name":"Pub1"},{"url":"https://fb.com/Pub2","name":"Pub2"}]
```

### Fallback legacy (página única, sin FB_PAGES)

```env
FB_PAGE_ID=123456789       # Para Graph API
FB_PAGE_NAME=MiPagina      # Nombre visible
FB_PAGE_URL=https://facebook.com/MiPagina   # Para Deep Scraper
```

### Otras variables de .env

```env
FB_ACCESS_TOKEN=EAAx...    # Token Graph API (requiere pages_read_engagement, etc.)
FB_EMAIL=user@email.com    # Para Playwright login
FB_PASSWORD=secret         # Para Playwright login
TELEGRAM_BOT_TOKEN=xxx     # Notificaciones (opcional)
TELEGRAM_CHAT_ID=xxx       # Notificaciones (opcional)
PROXY_URL=                  # Proxy opcional
MAX_POSTS=500               # Default para scrape legacy
```

---

## 4. FLUJO DE DATOS

```
FB_PAGES (.env)
    │
    ▼
./scrapeo full-scrape N
    │
    ├── ¿tiene "id"?  →  src.fb_scraper.bulk_scraper (Graph API, 3 fases)
    │                        │
    │                        ├── Fase 1: Posts (feed) con checkpoint
    │                        ├── Fase 2: Views (insights) con checkpoint
    │                        └── Fase 3: Comments con checkpoint
    │
    ├── ¿solo "url"?  →  src.main deep-scrape (Playwright/Deep Scraper)
    │                        │
    │                        └── Navegación URL + scroll + extracción + checkpoint
    │
    └── (al final) → python -m src.main analyze
                         │
                         ├── ExecutiveMetrics (NSI, CAI, insights)
                         ├── SentimentAnalyzer
                         ├── TopicDetection
                         └── _export_dashboard_data() → dashboard/data.js
```

---

## 5. ESQUEMA DE BASE DE DATOS (SQLite)

### Tabla: fb_posts
| Columna | Tipo | Notas |
|---|---|---|
| id | INTEGER | PK autoincrement |
| post_id | TEXT | UNIQUE |
| page_id | TEXT | |
| page_name | TEXT | |
| message | TEXT | Contenido del post |
| created_time | TEXT | ISO datetime |
| likes/loves/hahas/wows/sads/angrys_count | INTEGER | |
| comments_count | INTEGER | |
| shares_count | INTEGER | |
| views_count | INTEGER | |
| post_url | TEXT | |
| sentiment | TEXT | positive / neutral / negative |
| sentiment_score | FLOAT | 0.0 - 1.0 |
| topic_category | TEXT | obra_publica, seguridad, etc. |
| zona | TEXT | Centro, Norte, Este, Sur, Oeste |
| scraped_at | TIMESTAMP | Default now() |

### Tabla: fb_comments
| Columna | Tipo | Notas |
|---|---|---|
| id | INTEGER | PK autoincrement |
| comment_id | TEXT | UNIQUE |
| post_id | TEXT | FK a fb_posts |
| parent_id | TEXT | NULL si es top-level, comment_id del padre si es reply |
| author_name | TEXT | |
| message | TEXT | |
| created_time | TEXT | |
| sentiment | TEXT | |
| sentiment_score | FLOAT | |
| topic_category | TEXT | |
| zona | TEXT | |
| scraped_at | TIMESTAMP | |

### Tabla: problematicas
| Columna | Tipo |
|---|---|
| id | INTEGER PK |
| platform | TEXT |
| post_id | TEXT |
| topic | TEXT |
| zona | TEXT |
| message | TEXT |
| sentiment | TEXT |
| sentiment_score | FLOAT |

### Tabla: daily_metrics
| Columna | Tipo |
|---|---|
| id | INTEGER PK |
| platform | TEXT |
| date | TEXT |
| nsi | FLOAT |
| cai | FLOAT |
| engagement | FLOAT |
| controversy | FLOAT |
| effectiveness | FLOAT |
| risk_reputacional | FLOAT |
| total_posts | INTEGER |
| total_reactions | INTEGER |
| total_comments | INTEGER |
| total_shares | INTEGER |
| total_views | INTEGER |

### Tabla: insights
| Columna | Tipo |
|---|---|
| id | INTEGER PK |
| platform | TEXT |
| type | TEXT |
| title | TEXT |
| description | TEXT |
| severity | TEXT |
| created_at | TIMESTAMP |

---

## 6. COMANDOS POR MÉTODO DE SCRAPING

### 🔑 Graph API

Usa la REST API oficial de Facebook. Requiere `FB_ACCESS_TOKEN` con permisos y **page_id numérico**.
Más estable, datos completos (reacciones por tipo, views, replies), sin riesgo de bloqueo.

```bash
# 1) Scrape directo (src/fb_scraper/graph_api_scraper.py)
./scrapeo graph-scrape
./scrapeo graph-scrape --max 2000                        # posts objetivo
./scrapeo graph-scrape --page 0                           # página por índice en FB_PAGES
./scrapeo graph-scrape --page-id "12345" --page-name "MiPagina"
./scrapeo graph-scrape --token "EAAx..."                  # token explícito
./scrapeo graph-scrape --no-comments                      # solo posts, sin comentarios
./scrapeo graph-scrape --no-replies                       # comentarios sin replies
./scrapeo graph-scrape --log-level debug                  # modo verbose

# 2) Scraper orquestado 3 fases (src/fb_scraper/bulk_scraper.py)
# Fase 1: Posts → Fase 2: Views → Fase 3: Comentarios (con checkpoint cada N)
./scrapeo bulk-scrape 500                                 # 500 posts, todas las fases
./scrapeo full-scrape 1000                                # alias, mismo comportamiento
# Detrás de escena: itera FB_PAGES, para cada página con "id" ejecuta:
#   python -m src.fb_scraper.bulk_scraper --phase all --max 500

# 3) Reanudar Phase 3 (src/fb_scraper/phase3_resume.py)
# Extrae comentarios de posts que ya están en DB pero sin comentarios
./scrapeo phase3
./scrapeo phase3 --page 0                                 # página específica
./scrapeo phase3 --no-replies                             # solo comentarios top-level
./scrapeo phase3 --checkpoint-every 100                   # checkpoint cada 100 posts
```

### 🌐 Deep Scraper (Playwright + Anti-ban)

Usa Playwright con navegación tipo humana, anti-detección y cookies de sesión.
Acepta **URL completa** de páginas públicas (no requiere ID numérico ni token).

```bash
# 1) Deep scrape directo (src/fb_scraper/deep_scraper.py)
./scrapeo deep-scrape --page-url "https://facebook.com/PaginaPublica" --page-name "PaginaX"
./scrapeo deep-scrape --page-url "https://fb.com/Pagina" --page-name "X" --max 200
./scrapeo deep-scrape --page-url "https://facebook.com/Pagina" --page-name "X" --start "2024-01-01"
./scrapeo deep-scrape --page-url "..." --page-name "X" --headless          # sin ventana
./scrapeo deep-scrape --page-url "..." --page-name "X" --cookies-file "mis_cookies.json"
./scrapeo deep-scrape --page-url "..." --page-name "X" --checkpoint-every 25
./scrapeo deep-scrape --page-url "..." --page-name "X" --log-level debug

# 2) Deep scrape con índice de FB_PAGES
# Si FB_PAGES tiene una entrada como {"url":"https://...","name":"PaginaX"}:
./scrapeo deep-scrape --page 1                            # página #1 de FB_PAGES

# 3) Auto-detectado desde full-scrape
# full-scrape/bulk-scrape detecta automáticamente páginas sin "id" y las procesa con deep-scrape:
./scrapeo full-scrape 300                                 # mezcla Graph API + Deep Scraper
# Detrás de escena para cada página con "url" ejecuta:
#   python -m src.main deep-scrape --page-url "..." --page-name "X" --max 300
```

### 🎭 Playwright (Scraper base — legacy)

Scraper base con Playwright. Usa login por email/password o cookies.
Requiere `FB_EMAIL` + `FB_PASSWORD` en `.env`. No tiene anti-detección avanzada.

```bash
# 1) Scrape legacy (src/fb_scraper/playwright_scraper.py)
./scrapeo scrape                                          # usa FB_PAGE_NAME/FB_PAGE_URL de .env
./scrapeo scrape --max 500
./scrapeo scrape --platform facebook

# 2) Uso directo desde Python
source venv/bin/activate
python -c "
from src.fb_scraper.playwright_scraper import FacebookPlaywright
from src.config import Config
cfg = Config()
fb = FacebookPlaywright(email=cfg.FB_EMAIL, password=cfg.FB_PASSWORD)
posts = fb.scrape_page_posts(page_name=cfg.FB_PAGE_NAME, max_posts=100)
print(f'Scraped {len(posts)} posts')
"

# 3) Con cookies (sin email/password)
source venv/bin/activate
python -c "
from src.fb_scraper.playwright_scraper import FacebookPlaywright
fb = FacebookPlaywright(cookies_file='cookies.json')
posts = fb.scrape_page_posts(page_name='PaginaX', max_posts=200)
"
```

---

## 7. DECISIONES CLAVE

1. **Identificación automática de scraper**: Si la página tiene campo `id` → Graph API; si solo tiene `url` → Deep Scraper
2. **3 fases secuenciales** en Graph API: posts → views → comments con checkpoint cada N
3. **Sin Supabase** — solo SQLite local. SupabaseStorage es wrapper de LocalStorage por compatibilidad
4. **Dashboard HTML estático** — se regenera con `./scrapeo analyze` → escribe dashboard/data.js
5. **Anti-detección** en Deep Scraper: user-agent rotatorio, delays aleatorios, detección de ban
6. **Comentarios con stickers/imágenes**: detectados via `attachment.type`, guardados como `[sticker]`/`[image]`
7. **Posts compartidos**: detectados en `_get_post_metadata` y saltados
8. **Phase 3**: solo funciona con Graph API (requiere page_id numérico)
9. **Full-scrape**: itera todas las páginas de FB_PAGES, elige scraper automáticamente, corre analyze al final

---

## 8. ISSUES CONOCIDOS

- **iCloud Drive** evicta `.so` → proyecto debe estar fuera de Desktop/Documents
- **Graph API**: posts eliminados devuelven `(#100) Object does not exist` → se loggean y saltan
- **Deep Scraper**: requiere cookies de sesión válidas en `cookies.json`
- **Graph API**: solo funciona con ID numérico y token válido (no acepta URL ni ID alfanumérico)
- **Phase 3**: checkpoint en progress.json (se reanuda automáticamente)
- **Venv**: Python 3.11 venv puede dar ModuleNotFoundError si se instaló en sistema 3.14
