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

## Tests

```bash
pytest tests/
```
