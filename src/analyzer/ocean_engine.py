import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import numpy as np
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    np = None


def build_post_vector(post: Dict) -> List[float]:
    text = post.get("message") or post.get("description") or ""
    sentiment_map = {
        "muy_positivo": 1.0, "positivo": 0.5, "neutral": 0.0,
        "negativo": -0.5, "muy_negativo": -1.0,
    }

    topic_onehot = _topic_onehot(post.get("topic", ""))
    day_of_week = _day_of_week(post.get("created_time"))

    vec = [
        sentiment_map.get(post.get("sentiment", "neutral"), 0.0),
        post.get("sentiment_score", 0.0),
        float(len(text)),
        float(post.get("likes_count", 0)),
        float(post.get("comments_count", 0)),
        float(post.get("shares_count", 0)),
        float(post.get("views_count", 0) or 0),
        float(post.get("total_reactions", 0)),
        float(day_of_week),
    ]
    vec.extend(topic_onehot)
    return vec


def build_post_vector_for_prediction(post: Dict) -> List[float]:
    text = post.get("message") or post.get("description") or ""
    sentiment_map = {
        "muy_positivo": 1.0, "positivo": 0.5, "neutral": 0.0,
        "negativo": -0.5, "muy_negativo": -1.0,
    }

    topic_onehot = _topic_onehot(post.get("topic", ""))
    day_of_week = _day_of_week(post.get("created_time"))

    vec = [
        sentiment_map.get(post.get("sentiment", "neutral"), 0.0),
        post.get("sentiment_score", 0.0),
        float(len(text)),
        float(post.get("comments_count", 0)),
        float(post.get("shares_count", 0)),
        float(post.get("views_count", 0) or 0),
        float(day_of_week),
    ]
    vec.extend(topic_onehot)
    return vec


def _topic_onehot(topic: str) -> List[float]:
    topics = [
        "obras_publicas", "seguridad", "salud", "educacion", "empleo",
        "medio_ambiente", "movilidad", "servicios_publicos", "cultura",
        "deportes", "transparencia", "corrupcion",
    ]
    return [1.0 if topic == t else 0.0 for t in topics]


def _day_of_week(created_time) -> int:
    if not created_time:
        return 0
    try:
        if isinstance(created_time, str):
            dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        else:
            dt = created_time
        return dt.weekday()
    except (ValueError, TypeError):
        return 0


# ===========================
# PCA — REDUCCIÓN DE DIMENSIONES
# ===========================

def compute_pca(posts: List[Dict], n_components: int = 3) -> Dict:
    if not HAS_SKLEARN or len(posts) < n_components + 1:
        return {"error": "Faltan datos o sklearn no está instalado"}

    vectors = [build_post_vector(p) for p in posts]
    X = np.array(vectors)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=min(n_components, X_scaled.shape[0], X_scaled.shape[1]))
    X_pca = pca.fit_transform(X_scaled)

    components = []
    for i, row in enumerate(X_pca):
        components.append({
            "post_id": posts[i].get("id", ""),
            "platform": posts[i].get("platform", ""),
            "pc1": float(row[0]),
            "pc2": float(row[1]) if n_components > 1 else 0.0,
            "pc3": float(row[2]) if n_components > 2 else 0.0,
            "sentiment": posts[i].get("sentiment", ""),
            "topic": posts[i].get("topic", ""),
        })

    return {
        "components": components,
        "explained_variance": pca.explained_variance_ratio_.tolist(),
        "total_explained": float(pca.explained_variance_ratio_.sum()),
        "n_components": n_components,
    }


# ===========================
# K-MEANS — CLUSTERS DE CONTENIDO
# ===========================

def compute_clusters(posts: List[Dict], n_clusters: int = 5) -> Dict:
    if not HAS_SKLEARN or len(posts) < n_clusters:
        return {"error": "Faltan datos o sklearn no está instalado"}

    vectors = [build_post_vector(p) for p in posts]
    X = np.array(vectors)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        p = posts[i]
        clusters[int(label)].append({
            "post_id": p.get("id", ""),
            "platform": p.get("platform", ""),
            "sentiment": p.get("sentiment", ""),
            "topic": p.get("topic", ""),
            "zone": p.get("zone", ""),
            "total_reactions": p.get("total_reactions", 0),
            "message": (p.get("message") or p.get("description") or "")[:100],
        })

    profiles = {}
    for label, items in clusters.items():
        avg_reactions = sum(i["total_reactions"] for i in items) / len(items)
        tops = [i["topic"] for i in items if i["topic"]]
        top_topic = Counter(tops).most_common(1)[0][0] if tops else "sin_tema"
        sents = [i["sentiment"] for i in items]
        top_sent = Counter(sents).most_common(1)[0][0]
        platforms = [i["platform"] for i in items]
        top_plat = Counter(platforms).most_common(1)[0][0]
        profiles[str(label)] = {
            "size": len(items),
            "avg_reactions": round(avg_reactions, 0),
            "dominant_topic": top_topic,
            "dominant_sentiment": top_sent,
            "dominant_platform": top_plat,
            "pct": round(len(items) / len(posts) * 100, 1),
        }

    return {
        "clusters": {str(k): v for k, v in clusters.items()},
        "profiles": profiles,
        "n_clusters": n_clusters,
    }


# ===========================
# REGRESIÓN — PREDECIR ENGAGEMENT
# ===========================

def predict_engagement(posts: List[Dict]) -> Dict:
    if not HAS_SKLEARN or len(posts) < 20:
        return {"error": "Faltan datos o sklearn no está instalado"}

    vectors = [build_post_vector_for_prediction(p) for p in posts]
    y = np.array([p.get("total_reactions", 0) for p in posts])

    X = np.array(vectors)
    mask = y > 0
    if mask.sum() < 10:
        return {"error": "Muy pocos posts con reacciones para entrenar modelo"}

    X = X[mask]
    y = y[mask]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_scaled, y)

    feature_names = [
        "sentiment", "sentiment_score", "text_length",
        "comments", "shares", "views", "day_of_week",
        "topic_obras", "topic_seguridad", "topic_salud", "topic_educacion",
        "topic_empleo", "topic_medio_ambiente", "topic_movilidad",
        "topic_servicios", "topic_cultura", "topic_deportes",
        "topic_transparencia", "topic_corrupcion",
    ]

    coefs = list(zip(feature_names, model.coef_))
    coefs.sort(key=lambda x: -abs(x[1]))

    y_pred = model.predict(X_scaled)

    residuals = y - y_pred
    mae = float(np.mean(np.abs(residuals)))
    mape = float(np.mean(np.abs(residuals / (y + 1)))) * 100

    top_features = [
        {"feature": f, "coef": round(c, 2)}
        for f, c in coefs[:8]
    ]

    return {
        "mae": round(mae, 0),
        "mape": round(mape, 1),
        "samples": int(len(y)),
        "top_features": top_features,
        "coef_all": [{"feature": f, "coef": round(c, 2)} for f, c in coefs],
    }


# ===========================
# PREDECIR CONTROVERSIA (clasificación)
# ===========================

def predict_controversy(posts: List[Dict]) -> Dict:
    if not HAS_SKLEARN or len(posts) < 20:
        return {"error": "Faltan datos o sklearn no está instalado"}

    vectors = [build_post_vector_for_prediction(p) for p in posts]

    neg_mask = np.array([
        p.get("sentiment") in ("negativo", "muy_negativo") or
        (p.get("cares_count", 0) or 0) + (p.get("sads_count", 0) or 0) + (p.get("angrys_count", 0) or 0) > 10
        for p in posts
    ])

    if neg_mask.sum() < 5 or (~neg_mask).sum() < 5:
        return {"error": "Muy pocos posts negativos/controversiales para entrenar"}

    X = np.array(vectors)
    y = neg_mask.astype(int)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_scaled, y)

    feature_names = [
        "sentiment", "sentiment_score", "text_length",
        "comments", "shares", "views", "day_of_week",
        "topic_obras", "topic_seguridad", "topic_salud", "topic_educacion",
        "topic_empleo", "topic_medio_ambiente", "topic_movilidad",
        "topic_servicios", "topic_cultura", "topic_deportes",
        "topic_transparencia", "topic_corrupcion",
    ]

    coefs = list(zip(feature_names, model.coef_[0]))
    coefs.sort(key=lambda x: -abs(x[1]))

    probas = model.predict_proba(X_scaled)[:, 1]
    high_risk = []
    for i, prob in enumerate(probas):
        if prob > 0.7:
            high_risk.append({
                "post_id": posts[i].get("id", ""),
                "probability": round(float(prob), 3),
                "topic": posts[i].get("topic", ""),
                "sentiment": posts[i].get("sentiment", ""),
            })

    high_risk.sort(key=lambda x: -x["probability"])

    return {
        "accuracy": round(float(model.score(X_scaled, y)), 3),
        "controversial_samples": int(neg_mask.sum()),
        "high_risk_posts": high_risk[:10],
        "top_features": [
            {"feature": f, "coef": round(c, 3)}
            for f, c in coefs[:8]
        ],
    }


# ===========================
# EJECUTAR ANÁLISIS COMPLETO
# ===========================

def run_ocean_analysis(posts_fb: List[Dict], posts_tt: List[Dict]) -> Dict:
    result = {"has_sklearn": HAS_SKLEARN}

    if not HAS_SKLEARN:
        result["error"] = "scikit-learn no está instalado. Corré: pip install scikit-learn numpy"
        return result

    fb_vec = [build_post_vector(p) for p in posts_fb if p.get("total_reactions", 0) > 0]
    tt_vec = [build_post_vector(p) for p in posts_tt if p.get("total_reactions", 0) > 0]

    result["pca"] = compute_pca(posts_fb + posts_tt)
    result["clusters"] = compute_clusters(posts_fb + posts_tt)
    result["regression"] = predict_engagement(posts_fb + posts_tt)
    result["controversy"] = predict_controversy(posts_fb + posts_tt)

    return result
