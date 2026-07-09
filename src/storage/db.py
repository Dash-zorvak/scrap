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
    cares_count = sa.Column(sa.Integer, default=0)
    hahas_count = sa.Column(sa.Integer, default=0)
    wows_count = sa.Column(sa.Integer, default=0)
    sads_count = sa.Column(sa.Integer, default=0)
    angrys_count = sa.Column(sa.Integer, default=0)
    comments_count = sa.Column(sa.Integer, default=0)
    shares_count = sa.Column(sa.Integer, default=0)
    views_count = sa.Column(sa.Integer, default=0)
    post_url = sa.Column(sa.Text, default="")
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
    scraped_at = sa.Column(sa.DateTime, server_default=sa.func.now())


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
                message=(post.get("message") or "")[:10000],
                created_time=self._parse_dt(post.get("created_time")),
                likes_count=post.get("likes_count", 0),
                loves_count=post.get("loves_count", 0),
                cares_count=post.get("cares_count", 0),
                hahas_count=post.get("hahas_count", 0),
                wows_count=post.get("wows_count", 0),
                sads_count=post.get("sads_count", 0),
                angrys_count=post.get("angrys_count", 0),
                comments_count=post.get("comments_count", 0),
                shares_count=post.get("shares_count", 0),
                views_count=post.get("views_count", 0),
                post_url=post.get("post_url", ""),
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
                message=(comment.get("message") or "")[:5000],
                author_name=comment.get("author_name", ""),
                created_time=self._parse_dt(comment.get("created_time")),
                like_count=comment.get("like_count", 0),
                parent_comment_id=comment.get("parent_comment_id"),
            )
            s = self._session()
            s.merge(obj)
            s.commit()
            s.close()
            return True
        except Exception as e:
            logger.error(f"Local backup error (fb_comment): {e}")
            return False

    def purge_table(self, table: str) -> bool:
        try:
            s = self._session()
            model_map = {
                "fb_posts": FBPost,
                "fb_comments": FBComment,
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
                    "cares_count": r.cares_count,
                    "hahas_count": r.hahas_count,
                    "wows_count": r.wows_count,
                    "sads_count": r.sads_count,
                    "angrys_count": r.angrys_count,
                    "comments_count": r.comments_count,
                    "shares_count": r.shares_count,
                    "views_count": r.views_count,
                    "post_url": r.post_url,
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
                })
            return result
        except Exception as e:
            logger.error(f"Error reading fb_comments: {e}")
            return []

    def get_all_posts_paginated(self, fields: str = "post_id", limit: int = 5000) -> list:
        return self.get_fb_posts_all(fields=fields, limit=limit)
