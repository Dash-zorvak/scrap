import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TOPIC_SENSITIVITY_BASE: Dict[str, float] = {
    "malversacion": 1.6,
    "soborno": 1.5,
    "nepotismo": 1.4,
    "desvio": 1.3,
    "delincuencia": 1.5,
    "extorsion": 1.4,
    "violencia": 1.3,
    "pandillas": 1.2,
    "opacidad": 1.4,
    "falta_de_datos": 1.3,
    "rendicion": 1.2,
    "desabastecimiento": 1.3,
    "negligencia": 1.2,
    "hospital": 1.1,
    "agua": 1.2,
    "basura": 1.1,
    "alumbrado": 1.0,
    "drenaje": 1.0,
    "sobreprecio": 1.3,
    "retraso": 1.2,
    "mala_calidad": 1.2,
    "infraestructura_educativa": 1.1,
    "docentes": 1.0,
    "becas": 0.9,
    "desempleo": 1.1,
    "subempleo": 1.0,
    "salario": 0.9,
    "transporte": 0.9,
    "trafico": 0.8,
    "vialidad": 0.8,
    "contaminacion": 0.9,
    "deforestacion": 0.8,
    "cambio_climatico": 0.7,
}

TOPIC_DEFAULT_SENSITIVITY: Dict[str, float] = {
    "corrupcion": 1.3,
    "seguridad": 1.2,
    "transparencia": 1.2,
    "salud": 1.1,
    "servicios_publicos": 1.0,
    "obras_publicas": 1.0,
    "educacion": 0.9,
    "empleo": 0.9,
    "movilidad": 0.8,
    "medio_ambiente": 0.7,
    "uncategorized": 1.0,
}

SUBTOPIC_TO_TOPIC: Dict[str, str] = {
    "malversacion": "corrupcion",
    "soborno": "corrupcion",
    "nepotismo": "corrupcion",
    "desvio": "corrupcion",
    "delincuencia": "seguridad",
    "extorsion": "seguridad",
    "violencia": "seguridad",
    "pandillas": "seguridad",
    "opacidad": "transparencia",
    "falta_de_datos": "transparencia",
    "rendicion": "transparencia",
    "desabastecimiento": "salud",
    "negligencia": "salud",
    "hospital": "salud",
    "agua": "servicios_publicos",
    "basura": "servicios_publicos",
    "alumbrado": "servicios_publicos",
    "drenaje": "servicios_publicos",
    "sobreprecio": "obras_publicas",
    "retraso": "obras_publicas",
    "mala_calidad": "obras_publicas",
    "infraestructura_educativa": "educacion",
    "docentes": "educacion",
    "becas": "educacion",
    "desempleo": "empleo",
    "subempleo": "empleo",
    "salario": "empleo",
    "transporte": "movilidad",
    "trafico": "movilidad",
    "vialidad": "movilidad",
    "contaminacion": "medio_ambiente",
    "deforestacion": "medio_ambiente",
    "cambio_climatico": "medio_ambiente",
}

SEVERITY_LABELS = {1: "bajo", 2: "medio", 3: "alto", 4: "critico"}


def assign_topic_sensitivity(
    subtopics: List[str],
    topic_main: Optional[str] = None,
) -> float:
    if not subtopics:
        return TOPIC_DEFAULT_SENSITIVITY.get(topic_main or "uncategorized", 1.0)
    matched = [s for s in subtopics if s in TOPIC_SENSITIVITY_BASE]
    if not matched:
        return TOPIC_DEFAULT_SENSITIVITY.get(topic_main or "uncategorized", 1.0)
    return max(TOPIC_SENSITIVITY_BASE[s] for s in matched)


def quarterly_adjustment(
    base_sensitivity: float,
    daily_reactions_28d: List[float],
    velocity_score: float = 0.0,
    dampening_volatilidad: float = 0.3,
    dampening_velocidad: float = 0.2,
) -> float:
    if len(daily_reactions_28d) < 2:
        volatilidad_score = 0.0
    else:
        mean_r = sum(daily_reactions_28d) / len(daily_reactions_28d)
        if mean_r < 0.01:
            volatilidad_score = 0.0
        else:
            variance = sum((x - mean_r) ** 2 for x in daily_reactions_28d) / len(daily_reactions_28d)
            std_dev = math.sqrt(variance)
            raw_vol = (std_dev / mean_r) * dampening_volatilidad
            volatilidad_score = min(raw_vol, 0.5)

    raw_vel = abs(velocity_score) * dampening_velocidad
    velocidad_score = min(raw_vel, 0.4)

    adjusted = base_sensitivity * (1 + volatilidad_score) * (1 + velocidad_score)
    return max(0.5, min(2.0, adjusted))


class AlertRecord:
    def __init__(self, alert_type: str, post_id: str, triggered_at: datetime, score: float):
        self.alert_type = alert_type
        self.post_id = post_id
        self.triggered_at = triggered_at
        self.score = score


class SuppressionEngine:
    def __init__(self):
        self.history: List[AlertRecord] = []
        self.cooldown_map: Dict[str, timedelta] = {
            "ici": timedelta(days=3),
            "sdi": timedelta(days=7),
            "efi": timedelta(days=7),
            "tai": timedelta(days=3),
            "zdi": timedelta(days=7),
        }

    def is_suppressed(self, alert_type: str, score: float, now: datetime = None) -> bool:
        if now is None:
            now = datetime.now()
        key = alert_type.lower()

        recent = [r for r in self.history if r.alert_type == key]
        if recent:
            last = max(r.triggered_at for r in recent)
            if now - last < self.cooldown_map.get(key, timedelta(days=3)):
                logger.debug("Suppressed %s: cooldown active", alert_type)
                return True

        return False

    def record(self, alert_type: str, post_id: str, score: float, now: datetime = None):
        if now is None:
            now = datetime.now()
        self.history.append(AlertRecord(alert_type, post_id, now, score))


class AlertResult:
    def __init__(self, alert_type: str, severity: int, title: str, description: str,
                 score: float, category: str, topic: str = "", zona: str = ""):
        self.alert_type = alert_type
        self.severity = severity
        self.severity_label = SEVERITY_LABELS.get(severity, "bajo")
        self.title = title
        self.description = description
        self.score = round(score, 4)
        self.category = category
        self.topic = topic
        self.zona = zona

    def to_dict(self) -> Dict:
        return {
            "type": self.alert_type,
            "severity": self.severity,
            "severity_label": self.severity_label,
            "title": self.title,
            "description": self.description,
            "score": self.score,
            "category": self.category,
            "topic": self.topic,
            "zona": self.zona,
        }


def detect_controversy_spike(
    monthly_controversy: List[float],
    current_controversy_7d: float,
    suppression: SuppressionEngine,
    now: datetime = None,
    min_posts: int = 5,
    threshold_sigma: float = 2.0,
) -> Optional[AlertResult]:
    if len(monthly_controversy) < 4:
        return None

    mean_c = sum(monthly_controversy) / len(monthly_controversy)
    variance = sum((x - mean_c) ** 2 for x in monthly_controversy) / len(monthly_controversy)
    std_c = math.sqrt(variance)

    if std_c < 0.001:
        return None

    ici = (current_controversy_7d - mean_c) / std_c

    if ici <= threshold_sigma:
        return None

    if suppression.is_suppressed("ici", ici, now):
        return None

    severity = 4 if ici > 3.0 else (3 if ici > 2.5 else 2)
    pct_str = f"{current_controversy_7d * 100:.1f}%"
    return AlertResult(
        alert_type="ici",
        severity=severity,
        title=f"Pico de controversia: {pct_str} ({ici:.1f}\u03c3)",
        description=f"\u00cdndice de Controversia en {pct_str}, {ici:.1f} desviaciones sobre la media de {mean_c * 100:.1f}%. Requiere atenci\u00f3n inmediata.",
        score=ici,
        category="controversia",
    )


def detect_sentiment_dissonance(
    current_net_sentiment: float,
    prior_net_sentiment: float,
    suppression: SuppressionEngine,
    now: datetime = None,
    threshold: float = -0.20,
    min_posts: int = 5,
) -> Optional[AlertResult]:
    denom = max(abs(prior_net_sentiment), 0.01)
    sdi = (current_net_sentiment - prior_net_sentiment) / denom

    if sdi > threshold:
        return None

    if suppression.is_suppressed("sdi", sdi, now):
        return None

    drop_pct = abs(sdi) * 100
    return AlertResult(
        alert_type="sdi",
        severity=3,
        title=f"Disonancia de sentimiento: ca\u00edda del {drop_pct:.0f}%",
        description=f"El sentimiento neto cay\u00f3 de {prior_net_sentiment * 100:.1f}% a {current_net_sentiment * 100:.1f}%. Posible crisis de percepci\u00f3n.",
        score=sdi,
        category="sentimiento",
    )


def detect_engagement_fugue(
    current_engagement_rate: float,
    prior_engagement_rate: float,
    suppression: SuppressionEngine,
    now: datetime = None,
    threshold: float = -0.30,
    min_reactions: int = 30,
) -> Optional[AlertResult]:
    denom = max(prior_engagement_rate, 0.001)
    efi = (current_engagement_rate - prior_engagement_rate) / denom

    if efi > threshold:
        return None

    if suppression.is_suppressed("efi", efi, now):
        return None

    drop_pct = abs(efi) * 100
    return AlertResult(
        alert_type="efi",
        severity=2,
        title=f"Fuga de engagement: ca\u00edda del {drop_pct:.0f}%",
        description=f"La tasa de engagement cay\u00f3 de {prior_engagement_rate:.1%} a {current_engagement_rate:.1%}. Se\u00f1al de desconexi\u00f3n con la audiencia.",
        score=efi,
        category="engagement",
    )


def detect_topic_anomaly(
    topic_angry_ratio: float,
    overall_angry_ratio: float,
    topic_name: str,
    topic_post_count: int,
    suppression: SuppressionEngine,
    now: datetime = None,
    threshold_ratio: float = 2.0,
    threshold_min_ratio: float = 0.03,
    min_posts: int = 3,
) -> Optional[AlertResult]:
    if topic_post_count < min_posts:
        return None
    if topic_angry_ratio <= threshold_min_ratio:
        return None

    tai = topic_angry_ratio / max(overall_angry_ratio, 0.0001)
    if tai <= threshold_ratio:
        return None

    if suppression.is_suppressed("tai", tai, now):
        return None

    topic_label = topic_name.replace("_", " ").title()
    return AlertResult(
        alert_type="tai",
        severity=2,
        title=f"T\u00f3pico con rechazo inusual: {topic_label}",
        description=f"Ratio de enojo de {topic_angry_ratio:.1%} vs {overall_angry_ratio:.1%} promedio ({tai:.1f}x). {topic_post_count} publicaciones afectadas.",
        score=tai,
        category="topic_anomaly",
        topic=topic_name,
    )


def detect_zone_dissonance(
    zone_negative_rate: float,
    zone_name: str,
    zone_post_count: int,
    suppression: SuppressionEngine,
    now: datetime = None,
    threshold: float = 0.25,
    min_posts: int = 3,
) -> Optional[AlertResult]:
    if zone_post_count < min_posts:
        return None
    if zone_negative_rate <= threshold:
        return None

    zdi = zone_negative_rate / threshold
    if suppression.is_suppressed("zdi", zdi, now):
        return None

    zone_label = zone_name if zone_name != "unknown" else "Sin especificar"
    neg_pct = zone_negative_rate * 100
    return AlertResult(
        alert_type="zdi",
        severity=2,
        title=f"Disonancia en zona: {zone_label}",
        description=f"{neg_pct:.0f}% de publicaciones negativas en zona {zone_label}. Posible problema de ejecuci\u00f3n en el territorio.",
        score=zdi,
        category="zona_dissonance",
        zona=zone_name,
    )


def prioritize_alerts(alerts: List[AlertResult]) -> List[AlertResult]:
    severity_order = {4: 0, 3: 1, 2: 2, 1: 3}
    return sorted(alerts, key=lambda a: (severity_order.get(a.severity, 99), -abs(a.score)))


def run_all_detectors(
    posts: List[Dict],
    suppression: SuppressionEngine = None,
    now: datetime = None,
) -> Dict:
    if suppression is None:
        suppression = SuppressionEngine()
    if now is None:
        now = datetime.now()

    alerts: List[AlertResult] = []

    if not posts or len(posts) < 5:
        return {"alerts": [], "indices": _compute_indices(posts or []), "topic_sensitivity": {}, "alert_summary": ""}

    indices = _compute_indices(posts)

    monthly_data = _build_monthly_series(posts)
    monthly_keys = sorted(monthly_data.keys())

    controversy_values = [monthly_data[k]["controversy"] for k in monthly_keys if monthly_data[k]["posts"] >= 1]
    if controversy_values and len(controversy_values) >= 3:
        last_7d = _compute_controversy_window(posts, days=7)
        spike = detect_controversy_spike(controversy_values[:-1], last_7d, suppression, now)
        if spike:
            alerts.append(spike)

    sentiment_series = _compute_sentiment_series(posts)
    if len(sentiment_series) >= 2:
        current_ns = sentiment_series[-1]
        prior_ns = sentiment_series[-2]
        dissonance = detect_sentiment_dissonance(current_ns, prior_ns, suppression, now)
        if dissonance:
            alerts.append(dissonance)

    engagement_series = _compute_engagement_series(posts)
    if len(engagement_series) >= 2:
        cur_er = engagement_series[-1]
        pri_er = engagement_series[-2]
        fugue = detect_engagement_fugue(cur_er, pri_er, suppression, now)
        if fugue:
            alerts.append(fugue)

    topic_agg = _aggregate_topics(posts)
    total_angry = sum(t["angrys"] for t in topic_agg.values())
    total_likes_love = sum(t["likes"] + t["loves"] for t in topic_agg.values())
    overall_angry_ratio = total_angry / max(total_angry + total_likes_love, 1)

    for topic_name, agg in topic_agg.items():
        tr = agg["likes"] + agg["loves"] + agg["angrys"]
        angry_ratio = agg["angrys"] / max(tr, 1)
        anomaly = detect_topic_anomaly(
            angry_ratio, overall_angry_ratio, topic_name,
            agg["count"], suppression, now,
        )
        if anomaly:
            alerts.append(anomaly)

    zone_agg = _aggregate_zones(posts)
    for zone_name, agg in zone_agg.items():
        if agg["count"] == 0:
            continue
        neg_rate = agg["negative"] / agg["count"]
        dissonance = detect_zone_dissonance(neg_rate, zone_name, agg["count"], suppression, now)
        if dissonance:
            alerts.append(dissonance)

    for a in alerts:
        suppression.record(a.alert_type, "", a.score, now)

    return {
        "alerts": [a.to_dict() for a in prioritize_alerts(alerts)],
        "indices": indices,
        "topic_sensitivity": _compute_topic_sensitivity(posts),
        "alert_summary": _summarize_alerts(alerts),
    }


def _engagement_metrics(total_reactions, total_comments, total_shares, total_views, total_posts):
    """Engagement sin inflar la m\u00e9trica cuando no hay views (sin read_insights).
    Con views reales -> tasa por views. Sin views -> interacciones promedio por post (proxy)."""
    interactions = total_reactions + total_comments + total_shares
    if total_views > 0:
        return round((interactions / total_views) * 100, 2), "views"
    return round(interactions / max(total_posts, 1), 2), "per_post"


def _compute_indices(posts: List[Dict]) -> Dict:
    total = len(posts)
    total_reactions = sum(
        p.get("likes_count", 0) + p.get("loves_count", 0) + p.get("cares_count", 0) + p.get("hahas_count", 0)
        + p.get("wows_count", 0) + p.get("sads_count", 0) + p.get("angrys_count", 0)
        for p in posts
    )
    total_views = sum(p.get("views_count", 0) for p in posts)
    total_comments = sum(p.get("comments_count", 0) for p in posts)
    total_shares = sum(p.get("shares_count", 0) for p in posts)

    likes = sum(p.get("likes_count", 0) for p in posts)
    loves = sum(p.get("loves_count", 0) for p in posts)
    cares = sum(p.get("cares_count", 0) for p in posts)
    hahas = sum(p.get("hahas_count", 0) for p in posts)
    angrys = sum(p.get("angrys_count", 0) for p in posts)
    sads = sum(p.get("sads_count", 0) for p in posts)

    # "Me divierte" (hahas) en publicaciones oficiales es mayoritariamente
    # burla/sarcasmo: se trata como reaccion NEGATIVA (carga de controversia),
    # nunca como positiva. Positivas = Me gusta + Me encanta + Me importa.
    negativas = angrys + sads + hahas
    n = total_reactions or 1
    net_sentiment = (likes + loves + cares - negativas) / n
    controversy = negativas / n
    effectiveness = (likes + loves + cares) / n
    engagement, engagement_basis = _engagement_metrics(
        total_reactions, total_comments, total_shares, total_views, total
    )

    positive_count = sum(1 for p in posts if p.get("sentiment") == "positive")
    negative_count = sum(1 for p in posts if p.get("sentiment") == "negative")
    nsi = ((positive_count - negative_count) / max(total, 1)) * 100

    topic_groups = defaultdict(list)
    for p in posts:
        topic_groups[p.get("topic_category", "uncategorized")].append(p)
    max_topic_controversy = controversy
    for topic_posts in topic_groups.values():
        t_reactions = sum(p.get("likes_count", 0) + p.get("loves_count", 0) + p.get("cares_count", 0) + p.get("hahas_count", 0)
                         + p.get("wows_count", 0) + p.get("sads_count", 0) + p.get("angrys_count", 0) for p in topic_posts)
        t_neg = sum(p.get("angrys_count", 0) + p.get("sads_count", 0) + p.get("hahas_count", 0) for p in topic_posts)
        if t_reactions > 0:
            tc = t_neg / t_reactions
            if tc > max_topic_controversy:
                max_topic_controversy = tc

    nsi_deviation = max(0, (50 - nsi) / 100)
    vol_factor = min(2.0, 1.0 + total / 1000)

    risk = (max_topic_controversy * 10 * 0.50 + nsi_deviation * 0.50) * vol_factor
    risk = max(0.0, min(1.0, risk))

    como_pct = (likes + loves + cares) / max(total_reactions, 1) * 100
    no_gusta_pct = negativas / max(total_reactions, 1) * 100

    return {
        "engagement": round(engagement, 2),
        "engagementBasis": engagement_basis,
        "netSentiment": round(net_sentiment, 4),
        "controversy": round(controversy, 4),
        "effectiveness": round(effectiveness, 4),
        "riskReputacional": round(risk, 2),
        "nsi": round(nsi, 1),
        "aprobacion": round(como_pct, 1),
        "rechazo": round(no_gusta_pct, 1),
    }


def _build_monthly_series(posts: List[Dict]) -> Dict[str, Dict]:
    monthly = {}
    for p in posts:
        ct = p.get("created_time")
        if not ct:
            continue
        try:
            dt = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        key = dt.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"posts": 0, "reactions": 0, "comments": 0, "shares": 0,
                            "views": 0, "likes": 0, "loves": 0, "cares": 0, "hahas": 0, "angrys": 0, "sads": 0}
        monthly[key]["posts"] += 1
        monthly[key]["reactions"] += sum(p.get(c, 0) for c in
                                          ["likes_count", "loves_count", "cares_count", "hahas_count",
                                           "wows_count", "sads_count", "angrys_count"])
        monthly[key]["comments"] += p.get("comments_count", 0)
        monthly[key]["shares"] += p.get("shares_count", 0)
        monthly[key]["views"] += p.get("views_count", 0)
        monthly[key]["likes"] += p.get("likes_count", 0)
        monthly[key]["loves"] += p.get("loves_count", 0)
        monthly[key]["cares"] += p.get("cares_count", 0)
        monthly[key]["hahas"] += p.get("hahas_count", 0)
        monthly[key]["angrys"] += p.get("angrys_count", 0)
        monthly[key]["sads"] += p.get("sads_count", 0)

    for k in monthly:
        tr = monthly[k]["reactions"] or 1
        # hahas (Me divierte) cuenta como carga negativa/controversia.
        monthly[k]["controversy"] = (monthly[k]["angrys"] + monthly[k]["sads"] + monthly[k]["hahas"]) / tr
        denom = monthly[k]["views"] if monthly[k]["views"] > 0 else max(monthly[k]["posts"], 1)
        monthly[k]["engagement_rate"] = monthly[k]["reactions"] / denom
    return monthly


def _compute_controversy_window(posts: List[Dict], days: int = 7) -> float:
    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for p in posts:
        ct = p.get("created_time")
        if not ct:
            continue
        try:
            dt = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if dt >= cutoff:
            recent.append(p)
    if not recent:
        return 0.0
    likes = sum(p.get("likes_count", 0) for p in recent)
    loves = sum(p.get("loves_count", 0) for p in recent)
    cares = sum(p.get("cares_count", 0) for p in recent)
    hahas = sum(p.get("hahas_count", 0) for p in recent)
    angrys = sum(p.get("angrys_count", 0) for p in recent)
    sads = sum(p.get("sads_count", 0) for p in recent)
    tr = likes + loves + cares + hahas + angrys + sads or 1
    return (angrys + sads + hahas) / tr


def _compute_sentiment_series(posts: List[Dict]) -> List[float]:
    monthly = _build_monthly_series(posts)
    series = []
    for k in sorted(monthly.keys()):
        v = monthly[k]
        tr = v["reactions"] or 1
        ns = (v["likes"] + v["loves"] + v["cares"] - v["angrys"] - v["sads"] - v["hahas"]) / tr
        series.append(ns)
    return series


def _compute_engagement_series(posts: List[Dict]) -> List[float]:
    monthly = _build_monthly_series(posts)
    series = []
    for k in sorted(monthly.keys()):
        v = monthly[k]
        denom = v["views"] if v["views"] > 0 else max(v["posts"], 1)
        rate = v["reactions"] / denom
        series.append(rate)
    return series


def _aggregate_topics(posts: List[Dict]) -> Dict[str, Dict]:
    agg: Dict[str, Dict] = {}
    for p in posts:
        topic = p.get("topic_category", "uncategorized")
        if topic not in agg:
            agg[topic] = {"count": 0, "likes": 0, "loves": 0, "cares": 0,
                          "angrys": 0, "sads": 0, "negative": 0}
        agg[topic]["count"] += 1
        agg[topic]["likes"] += p.get("likes_count", 0)
        agg[topic]["loves"] += p.get("loves_count", 0)
        agg[topic]["cares"] += p.get("cares_count", 0)
        agg[topic]["angrys"] += p.get("angrys_count", 0)
        agg[topic]["sads"] += p.get("sads_count", 0)
        if p.get("sentiment") == "negative":
            agg[topic]["negative"] += 1
    return agg


def _aggregate_zones(posts: List[Dict]) -> Dict[str, Dict]:
    agg: Dict[str, Dict] = {}
    for p in posts:
        zona = p.get("zona", "unknown")
        if zona not in agg:
            agg[zona] = {"count": 0, "negative": 0, "likes": 0, "cares": 0, "angrys": 0}
        agg[zona]["count"] += 1
        agg[zona]["likes"] += p.get("likes_count", 0)
        agg[zona]["cares"] += p.get("cares_count", 0)
        agg[zona]["angrys"] += p.get("angrys_count", 0)
        if p.get("sentiment") == "negative":
            agg[zona]["negative"] += 1
    return agg


def _compute_topic_sensitivity(posts: List[Dict]) -> Dict[str, float]:
    topic_counts = defaultdict(int)
    for p in posts:
        topic = p.get("topic_category", "uncategorized")
        topic_counts[topic] += 1

    result = {}
    for topic, count in topic_counts.items():
        base = TOPIC_DEFAULT_SENSITIVITY.get(topic, 1.0)
        result[topic] = {"base": base, "adjusted": base, "posts": count}
    return result


def _summarize_alerts(alerts: List[AlertResult]) -> Dict:
    total = len(alerts)
    by_severity = defaultdict(int)
    by_type = defaultdict(int)
    for a in alerts:
        by_severity[a.severity_label] += 1
        by_type[a.alert_type] += 1
    return {
        "total": total,
        "by_severity": dict(by_severity),
        "by_type": dict(by_type),
    }
