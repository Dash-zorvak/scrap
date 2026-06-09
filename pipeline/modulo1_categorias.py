import re
import json
import logging
import sqlite3
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.cluster import KMeans

from pipeline.config import PIPELINE_DB, OUTPUT_DIR, N_TOPICS, STOPWORDS_EXTRA
from pipeline.create_views import get_db, FB_POSTS_QUERY, TT_POSTS_QUERY

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

HAS_SENTENCE = False
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE = True
except ImportError:
    log.warning("sentence-transformers no instalado — usando TF-IDF + LDA")

STOPWORDS_ES = set([
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las",
    "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como",
    "más", "pero", "sus", "le", "ya", "este", "entre", "porque", "este",
    "esta", "todo", "esa", "eso", "ese", "son", "dos", "también", "fue",
    "era", "muy", "sin", "sobre", "tiene", "sido", "han", "tener", "ser",
    "había", "tanto", "hasta", "desde", "donde", "está", "están", "qué",
    "cómo", "cuando", "solo", "bien", "tema", "va", "así",
] + [w.lower() for w in STOPWORDS_EXTRA])

URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMOJI_RE = re.compile(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ¿¡]")
NON_ALPHA_RE = re.compile(r"[^a-záéíóúüñ\s]")


def limpiar_texto(texto: str) -> str:
    texto = texto.lower()
    texto = URL_RE.sub("", texto)
    texto = EMOJI_RE.sub("", texto)
    texto = NON_ALPHA_RE.sub(" ", texto)
    tokens = [w for w in texto.split() if w not in STOPWORDS_ES and len(w) > 2]
    return " ".join(tokens)


def cargar_posts() -> pd.DataFrame:
    conn = get_db()

    fb = pd.read_sql(FB_POSTS_QUERY, conn)
    tt = pd.read_sql(TT_POSTS_QUERY, conn)
    conn.close()

    fb = fb[fb["texto"].str.len() > 10]
    tt = tt[tt["texto"].str.len() > 10]
    df = pd.concat([fb, tt], ignore_index=True)
    df["texto_limpio"] = df["texto"].apply(limpiar_texto)
    df = df[df["texto_limpio"].str.len() > 5].reset_index(drop=True)
    log.info(f"Posts cargados: {len(df)} (FB: {len(fb)}, TT: {len(tt)})")
    return df


def generar_embeddings(textos: list) -> np.ndarray:
    if HAS_SENTENCE:
        log.info("Generando embeddings con sentence-transformers...")
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return model.encode(textos, show_progress_bar=True)
    log.warning("Fallback: usando TF-IDF (512 features)")
    vec = TfidfVectorizer(max_features=512, max_df=0.85, min_df=2)
    return vec.fit_transform(textos).toarray()


def clusterizar(embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
    if len(embeddings) < n_clusters:
        n_clusters = max(2, len(embeddings) // 5)
    log.info(f"Clusterizando con K-Means (k={n_clusters})...")
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=5)
    return km.fit_predict(embeddings)


def etiquetar_clusters(df: pd.DataFrame, cluster_col: str = "cluster") -> dict:
    labels = {}
    for cid in sorted(df[cluster_col].unique()):
        textos = df[df[cluster_col] == cid]["texto_limpio"].tolist()
        top_words = Counter(" ".join(textos).split()).most_common(5)
        words = [w for w, _ in top_words]
        labels[int(cid)] = {
            "etiqueta": f"Tema {cid + 1}",
            "palabras_clave": words,
            "cantidad": len(textos),
        }
        log.info(f"  Cluster {cid}: {len(textos)} posts — {', '.join(words)}")
    return labels


def guardar_resultados(df: pd.DataFrame, etiquetas: dict):
    conn = sqlite3.connect(PIPELINE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS post_categorias (
            id TEXT,
            plataforma TEXT,
            cluster INTEGER,
            etiqueta TEXT,
            palabras_clave TEXT
        )
    """)
    conn.execute("DELETE FROM post_categorias")

    for _, row in df.iterrows():
        cid = int(row["cluster"])
        info = etiquetas.get(cid, {})
        conn.execute(
            "INSERT INTO post_categorias (id, plataforma, cluster, etiqueta, palabras_clave) VALUES (?,?,?,?,?)",
            (row["id"], row["plataforma"], cid, info.get("etiqueta", ""),
             ",".join(info.get("palabras_clave", []))),
        )

    conn.commit()
    conn.close()

    csv_path = f"{OUTPUT_DIR}/post_categorias.csv"
    df.to_csv(csv_path, index=False)
    log.info(f"Resultados guardados: {len(df)} posts en post_categorias + CSV")


def run():
    log.info("=" * 50)
    log.info("MÓDULO 1 — Categorización de contenido")
    log.info("=" * 50)

    df = cargar_posts()
    textos = df["texto_limpio"].tolist()

    embeddings = generar_embeddings(textos)
    clusters = clusterizar(embeddings, N_TOPICS)
    df["cluster"] = clusters

    etiquetas = etiquetar_clusters(df)
    guardar_resultados(df, etiquetas)

    log.info("Módulo 1 completado.")
    return df


if __name__ == "__main__":
    run()
