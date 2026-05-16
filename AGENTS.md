# scrapeo-social

> **Plan V2 Activo**: Ver `PLAN_V2.md` para la estrategia actualizada.

Analítica de percepción pública para redes sociales de Alcaldía de Santa Ana.

## Objetivo

Extraer y analizar contenido del último año de:
- **Facebook**: 20,000 posts (10K Alcaldía + 10K Alcalde)
- **TikTok**: 4,000 videos (2K Alcaldía + 2K Alcalde)

Con análisis de reacciones, sentimiento, temas clave, datos demográficos y marketing ejecutivo.

## Volúmenes

| Plataforma | Cuenta | Posts/Videos | Comentarios Estimados |
|------------|--------|--------------|----------------------|
| Facebook | Alcaldía | 10,000 | ~1,000,000 |
| Facebook | Alcalde | 10,000 | ~1,000,000 |
| TikTok | Alcaldía | 2,000 | ~200,000 |
| TikTok | Alcalde | 2,000 | ~200,000 |
| **TOTAL** | | **24,000** | **~2,400,000** |

## Estructura del Proyecto

```
scrapeo-social/
├── src/
│   ├── main.py              # CLI: scrape, analyze, status
│   ├── config.py           # Configuración desde .env
│   ├── analyzer/
│   │   ├── sentiment.py    # Analizador español (3 niveles)
│   │   ├── trends.py       # Análisis de tendencias
│   │   └── reporting.py   # Generación de informes JSON/PNG
│   ├── fb_scraper/
│   │   ├── playwright_scraper.py  # Scraper FB con Playwright
│   │   └── models.py       # FBPostData, FBCommentData
│   ├── tiktok_scraper/
│   │   ├── scraper.py      # Scraper TT (JSON embebido)
│   │   └── models.py       # TTPostData, TTCommentData
│   └── storage/
│       └── db.py           # SQLite + SQLAlchemy
├── data/                   # SQLite database
├── outputs/                # Informes JSON y gráficos
├── .env                    # Credenciales y configuración
└── scrapeo                 # Wrapper: activa venv y ejecuta main
```

## Comandos

```bash
./scrapeo scrape --platform facebook   # Scrapear FB
./scrapeo scrape --platform tiktok     # Scrapear TikTok
./scrapeo scrape --platform all       # Ambas plataformas
./scrapeo analyze --platform all      # Generar informe
./scrapeo status                      # Ver estado de BD
```

## Configuración (.env)

```env
# Facebook
FB_PAGE_URL=https://www.facebook.com/SantaAnaAlcaldia
FB_PAGE_NAME=Santa Ana Alcaldía
FB_EMAIL=dagorosales40@gmail.com
FB_PASSWORD=...

# TikTok
TT_USERNAME=alcaldiasa

# Scraping
MAX_POSTS=20000
DAYS_BACK=730
```

## Entorno de Ejecución

```bash
# El wrapper ./scrapeo ya activa el venv automáticamente
./scrapeo status

# O manualmente:
source venv/bin/activate
python -m src.main status
```

## Plan de Trabajo

### Fase 1: Creación y Calentamiento de Cuentas FB

1. **Crear 3-5 cuentas Facebook** desde cero
2. **Calentamiento** (mínimo 3 días):
   -行为 humana natural: likes, comentarios, seguimientos
   - Evitar contenido político inicialmente
   - Usar distintas IPs/dispositivos si es posible
3. **Rotación**: cada cuenta usada max 25-40 posts/día

### Fase 2: Configuración de Scraper FB

El scraper actual requiere login. Necesita:
- `FB_EMAIL` y `FB_PASSWORD` en .env
- Considerar agregar más cuentas al config para rotación automática

### Fase 3: Scraping Piloto

- ~500 posts de FB
- ~100 videos de TT
- Medir: CAPTCHAs, bloqueos, shadowbans
- Ajustar delays según resultados

### Fase 4: Scraping a Escala

- Facebook: 20,000 posts (2 cuentas objetivo)
- TikTok: 4,000 videos
- Monitoreo continuo de límites

### Fase 5: Análisis e Informe

El informe debe incluir:
- Distribución de reacciones (like, love, care, haha, wow, sad, angry)
- Sentimiento por post y por tema
- **Insight clave**: "En el post ID X se mencionó '[palabra]' y eso provocó [reacción] según análisis de comentarios. Este tema le interesa a la población."

Formato JSON del informe:
```json
{
  "post_id": "...",
  "platform": "fb|tt",
  "timestamp": "...",
  "text": "...",
  "reactions": {"total": N, "by_type": {...}},
  "topics_detected": [{"main": "...", "confidence": 0.9}],
  "comment_sentiment": "positive|negative|neutral",
  "actionable_insight": "En el post se mencionó X y eso provocó Y"
}
```

## Límites y Mitigación

| Plataforma | Límite Diario | Delay Entre Acciones |
|------------|---------------|---------------------|
| Facebook   | 25-40 posts/cuenta | 15-45 segundos |
| TikTok     | 60-80 videos/cuenta | 10-30 segundos |

**Mitigaciones**:
- Delays aleatorios
- Scraping solo 8am-6pm hora local
- Rotación de user-agents
- Comportamiento humano simulado
- Checkpointing cada 50 posts

## Notas Importantes

1. **Sin propuesta de campaña**: El entregable es solo análisis de datos para presentar al edil
2. **Sin temas definidos aún**: El detector de temas se entrenará con los datos extraídos
3. **Password FB vacío**: Actualmente sin credenciales en .env
4. **TikTok**: Solo configurable un username en .env, considerar extensión para múltiples cuentas