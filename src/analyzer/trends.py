import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    def __init__(self, db_session):
        self.session = db_session

    @staticmethod
    def _time_col(model):
        return model.created_time if hasattr(model, "created_time") else model.create_time

    @staticmethod
    def _time_val(row):
        return row.created_time if hasattr(row, "created_time") else row.create_time

    def sentiment_over_time(self, platform: str = "facebook", window_days: int = 30):
        from src.storage.db import FBPost, TTPost

        model = FBPost if platform == "facebook" else TTPost
        time_col = self._time_col(model)

        rows = (
            self.session.query(model)
            .filter(time_col.isnot(None))
            .filter(model.sentiment != "")
            .all()
        )

        if not rows:
            return {"labels": [], "positive": [], "negative": [], "neutral": [], "total": []}

        times = [self._time_val(r) for r in rows if self._time_val(r)]
        min_date = min(times)
        max_date = max(times)

        min_date = min_date.replace(hour=0, minute=0, second=0, microsecond=0)
        max_date = max_date.replace(hour=0, minute=0, second=0, microsecond=0)

        buckets = {}
        current = min_date
        while current <= max_date:
            bucket_end = current + timedelta(days=window_days)
            buckets[(current, bucket_end)] = {"pos": 0, "neg": 0, "neu": 0, "total": 0}
            current = bucket_end

        for row in rows:
            t = self._time_val(row)
            if not t:
                continue
            for (start, end), counts in buckets.items():
                if start <= t < end:
                    counts["total"] += 1
                    if row.sentiment == "positive":
                        counts["pos"] += 1
                    elif row.sentiment == "negative":
                        counts["neg"] += 1
                    else:
                        counts["neu"] += 1
                    break

        result = {
            "labels": [],
            "positive": [],
            "negative": [],
            "neutral": [],
            "total": [],
        }
        for (start, end), counts in sorted(buckets.items(), key=lambda x: x[0][0]):
            total = counts["total"]
            result["labels"].append(start.strftime("%Y-%m-%d"))
            result["positive"].append(round(counts["pos"] / total * 100, 1) if total else 0)
            result["negative"].append(round(counts["neg"] / total * 100, 1) if total else 0)
            result["neutral"].append(round(counts["neu"] / total * 100, 1) if total else 0)
            result["total"].append(total)

        return result

    def engagement_analysis(self, platform: str = "facebook"):
        from src.storage.db import FBPost, TTPost

        model = FBPost if platform == "facebook" else TTPost
        rows = self.session.query(model).all()

        if not rows:
            return {}

        total_posts = len(rows)
        total_reactions = sum(
            r.likes_count + getattr(r, "loves_count", 0) + getattr(r, "cares_count", 0) + getattr(r, "hahas_count", 0)
            + getattr(r, "wows_count", 0) + getattr(r, "sads_count", 0)
            + getattr(r, "angrys_count", 0)
            for r in rows
        )
        total_comments = sum(r.comments_count for r in rows)
        total_shares = sum(getattr(r, "shares_count", 0) for r in rows) or sum(
            getattr(r, "views_count", 0) for r in rows
        )

        engagement_by_sentiment = {"positive": [], "negative": [], "neutral": []}
        for r in rows:
            if r.sentiment in engagement_by_sentiment:
                eng = r.likes_count + r.comments_count * 2 + getattr(r, "shares_count", 0) * 3
                engagement_by_sentiment[r.sentiment].append(eng)

        avg_engagement = {}
        for sent, vals in engagement_by_sentiment.items():
            avg_engagement[sent] = round(np.mean(vals), 1) if vals else 0

        return {
            "total_posts": total_posts,
            "total_reactions": total_reactions,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_reactions_per_post": round(total_reactions / total_posts, 1) if total_posts else 0,
            "avg_comments_per_post": round(total_comments / total_posts, 1) if total_posts else 0,
            "avg_engagement_by_sentiment": avg_engagement,
        }

    def top_posts(self, platform: str = "facebook", limit: int = 20):
        from src.storage.db import FBPost, TTPost

        model = FBPost if platform == "facebook" else TTPost
        text_col = model.message if hasattr(model, "message") else model.description
        rows = self.session.query(model).filter(text_col != "").all()

        scored = []
        for r in rows:
            engagement = (
                r.likes_count
                + r.comments_count * 2
                + getattr(r, "shares_count", 0) * 3
            )
            scored.append((engagement, r))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "id": r.post_id if hasattr(r, "post_id") else r.id,
                "message": (r.message if hasattr(r, "message") else r.description)[:200],
                "engagement_score": score,
                "likes": r.likes_count,
                "comments": r.comments_count,
                "sentiment": r.sentiment,
                "date": (self._time_val(r).isoformat() if self._time_val(r) else ""),
            }
            for score, r in scored[:limit]
        ]

    def reaction_breakdown(self):
        from src.storage.db import FBPost

        rows = self.session.query(FBPost).all()
        if not rows:
            return {}

        total = len(rows)
        likes = sum(r.likes_count for r in rows)
        loves = sum(r.loves_count for r in rows)
        cares = sum(r.cares_count for r in rows)
        hahas = sum(r.hahas_count for r in rows)
        wows = sum(r.wows_count for r in rows)
        sads = sum(r.sads_count for r in rows)
        angrys = sum(r.angrys_count for r in rows)

        all_reactions = likes + loves + cares + hahas + wows + sads + angrys

        return {
            "total_reactions": all_reactions,
            "likes": {"count": likes, "pct": round(likes / all_reactions * 100, 1) if all_reactions else 0},
            "loves": {"count": loves, "pct": round(loves / all_reactions * 100, 1) if all_reactions else 0},
            "hahas": {"count": hahas, "pct": round(hahas / all_reactions * 100, 1) if all_reactions else 0},
            "wows": {"count": wows, "pct": round(wows / all_reactions * 100, 1) if all_reactions else 0},
            "sads": {"count": sads, "pct": round(sads / all_reactions * 100, 1) if all_reactions else 0},
            "angrys": {"count": angrys, "pct": round(angrys / all_reactions * 100, 1) if all_reactions else 0},
        }
