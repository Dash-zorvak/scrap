#!/usr/bin/env python3
"""
Bulk scraper optimizado para Facebook Graph API.
Tres fases independientes con checkpoint:

Fase 1 (posts):   Mensaje + reacciones + shares (~1s/post)
Fase 2 (views):   Backfill de views_count (~2.5s/post)
Fase 3 (comments): Comentarios + replies (~10-120s/post)
"""

import logging
import time
import requests
import os
import json
from typing import List, Optional
from datetime import datetime

from src.fb_scraper.graph_api_scraper import GraphAPIScraper, FB_GRAPH_API
from src.storage.supabase_client import SupabaseStorage
from src.config import Config
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona

logger = logging.getLogger(__name__)
CHECKPOINT_FILE = "scraper_checkpoint.json"


class BulkFacebookScraper:
    """Scraper optimizado para extracción masiva con reintentos y checkpoint."""

    def __init__(self):
        cfg = Config()
        self.access_token = cfg.FB_ACCESS_TOKEN
        self.page_id = cfg.FB_PAGE_ID or "395582594151511"
        self.page_name = cfg.FB_PAGE_NAME or "Jose Chicas"
        self.storage = SupabaseStorage()
        self.analyzer = SentimentAnalyzer()

    def _request(self, endpoint: str, params: dict = None, retries: int = 2) -> Optional[dict]:
        url = f"{FB_GRAPH_API}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token
        for attempt in range(retries + 1):
            try:
                r = requests.get(url, params=params, timeout=30)
                data = r.json()
                if "error" in data:
                    logger.error(f"API error: {data['error']}")
                    return None
                return data
            except requests.Timeout:
                logger.warning(f"Timeout on {endpoint}, attempt {attempt+1}/{retries+1}")
                time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Request error: {e}")
                return None
        return None

    # ---------- CHECKPOINT ----------

    def _save_checkpoint(self, phase: str, processed: int, total: int):
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump({"phase": phase, "processed": processed, "total": total, "time": datetime.now().isoformat()}, f)

    def _load_checkpoint(self, phase: str) -> int:
        if not os.path.exists(CHECKPOINT_FILE):
            return 0
        try:
            with open(CHECKPOINT_FILE) as f:
                cp = json.load(f)
            if cp.get("phase") == phase:
                return cp.get("processed", 0)
        except:
            pass
        return 0

    # ---------- FASE 1: POSTS ----------

    def get_all_post_ids(self, max_posts: int = 20000) -> List[str]:
        all_ids = []
        params = {"limit": 100}
        page = 0
        while len(all_ids) < max_posts:
            data = self._request(f"{self.page_id}/posts", params)
            if not data or "data" not in data or not data["data"]:
                break
            posts = data["data"]
            all_ids.extend(p["id"] for p in posts)
            page += 1
            if (page + 1) % 5 == 0:
                logger.info(f"Page {page+1}: {len(all_ids)} IDs collected")
            cursor = data.get("paging", {}).get("cursors", {}).get("after")
            if not cursor:
                break
            params["after"] = cursor
            time.sleep(0.5)
        logger.info(f"Total post IDs: {len(all_ids)}")
        return all_ids[:max_posts]

    def _get_post_basic(self, post_id: str) -> Optional[dict]:
        fields = (
            "id,message,created_time,"
            "reactions.type(LIKE).summary(true).as(r_like),"
            "reactions.type(LOVE).summary(true).as(r_love),"
            "reactions.type(HAHA).summary(true).as(r_haha),"
            "reactions.type(WOW).summary(true).as(r_wow),"
            "reactions.type(SAD).summary(true).as(r_sad),"
            "reactions.type(ANGRY).summary(true).as(r_angry),"
            "comments.summary(true),"
            "shares"
        )
        data = self._request(post_id, {"fields": fields})
        if not data:
            return None
        alias_map = {"r_like": "likes_count", "r_love": "loves_count", "r_haha": "hahas_count",
                     "r_wow": "wows_count", "r_sad": "sads_count", "r_angry": "angrys_count"}
        reactions = {}
        for alias, field in alias_map.items():
            s = data.get(alias, {})
            reactions[field] = s.get("summary", {}).get("total_count", 0) if isinstance(s, dict) else 0
        data["reactions_by_type"] = reactions
        return data

    def _save_post(self, post_data: dict) -> bool:
        post_id = post_data.get("id", "")
        message = post_data.get("message", "") or ""
        if not post_id:
            return False
        r = post_data.get("reactions_by_type", {})
        comments = post_data.get("comments", {})
        shares_data = post_data.get("shares", {})
        sentiment, score = self.analyzer.analyze(message)
        topic = get_main_topic(message)
        zona = detect_zona(message)
        record = {
            "post_id": post_id,
            "page_id": self.page_id,
            "page_name": self.page_name,
            "message": message[:10000],
            "created_time": post_data.get("created_time"),
            "likes_count": r.get("likes_count", 0),
            "loves_count": r.get("loves_count", 0),
            "hahas_count": r.get("hahas_count", 0),
            "wows_count": r.get("wows_count", 0),
            "sads_count": r.get("sads_count", 0),
            "angrys_count": r.get("angrys_count", 0),
            "comments_count": comments.get("summary", {}).get("total_count", 0) if isinstance(comments, dict) else 0,
            "shares_count": shares_data.get("count", 0) if isinstance(shares_data, dict) else 0,
            "post_url": f"https://www.facebook.com/{post_id}",
            "sentiment": sentiment,
            "sentiment_score": score,
            "topic_category": topic,
            "zona": zona,
        }
        return self.storage.insert_fb_post(record)

    def phase_1_posts(self, max_posts: int = 20000, checkpoint: int = 50):
        """Fase 1: Solo posts. Sin views, sin comentarios."""
        logger.info("=" * 50)
        logger.info("FASE 1: Posts (reacciones + texto + shares)")
        logger.info("=" * 50)
        post_ids = self.get_all_post_ids(max_posts)
        logger.info(f"Total IDs: {len(post_ids)}")
        start = time.time()
        saved = 0
        errors = 0
        skipped = self._load_checkpoint("phase_1")
        if skipped > 0:
            logger.info(f"Resuming from checkpoint: {skipped} already processed")
        for i, pid in enumerate(post_ids):
            if i < skipped:
                continue
            details = self._get_post_basic(pid)
            if details and self._save_post(details):
                saved += 1
            else:
                errors += 1
            if (i + 1) % checkpoint == 0:
                self._save_checkpoint("phase_1", i + 1, len(post_ids))
                elapsed = time.time() - start
                rate = (i + 1 - skipped) / elapsed if elapsed > 0 else 0
                remaining = (len(post_ids) - i - 1) / rate if rate > 0 else 0
                logger.info(f"  [{i+1}/{len(post_ids)}] saved={saved} errors={errors} | "
                            f"{rate:.1f} posts/s | ETA: {remaining/60:.0f} min")
        elapsed = time.time() - start
        logger.info(f"Fase 1 done: {saved} saved, {errors} errors, {elapsed:.0f}s")
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        return {"saved": saved, "errors": errors, "elapsed": elapsed}

    # ---------- FASE 2: VIEWS ----------

    def _get_post_views(self, post_id: str) -> Optional[int]:
        metrics = ["post_impressions_unique"]
        for metric in metrics:
            data = self._request(f"{post_id}/insights", {"metric": metric})
            if data and "data" in data and data["data"]:
                values = data["data"][0].get("values", [])
                if values:
                    return values[-1].get("value", 0)
        return None

    def _get_all_posts_paginated(self, fields: str = "post_id,views_count", limit: int = 5000) -> list:
        """Fetch all posts using pagination (Supabase max 1000 per request)."""
        all_posts = []
        page_size = 1000
        offset = 0
        while offset < limit:
            remaining = limit - offset
            fetch = min(page_size, remaining)
            r = self.storage.client.table("fb_posts")\
                .select(fields)\
                .order("created_time", desc=True)\
                .range(offset, offset + fetch - 1)\
                .execute()
            batch = r.data or []
            if not batch:
                break
            all_posts.extend(batch)
            offset += len(batch)
            if len(batch) < fetch:
                break
            logger.info(f"  Fetched {len(all_posts)} posts so far...")
        return all_posts

    def phase_2_views(self, max_posts: int = 5000, checkpoint: int = 50):
        """Fase 2: Backfill de views_count para posts existentes."""
        logger.info("=" * 50)
        logger.info("FASE 2: Views (backfill)")
        logger.info("=" * 50)
        posts = self._get_all_posts_paginated("post_id,views_count", max_posts)
        logger.info(f"Total posts to process: {len(posts)}")
        start = time.time()
        updated = 0
        skipped = 0
        errors = 0
        total_views = 0
        start_idx = self._load_checkpoint("phase_2")
        if start_idx > 0:
            logger.info(f"Resuming from checkpoint: {start_idx}")
        for i, post in enumerate(posts):
            if i < start_idx:
                skipped += 1
                continue
            pid = post["post_id"]
            if post.get("views_count", 0) and post["views_count"] > 0:
                skipped += 1
                continue
            views = self._get_post_views(pid)
            if views is not None:
                self.storage.client.table("fb_posts")\
                    .update({"views_count": views})\
                    .eq("post_id", pid)\
                    .execute()
                updated += 1
                total_views += views
            else:
                errors += 1
            if (i + 1) % checkpoint == 0:
                self._save_checkpoint("phase_2", i + 1, len(posts))
                elapsed = time.time() - start
                rate = (i + 1 - start_idx) / elapsed if elapsed > 0 else 0
                remaining = (len(posts) - i - 1) / rate if rate > 0 else 0
                logger.info(f"  [{i+1}/{len(posts)}] updated={updated} errors={errors} skipped={skipped} | "
                            f"views={total_views} | ETA: {remaining/60:.0f} min")
        elapsed = time.time() - start
        logger.info(f"Fase 2 done: {updated} updated, {errors} errors, {total_views} total views, {elapsed:.0f}s")
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        return {"updated": updated, "errors": errors, "views": total_views, "elapsed": elapsed}

    # ---------- FASE 3: COMMENTS ----------

    def _get_comments(self, post_id: str, limit: int = 100) -> List[dict]:
        params = {"fields": "id,message,created_time,from,like_count,parent_id", "limit": min(limit, 100), "filter": "stream"}
        all_comments = []
        data = self._request(f"{post_id}/comments", params)
        if data and "data" in data:
            all_comments.extend(data["data"])
            while "paging" in data and "next" in data["paging"]:
                after = data["paging"]["next"].split("after=")[1].split("&")[0]
                params["after"] = after
                data = self._request(f"{post_id}/comments", params)
                if data and "data" in data:
                    all_comments.extend(data["data"])
                else:
                    break
        return all_comments

    def _get_replies(self, comment_id: str) -> List[dict]:
        params = {"fields": "id,message,created_time,from,like_count", "limit": 100}
        data = self._request(f"{comment_id}/comments", params)
        return data["data"] if data and "data" in data else []

    def _save_comment(self, comment: dict, post_id: str, parent_id: str = None) -> bool:
        cid = comment.get("id", "")
        msg = comment.get("message", "") or ""
        if not cid or not msg:
            return False
        sentiment, score = self.analyzer.analyze(msg)
        topic = get_main_topic(msg)
        zona = detect_zona(msg)
        record = {
            "comment_id": cid,
            "post_id": post_id,
            "message": msg[:5000],
            "author_name": comment.get("from", {}).get("name", "Unknown") if isinstance(comment.get("from"), dict) else "Unknown",
            "created_time": comment.get("created_time"),
            "like_count": comment.get("like_count", 0),
            "parent_comment_id": parent_id,
            "sentiment": sentiment,
            "sentiment_score": score,
            "topic_category": topic,
            "zona": zona,
        }
        return self.storage.insert_fb_comment(record)

    def phase_3_comments(self, batch_size: int = 50, get_replies: bool = True, max_posts: int = None):
        """Fase 3: Comentarios + replies, en lotes checkpointeados."""
        logger.info("=" * 50)
        logger.info("FASE 3: Comments + Replies")
        logger.info("=" * 50)
        r = self.storage.client.table("fb_posts")\
            .select("post_id")\
            .order("created_time", desc=True)\
            .execute()
        all_posts = r.data or []
        if max_posts:
            all_posts = all_posts[:max_posts]
        logger.info(f"Total posts: {len(all_posts)}")
        start = time.time()
        total_comments = 0
        total_replies = 0
        errors = 0
        posts_done = 0
        for i, post in enumerate(all_posts):
            pid = post["post_id"]
            comments = self._get_comments(pid)
            for c in comments:
                ok = self._save_comment(c, pid)
                if ok:
                    total_comments += 1
                    cid = c["id"]
                    if get_replies and not c.get("parent_id"):
                        replies = self._get_replies(cid)
                        for rp in replies:
                            if self._save_comment(rp, pid, parent_id=cid):
                                total_replies += 1
                                total_comments += 1
                else:
                    errors += 1
            posts_done += 1
            if posts_done % batch_size == 0:
                elapsed = time.time() - start
                self._save_checkpoint("phase_3", i + 1, len(all_posts))
                logger.info(f"  [{i+1}/{len(all_posts)} posts] comments={total_comments} "
                            f"replies={total_replies} errors={errors} | {elapsed/60:.1f} min")
        elapsed = time.time() - start
        logger.info(f"Fase 3 done: {total_comments} comments, {total_replies} replies, "
                    f"{errors} errors, {elapsed:.0f}s")
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        return {"comments": total_comments, "replies": total_replies, "errors": errors, "elapsed": elapsed}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    import argparse
    parser = argparse.ArgumentParser(description="Bulk Facebook Scraper - 3 fases")
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="1",
                        help="1=posts, 2=views, 3=comments")
    parser.add_argument("--max", type=int, default=5000, help="Max posts (fase 1 y 2)")
    parser.add_argument("--batch", type=int, default=50, help="Checkpoint cada N items")
    parser.add_argument("--no-replies", action="store_true", help="Saltar replies en fase 3")
    args = parser.parse_args()

    scraper = BulkFacebookScraper()

    if args.phase in ("1", "all"):
        scraper.phase_1_posts(max_posts=args.max, checkpoint=args.batch)

    if args.phase in ("2", "all"):
        scraper.phase_2_views(max_posts=args.max, checkpoint=args.batch)

    if args.phase in ("3", "all"):
        scraper.phase_3_comments(batch_size=args.batch, get_replies=not args.no_replies,
                                 max_posts=args.max if args.phase == "3" else None)


if __name__ == "__main__":
    main()
