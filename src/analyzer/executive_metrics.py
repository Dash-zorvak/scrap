import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter, defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class ExecutiveMetrics:
    def __init__(self, storage):
        self.storage = storage

    def calculate_nsi(self, positive_count: int, negative_count: int, total: int) -> float:
        if total == 0:
            return 0
        positive_pct = (positive_count / total) * 100
        negative_pct = (negative_count / total) * 100
        return round(positive_pct - negative_pct, 1)

    def calculate_cai(self, negative_velocity: float, emergency_keywords: int, volume_spike: float) -> float:
        cai = (negative_velocity * 0.4) + (emergency_keywords * 0.3) + (volume_spike * 0.3)
        return round(cai, 1)

    def get_engagement_score(self, post: Dict) -> float:
        likes = post.get("likes_count", 0)
        loves = post.get("loves_count", 0)
        comments = post.get("comments_count", 0)
        shares = post.get("shares_count", 0)
        return likes + (loves * 1.5) + (comments * 2) + (shares * 3)

    def generate_daily_metrics(self, platform: str) -> Dict:
        posts = self.storage.get_fb_posts(limit=10000)
        comments_count = self.storage.get_executive_summary().get("fb_comments", 0)

        if not posts:
            return {}

        positive_count = sum(1 for p in posts if p.get("sentiment") == "positive")
        negative_count = sum(1 for p in posts if p.get("sentiment") == "negative")
        neutral_count = sum(1 for p in posts if p.get("sentiment") == "neutral")

        total_reactions = sum(
            p.get("likes_count", 0) + p.get("loves_count", 0) + p.get("comments_count", 0)
            for p in posts
        )

        positive_pct = (positive_count / len(posts)) * 100 if posts else 0
        negative_pct = (negative_count / len(posts)) * 100 if posts else 0
        neutral_pct = (neutral_count / len(posts)) * 100 if posts else 0

        nsi = self.calculate_nsi(positive_count, negative_count, len(posts))

        emergency_count = sum(
            1 for p in posts if p.get("topic_category") in ["seguridad", "corrupcion"]
        )

        negative_velocity = negative_pct
        emergency_score = (emergency_count / len(posts)) * 100 if posts else 0
        volume_spike = 0

        cai = self.calculate_cai(negative_velocity, emergency_score, volume_spike)

        topic_counts = Counter()
        for p in posts:
            topic = p.get("topic_category", "")
            if topic:
                topic_counts[topic] += 1

        top_topics = [{"topic": t, "count": c} for t, c in topic_counts.most_common(5)]

        return {
            "platform": platform,
            "date": datetime.now().date(),
            "total_posts": len(posts),
            "total_comments": comments_count,
            "total_reactions": total_reactions,
            "positive_pct": round(positive_pct, 1),
            "negative_pct": round(negative_pct, 1),
            "neutral_pct": round(neutral_pct, 1),
            "nsi": nsi,
            "cai": cai,
            "top_topics": top_topics,
            "top_problematicas": top_topics,
        }

    def generate_insights(self, platform: str, limit: int = 10) -> List[Dict]:
        posts = self.storage.get_fb_posts(limit=1000)

        if not posts:
            return []

        insights = []

        topic_sentiment = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
        topic_volume = defaultdict(int)

        for post in posts:
            topic = post.get("topic_category", "")
            sentiment = post.get("sentiment", "")

            if topic:
                topic_sentiment[topic][sentiment] += 1
                topic_volume[topic] += 1

        for topic, counts in topic_sentiment.items():
            total = sum(counts.values())
            if total < 3:
                continue

            pos_pct = (counts["positive"] / total) * 100
            neg_pct = (counts["negative"] / total) * 100

            if neg_pct > 40:
                priority = 5
                insight_type = "crisis_alert"
                title = f"Tema crítico: {topic.replace('_', ' ').title()}"
                description = f"Este tema genera {neg_pct:.0f}% de sentiment negativo. Requiere atención inmediata."
            elif neg_pct > 20:
                priority = 3
                insight_type = "concern"
                title = f"Preocupación: {topic.replace('_', ' ').title()}"
                description = f"Sentimiento negativo en {neg_pct:.0f}% de posts sobre este tema."
            else:
                continue

            insights.append({
                "insight_type": insight_type,
                "title": title,
                "description": description,
                "topic": topic,
                "sentiment": "negative" if neg_pct > 20 else "positive",
                "priority": priority,
                "metric_data": {
                    "total_mentions": total,
                    "positive_pct": round(pos_pct, 1),
                    "negative_pct": round(neg_pct, 1),
                    "neutral_pct": round(100 - pos_pct - neg_pct, 1)
                }
            })

        zona_analysis = defaultdict(lambda: {"topics": Counter(), "sentiment": []})

        for post in posts:
            zona = post.get("zona", "")
            topic = post.get("topic_category", "")
            sentiment = post.get("sentiment", "")

            if zona:
                if topic:
                    zona_analysis[zona]["topics"][topic] += 1
                zona_analysis[zona]["sentiment"].append(sentiment)

        for zona, data in zona_analysis.items():
            if not data["topics"]:
                continue

            top_topic = data["topics"].most_common(1)[0]
            neg_sentiments = sum(1 for s in data["sentiment"] if s == "negative")
            total_sentiments = len(data["sentiment"])

            if total_sentiments > 0 and (neg_sentiments / total_sentiments) > 0.3:
                insights.append({
                    "insight_type": "zona_alert",
                    "title": f"Zona {zona}: Problema en {top_topic[0].replace('_', ' ').title()}",
                    "description": f"La zona {zona} tiene {neg_sentiments} comentarios negativos sobre {top_topic[0]} ({top_topic[1]} menciones)",
                    "topic": top_topic[0],
                    "zona": zona,
                    "sentiment": "negative",
                    "priority": 4,
                    "metric_data": {
                        "mentions": top_topic[1],
                        "negative_ratio": round((neg_sentiments / total_sentiments) * 100, 1)
                    }
                })

        posts_by_engagement = sorted(
            posts,
            key=lambda p: self.get_engagement_score(p),
            reverse=True
        )[:5]

        for post in posts_by_engagement:
            topic = post.get("topic_category", "")
            sentiment = post.get("sentiment", "")

            if sentiment == "negative" and topic:
                insights.append({
                    "insight_type": "high_impact_negative",
                    "title": f"Post de alto impacto negativo: {topic.replace('_', ' ').title()}",
                    "description": f"Post con alto engagement pero sentiment negativo sobre {topic}",
                    "topic": topic,
                    "sentiment": "negative",
                    "priority": 4,
                    "post_id": post.get("post_id", ""),
                    "metric_data": {
                        "engagement": self.get_engagement_score(post),
                        "likes": post.get("likes_count", 0),
                        "comments": post.get("comments_count", 0)
                    }
                })

        insights.sort(key=lambda x: x["priority"], reverse=True)
        return insights[:limit]

    def get_problematicas_by_zone(self, days: int = 30) -> Dict:
        problematicas = []

        fb_posts = self.storage.get_fb_posts(limit=5000)

        for post in fb_posts:
            topic = post.get("topic_category", "")
            zona = post.get("zona", "")
            sentiment = post.get("sentiment", "")

            if topic:
                problematicas.append({
                    "topic": topic,
                    "zona": zona,
                    "sentiment": sentiment,
                    "platform": "facebook",
                })

        zona_topic_counts = defaultdict(lambda: defaultdict(int))
        zona_sentiment = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

        for p in problematicas:
            zona = p.get("zona") or "Sin zona"
            topic = p.get("topic")
            sentiment = p.get("sentiment")

            if topic and zona:
                zona_topic_counts[zona][topic] += 1
                if sentiment:
                    zona_sentiment[zona][sentiment] += 1

        result = {}
        for zona, topics in zona_topic_counts.items():
            result[zona] = {
                "topics": dict(topics),
                "total_mentions": sum(topics.values()),
                "sentiment": dict(zona_sentiment[zona]),
                "negative_pct": 0
            }

            total = sum(zona_sentiment[zona].values())
            if total > 0:
                result[zona]["negative_pct"] = round(
                    (zona_sentiment[zona].get("negative", 0) / total) * 100, 1
                )

        return result

    def get_sentiment_trend(self, days: int = 30) -> Dict:
        metrics = self.storage.get_daily_metrics(days=days)

        if not metrics:
            return {"labels": [], "positive": [], "negative": [], "neutral": []}

        labels = []
        positive = []
        negative = []
        neutral = []

        for m in sorted(metrics, key=lambda x: x.get("date", "")):
            labels.append(str(m.get("date", "")))
            positive.append(m.get("positive_pct", 0))
            negative.append(m.get("negative_pct", 0))
            neutral.append(m.get("neutral_pct", 0))

        return {
            "labels": labels,
            "positive": positive,
            "negative": negative,
            "neutral": neutral
        }
