import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.storage.db import LocalStorage

logger = logging.getLogger(__name__)


class SupabaseStorage:
    """Local-only storage. Name kept for backward compatibility."""

    def __init__(self, local_backup: bool = True):
        self.local = LocalStorage()

    def insert_fb_post(self, post: Dict[str, Any]) -> bool:
        return self.local.insert_fb_post(post)

    def insert_fb_comment(self, comment: Dict[str, Any]) -> bool:
        return self.local.insert_fb_comment(comment)

    def insert_problematica(self, problematica: Dict[str, Any]) -> bool:
        return self.local.insert_problematica(problematica)

    def insert_insight(self, insight: Dict[str, Any]) -> bool:
        return self.local.insert_insight(insight)

    def insert_daily_metric(self, metric: Dict[str, Any]) -> bool:
        return self.local.insert_daily_metric(metric)

    def get_fb_posts(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        return self.local.get_fb_posts(limit=limit, offset=offset)

    def get_fb_post(self, post_id: str) -> Optional[Dict]:
        return self.local.get_fb_post(post_id)

    def get_daily_metrics(self, days: int = 30) -> List[Dict]:
        return self.local.get_daily_metrics(days=days)

    def get_problematicas_by_zone(self, days: int = 30) -> List[Dict]:
        return self.local.get_problematicas_by_zone(days=days)

    def get_insights(self, limit: int = 20) -> List[Dict]:
        return self.local.get_insights(limit=limit)

    def get_zonas(self) -> List[Dict]:
        return self.local.get_zonas()

    def get_topics(self) -> List[Dict]:
        return self.local.get_topics()

    def get_executive_summary(self) -> Dict:
        return self.local.get_executive_summary()

    def get_fb_comments(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        return self.local.get_fb_comments(limit=limit, offset=offset)

    def get_all_posts_paginated(self, fields: str = "post_id", limit: int = 5000) -> list:
        return self.local.get_all_posts_paginated(fields=fields, limit=limit)

    def get_posts_comment_counts(self) -> Dict[str, int]:
        return self.local.get_posts_comment_counts()

    def get_posts_without_comments(self) -> list:
        return self.local.get_posts_without_comments()

    def post_exists(self, post_id: str) -> bool:
        return self.local.post_exists(post_id)

    def update_post_views(self, post_id: str, views_count: int) -> bool:
        return self.local.update_post_views(post_id, views_count)

    def insert_nlp_result(self, data: Dict[str, Any]) -> bool:
        return self.local.insert_nlp_result(data)

    def get_nlp_results(self, item_type: str = None, analysis_type: str = None, limit: int = 5000) -> list:
        return self.local.get_nlp_results(item_type=item_type, analysis_type=analysis_type, limit=limit)

    def get_nlp_result(self, item_type: str, item_id: str, analysis_type: str) -> Optional[dict]:
        return self.local.get_nlp_result(item_type, item_id, analysis_type)

    def count_nlp_pending(self, item_type: str) -> int:
        return self.local.count_nlp_pending(item_type)

    def purge_all(self) -> bool:
        try:
            tables = ["fb_posts", "fb_comments", "problematicas", "insights", "daily_metrics", "nlp_results"]
            for table in tables:
                self.local.purge_table(table)
            logger.info("All data purged")
            return True
        except Exception as e:
            logger.error(f"Error purging data: {e}")
            return False

    def verify_sync(self) -> Dict[str, Dict]:
        return {"note": "Local-only storage. No sync needed."}

    @property
    def client(self):
        raise AttributeError("Supabase client no longer available. Use local storage only.")
