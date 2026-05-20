import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()


class FBPost(Base):
    __tablename__ = "fb_posts"

    post_id = sa.Column(sa.Text, primary_key=True)
    page_id = sa.Column(sa.Text, default="")
    page_name = sa.Column(sa.Text, default="")
    message = sa.Column(sa.Text, default="")
    created_time = sa.Column(sa.DateTime, nullable=True)
    likes_count = sa.Column(sa.Integer, default=0)
    loves_count = sa.Column(sa.Integer, default=0)
    hahas_count = sa.Column(sa.Integer, default=0)
    wows_count = sa.Column(sa.Integer, default=0)
    sads_count = sa.Column(sa.Integer, default=0)
    angrys_count = sa.Column(sa.Integer, default=0)
    comments_count = sa.Column(sa.Integer, default=0)
    shares_count = sa.Column(sa.Integer, default=0)
    views_count = sa.Column(sa.Integer, default=0)
    post_url = sa.Column(sa.Text, default="")
    sentiment = sa.Column(sa.Text, default="")
    sentiment_score = sa.Column(sa.Float, default=0.0)
    topic_category = sa.Column(sa.Text, default="")
    zona = sa.Column(sa.Text, default="")
    scraped_at = sa.Column(sa.DateTime, server_default=sa.func.now())
    source = sa.Column(sa.Text, default="graph_api")


class FBComment(Base):
    __tablename__ = "fb_comments"

    comment_id = sa.Column(sa.Text, primary_key=True)
    post_id = sa.Column(sa.Text, nullable=False, index=True)
    message = sa.Column(sa.Text, default="")
    author_name = sa.Column(sa.Text, default="")
    created_time = sa.Column(sa.DateTime, nullable=True)
    like_count = sa.Column(sa.Integer, default=0)
    parent_comment_id = sa.Column(sa.Text, nullable=True)
    sentiment = sa.Column(sa.Text, default="")
    sentiment_score = sa.Column(sa.Float, default=0.0)
    topic_category = sa.Column(sa.Text, default="")
    zona = sa.Column(sa.Text, default="")
    scraped_at = sa.Column(sa.DateTime, server_default=sa.func.now())


class Problema(Base):
    __tablename__ = "problematicas"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    platform = sa.Column(sa.Text, default="")
    post_id = sa.Column(sa.Text, default="")
    comment_id = sa.Column(sa.Text, default="")
    topic = sa.Column(sa.Text, default="")
    zona = sa.Column(sa.Text, default="")
    message = sa.Column(sa.Text, default="")
    sentiment = sa.Column(sa.Text, default="")
    sentiment_score = sa.Column(sa.Float, default=0.0)
    detected_at = sa.Column(sa.DateTime, server_default=sa.func.now())


class Insight(Base):
    __tablename__ = "insights"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    insight_type = sa.Column(sa.Text, default="")
    title = sa.Column(sa.Text, default="")
    description = sa.Column(sa.Text, default="")
    topic = sa.Column(sa.Text, default="")
    zona = sa.Column(sa.Text, default="")
    sentiment = sa.Column(sa.Text, default="")
    priority = sa.Column(sa.Integer, default=0)
    post_id = sa.Column(sa.Text, default="")
    metric_data = sa.Column(sa.Text, default="{}")
    created_at = sa.Column(sa.DateTime, server_default=sa.func.now())


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    platform = sa.Column(sa.Text, nullable=False)
    date = sa.Column(sa.Date, nullable=False)
    total_posts = sa.Column(sa.Integer, default=0)
    total_comments = sa.Column(sa.Integer, default=0)
    total_reactions = sa.Column(sa.Integer, default=0)
    positive_pct = sa.Column(sa.Float, default=0.0)
    negative_pct = sa.Column(sa.Float, default=0.0)
    neutral_pct = sa.Column(sa.Float, default=0.0)
    nsi = sa.Column(sa.Float, default=0.0)
    cai = sa.Column(sa.Float, default=0.0)
    top_topics = sa.Column(sa.Text, default="[]")
    top_problematicas = sa.Column(sa.Text, default="[]")


class LocalStorage:
    def __init__(self, db_path: str = None):
        if db_path is None:
            cfg = Config()
            db_path = os.path.join(cfg.DATA_DIR, "backup.db")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self.engine = sa.create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _session(self):
        return self.Session()

    def _parse_dt(self, val):
        if val is None or isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except (ValueError, TypeError):
                return None
        return None

    # ── inserts ──────────────────────────────────────────────

    def insert_fb_post(self, post: Dict[str, Any]) -> bool:
        try:
            obj = FBPost(
                post_id=post.get("post_id"),
                page_id=post.get("page_id", ""),
                page_name=post.get("page_name", ""),
                message=post.get("message", "")[:10000],
                created_time=self._parse_dt(post.get("created_time")),
                likes_count=post.get("likes_count", 0),
                loves_count=post.get("loves_count", 0),
                hahas_count=post.get("hahas_count", 0),
                wows_count=post.get("wows_count", 0),
                sads_count=post.get("sads_count", 0),
                angrys_count=post.get("angrys_count", 0),
                comments_count=post.get("comments_count", 0),
                shares_count=post.get("shares_count", 0),
                views_count=post.get("views_count", 0),
                post_url=post.get("post_url", ""),
                sentiment=post.get("sentiment", ""),
                sentiment_score=post.get("sentiment_score", 0),
                topic_category=post.get("topic_category", ""),
                zona=post.get("zona", ""),
                source=post.get("source", "graph_api"),
            )
            s = self._session()
            s.merge(obj)
            s.commit()
            s.close()
            return True
        except Exception as e:
            logger.error(f"Local backup error (fb_post): {e}")
            return False

    def insert_fb_comment(self, comment: Dict[str, Any]) -> bool:
        try:
            obj = FBComment(
                comment_id=comment.get("comment_id"),
                post_id=comment.get("post_id", ""),
                message=comment.get("message", "")[:5000],
                author_name=comment.get("author_name", ""),
                created_time=self._parse_dt(comment.get("created_time")),
                like_count=comment.get("like_count", 0),
                parent_comment_id=comment.get("parent_comment_id"),
                sentiment=comment.get("sentiment", ""),
                sentiment_score=comment.get("sentiment_score", 0),
                topic_category=comment.get("topic_category", ""),
                zona=comment.get("zona", ""),
            )
            s = self._session()
            s.merge(obj)
            s.commit()
            s.close()
            return True
        except Exception as e:
            logger.error(f"Local backup error (fb_comment): {e}")
            return False

    def insert_problematica(self, data: Dict[str, Any]) -> bool:
        try:
            obj = Problema(
                platform=data.get("platform", ""),
                post_id=data.get("post_id", ""),
                comment_id=data.get("comment_id", ""),
                topic=data.get("topic", ""),
                zona=data.get("zona", ""),
                message=data.get("message", ""),
                sentiment=data.get("sentiment", ""),
                sentiment_score=data.get("sentiment_score", 0),
            )
            s = self._session()
            s.add(obj)
            s.commit()
            s.close()
            return True
        except Exception as e:
            logger.error(f"Local backup error (problematica): {e}")
            return False

    def insert_insight(self, data: Dict[str, Any]) -> bool:
        try:
            metric_data = data.get("metric_data", {})
            if not isinstance(metric_data, str):
                metric_data = json.dumps(metric_data)

            obj = Insight(
                insight_type=data.get("insight_type", ""),
                title=data.get("title", ""),
                description=data.get("description", ""),
                topic=data.get("topic", ""),
                zona=data.get("zona", ""),
                sentiment=data.get("sentiment", ""),
                priority=data.get("priority", 0),
                post_id=data.get("post_id", ""),
                metric_data=metric_data,
            )
            s = self._session()
            s.add(obj)
            s.commit()
            s.close()
            return True
        except Exception as e:
            logger.error(f"Local backup error (insight): {e}")
            return False

    def insert_daily_metric(self, metric: Dict[str, Any]) -> bool:
        try:
            top_topics = metric.get("top_topics", [])
            top_problematicas = metric.get("top_problematicas", [])
            if not isinstance(top_topics, str):
                top_topics = json.dumps(top_topics)
            if not isinstance(top_problematicas, str):
                top_problematicas = json.dumps(top_problematicas)

            dt_val = metric.get("date", datetime.now().date())
            if isinstance(dt_val, str):
                try:
                    dt_val = datetime.fromisoformat(dt_val).date()
                except (ValueError, TypeError):
                    dt_val = datetime.now().date()

            s = self._session()
            existing = (
                s.query(DailyMetric)
                .filter(
                    DailyMetric.platform == metric.get("platform", ""),
                    DailyMetric.date == dt_val,
                )
                .first()
            )
            if existing:
                existing.total_posts = metric.get("total_posts", 0)
                existing.total_comments = metric.get("total_comments", 0)
                existing.total_reactions = metric.get("total_reactions", 0)
                existing.positive_pct = metric.get("positive_pct", 0)
                existing.negative_pct = metric.get("negative_pct", 0)
                existing.neutral_pct = metric.get("neutral_pct", 0)
                existing.nsi = metric.get("nsi", 0)
                existing.cai = metric.get("cai", 0)
                existing.top_topics = top_topics
                existing.top_problematicas = top_problematicas
            else:
                s.add(
                    DailyMetric(
                        platform=metric.get("platform", ""),
                        date=dt_val,
                        total_posts=metric.get("total_posts", 0),
                        total_comments=metric.get("total_comments", 0),
                        total_reactions=metric.get("total_reactions", 0),
                        positive_pct=metric.get("positive_pct", 0),
                        negative_pct=metric.get("negative_pct", 0),
                        neutral_pct=metric.get("neutral_pct", 0),
                        nsi=metric.get("nsi", 0),
                        cai=metric.get("cai", 0),
                        top_topics=top_topics,
                        top_problematicas=top_problematicas,
                    )
                )
            s.commit()
            s.close()
            return True
        except Exception as e:
            logger.error(f"Local backup error (daily_metric): {e}")
            return False

    # ── counts ───────────────────────────────────────────────

    def count(self, table: str) -> int:
        try:
            s = self._session()
            model_map = {
                "fb_posts": FBPost,
                "fb_comments": FBComment,
                "problematicas": Problema,
                "insights": Insight,
                "daily_metrics": DailyMetric,
            }
            model = model_map.get(table)
            if model is None:
                return 0
            cnt = s.query(model).count()
            s.close()
            return cnt
        except Exception as e:
            logger.error(f"Error counting {table}: {e}")
            return -1

    # ── reads (for verification) ─────────────────────────────

    def get_all_ids(self, table: str, id_column: str) -> set:
        try:
            s = self._session()
            model_map = {
                "fb_posts": FBPost,
                "fb_comments": FBComment,
            }
            model = model_map.get(table)
            if model is None:
                return set()
            col = getattr(model, id_column)
            ids = [row[0] for row in s.query(col).all()]
            s.close()
            return set(ids)
        except Exception as e:
            logger.error(f"Error reading ids from {table}: {e}")
            return set()
