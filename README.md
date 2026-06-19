---
title: Panel Santa Ana
emoji: 📊
colorFrom: blue
colorTo: gray
sdk: streamlit
app_file: dashboard/app.py
pinned: false
---

# Scrapeo Social

Analítica de percepción pública para Facebook de la Alcaldía de Santa Ana.

## Stack

- **Scraping**: Facebook Graph API
- **Almacenamiento**: SQLite (SQLAlchemy)
- **Dashboard HTML**: Estático, generado desde SQLite
- **Dashboard Ciencia de Datos**: Streamlit (4 bloques)
- **NLP**: Sentimiento español (3 niveles), emociones (6 categorías), entidades (spaCy + gazetteer), colocaciones, tópicos latentes (LDA)
- **Alertas**: Cambridge Index — 5 tipos de alertas predictivas con supresión

## Comandos

```bash
./scrapeo graph-scrape --max 500       # Scraping vía Graph API
./scrapeo analyze                      # Métricas, insights y exportar dashboard
./scrapeo cambridge                    # Cambridge Index — alertas predictivas
./scrapeo status                       # Estado de la base de datos
./scrapeo nlp --batch 1000             # Pipeline NLP
./scrapeo phase3                       # Extraer comentarios pendientes

# Dashboard estático:
open dashboard/index.html

# Dashboard Streamlit:
streamlit run dashboard/app.py
```

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download es_core_news_sm
cp .env.example .env  # Editar con FB_ACCESS_TOKEN
```

Requiere `FB_ACCESS_TOKEN` con permisos `pages_read_engagement`, `pages_read_user_content`, `pages_manage_posts`, `read_insights`.

## Dashboard Streamlit — Bloques

El dashboard se compone de cuatro bloques principales:

| Bloque | Contenido |
|--------|-----------|
| **I — Pulso General** | Engagement, sentimiento, emociones, nube de palabras, tendencias semanales, volumen diario de comentarios |
| **II — Segmentación de Audiencia** | Distribución por tópicos y zonas, análisis por tipo de post, polaridad por zona, emergencias |
| **III — Riesgo y Autenticidad** | Controversia (predicción), anomalías en engagement, sentimiento vs. engagement, viralidad vs. sentimiento |
| **IV — Memoria e Inteligencia Aplicada** | Insight Engine — alertas del Cambridge Index, análisis de narrativas, detección temprana de contagio |

## Guía del operador (carga PDF)

1. **Subir PDF** desde la barra lateral → se extraen posts vía Groq Vision.
2. **Revisar extracción 1→N**: cada post subido se muestra como tarjeta; editar si la IA omitió/alucinó datos.
3. **Guardar lote**: los posts revisados se persisten en SQLite.
4. **Procesar lote**: reconstruye tablas agregadas (sentimiento, categorías, engagement, series).
5. **Validar en dashboard**: navegar los bloques para ver los resultados.

## Despliegue en Hugging Face Spaces

El host por defecto. El disco de un Space es **efímero** (se borra al reiniciar o
reconstruir), por lo que las bases SQLite se persisten en un **Dataset privado**
de Hugging Face mediante `dashboard/hf_sync.py`.

1. Crear un **Space** (SDK *Streamlit*, hardware *CPU basic*, gratis). El
   frontmatter de este README ya define `sdk: streamlit` y
   `app_file: dashboard/app.py`.
2. Subir el código del repo al Space (o conectarlo a GitHub).
3. Crear un **Access Token** con permiso de escritura en
   *Settings → Access Tokens*.
4. Configurar los **Secrets** del Space (*Settings → Variables and secrets*):
   - `GROQ_API_KEY` (obligatoria) — clave de Groq para visión y sentimiento.
   - `HF_DATASET_REPO` — repo del Dataset persistente, formato `usuario/panel-santa-ana-data`.
   - `HF_TOKEN` — el token de escritura del paso 3.
   - `MOTOR_SENTIMIENTO=groq` (opcional) — evita cargar torch/BERT y ahorra RAM.
5. El Dataset privado se crea automáticamente en el primer guardado si no existe.
6. Sin `HF_DATASET_REPO`/`HF_TOKEN` la app funciona igual, pero los datos **no**
   sobreviven a un reinicio del Space.

## Despliegue en Railway

1. Crear servicio desde el repo (Railway autodetecta `nixpacks.toml`).
2. Configurar variables de entorno en Railway:
   - `GROQ_API_KEY` (obligatoria) — clave de Groq para visión y sentimiento de respaldo.
   - `DATA_DIR=/data` — ruta donde se montará el volumen persistente.
   - `MOTOR_SENTIMIENTO=groq` (recomendado) — evita cargar torch/BERT, ahorra RAM.
3. Crear un **Volume** en Railway y montarlo en `/data` (el valor de `DATA_DIR`).
   **Advertencia:** sin volumen, las bases de datos se borran en cada deploy.
4. Railway inyecta `$PORT` automáticamente; el `Procfile`/`nixpacks.toml` ya lo usan.
5. RAM: BERT (torch) consume ~2–3 GiB. Con `MOTOR_SENTIMIENTO=groq` se evita cargar el modelo local y el sentimiento usa la API de Groq.

## Tests

```bash
pytest tests/
```
