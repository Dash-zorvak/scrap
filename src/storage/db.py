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


class NLPResult(Base):
    __tablename__ = "nlp_results"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    item_type = sa.Column(sa.Text, nullable=False, index=True)   # "post" | "comment"
    item_id = sa.Column(sa.Text, nullable=False, index=True)      # post_id | comment_id
    analysis_type = sa.Column(sa.Text, nullable=False, index=True) # "emotions" | "entities" | "collocations" | "latent_topic"
    result_json = sa.Column(sa.Text, default="{}")
    model_version = sa.Column(sa.Text, default="1.0")
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
            db_path = os.getenv("FACEBOOK_DB", "")
            if not db_path:
                cfg = Config()
                db_path = os.path.join(cfg.DATA_DIR, "facebook.db")
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

    # ── purge ────────────────────────────────────────────────

    # ── nlp_results ──────────────────────────────────────────

    def insert_nlp_result(self, data: Dict[str, Any]) -> bool:
        try:
            result_json = data.get("result_json", {})
            if not isinstance(result_json, str):
                result_json = json.dumps(result_json)
            obj = NLPResult(
                item_type=data.get("item_type", ""),
                item_id=data.get("item_id", ""),
                analysis_type=data.get("analysis_type", ""),
                result_json=result_json,
                model_version=data.get("model_version", "1.0"),
            )
            s = self._session()
            s.merge(obj)
            s.commit()
            s.close()
            return True
        except Exception as e:
            logger.error(f"Error inserting nlp_result: {e}")
            return False

    def get_nlp_results(self, item_type: str = None, analysis_type: str = None, limit: int = 5000) -> list:
        try:
            s = self._session()
            q = s.query(NLPResult)
            if item_type:
                q = q.filter(NLPResult.item_type == item_type)
            if analysis_type:
                q = q.filter(NLPResult.analysis_type == analysis_type)
            rows = q.order_by(NLPResult.created_at.desc()).limit(limit).all()
            s.close()
            result = []
            for r in rows:
                rj = r.result_json
                if isinstance(rj, str):
                    try:
                        rj = json.loads(rj)
                    except:
                        rj = {}
                result.append({
                    "id": r.id,
                    "item_type": r.item_type,
                    "item_id": r.item_id,
                    "analysis_type": r.analysis_type,
                    "result_json": rj,
                    "model_version": r.model_version,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })
            return result
        except Exception as e:
            logger.error(f"Error reading nlp_results: {e}")
            return []

    def get_nlp_result(self, item_type: str, item_id: str, analysis_type: str) -> Optional[dict]:
        try:
            s = self._session()
            r = s.query(NLPResult).filter(
                NLPResult.item_type == item_type,
                NLPResult.item_id == item_id,
                NLPResult.analysis_type == analysis_type,
            ).first()
            s.close()
            if not r:
                return None
            rj = r.result_json
            if isinstance(rj, str):
                try:
                    rj = json.loads(rj)
                except:
                    rj = {}
            return {
                "id": r.id,
                "item_type": r.item_type,
                "item_id": r.item_id,
                "analysis_type": r.analysis_type,
                "result_json": rj,
                "model_version": r.model_version,
            }
        except Exception as e:
            logger.error(f"Error reading nlp_result: {e}")
            return None

    def count_nlp_pending(self, item_type: str) -> int:
        """Count items that haven't had emotions analysis yet."""
        try:
            s = self._session()
            from sqlalchemy.orm import aliased
            nr = aliased(NLPResult)
            done_ids = s.query(nr.item_id).filter(
                nr.item_type == item_type,
                nr.analysis_type == "emotions",
            ).subquery()
            if item_type == "post":
                pending = s.query(FBPost.post_id).filter(~FBPost.post_id.in_(done_ids)).count()
            elif item_type == "comment":
                pending = s.query(FBComment.comment_id).filter(~FBComment.comment_id.in_(done_ids)).count()
            else:
                pending = 0
            s.close()
            return pending
        except Exception as e:
            logger.error(f"Error counting nlp pending: {e}")
            return 0

    def purge_table(self, table: str) -> bool:
        try:
            s = self._session()
            model_map = {
                "fb_posts": FBPost,
                "fb_comments": FBComment,
                "problematicas": Problema,
                "insights": Insight,
                "daily_metrics": DailyMetric,
                "nlp_results": NLPResult,
            }
            model = model_map.get(table)
            if model is None:
                s.close()
                return False
            s.query(model).delete()
            s.commit()
            s.close()
            logger.info(f"Local purge: {table}")
            return True
        except Exception as e:
            logger.error(f"Local backup error (purge {table}): {e}")
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

    # ── reads (for dashboard & analysis) ─────────────────────

    def get_fb_posts(self, limit: int = 100, offset: int = 0) -> list:
        try:
            s = self._session()
            rows = s.query(FBPost).order_by(FBPost.created_time.desc().nullslast()).offset(offset).limit(limit).all()
            s.close()
            result = []
            for r in rows:
                result.append({
                    "post_id": r.post_id,
                    "page_id": r.page_id,
                    "page_name": r.page_name,
                    "message": r.message,
                    "created_time": r.created_time.isoformat() if r.created_time else None,
                    "likes_count": r.likes_count,
                    "loves_count": r.loves_count,
                    "hahas_count": r.hahas_count,
                    "wows_count": r.wows_count,
                    "sads_count": r.sads_count,
                    "angrys_count": r.angrys_count,
                    "comments_count": r.comments_count,
                    "shares_count": r.shares_count,
                    "views_count": r.views_count,
                    "post_url": r.post_url,
                    "sentiment": r.sentiment,
                    "sentiment_score": r.sentiment_score,
                    "topic_category": r.topic_category,
                    "zona": r.zona,
                    "source": r.source,
                })
            return result
        except Exception as e:
            logger.error(f"Error reading fb_posts: {e}")
            return []

    def get_fb_post(self, post_id: str) -> Optional[dict]:
        try:
            s = self._session()
            r = s.query(FBPost).filter(FBPost.post_id == post_id).first()
            s.close()
            if not r:
                return None
            return {
                "post_id": r.post_id,
                "page_id": r.page_id,
                "page_name": r.page_name,
                "message": r.message,
                "created_time": r.created_time.isoformat() if r.created_time else None,
                "likes_count": r.likes_count,
                "loves_count": r.loves_count,
                "hahas_count": r.hahas_count,
                "wows_count": r.wows_count,
                "sads_count": r.sads_count,
                "angrys_count": r.angrys_count,
                "comments_count": r.comments_count,
                "shares_count": r.shares_count,
                "views_count": r.views_count,
                "post_url": r.post_url,
                "sentiment": r.sentiment,
                "sentiment_score": r.sentiment_score,
                "topic_category": r.topic_category,
                "zona": r.zona,
                "source": r.source,
            }
        except Exception as e:
            logger.error(f"Error reading fb_post {post_id}: {e}")
            return None

    def get_fb_posts_all(self, fields: str = None, limit: int = 5000) -> list:
        try:
            s = self._session()
            query = s.query(FBPost).order_by(FBPost.created_time.desc().nullslast())
            if limit:
                query = query.limit(limit)
            rows = query.all()
            s.close()
            result = []
            for r in rows:
                d = {"post_id": r.post_id}
                if fields:
                    flds = [f.strip() for f in fields.split(",")]
                    if "views_count" in flds:
                        d["views_count"] = r.views_count
                    if "comments_count" in flds:
                        d["comments_count"] = r.comments_count
                result.append(d)
            return result
        except Exception as e:
            logger.error(f"Error reading all fb_posts: {e}")
            return []

    def get_posts_comment_counts(self) -> dict:
        try:
            s = self._session()
            rows = s.query(FBPost.post_id, FBPost.comments_count).all()
            s.close()
            return {r.post_id: r.comments_count for r in rows if r.comments_count and r.comments_count > 0}
        except Exception as e:
            logger.error(f"Error reading comment counts: {e}")
            return {}

    def get_posts_without_comments(self) -> list:
        try:
            s = self._session()
            all_rows = s.query(FBPost.post_id).all()
            all_ids = {r.post_id for r in s.query(FBComment.post_id).distinct().all()}
            s.close()
            return [r.post_id for r in all_rows if r.post_id not in all_ids]
        except Exception as e:
            logger.error(f"Error getting posts without comments: {e}")
            return []

    def post_exists(self, post_id: str) -> bool:
        try:
            s = self._session()
            r = s.query(FBPost.post_id).filter(FBPost.post_id == post_id).first()
            s.close()
            return r is not None
        except Exception as e:
            logger.error(f"Error checking post exists: {e}")
            return False

    def update_post_views(self, post_id: str, views_count: int) -> bool:
        try:
            s = self._session()
            r = s.query(FBPost).filter(FBPost.post_id == post_id).first()
            if r:
                r.views_count = views_count
                s.commit()
            s.close()
            return True
        except Exception as e:
            logger.error(f"Error updating post views: {e}")
            return False

    def get_executive_summary(self) -> dict:
        try:
            s = self._session()
            fb_posts = s.query(FBPost).count()
            fb_comments = s.query(FBComment).count()
            fb_positive = s.query(FBPost).filter(FBPost.sentiment == "positive").count()
            fb_negative = s.query(FBPost).filter(FBPost.sentiment == "negative").count()
            s.close()
            return {
                "fb_posts": fb_posts,
                "fb_comments": fb_comments,
                "fb_positive": fb_positive,
                "fb_negative": fb_negative,
            }
        except Exception as e:
            logger.error(f"Error getting executive summary: {e}")
            return {}

    def get_fb_comments(self, limit: int = 100, offset: int = 0) -> list:
        try:
            s = self._session()
            rows = s.query(FBComment).order_by(FBComment.created_time.desc().nullslast()).offset(offset).limit(limit).all()
            s.close()
            result = []
            for r in rows:
                result.append({
                    "comment_id": r.comment_id,
                    "post_id": r.post_id,
                    "message": r.message,
                    "author_name": r.author_name,
                    "created_time": r.created_time.isoformat() if r.created_time else None,
                    "like_count": r.like_count,
                    "parent_comment_id": r.parent_comment_id,
                    "sentiment": r.sentiment,
                    "sentiment_score": r.sentiment_score,
                    "topic_category": r.topic_category,
                    "zona": r.zona,
                })
            return result
        except Exception as e:
            logger.error(f"Error reading fb_comments: {e}")
            return []

    def get_daily_metrics(self, days: int = 30) -> list:
        try:
            s = self._session()
            from datetime import timedelta, date
            cutoff = date.today() - timedelta(days=days)
            rows = s.query(DailyMetric).filter(DailyMetric.date >= cutoff).order_by(DailyMetric.date.desc()).all()
            s.close()
            result = []
            for r in rows:
                result.append({
                    "platform": r.platform,
                    "date": r.date.isoformat() if r.date else None,
                    "total_posts": r.total_posts,
                    "total_comments": r.total_comments,
                    "total_reactions": r.total_reactions,
                    "positive_pct": r.positive_pct,
                    "negative_pct": r.negative_pct,
                    "neutral_pct": r.neutral_pct,
                    "nsi": r.nsi,
                    "cai": r.cai,
                    "top_topics": r.top_topics if isinstance(r.top_topics, list) else json.loads(r.top_topics or "[]"),
                    "top_problematicas": r.top_problematicas if isinstance(r.top_problematicas, list) else json.loads(r.top_problematicas or "[]"),
                })
            return result
        except Exception as e:
            logger.error(f"Error reading daily_metrics: {e}")
            return []

    def get_zonas(self) -> list:
        try:
            s = self._session()
            rows = s.query(FBPost.zona, sa.func.count(FBPost.zona)).filter(FBPost.zona != "").group_by(FBPost.zona).all()
            s.close()
            return [{"zona": r[0], "count": r[1]} for r in rows]
        except Exception as e:
            logger.error(f"Error reading zonas: {e}")
            return []

    def get_topics(self) -> list:
        try:
            s = self._session()
            rows = s.query(FBPost.topic_category, sa.func.count(FBPost.topic_category)).filter(FBPost.topic_category != "").group_by(FBPost.topic_category).all()
            s.close()
            return [{"topic": r[0], "count": r[1]} for r in rows]
        except Exception as e:
            logger.error(f"Error reading topics: {e}")
            return []

    def get_insights(self, limit: int = 20) -> list:
        try:
            s = self._session()
            rows = s.query(Insight).order_by(Insight.priority.desc()).limit(limit).all()
            s.close()
            result = []
            for r in rows:
                md = r.metric_data
                if isinstance(md, str):
                    try:
                        md = json.loads(md)
                    except:
                        md = {}
                result.append({
                    "id": r.id,
                    "insight_type": r.insight_type,
                    "title": r.title,
                    "description": r.description,
                    "topic": r.topic,
                    "zona": r.zona,
                    "sentiment": r.sentiment,
                    "priority": r.priority,
                    "post_id": r.post_id,
                    "metric_data": md,
                })
            return result
        except Exception as e:
            logger.error(f"Error reading insights: {e}")
            return []

    def get_problematicas_by_zone(self, days: int = 30) -> list:
        try:
            s = self._session()
            from datetime import timedelta, datetime
            cutoff = datetime.now() - timedelta(days=days)
            rows = s.query(Problema).filter(Problema.detected_at >= cutoff).all()
            s.close()
            result = []
            for r in rows:
                result.append({
                    "id": r.id,
                    "platform": r.platform,
                    "post_id": r.post_id,
                    "comment_id": r.comment_id,
                    "topic": r.topic,
                    "zona": r.zona,
                    "message": r.message,
                    "sentiment": r.sentiment,
                    "sentiment_score": r.sentiment_score,
                })
            return result
        except Exception as e:
            logger.error(f"Error reading problematicas: {e}")
            return []

    def get_all_posts_paginated(self, fields: str = "post_id", limit: int = 5000) -> list:
        return self.get_fb_posts_all(fields=fields, limit=limit)
