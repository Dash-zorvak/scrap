import logging
import re
from collections import Counter
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    HAS_LDA = True
except ImportError:
    HAS_LDA = False


def extract_latent_topics(
    texts: List[str],
    n_topics: int = 8,
    n_top_words: int = 10,
    max_features: int = 1000,
) -> Dict[str, Any]:
    if not texts or len(texts) < 10 or not HAS_LDA:
        return {"topics": [], "error": "insufficient data or sklearn unavailable"}

    cleaned = []
    for t in texts:
        if t:
            t_clean = re.sub(r'[^\w\s]', ' ', t.lower())
            t_clean = re.sub(r'\s+', ' ', t_clean).strip()
            if len(t_clean.split()) >= 3:
                cleaned.append(t_clean)

    if len(cleaned) < 10:
        return {"topics": [], "error": "not enough valid documents (need 10+)"}

    SPANISH_STOP_WORDS = [
        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se",
        "las", "por", "un", "para", "con", "no", "una", "su", "al",
        "lo", "como", "más", "pero", "sus", "le", "ya", "este", "entre",
        "porque", "ese", "esa", "todo", "también", "fue", "era", "son",
        "han", "hay", "ser", "muy", "sin", "sobre", "cada", "quien",
        "donde", "cuando", "desde", "luego", "entonces", "después",
        "tanto", "así", "solo", "hace", "hacen", "ello", "ellos", "ellas",
    ]
    try:
        vec = CountVectorizer(
            max_features=max_features,
            stop_words=SPANISH_STOP_WORDS,
            min_df=2,
            max_df=0.85,
        )
        X = vec.fit_transform(cleaned)
        feature_names = vec.get_feature_names_out()

        lda = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            learning_method="online",
            max_iter=10,
        )
        lda.fit(X)

        topics = []
        for topic_idx, topic in enumerate(lda.components_):
            top_words = [feature_names[i] for i in topic.argsort()[:-n_top_words - 1:-1]]
            topics.append({
                "id": topic_idx,
                "words": top_words,
                "weight": float(topic.sum()),
            })

        doc_topic_dist = lda.transform(X)
        topic_dominance = Counter()
        for dist in doc_topic_dist:
            dominant = int(dist.argmax())
            topic_dominance[dominant] += 1

        for t in topics:
            t["doc_count"] = int(topic_dominance.get(t["id"], 0))
            t["pct"] = round(t["doc_count"] / len(cleaned) * 100, 1)

        topics.sort(key=lambda x: -x["doc_count"])

        return {
            "topics": topics,
            "n_docs": len(cleaned),
            "n_topics": n_topics,
            "vocabulary_size": len(feature_names),
        }

    except Exception as e:
        logger.warning(f"Latent topic extraction failed: {e}")
        return {"topics": [], "error": str(e)}
