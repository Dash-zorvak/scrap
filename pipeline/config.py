import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

FB_DB = os.path.join(DATA_DIR, "facebook.db")
TT_DB = os.path.join(DATA_DIR, "tiktok.db")
PIPELINE_DB = os.path.join(DATA_DIR, "pipeline.db")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# NLP
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
N_TOPICS = 10
STOPWORDS_EXTRA = [
    "https", "http", "com", "www", "rt", "si", "no", "mas",
    "dijo", "hizo", "vez", "asi", "todo", "nadie",
]

# Sentiment
SENTIMENT_MIN_TEXT_LENGTH = 3

# Engagement
MIN_REACTIONS_FOR_RATIO = 10

# Series
ROLLING_WINDOW = 4
ANOMALY_STD_THRESHOLD = 2.0

# Noticias (future)
NEWS_SOURCES = []
