import json
import logging
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.analyzer.sentiment import SENTIMENT_ORDER
from src.intelligence.cambridge_index import (
    run_all_detectors, SuppressionEngine,
)

logger = logging.getLogger(__name__)

DIMENSION_WEIGHTS: Dict[str, float] = {
    "aprobacion": 1.0,
    "conexion": 1.0,
    "tranquilidad": 1.0,
    "diversidad_temas": 0.8,
    "presencia_zonas": 0.7,
    "consistencia": 0.9,
    "atencion": 0.6,
}

DIMENSION_LABELS: Dict[str, Dict] = {
    "aprobacion": {
        "label": "Aprobación Ciudadana",
        "description": "Sentimiento neto de la población",
        "unit": "%",
        "higher_is_better": True,
    },
    "conexion": {
        "label": "Conexión con la Gente",
        "description": "Nivel de engagement e interacción",
        "unit": "%",
        "higher_is_better": True,
    },
    "tranquilidad": {
        "label": "Tranquilidad",
        "description": "Ausencia de controversia y enojo",
        "unit": "%",
        "higher_is_better": True,
    },
    "diversidad_temas": {
        "label": "Diversidad de Temas",
        "description": "Variedad de tópicos gestionados",
        "unit": "%",
        "higher_is_better": True,
    },
    "presencia_zonas": {
        "label": "Presencia en Zonas",
        "description": "Cobertura territorial de los mensajes",
        "unit": "%",
        "higher_is_better": True,
    },
    "consistencia": {
        "label": "Consistencia",
        "description": "Estabilidad emocional de la audiencia",
        "unit": "%",
        "higher_is_better": True,
    },
    "atencion": {
        "label": "Atención a la Comunidad",
        "description": "Capacidad de generar conversación",
        "unit": "%",
        "higher_is_better": True,
    },
}

PLATFORM_WEIGHTS: Dict[str, float] = {
    "facebook": 0.55,
    "tiktok": 0.45,
}


def compute_dimension_aprobacion(posts: List[Dict]) -> float:
    total = len(posts)
    if total == 0:
        return 50.0
    score = 0.0
    count = 0
    for p in posts:
        s = p.get("sentiment", "neutral")
        sv = SENTIMENT_ORDER.get(s, 0)
        score += sv
        count += 1
    if count == 0:
        return 50.0
    avg = score / count
    return max(0, min(100, (avg + 2) * 25))


def compute_dimension_conexion(posts: List[Dict]) -> float:
    total_views = sum(p.get("views_count", 0) for p in posts)
    total_reactions = sum(p.get("total_reactions", 0) for p in posts)
    total_comments = sum(p.get("comments_count", 0) for p in posts)
    total_shares = sum(p.get("shares_count", 0) for p in posts)
    total = len(posts)
    if total == 0:
        return 50.0
    if total_views > 0:
        eng_rate = (total_reactions + total_comments + total_shares) / total_views
        score = min(100, eng_rate * 2000)
    else:
        avg_reactions = (total_reactions + total_comments + total_shares) / total
        score = min(100, avg_reactions / 50 * 100)
    return max(0, score)


def compute_dimension_tranquilidad(posts: List[Dict]) -> float:
    total_reactions = sum(p.get("total_reactions", 0) for p in posts)
    angrys = sum(p.get("angrys_count", 0) for p in posts)
    sads = sum(p.get("sads_count", 0) for p in posts)
    if total_reactions == 0:
        return 50.0
    controversy = (angrys + sads) / total_reactions
    return max(0, min(100, (1 - controversy) * 100))


def compute_dimension_diversidad(posts: List[Dict]) -> float:
    total = len(posts)
    if total == 0:
        return 0.0
    with_topic = sum(1 for p in posts if p.get("topic"))
    return (with_topic / total) * 100


def compute_dimension_presencia(posts: List[Dict]) -> float:
    total = len(posts)
    if total == 0:
        return 0.0
    with_zone = sum(1 for p in posts if p.get("zone") or p.get("zone_ner"))
    return (with_zone / total) * 100


def compute_dimension_consistencia(posts: List[Dict]) -> float:
    valid = [p for p in posts if p.get("sentiment") and p.get("created_time")]
    if len(valid) < 5:
        return 50.0
    try:
        monthly = defaultdict(list)
        for p in valid:
            ct = p.get("created_time", "")
            if isinstance(ct, str) and len(ct) >= 7:
                month = ct[:7]
            else:
                continue
            sv = SENTIMENT_ORDER.get(p.get("sentiment", "neutral"), 0)
            monthly[month].append(sv)

        if len(monthly) < 2:
            return 50.0

        monthly_avgs = [sum(v) / len(v) for v in monthly.values()]
        mean = sum(monthly_avgs) / len(monthly_avgs)
        variance = sum((x - mean) ** 2 for x in monthly_avgs) / len(monthly_avgs)
        std_dev = math.sqrt(variance)

        consistency = max(0, 100 - std_dev * 30)
        return min(100, consistency)
    except Exception:
        return 50.0


def compute_dimension_atencion(posts: List[Dict]) -> float:
    total = len(posts)
    if total == 0:
        return 50.0
    total_comments = sum(p.get("comments_count", 0) for p in posts)
    avg_comments = total_comments / total
    score = min(100, avg_comments * 10)
    return max(0, score)


def compute_all_dimensions(posts: List[Dict]) -> Dict[str, float]:
    return {
        "aprobacion": round(compute_dimension_aprobacion(posts), 1),
        "conexion": round(compute_dimension_conexion(posts), 1),
        "tranquilidad": round(compute_dimension_tranquilidad(posts), 1),
        "diversidad_temas": round(compute_dimension_diversidad(posts), 1),
        "presencia_zonas": round(compute_dimension_presencia(posts), 1),
        "consistencia": round(compute_dimension_consistencia(posts), 1),
        "atencion": round(compute_dimension_atencion(posts), 1),
    }


def compute_iq_score(dimensions: Dict[str, float],
                     weights: Optional[Dict[str, float]] = None) -> float:
    if weights is None:
        weights = DIMENSION_WEIGHTS

    total_weight = 0.0
    weighted_sum = 0.0
    for dim, value in dimensions.items():
        w = weights.get(dim, 1.0)
        weighted_sum += value * w
        total_weight += w

    if total_weight == 0:
        return 50.0
    return round(weighted_sum / total_weight, 1)


def compute_matrix_position(posts: List[Dict],
                            x_dim: str = "aprobacion",
                            y_dim: str = "conexion") -> Dict:
    dims = compute_all_dimensions(posts)
    return {
        "x": dims.get(x_dim, 50),
        "y": dims.get(y_dim, 50),
        "x_label": DIMENSION_LABELS.get(x_dim, {}).get("label", x_dim),
        "y_label": DIMENSION_LABELS.get(y_dim, {}).get("label", y_dim),
        "quadrant": _get_quadrant(dims.get(x_dim, 50), dims.get(y_dim, 50)),
    }


def _get_quadrant(x: float, y: float) -> str:
    if x >= 50 and y >= 50:
        return "LIDERAZGO: Alta aprobación y conexión"
    elif x >= 50 and y < 50:
        return "INSTITUCIONAL: Bien visto pero poca interacción"
    elif x < 50 and y >= 50:
        return "POPULISTA: Mucha interacción pero desaprobación"
    else:
        return "CRISIS: Baja aprobación y baja conexión"


def compute_iq_full(posts_fb: List[Dict],
                    posts_tt: List[Dict]) -> Dict:
    dims_fb = compute_all_dimensions(posts_fb)
    dims_tt = compute_all_dimensions(posts_tt)

    iq_fb = compute_iq_score(dims_fb)
    iq_tt = compute_iq_score(dims_tt)

    weights = PLATFORM_WEIGHTS
    iq_general = round(
        iq_fb * weights.get("facebook", 0.5) + iq_tt * weights.get("tiktok", 0.5),
        1,
    )

    return {
        "iq_general": iq_general,
        "iq_facebook": iq_fb,
        "iq_tiktok": iq_tt,
        "dimensions_fb": dims_fb,
        "dimensions_tt": dims_tt,
        "radar_fb": _dimensions_to_radar(dims_fb),
        "radar_tt": _dimensions_to_radar(dims_tt),
        "matrix_fb": compute_matrix_position(posts_fb),
        "matrix_tt": compute_matrix_position(posts_tt),
    }


def _dimensions_to_radar(dims: Dict[str, float]) -> List[Dict]:
    radar = []
    for key, info in DIMENSION_LABELS.items():
        radar.append({
            "dimension": key,
            "label": info["label"],
            "value": dims.get(key, 0),
            "full_mark": 100,
        })
    return radar


def compute_cambridge_alerts(posts: List[Dict]) -> Dict:
    fb_posts_dicts = []
    for p in posts:
        fb_posts_dicts.append({
            "likes_count": p.get("likes_count", 0),
            "loves_count": p.get("loves_count", 0),
            "hahas_count": p.get("hahas_count", 0),
            "wows_count": p.get("wows_count", 0),
            "sads_count": p.get("sads_count", 0),
            "angrys_count": p.get("angrys_count", 0),
            "comments_count": p.get("comments_count", 0),
            "shares_count": p.get("shares_count", 0),
            "views_count": p.get("views_count", 0),
            "created_time": p.get("created_time"),
            "sentiment": p.get("sentiment", "neutral"),
            "topic_category": p.get("topic", ""),
            "zona": p.get("zone", ""),
        })

    suppression = SuppressionEngine()
    return run_all_detectors(fb_posts_dicts, suppression)


def get_sentiment_breakdown(posts: List[Dict]) -> Dict:
    total = len(posts)
    if total == 0:
        return {}
    counts = Counter(p.get("sentiment", "neutral") for p in posts)
    breakdown = {}
    order = ["muy_positivo", "positivo", "neutral", "negativo", "muy_negativo"]
    for level in order:
        count = counts.get(level, 0)
        breakdown[level] = {
            "count": count,
            "pct": round(count / total * 100, 1),
        }
    return breakdown
