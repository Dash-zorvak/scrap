# Scrapeo Social

Analítica de percepción pública para Facebook de la Alcaldía de Santa Ana.

## Stack

- **Scraping**: Facebook Graph API
- **Almacenamiento**: SQLite (SQLAlchemy)
- **Dashboard HTML**: Estático, generado desde SQLite
- **Dashboard Ciencia de Datos**: Streamlit (7 tabs)
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
streamlit run dashboard/streamlit_app.py
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
