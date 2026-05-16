import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from src.config import Config

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        cfg = Config()
        _supabase_client = create_client(cfg.SUPABASE_URL, cfg.SUPABASE_KEY)
        logger.info("Supabase client initialized")
    return _supabase_client


class SupabaseStorage:
    def __init__(self):
        self.client = get_supabase_client()

    def insert_fb_post(self, post: Dict[str, Any]) -> bool:
        try:
            data = {
                "post_id": post.get("post_id"),
                "page_id": post.get("page_id", ""),
                "page_name": post.get("page_name", ""),
                "message": post.get("message", "")[:10000],
                "created_time": post.get("created_time"),
                "likes_count": post.get("likes_count", 0),
                "loves_count": post.get("loves_count", 0),
                "hahas_count": post.get("hahas_count", 0),
                "wows_count": post.get("wows_count", 0),
                "sads_count": post.get("sads_count", 0),
                "angrys_count": post.get("angrys_count", 0),
                "comments_count": post.get("comments_count", 0),
                "shares_count": post.get("shares_count", 0),
                "post_url": post.get("post_url", ""),
                "sentiment": post.get("sentiment", ""),
                "sentiment_score": post.get("sentiment_score", 0),
                "topic_category": post.get("topic_category", ""),
                "zona": post.get("zona", ""),
            }
            self.client.table("fb_posts").upsert(data, on_conflict="post_id").execute()
            return True
        except Exception as e:
            logger.error(f"Error inserting FB post: {e}")
            return False

    def insert_tt_post(self, post: Dict[str, Any]) -> bool:
        try:
            data = {
                "video_id": post.get("video_id"),
                "username": post.get("username", ""),
                "description": post.get("description", "")[:10000],
                "create_time": post.get("create_time"),
                "likes_count": post.get("likes_count", 0),
                "comments_count": post.get("comments_count", 0),
                "shares_count": post.get("shares_count", 0),
                "views_count": post.get("views_count", 0),
                "video_url": post.get("video_url", ""),
                "sentiment": post.get("sentiment", ""),
                "sentiment_score": post.get("sentiment_score", 0),
                "topic_category": post.get("topic_category", ""),
                "zona": post.get("zona", ""),
            }
            self.client.table("tt_posts").upsert(data, on_conflict="video_id").execute()
            return True
        except Exception as e:
            logger.error(f"Error inserting TT post: {e}")
            return False

    def insert_fb_comment(self, comment: Dict[str, Any]) -> bool:
        try:
            data = {
                "comment_id": comment.get("comment_id"),
                "post_id": comment.get("post_id", ""),
                "message": comment.get("message", "")[:5000],
                "author_name": comment.get("author_name", ""),
                "created_time": comment.get("created_time"),
                "like_count": comment.get("like_count", 0),
                "sentiment": comment.get("sentiment", ""),
                "sentiment_score": comment.get("sentiment_score", 0),
                "topic_category": comment.get("topic_category", ""),
                "zona": comment.get("zona", ""),
            }
            self.client.table("fb_comments").upsert(data, on_conflict="comment_id").execute()
            return True
        except Exception as e:
            logger.error(f"Error inserting FB comment: {e}")
            return False

    def insert_tt_comment(self, comment: Dict[str, Any]) -> bool:
        try:
            data = {
                "comment_id": comment.get("comment_id"),
                "video_id": comment.get("video_id", ""),
                "message": comment.get("message", "")[:5000],
                "author_name": comment.get("author_name", ""),
                "create_time": comment.get("create_time"),
                "like_count": comment.get("like_count", 0),
                "sentiment": comment.get("sentiment", ""),
                "sentiment_score": comment.get("sentiment_score", 0),
                "topic_category": comment.get("topic_category", ""),
                "zona": comment.get("zona", ""),
            }
            self.client.table("tt_comments").upsert(data, on_conflict="comment_id").execute()
            return True
        except Exception as e:
            logger.error(f"Error inserting TT comment: {e}")
            return False

    def insert_problematica(self, problematica: Dict[str, Any]) -> bool:
        try:
            data = {
                "platform": problematica.get("platform", ""),
                "post_id": problematica.get("post_id", ""),
                "comment_id": problematica.get("comment_id", ""),
                "topic": problematica.get("topic", ""),
                "zona": problematica.get("zona", ""),
                "message": problematica.get("message", ""),
                "sentiment": problematica.get("sentiment", ""),
                "sentiment_score": problematica.get("sentiment_score", 0),
            }
            self.client.table("problematicas").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error inserting problematica: {e}")
            return False

    def insert_insight(self, insight: Dict[str, Any]) -> bool:
        try:
            data = {
                "insight_type": insight.get("insight_type", ""),
                "title": insight.get("title", ""),
                "description": insight.get("description", ""),
                "topic": insight.get("topic", ""),
                "zona": insight.get("zona", ""),
                "sentiment": insight.get("sentiment", ""),
                "priority": insight.get("priority", 0),
                "post_id": insight.get("post_id", ""),
                "metric_data": insight.get("metric_data", {}),
            }
            self.client.table("insights").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error inserting insight: {e}")
            return False

    def insert_daily_metric(self, metric: Dict[str, Any]) -> bool:
        try:
            data = {
                "platform": metric.get("platform", ""),
                "date": metric.get("date", datetime.now().date()),
                "total_posts": metric.get("total_posts", 0),
                "total_comments": metric.get("total_comments", 0),
                "total_reactions": metric.get("total_reactions", 0),
                "positive_pct": metric.get("positive_pct", 0),
                "negative_pct": metric.get("negative_pct", 0),
                "neutral_pct": metric.get("neutral_pct", 0),
                "nsi": metric.get("nsi", 0),
                "cai": metric.get("cai", 0),
                "top_topics": metric.get("top_topics", []),
                "top_problematicas": metric.get("top_problematicas", []),
            }
            self.client.table("daily_metrics").upsert(
                data, on_conflict="platform,date"
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error inserting daily metric: {e}")
            return False

    def get_fb_posts(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        try:
            result = (
                self.client.table("fb_posts")
                .select("*")
                .order("created_time", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting FB posts: {e}")
            return []

    def get_tt_posts(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        try:
            result = (
                self.client.table("tt_posts")
                .select("*")
                .order("create_time", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting TT posts: {e}")
            return []

    def get_daily_metrics(self, platform: str = "all", days: int = 30) -> List[Dict]:
        try:
            if platform == "all":
                result = (
                    self.client.table("daily_metrics")
                    .select("*")
                    .order("date", desc=True)
                    .limit(days * 2)
                    .execute()
                )
            else:
                result = (
                    self.client.table("daily_metrics")
                    .select("*")
                    .eq("platform", platform)
                    .order("date", desc=True)
                    .limit(days)
                    .execute()
                )
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting daily metrics: {e}")
            return []

    def get_problematicas_by_zone(self, days: int = 30) -> List[Dict]:
        try:
            result = (
                self.client.table("problematicas")
                .select("*")
                .gte("detected_at", datetime.now().isoformat())
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting problematicas: {e}")
            return []

    def get_insights(self, limit: int = 20) -> List[Dict]:
        try:
            result = (
                self.client.table("insights")
                .select("*")
                .order("priority", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting insights: {e}")
            return []

    def get_zonas(self) -> List[Dict]:
        try:
            result = self.client.table("zonas").select("*").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting zonas: {e}")
            return []

    def get_topics(self) -> List[Dict]:
        try:
            result = self.client.table("topics").select("*").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting topics: {e}")
            return []

    def get_executive_summary(self) -> Dict:
        try:
            fb_count = (
                self.client.table("fb_posts").select("id", count="exact").execute().count
            )
            tt_count = (
                self.client.table("tt_posts").select("id", count="exact").execute().count
            )
            fb_comments = (
                self.client.table("fb_comments")
                .select("id", count="exact")
                .execute().count
            )
            tt_comments = (
                self.client.table("tt_comments")
                .select("id", count="exact")
                .execute().count
            )

            fb_positive = (
                self.client.table("fb_posts")
                .select("id", count="exact")
                .eq("sentiment", "positive")
                .execute().count
            )
            fb_negative = (
                self.client.table("fb_posts")
                .select("id", count="exact")
                .eq("sentiment", "negative")
                .execute().count
            )

            tt_positive = (
                self.client.table("tt_posts")
                .select("id", count="exact")
                .eq("sentiment", "positive")
                .execute().count
            )
            tt_negative = (
                self.client.table("tt_posts")
                .select("id", count="exact")
                .eq("sentiment", "negative")
                .execute().count
            )

            return {
                "fb_posts": fb_count,
                "tt_posts": tt_count,
                "fb_comments": fb_comments,
                "tt_comments": tt_comments,
                "fb_positive": fb_positive,
                "fb_negative": fb_negative,
                "tt_positive": tt_positive,
                "tt_negative": tt_negative,
            }
        except Exception as e:
            logger.error(f"Error getting executive summary: {e}")
            return {}