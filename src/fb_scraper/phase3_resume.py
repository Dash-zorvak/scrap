"""
Phase 3 Resume — Complete comment extraction for remaining posts.

Resumes from where Phase 3 was paused (1,100/4,763 posts).
- Fetches comments via Graph API
- Processes sentiment, topic, zona for each comment + replies
- Saves to Supabase + local SQLite
- Checkpoints every 50 posts
"""
import logging
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Set
import requests

from src.fb_scraper.models import FBCommentData
from src.storage.supabase_client import SupabaseStorage
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona
from src.notifications.telegram import TelegramNotifier
from src.config import Config

logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"
CHECKPOINT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "phase3_checkpoint.json")


class Phase3Resumer:
    def __init__(self, access_token: str = None, page_id: str = None):
        cfg = Config()
        self.access_token = access_token or cfg.FB_ACCESS_TOKEN
        self.page_id = page_id or cfg.FB_PAGE_ID or "395582594151511"
        self.storage = SupabaseStorage()
        self.analyzer = SentimentAnalyzer()
        self.notifier = TelegramNotifier()

        self.stats = {
            "posts_processed": 0,
            "comments_scraped": 0,
            "replies_scraped": 0,
            "errors": 0,
            "start_time": time.time(),
        }

    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        url = f"{FB_GRAPH_API}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if "error" in data:
                logger.error(f"Graph API Error: {data['error']}")
                self.stats["errors"] += 1
                return None
            return data
        except Exception as e:
            logger.error(f"Request error: {e}")
            self.stats["errors"] += 1
            return None

    def get_comments(self, post_id: str) -> List[Dict]:
        all_comments = []
        params = {
            "fields": "id,message,created_time,from,like_count,parent_id",
            "limit": 100,
            "filter": "stream",
        }
        data = self._make_request(f"{post_id}/comments", params)
        if data and "data" in data:
            all_comments.extend(data["data"])
            while "paging" in data and "next" in data["paging"]:
                try:
                    after = data["paging"]["next"].split("after=")[1].split("&")[0]
                    params["after"] = after
                except (IndexError, KeyError):
                    break
                data = self._make_request(f"{post_id}/comments", params)
                if data and "data" in data:
                    all_comments.extend(data["data"])
                else:
                    break
        return all_comments

    def get_replies(self, comment_id: str) -> List[Dict]:
        replies = []
        params = {"fields": "id,message,created_time,from,like_count", "limit": 100}
        data = self._make_request(f"{comment_id}/comments", params)
        if data and "data" in data:
            replies = data["data"]
        return replies

    def process_post_comments(self, post_id: str, get_replies: bool = True) -> int:
        comments = self.get_comments(post_id)
        count = 0
        for c in comments:
            try:
                cid = c.get("id", "")
                msg = c.get("message", "") or ""
                if not cid or not msg:
                    continue
                parent_id = c.get("parent_id")
                sentiment, score = self.analyzer.analyze(msg)
                topic = get_main_topic(msg)
                zona = detect_zona(msg)

                record = {
                    "comment_id": cid,
                    "post_id": post_id,
                    "message": msg[:5000],
                    "author_name": c.get("from", {}).get("name", "Unknown") if isinstance(c.get("from"), dict) else "Unknown",
                    "created_time": c.get("created_time"),
                    "like_count": c.get("like_count", 0),
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "topic_category": topic,
                    "zona": zona,
                    "parent_comment_id": None,
                }
                self.storage.insert_fb_comment(record)
                self.stats["comments_scraped"] += 1
                count += 1

                if get_replies and not parent_id:
                    replies = self.get_replies(cid)
                    for r in replies:
                        rid = r.get("id", "")
                        rmsg = r.get("message") or ""
                        if not rid or not rmsg:
                            continue
                        rs, rsc = self.analyzer.analyze(rmsg)
                        rt = get_main_topic(rmsg)
                        rz = detect_zona(rmsg)
                        rrec = {
                            "comment_id": rid,
                            "post_id": post_id,
                            "message": rmsg[:5000],
                            "author_name": r.get("from", {}).get("name", "Unknown") if isinstance(r.get("from"), dict) else "Unknown",
                            "created_time": r.get("created_time"),
                            "like_count": r.get("like_count", 0),
                            "sentiment": rs,
                            "sentiment_score": rsc,
                            "topic_category": rt,
                            "zona": rz,
                            "parent_comment_id": cid,
                        }
                        self.storage.insert_fb_comment(rrec)
                        self.stats["replies_scraped"] += 1
                        self.stats["comments_scraped"] += 1
                        count += 1
            except Exception as e:
                logger.error(f"Error processing comment for {post_id}: {e}")
                self.stats["errors"] += 1
        return count

    def get_posts_remaining(self) -> List[str]:
        """Get post IDs that still need comments."""
        return self.storage.get_posts_without_comments()

    def save_checkpoint(self, processed: int, post_id: str):
        cp = {"last_processed": post_id, "posts_done": processed, "timestamp": datetime.now().isoformat(), "stats": self.stats}
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(cp, f)

    def load_checkpoint(self) -> Optional[Dict]:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
        return None

    def _get_comment_counts_map(self) -> Dict[str, int]:
        return self.storage.get_posts_comment_counts()

    def run(self, get_replies: bool = True, checkpoint_every: int = 50):
        remaining = self.get_posts_remaining()
        if not remaining:
            logger.info("All posts already have comments. Nothing to do.")
            return self.stats

        comment_counts = self._get_comment_counts_map()

        checkpoint = self.load_checkpoint()
        start_idx = 0
        if checkpoint:
            last_id = checkpoint.get("last_processed")
            if last_id and last_id in remaining:
                start_idx = remaining.index(last_id) + 1
                self.stats = checkpoint.get("stats", self.stats)
                logger.info(f"Resuming from post {start_idx}/{len(remaining)} (last: {last_id})")

        posts_to_process = remaining[start_idx:]
        logger.info(f"Starting Phase 3: {len(posts_to_process)} posts to process")
        self.stats["start_time"] = time.time()

        total_posts = len(remaining)
        already_done = self.storage.get_executive_summary().get("fb_posts", 0) - total_posts
        label = "↻ Checkpoint" if checkpoint else "▸ Nuevo"
        self.notifier.send(
            f"📌 *Comentarios Fase 3* {label}\n"
            f"Total: {total_posts + already_done} posts · Pendientes: {len(posts_to_process)}\n"
            f"Con comentarios (API): {len(comment_counts)}"
        )

        skipped_no_comments = 0
        for i, post_id in enumerate(posts_to_process):
            if post_id not in comment_counts:
                skipped_no_comments += 1
                self.stats["posts_processed"] += 1
                continue

            logger.info(f"[{i+1}/{len(posts_to_process)}] Comments for {post_id}")
            count = self.process_post_comments(post_id, get_replies=get_replies)
            self.stats["posts_processed"] += 1

            if (i + 1) % checkpoint_every == 0:
                elapsed = (time.time() - self.stats["start_time"]) / 60
                pct = (i + 1) / len(posts_to_process) * 100
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(posts_to_process) - i - 1) / rate if rate > 0 else 0
                logger.info(f"Checkpoint: {i+1}/{len(posts_to_process)} ({pct:.0f}%), {self.stats['comments_scraped']} comments, {elapsed:.1f} min")
                self.save_checkpoint(i + 1, post_id)
                self.notifier.send(
                    f"📊 *Fase 3* · {pct:.0f}%\n"
                    f"Posts: {i+1}/{len(posts_to_process)} · Saltados: {skipped_no_comments}\n"
                    f"Comentarios: {self.stats['comments_scraped']} · Replies: {self.stats['replies_scraped']}\n"
                    f"Ritmo: {rate:.1f} post/min · ETA: {eta:.0f} min\n"
                    f"⚠ Errores: {self.stats['errors']}"
                )

            time.sleep(0.5)

        elapsed = (time.time() - self.stats["start_time"]) / 60
        logger.info(f"Phase 3 complete: {self.stats['posts_processed']} posts, {self.stats['comments_scraped']} comments, {elapsed:.1f} min")

        self.notifier.send(
            f"✅ *Fase 3 completa*\n"
            f"Posts: {self.stats['posts_processed']} · Saltados (0 comments): {skipped_no_comments}\n"
            f"Comentarios: {self.stats['comments_scraped']} · Replies: {self.stats['replies_scraped']}\n"
            f"Tiempo: {elapsed:.0f} min · Errores: {self.stats['errors']}"
        )

        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)

        return self.stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 3 Resume - Complete comment extraction")
    parser.add_argument("--token", help="FB Access Token")
    parser.add_argument("--page-id", default="395582594151511")
    parser.add_argument("--no-replies", action="store_true", help="Skip reply threads")
    parser.add_argument("--checkpoint-every", type=int, default=50)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    resumer = Phase3Resumer(access_token=args.token, page_id=args.page_id)
    stats = resumer.run(get_replies=not args.no_replies, checkpoint_every=args.checkpoint_every)
    print(f"\nDone: {stats['posts_processed']} posts, {stats['comments_scraped']} comments, {stats['replies_scraped']} replies, {stats['errors']} errors")


if __name__ == "__main__":
    main()
