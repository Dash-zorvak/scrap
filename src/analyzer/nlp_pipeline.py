import json
import logging
import re
from collections import Counter, defaultdict
from typing import List, Dict, Optional, Any, Tuple

from src.analyzer.emotion_lexicon import EMOTION_LEXICON, EMOTION_COLORS
from src.analyzer.gazetteer import GAZETTEER, FUNCIONARIO_VARIANTS

logger = logging.getLogger(__name__)

try:
    import spacy
    _nlp = spacy.load("es_core_news_sm")
    HAS_SPACY = True
except Exception:
    _nlp = None
    HAS_SPACY = False
    logger.warning("spaCy es_core_news_sm not available — entity extraction disabled")

try:
    from sklearn.feature_extraction.text import CountVectorizer
    HAS_SKLEARN = True
except Exception:
    HAS_SKLEARN = False

_emotion_analyzer = None
HAS_PYSENTIMIENTO = False
_NLP_PYS_TRIED = False

def _init_pysentimiento_nlp():
    global _emotion_analyzer, HAS_PYSENTIMIENTO, _NLP_PYS_TRIED
    if HAS_PYSENTIMIENTO or _emotion_analyzer is not None or _NLP_PYS_TRIED:
        return
    _NLP_PYS_TRIED = True
    try:
        from src.analyzer.sentiment import _run_with_timeout
        from pysentimiento import create_analyzer

        def _load():
            return create_analyzer(task="emotion", lang="es")

        loaded = _run_with_timeout(_load)
        if loaded is not None:
            _emotion_analyzer = loaded
            HAS_PYSENTIMIENTO = True
            logger.info("pysentimiento loaded for NLP pipeline")
        else:
            logger.info("pysentimiento timed out — using rule-based emotion detection")
    except Exception:
        HAS_PYSENTIMIENTO = False
        logger.info("pysentimiento not available — using rule-based emotion detection")

MODEL_VERSION = "1.0"


def analyze_emotions(text: str) -> Dict[str, float]:
    if not text:
        return {}
    _init_pysentimiento_nlp()
    text_lower = text.lower()
    scores = defaultdict(float)

    # 1. Rule-based: word-boundary keyword matching
    for emotion, keywords in EMOTION_LEXICON.items():
        score = 0
        for kw in keywords:
            pattern = re.compile(r'\b' + re.escape(kw) + r'\b')
            matches = pattern.findall(text_lower)
            if matches:
                score += len(matches)
        if score > 0:
            scores[emotion] = score

    # 2. Neural (pysentimiento): use if available and confident
    if HAS_PYSENTIMIENTO:
        try:
            result = _emotion_analyzer.predict(text[:512])
            neural = dict(result.probas)
            # If neural model is confident in a non-"others" emotion, blend it
            top_emo = max(neural, key=neural.get)
            top_val = neural[top_emo]
            if top_emo != "others" and top_val > 0.3:
                # Blend: weight neural higher when it's confident
                weight = min(top_val, 0.8)
                for emo, val in neural.items():
                    scores[emo] += val * weight
            elif top_emo == "others" and top_val < 0.5:
                # Low "others" confidence — use neural directly
                return neural
            # else: "others" dominant, keep rule-based
        except Exception as e:
            logger.warning(f"pysentimiento emotion failed, falling back: {e}")

    total = sum(scores.values()) or 1
    if not scores:
        scores["neutral"] = 1.0
        return dict(scores)
    return {k: round(v / total, 4) for k, v in sorted(scores.items(), key=lambda x: -x[1])}


def analyze_entities(text: str) -> Dict[str, Any]:
    if not text:
        return {"locations": [], "people": [], "organizations": [], "programs": [], "gazetteer_matches": []}
    text_lower = text.lower()
    result = {
        "locations": [],
        "people": [],
        "organizations": [],
        "programs": [],
        "gazetteer_matches": [],
    }
    if HAS_SPACY:
        doc = _nlp(text[:5000])
        for ent in doc.ents:
            label = ent.label_
            text_clean = ent.text.strip()
            if label in ("LOC", "GPE"):
                result["locations"].append(text_clean)
            elif label == "PER":
                result["people"].append(text_clean)
            elif label in ("ORG", "MISC"):
                result["organizations"].append(text_clean)
    for category, items in GAZETTEER.items():
        for item in items:
            if item in text_lower:
                result["gazetteer_matches"].append({
                    "category": category,
                    "value": item,
                })
    for canonical, variants in FUNCIONARIO_VARIANTS.items():
        for v in variants:
            if v in text_lower:
                result["people"].append(canonical)
                break
    result["locations"] = list(dict.fromkeys(result["locations"]))[:20]
    result["people"] = list(dict.fromkeys(result["people"]))[:20]
    result["organizations"] = list(set(result["organizations"]))[:20]
    result["gazetteer_matches"] = result["gazetteer_matches"][:30]
    return result


def extract_collocations(texts: List[str], n: int = 2, top_k: int = 50) -> Dict[str, Any]:
    if not texts or not HAS_SKLEARN:
        return {"ngrams": {}, "total_docs": len(texts) if texts else 0}
    cleaned = [re.sub(r'[^\w\s]', ' ', t.lower()) for t in texts if t and len(t.split()) >= n]
    if len(cleaned) < 3:
        return {"ngrams": {}, "total_docs": len(cleaned)}
    SPANISH_STOP_WORDS = [
        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se",
        "las", "por", "un", "para", "con", "no", "una", "su", "al",
        "lo", "como", "más", "pero", "sus", "le", "ya", "este", "entre",
        "porque", "ese", "esa", "eso", "eso", "esta", "esto", "todo",
        "también", "fue", "era", "son", "han", "había", "hay", "ser",
        "sido", "está", "están", "estar", "muy", "sin", "sobre", "hasta",
        "contra", "tras", "durante", "través", "cada", "quien", "cual",
        "donde", "cuando", "desde", "luego", "entonces", "después",
        "tanto", "así", "solo", "sólo", "hace", "hacen", "hacer",
        "ello", "ellos", "ellas", "nos", "os", "te", "me", "mi",
    ]
    try:
        vec = CountVectorizer(
            ngram_range=(n, n),
            max_df=0.95,
            min_df=2,
            stop_words=SPANISH_STOP_WORDS,
        )
        X = vec.fit_transform(cleaned)
        freqs = X.sum(axis=0).A1
        terms = vec.get_feature_names_out()
        ranked = sorted(zip(terms, freqs), key=lambda x: -x[1])[:top_k]
        return {
            "ngrams": {t: int(f) for t, f in ranked},
            "total_docs": len(cleaned),
        }
    except Exception as e:
        logger.warning(f"Collocation extraction failed: {e}")
        return {"ngrams": {}, "total_docs": len(cleaned)}


def build_collocation_insights(texts: List[str]) -> Dict[str, Any]:
    bigrams = extract_collocations(texts, 2)
    trigrams = extract_collocations(texts, 3)
    return {
        "bigrams": bigrams,
        "trigrams": trigrams,
    }


def analyze_sentiment(text: str) -> Tuple[str, float]:
    from src.analyzer.sentiment import SentimentAnalyzer
    sa = SentimentAnalyzer()
    return sa.analyze(text)


def process_text(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        return {"emotions": {}, "entities": {}, "sentiment": "neutral", "sentiment_score": 0.0}
    emotions = analyze_emotions(text)
    entities = analyze_entities(text)
    sentiment_label, sentiment_score = analyze_sentiment(text)
    return {
        "emotions": emotions,
        "entities": entities,
        "sentiment": sentiment_label,
        "sentiment_score": sentiment_score,
    }


def process_fb_post(post: Dict[str, Any], storage) -> bool:
    text = post.get("message", "")
    result = process_text(text)
    ok = True
    for analysis_type in ("emotions", "entities"):
        data = {
            "item_type": "post",
            "item_id": post.get("post_id", ""),
            "analysis_type": analysis_type,
            "result_json": result.get(analysis_type, {}),
            "model_version": MODEL_VERSION,
        }
        if not storage.insert_nlp_result(data):
            ok = False
    return ok


def process_fb_comment(comment: Dict[str, Any], storage) -> bool:
    text = comment.get("message", "")
    result = process_text(text)
    ok = True
    for analysis_type in ("emotions", "entities"):
        data = {
            "item_type": "comment",
            "item_id": comment.get("comment_id", ""),
            "analysis_type": analysis_type,
            "result_json": result.get(analysis_type, {}),
            "model_version": MODEL_VERSION,
        }
        if not storage.insert_nlp_result(data):
            ok = False
    return ok


def process_pending(storage, batch_size: int = 200) -> Dict[str, int]:
    stats = {"posts": 0, "comments": 0, "errors": 0}
    posts = storage.get_fb_posts(limit=batch_size)
    processed_ids = set()
    for nr in storage.get_nlp_results(item_type="post", analysis_type="emotions", limit=50000):
        processed_ids.add(nr["item_id"])
    pending = [p for p in posts if p.get("post_id") not in processed_ids]
    for post in pending:
        try:
            process_fb_post(post, storage)
            stats["posts"] += 1
        except Exception as e:
            logger.error(f"Error processing post {post.get('post_id')}: {e}")
            stats["errors"] += 1
    processed_comment_ids = set()
    for nr in storage.get_nlp_results(item_type="comment", analysis_type="emotions", limit=50000):
        processed_comment_ids.add(nr["item_id"])
    comments = storage.get_fb_comments(limit=batch_size)
    pending_comments = [c for c in comments if c.get("comment_id") not in processed_comment_ids]
    for comment in pending_comments:
        try:
            process_fb_comment(comment, storage)
            stats["comments"] += 1
        except Exception as e:
            logger.error(f"Error processing comment {comment.get('comment_id')}: {e}")
            stats["errors"] += 1
    return stats


def process_latent_topics(storage, n_topics: int = 8) -> Dict[str, Any]:
    from src.analyzer.latent_topics import extract_latent_topics
    posts = storage.get_fb_posts(limit=10000)
    texts = [p.get("message", "") for p in posts if p.get("message")]
    result = extract_latent_topics(texts, n_topics=n_topics)
    data = {
        "item_type": "global",
        "item_id": "corpus_topics",
        "analysis_type": "latent_topic",
        "result_json": result,
        "model_version": MODEL_VERSION,
    }
    storage.insert_nlp_result(data)
    return result


def process_all_collocations(storage) -> Dict[str, Any]:
    posts = storage.get_fb_posts(limit=10000)
    comments = storage.get_fb_comments(limit=50000)
    all_texts = [p.get("message", "") for p in posts if p.get("message")] + \
                [c.get("message", "") for c in comments if c.get("message")]
    collocations = build_collocation_insights(all_texts)
    data = {
        "item_type": "global",
        "item_id": "corpus",
        "analysis_type": "collocations",
        "result_json": collocations,
        "model_version": MODEL_VERSION,
    }
    storage.insert_nlp_result(data)
    return collocations
