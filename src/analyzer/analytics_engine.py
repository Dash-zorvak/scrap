import json
import logging
import os
import sqlite3
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from src.analyzer.sentiment import SentimentAnalyzer, SENTIMENT_ORDER
from src.analyzer.topic_detection import (
    get_main_topic, detect_zona, detect_topics, detect_zona_ner,
    detect_emerging_topics, is_emergency, extract_problematicas,
)
from src.analyzer.nlp_pipeline import analyze_entities

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
CACHE_DB = os.path.join(DATA_DIR, "analytics_cache.db")


def _dict_factory(cursor, row):
    d = {}
    for i, col in enumerate(cursor.description):
        d[col[0]] = row[i]
    return d


class AnalyticsEngine:
    fb_db: str
    tt_db: str
    cache_db: str

    def __init__(
        self,
        fb_db: str = "",
        tt_db: str = "",
        cache_db: str = "",
    ):
        self.fb_db = fb_db or os.path.join(DATA_DIR, "facebook.db")
        self.tt_db = tt_db or os.path.join(DATA_DIR, "tiktok.db")
        self.cache_db = cache_db or CACHE_DB
        self._ensure_cache_db()

    def _ensure_cache_db(self):
        os.makedirs(os.path.dirname(self.cache_db), exist_ok=True)
        conn = sqlite3.connect(self.cache_db)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS processed_posts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                sentiment TEXT,
                sentiment_score REAL,
                topic TEXT,
                zone TEXT,
                zone_ner TEXT,
                emotions TEXT,
                entities TEXT,
                is_emergency INTEGER DEFAULT 0,
                problematicas TEXT,
                processed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS processed_comments (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                post_id TEXT,
                sentiment TEXT,
                sentiment_score REAL,
                topic TEXT,
                zone TEXT,
                emotions TEXT,
                processed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_metrics (
                platform TEXT NOT NULL,
                date TEXT NOT NULL,
                total_posts INTEGER,
                total_comments INTEGER,
                total_reactions INTEGER,
                sentiment_dist TEXT,
                topics_dist TEXT,
                zones_dist TEXT,
                metrics_json TEXT,
                computed_at TEXT,
                PRIMARY KEY (platform, date)
            );
            CREATE TABLE IF NOT EXISTS iq_scores (
                platform TEXT,
                date TEXT,
                iq_general REAL,
                dimensions TEXT,
                radar_data TEXT,
                alerts TEXT,
                computed_at TEXT,
                PRIMARY KEY (platform, date)
            );
        """)
        conn.commit()
        conn.close()

    # --- READING UNIFIED RAW DATA ---

    def get_all_posts(self, platform: Optional[str] = None) -> List[Dict]:
        posts = []
        if platform is None or platform == "facebook":
            posts.extend(self._get_fb_posts())
        if platform is None or platform == "tiktok":
            posts.extend(self._get_tt_posts())
        return posts

    def _get_fb_posts(self) -> List[Dict]:
        conn = sqlite3.connect(self.fb_db)
        conn.row_factory = _dict_factory
        cur = conn.execute("""
            SELECT post_id AS id, 'facebook' AS platform,
                   page_name AS account, message, created_time,
                   COALESCE(likes_count,0) AS likes_count,
                   COALESCE(loves_count,0) AS loves_count,
                   COALESCE(hahas_count,0) AS hahas_count,
                   COALESCE(wows_count,0) AS wows_count,
                   COALESCE(sads_count,0) AS sads_count,
                   COALESCE(angrys_count,0) AS angrys_count,
                   COALESCE(comments_count,0) AS comments_count,
                   COALESCE(shares_count,0) AS shares_count,
                   COALESCE(views_count,0) AS views_count,
                   post_url AS url, source
            FROM fb_posts
            WHERE created_time IS NULL OR created_time > '2020-01-01'
            ORDER BY created_time DESC
        """)
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            r["total_reactions"] = (r["likes_count"] + r["loves_count"] + r["hahas_count"]
                                    + r["wows_count"] + r["sads_count"] + r["angrys_count"])
        return rows

    def _get_tt_posts(self) -> List[Dict]:
        conn = sqlite3.connect(self.tt_db)
        conn.row_factory = _dict_factory
        cur = conn.execute("""
            SELECT v.id AS id, 'tiktok' AS platform,
                   a.display_name AS account, v.description AS message,
                   v.created_at AS created_time,
                   COALESCE(v.likes,0) AS likes_count,
                   0 AS loves_count, 0 AS hahas_count,
                   0 AS wows_count, 0 AS sads_count, 0 AS angrys_count,
                   COALESCE(v.comments_count,0) AS comments_count,
                   COALESCE(v.shares,0) AS shares_count,
                   COALESCE(v.views,0) AS views_count,
                   v.url, 'tiktok' AS source
            FROM videos v
            JOIN accounts a ON v.account_id = a.id
            ORDER BY v.created_at DESC
        """)
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            r["total_reactions"] = r["likes_count"]
        return rows

    def get_all_comments(self, platform: Optional[str] = None) -> List[Dict]:
        comments = []
        if platform is None or platform == "facebook":
            comments.extend(self._get_fb_comments())
        if platform is None or platform == "tiktok":
            comments.extend(self._get_tt_comments())
        return comments

    def _get_fb_comments(self) -> List[Dict]:
        conn = sqlite3.connect(self.fb_db)
        conn.row_factory = _dict_factory
        cur = conn.execute("""
            SELECT comment_id AS id, 'facebook' AS platform,
                   post_id, author_name, message AS text,
                   COALESCE(like_count,0) AS likes_count,
                   created_time
            FROM fb_comments
            ORDER BY created_time DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows

    def _get_tt_comments(self) -> List[Dict]:
        conn = sqlite3.connect(self.tt_db)
        conn.row_factory = _dict_factory
        cur = conn.execute("""
            SELECT c.id AS id, 'tiktok' AS platform,
                   c.video_id AS post_id, c.username AS author_name,
                   c.text, COALESCE(c.likes,0) AS likes_count,
                   c.created_at AS created_time
            FROM comments c
            WHERE c.text IS NOT NULL AND c.text != ''
            ORDER BY c.created_at DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows

    # --- PROCESSING PIPELINE ---

    def process_post(self, post: Dict, sentiment_only: bool = False) -> Dict:
        cached = self._get_cached_processed(post["id"], post["platform"], "post")
        if cached:
            reconstructed = {
                "sentiment": cached.get("sentiment"),
                "sentiment_score": cached.get("sentiment_score"),
                "topic": cached.get("topic", ""),
                "zone": cached.get("zone", ""),
                "zone_ner": json.loads(cached["zone_ner"]) if cached.get("zone_ner") else [],
                "emotions": json.loads(cached["emotions"]) if cached.get("emotions") else {},
                "entities": json.loads(cached["entities"]) if cached.get("entities") else [],
                "is_emergency": bool(cached.get("is_emergency")),
                "problematicas": json.loads(cached["problematicas"]) if cached.get("problematicas") else [],
            }
            post.update(reconstructed)
            return post

        text = post.get("message") or post.get("description") or ""

        if not text or len(text.strip()) < 3:
            processed = {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "topic": "",
                "zone": "",
                "zone_ner": [],
                "emotions": {},
                "entities": [],
                "is_emergency": False,
                "problematicas": [],
            }
            post.update(processed)
            self._cache_processed(post["id"], post["platform"], "post", processed)
            return post

        analyzer = SentimentAnalyzer()
        sentiment, score = analyzer.analyze(text)

        if sentiment_only:
            processed = {
                "sentiment": sentiment,
                "sentiment_score": score,
                "topic": "",
                "zone": "",
                "zone_ner": [],
                "emotions": {},
                "entities": [],
                "is_emergency": False,
                "problematicas": [],
            }
            post.update(processed)
            self._cache_processed(post["id"], post["platform"], "post", processed)
            return post

        emotions = analyzer.analyze_emotions(text)
        main_topic = get_main_topic(text)
        zone = detect_zona(text)
        zone_ner = detect_zona_ner(text)
        emergency = is_emergency(text)
        entities = analyze_entities(text)
        problematicas = extract_problematicas(text, sentiment)

        processed = {
            "sentiment": sentiment,
            "sentiment_score": score,
            "topic": main_topic,
            "zone": zone or (zone_ner[0] if zone_ner else ""),
            "zone_ner": zone_ner,
            "emotions": emotions,
            "entities": entities,
            "is_emergency": emergency,
            "problematicas": problematicas,
        }
        post.update(processed)
        self._cache_processed(post["id"], post["platform"], "post", processed)
        return post

    def process_comment(self, comment: Dict) -> Dict:
        cached = self._get_cached_processed(comment["id"], comment["platform"], "comment")
        if cached:
            reconstructed = {
                "sentiment": cached.get("sentiment"),
                "sentiment_score": cached.get("sentiment_score"),
                "topic": cached.get("topic", ""),
                "zone": cached.get("zone", ""),
                "emotions": json.loads(cached.get("emotions", "{}")),
            }
            comment.update(reconstructed)
            return comment

        text = comment.get("text") or ""

        if not text or len(text.strip()) < 3:
            processed = {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "topic": "",
                "zone": "",
                "emotions": {},
                "post_id": comment.get("post_id", ""),
            }
            comment.update(processed)
            self._cache_processed(comment["id"], comment["platform"], "comment", processed)
            return comment

        analyzer = SentimentAnalyzer()
        sentiment, score = analyzer.analyze(text)
        emotions = analyzer.analyze_emotions(text)
        main_topic = get_main_topic(text)
        zone = detect_zona(text)

        processed = {
            "sentiment": sentiment,
            "sentiment_score": score,
            "topic": main_topic,
            "zone": zone,
            "emotions": emotions,
            "post_id": comment.get("post_id", ""),
        }
        comment.update(processed)
        self._cache_processed(comment["id"], comment["platform"], "comment", processed)
        return comment

    def process_all_posts(self, platform: Optional[str] = None, batch_size: int = 100) -> List[Dict]:
        posts = self.get_all_posts(platform)
        total = len(posts)
        for i, post in enumerate(posts):
            self.process_post(post)
            if (i + 1) % batch_size == 0:
                logger.info(f"Processed {i+1}/{total} posts")
        return posts

    def process_all_comments(self, platform: Optional[str] = None, batch_size: int = 500) -> List[Dict]:
        comments = self.get_all_comments(platform)
        total = len(comments)
        for i, c in enumerate(comments):
            self.process_comment(c)
            if (i + 1) % batch_size == 0:
                logger.info(f"Processed {i+1}/{total} comments")
        return comments

    # --- CACHE ---

    def _get_cached_processed(self, item_id: str, platform: str, item_type: str) -> Optional[Dict]:
        conn = sqlite3.connect(self.cache_db)
        conn.row_factory = _dict_factory
        cur = conn.execute(
            "SELECT * FROM processed_posts WHERE id = ? AND platform = ?"
            if item_type == "post"
            else "SELECT * FROM processed_comments WHERE id = ? AND platform = ?",
            (item_id, platform),
        )
        row = cur.fetchone()
        conn.close()
        return row

    def _cache_processed(self, item_id: str, platform: str, item_type: str, data: Dict):
        table = "processed_posts" if item_type == "post" else "processed_comments"

        if item_type == "post":
            zone_ner_json = json.dumps(data.get("zone_ner", []), ensure_ascii=False)
            entities_json = json.dumps(data.get("entities", []), ensure_ascii=False)
            emotions_json = json.dumps(data.get("emotions", {}), ensure_ascii=False)
            problematicas_json = json.dumps(data.get("problematicas", []), ensure_ascii=False)

            conn = sqlite3.connect(self.cache_db)
            conn.execute(f"""
                INSERT OR REPLACE INTO {table}
                (id, platform, sentiment, sentiment_score, topic, zone, zone_ner,
                 emotions, entities, is_emergency, problematicas, processed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            """, (
                item_id, platform,
                data.get("sentiment"), data.get("sentiment_score"),
                data.get("topic"), data.get("zone"), zone_ner_json,
                emotions_json, entities_json,
                1 if data.get("is_emergency") else 0,
                problematicas_json,
            ))
            conn.commit()
            conn.close()
        else:
            emotions_json = json.dumps(data.get("emotions", {}), ensure_ascii=False)
            conn = sqlite3.connect(self.cache_db)
            conn.execute(f"""
                INSERT OR REPLACE INTO {table}
                (id, platform, post_id, sentiment, sentiment_score, topic, zone,
                 emotions, processed_at)
                VALUES (?,?,?,?,?,?,?,?,datetime('now'))
            """, (
                item_id, platform, data.get("post_id", ""),
                data.get("sentiment"), data.get("sentiment_score"),
                data.get("topic"), data.get("zone"),
                emotions_json,
            ))
            conn.commit()
            conn.close()

    # --- DAILY METRICS ---

    def compute_daily_metrics(self, posts: List[Dict], comments: List[Dict],
                              platform: str, date_str: str) -> Dict:
        sentiments = [p.get("sentiment", "neutral") for p in posts]
        sentiment_dist = dict(Counter(sentiments))

        topics = [p.get("topic", "") for p in posts if p.get("topic")]
        topics_dist = dict(Counter(topics).most_common(10))

        zones = [p.get("zone", "") for p in posts if p.get("zone")]
        zones_dist = dict(Counter(zones).most_common(10))

        total_reactions = sum(p.get("total_reactions", 0) for p in posts)

        metrics = {
            "platform": platform,
            "date": date_str,
            "total_posts": len(posts),
            "total_comments": len(comments),
            "total_reactions": total_reactions,
            "sentiment_dist": sentiment_dist,
            "topics_dist": topics_dist,
            "zones_dist": zones_dist,
        }

        conn = sqlite3.connect(self.cache_db)
        conn.execute("""
            INSERT OR REPLACE INTO daily_metrics
            (platform, date, total_posts, total_comments, total_reactions,
             sentiment_dist, topics_dist, zones_dist, metrics_json, computed_at)
            VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))
        """, (
            platform, date_str, len(posts), len(comments), total_reactions,
            json.dumps(sentiment_dist, ensure_ascii=False),
            json.dumps(topics_dist, ensure_ascii=False),
            json.dumps(zones_dist, ensure_ascii=False),
            json.dumps(metrics, ensure_ascii=False),
        ))
        conn.commit()
        conn.close()
        return metrics

    # --- PIPELINE ORCHESTRATOR ---

    def run_full_pipeline(self, platforms: Optional[List[str]] = None) -> Dict:
        if platforms is None:
            platforms = ["facebook", "tiktok"]

        results = {}
        for pl in platforms:
            logger.info(f"Processing {pl} posts...")
            posts = self.process_all_posts(pl)
            logger.info(f"Processing {pl} comments...")
            comments = self.process_all_comments(pl)
            today = datetime.now().strftime("%Y-%m-%d")
            metrics = self.compute_daily_metrics(posts, comments, pl, today)
            results[pl] = {
                "posts_count": len(posts),
                "comments_count": len(comments),
                "metrics": metrics,
            }
            logger.info(f"{pl}: {len(posts)} posts, {len(comments)} comments")

        return results
