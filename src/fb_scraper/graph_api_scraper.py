#!/usr/bin/env python3
"""
Graph API Scraper - Extrae posts usando Facebook Graph API
Más estable que scraping HTML, devuelve datos completos.

Extrae:
- Todos los posts con texto completo
- Reacciones por tipo (likes, loves, hahas, wows, sads, angrys)
- Todos los comentarios (incluyendo replies/hilos)
- Número de visualizaciones (views)
- Zona demográfica desde texto del comentario
"""

import logging
import time
import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from src.fb_scraper.models import FBPostData, FBCommentData
from src.storage.supabase_client import SupabaseStorage
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona
from src.notifications.telegram import TelegramNotifier
from src.config import Config

logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"


class GraphAPIScraper:
    """Scraper usando Graph API - más estable que HTML scraping."""

    def __init__(
        self,
        access_token: str = None,
        page_id: str = None,
        page_name: str = None,
    ):
        cfg = Config()
        self.access_token = access_token or cfg.FB_ACCESS_TOKEN or os.getenv("FB_ACCESS_TOKEN")

        # Get page ID: explicit config > from URL
        if page_id:
            self.page_id = page_id
        elif cfg.FB_PAGE_ID:
            self.page_id = cfg.FB_PAGE_ID
        elif "SantaAnaAlcaldia" in cfg.FB_PAGE_URL:
            self.page_id = "SantaAnaAlcaldia"
        else:
            self.page_id = "395582594151511"

        self.page_name = page_name or cfg.FB_PAGE_NAME or "Santa Ana Alcaldía"
        self.base_url = f"{FB_GRAPH_API}/{self.page_id}"
        self.storage = SupabaseStorage()
        self.analyzer = SentimentAnalyzer()
        self.notifier = TelegramNotifier()

        self.stats = {
            "posts_scraped": 0,
            "comments_scraped": 0,
            "replies_scraped": 0,
            "views_total": 0,
            "errors": 0,
            "error_codes": {},
            "start_time": None,
        }

        if not self.access_token:
            raise ValueError("FB_ACCESS_TOKEN no encontrado en .env")

    def _make_request(self, endpoint: str, params: dict = None, count_error: bool = True) -> Optional[dict]:
        """Hace request a Graph API con manejo de errores."""
        url = f"{FB_GRAPH_API}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token

        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if "error" in data:
                code = data["error"].get("code", 0)
                msg = data["error"].get("message", "")[:120]
                if code == 100 and ("does not exist" in msg or "Object does not exist" in msg):
                    logger.debug(f"Post {endpoint} deleted: {msg}")
                else:
                    logger.error(f"Graph API Error ({code}): {msg}")
                    if count_error:
                        self.stats["errors"] += 1
                        if code not in self.stats.get("error_codes", {}):
                            self.stats.setdefault("error_codes", {})[code] = 0
                        self.stats["error_codes"][code] = self.stats["error_codes"].get(code, 0) + 1
                return None

            return data

        except Exception as e:
            logger.error(f"Request error: {e}")
            if count_error:
                self.stats["errors"] += 1
            return None

    def get_posts(self, limit: int = 100, max_pages: int = 100) -> List[Dict]:
        """Obtiene posts desde Graph API - solo IDs para pagination estable."""
        all_posts = []
        
        # Solo campos básicos para evitar "too much data"
        params = {
            "fields": "id,created_time",
            "limit": 100,
        }

        for page_num in range(max_pages):
            if len(all_posts) >= limit:
                break
                
            logger.info(f"Fetching posts page {page_num + 1}... (total: {len(all_posts)})")

            data = self._make_request(f"{self.page_id}/posts", params)

            if not data or "data" not in data:
                logger.warning(f"No data returned on page {page_num + 1}")
                break

            posts = data["data"]
            if not posts:
                logger.warning(f"No more posts on page {page_num + 1}")
                break

            all_posts.extend(posts)
            logger.info(f"  Got {len(posts)} posts (total: {len(all_posts)})")

            # Check for next page using "after" cursor
            if "paging" in data and "cursors" in data.get("paging", {}):
                after_cursor = data["paging"]["cursors"].get("after")
                if after_cursor:
                    params["after"] = after_cursor
                else:
                    break
            else:
                break

            time.sleep(1)  # Rate limiting

        logger.info(f"Total post IDs retrieved: {len(all_posts)}")
        return all_posts

    def get_post_details(self, post_id: str) -> Optional[Dict]:
        """Obtiene detalles completos de un post incluyendo reacciones por tipo y views."""
        fields = (
            "id,message,created_time,"
            "permalink_url,"
            "attachments{title,description,url,type},"
            "reactions.summary(true),"
            "comments.summary(true),"
            "shares"
        )

        data = self._make_request(post_id, {"fields": fields})
        if not data:
            return None

        reactions_by_type = self._get_reactions_by_type(post_id)
        data["reactions_by_type"] = reactions_by_type

        views = self._get_post_views(post_id)
        data["views_count"] = views or 0

        return data

    def _get_reactions_by_type(self, post_id: str) -> Dict[str, int]:
        """Extrae reacciones por tipo. No cuenta errores (es esperado que
        algunos tipos no estén disponibles)."""
        url = f"{FB_GRAPH_API}/{post_id}"
        reaction_fields = [
            "reactions.type(LIKE).summary(true).as(r_like)",
            "reactions.type(LOVE).summary(true).as(r_love)",
            "reactions.type(HAHA).summary(true).as(r_haha)",
            "reactions.type(WOW).summary(true).as(r_wow)",
            "reactions.type(SAD).summary(true).as(r_sad)",
            "reactions.type(ANGRY).summary(true).as(r_angry)",
        ]
        data = None
        try:
            resp = requests.get(url, params={"fields": ",".join(reaction_fields), "access_token": self.access_token}, timeout=15)
            d = resp.json()
            if "error" not in d:
                data = d
        except Exception:
            pass

        counts = {}
        if data:
            # Map alias names to our field names
            alias_map = {
                "r_like": "likes_count",
                "r_love": "loves_count",
                "r_haha": "hahas_count",
                "r_wow": "wows_count",
                "r_sad": "sads_count",
                "r_angry": "angrys_count",
            }
            for alias, field_name in alias_map.items():
                summary = data.get(alias, {})
                if isinstance(summary, dict):
                    counts[field_name] = summary.get("summary", {}).get("total_count", 0)
                else:
                    counts[field_name] = 0
        else:
            for field_name in ["likes_count", "loves_count", "hahas_count", "wows_count", "sads_count", "angrys_count"]:
                counts[field_name] = 0

        return counts

    def _get_post_views(self, post_id: str) -> Optional[int]:
        """Obtiene número de visualizaciones del post usando read_insights.
        No cuenta errores de insights como errores del scraper (es esperado que
        muchas métricas no estén disponibles)."""
        url = f"{FB_GRAPH_API}/{post_id}/insights"
        metrics = ["post_impressions", "post_impressions_unique", "post_views", "post_views_unique"]
        for metric in metrics:
            try:
                resp = requests.get(url, params={"metric": metric, "access_token": self.access_token}, timeout=15)
                data = resp.json()
                if "error" not in data and "data" in data and len(data["data"]) > 0:
                    values = data["data"][0].get("values", [])
                    if values:
                        return values[-1].get("value", 0)
            except Exception:
                pass
        return None

    def get_comments(self, post_id: str, limit: int = 100) -> List[Dict]:
        """Obtiene comentarios de un post incluyendo replies/hilos."""
        all_comments = []

        # Get top-level comments
        params = {
            "fields": "id,message,created_time,from,like_count,parent_id",
            "limit": min(limit, 100),
            "filter": "stream",
        }

        # First batch
        data = self._make_request(f"{post_id}/comments", params)
        if data and "data" in data:
            all_comments.extend(data["data"])

            # Pagination for more comments
            while "paging" in data and "next" in data["paging"]:
                after_match = data["paging"]["next"].split("after=")[1].split("&")[0]
                params["after"] = after_match
                data = self._make_request(f"{post_id}/comments", params)
                if data and "data" in data:
                    all_comments.extend(data["data"])
                else:
                    break

        return all_comments

    def get_comment_replies(self, comment_id: str, limit: int = 100) -> List[Dict]:
        """Obtiene replies (respuestas) de un comentario."""
        replies = []
        params = {
            "fields": "id,message,created_time,from,like_count",
            "limit": min(limit, 100),
        }

        data = self._make_request(f"{comment_id}/comments", params)
        if data and "data" in data:
            replies = data["data"]

        return replies

    def process_post(self, post_data: Dict) -> bool:
        """Procesa un post y lo guarda en Supabase."""
        try:
            post_id = post_data.get("id", "")
            message = post_data.get("message", "") or ""

            if not post_id:
                return False

            # Extract reactions by type
            reactions_by_type = post_data.get("reactions_by_type", {})
            likes_count = reactions_by_type.get("likes_count", 0)
            loves_count = reactions_by_type.get("loves_count", 0)
            hahas_count = reactions_by_type.get("hahas_count", 0)
            wows_count = reactions_by_type.get("wows_count", 0)
            sads_count = reactions_by_type.get("sads_count", 0)
            angrys_count = reactions_by_type.get("angrys_count", 0)

            # If no breakdown, use total
            if likes_count == 0:
                reactions = post_data.get("reactions", {})
                likes_count = reactions.get("summary", {}).get("total_count", 0) if isinstance(reactions, dict) else 0

            # Extract comments count
            comments = post_data.get("comments", {})
            comments_count = comments.get("summary", {}).get("total_count", 0) if isinstance(comments, dict) else 0

            # Extract shares
            shares_data = post_data.get("shares", {})
            shares_count = shares_data.get("count", 0) if isinstance(shares_data, dict) else 0

            # Extract views
            views_count = post_data.get("views_count", 0)

            # Use actual permalink_url from API, fallback to constructed URL
            post_url = post_data.get("permalink_url", "") or f"https://www.facebook.com/{post_id}"

            # Analyze sentiment
            sentiment, score = self.analyzer.analyze(message)
            topic = get_main_topic(message)
            zona = detect_zona(message)

            post_record = {
                "post_id": post_id,
                "page_id": self.page_id,
                "page_name": self.page_name,
                "message": message[:10000],
                "created_time": post_data.get("created_time"),
                "likes_count": likes_count,
                "loves_count": loves_count,
                "hahas_count": hahas_count,
                "wows_count": wows_count,
                "sads_count": sads_count,
                "angrys_count": angrys_count,
                "comments_count": comments_count,
                "shares_count": shares_count,
                "views_count": views_count,
                "post_url": post_url,
                "sentiment": sentiment,
                "sentiment_score": score,
                "topic_category": topic,
                "zona": zona,
            }

            success = self.storage.insert_fb_post(post_record)

            if success:
                self.stats["posts_scraped"] += 1
                if views_count:
                    self.stats["views_total"] += views_count

            return success

        except Exception as e:
            logger.error(f"Error processing post: {e}")
            self.stats["errors"] += 1
            return False

    def process_comments(self, post_id: str, get_replies: bool = True):
        """Procesa comentarios de un post incluyendo hilos (replies) con parent_comment_id."""
        comments = self.get_comments(post_id)

        for comment_data in comments:
            try:
                comment_id = comment_data.get("id", "")
                message = comment_data.get("message", "") or ""
                parent_id = comment_data.get("parent_id", None)

                if not comment_id or not message:
                    continue

                sentiment, score = self.analyzer.analyze(message)
                topic = get_main_topic(message)
                zona = detect_zona(message)

                comment_record = {
                    "comment_id": comment_id,
                    "post_id": post_id,
                    "message": message[:5000],
                    "author_name": comment_data.get("from", {}).get("name", "Unknown") if isinstance(comment_data.get("from"), dict) else "Unknown",
                    "created_time": comment_data.get("created_time"),
                    "like_count": comment_data.get("like_count", 0),
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "topic_category": topic,
                    "zona": zona,
                    "parent_comment_id": None,
                }

                self.storage.insert_fb_comment(comment_record)
                self.stats["comments_scraped"] += 1

                if get_replies and not parent_id:
                    replies = self.get_comment_replies(comment_id)
                    for reply_data in replies:
                        try:
                            reply_id = reply_data.get("id", "")
                            reply_message = reply_data.get("message") or ""

                            if not reply_id or not reply_message:
                                continue

                            reply_sentiment, reply_score = self.analyzer.analyze(reply_message)
                            reply_topic = get_main_topic(reply_message)
                            reply_zona = detect_zona(reply_message)

                            reply_record = {
                                "comment_id": reply_id,
                                "post_id": post_id,
                                "message": reply_message[:5000],
                                "author_name": reply_data.get("from", {}).get("name", "Unknown") if isinstance(reply_data.get("from"), dict) else "Unknown",
                                "created_time": reply_data.get("created_time"),
                                "like_count": reply_data.get("like_count", 0),
                                "sentiment": reply_sentiment,
                                "sentiment_score": reply_score,
                                "topic_category": reply_topic,
                                "zona": reply_zona,
                                "parent_comment_id": comment_id,
                            }

                            self.storage.insert_fb_comment(reply_record)
                            self.stats["replies_scraped"] += 1
                            self.stats["comments_scraped"] += 1

                        except Exception as e:
                            logger.error(f"Error processing reply: {e}")

            except Exception as e:
                logger.error(f"Error processing comment: {e}")

    def _check_token(self) -> bool:
        """Verifica que el token sea válido antes de empezar."""
        try:
            resp = requests.get(
                f"{FB_GRAPH_API}/me",
                params={"access_token": self.access_token},
                timeout=10,
            )
            data = resp.json()
            if "error" in data:
                logger.error(f"Token inválido: {data['error']}")
                return False
            logger.info(f"Token OK — app: {data.get('name', 'me')}, id: {data.get('id', '?')}")
            return True
        except Exception as e:
            logger.error(f"Error verificando token: {e}")
            return False

    def scrape(self, max_posts: int = 1000, get_comments: bool = True, get_replies: bool = True):
        """Ejecuta scraping completo."""
        if not self._check_token():
            logger.error("Token inválido o expirado. Deteniendo scrape.")
            return self.stats

        self.stats["start_time"] = time.time()

        # Step 1: Get post IDs (lightweight, good pagination)
        logger.info("Step 1: Fetching post IDs...")
        post_ids = self.get_posts(limit=max_posts)

        # Get ALL posts (no date filter - for full extraction)
        logger.info(f"Posts retrieved (all): {len(post_ids)}")

        self.notifier.send(
            f"🚀 *Fase 1 — Graph API*\n"
            f"Página: {self.page_name}\n"
            f"Target: {max_posts} posts · {len(post_ids)} obtenidos\n"
            f"Comentarios: {'Sí' if get_comments else 'No'} · Replies: {'Sí' if get_replies else 'No'}"
        )

        # Step 2: Get full details for each post
        for i, post_id_data in enumerate(post_ids):
            post_id = post_id_data.get("id", "")
            if not post_id:
                continue

            logger.info(f"Fetching details for post {i+1}/{len(post_ids)}: {post_id}")

            # Get full post details (errors already counted inside get_post_details)
            full_post = self.get_post_details(post_id)
            if full_post:
                success = self.process_post(full_post)

                comments_before = self.stats["comments_scraped"]
                if success and get_comments:
                    self.process_comments(post_id, get_replies=get_replies)
                comments_this_post = self.stats["comments_scraped"] - comments_before
            else:
                comments_this_post = 0

            # Early notification: post 1, then every 5, or when a post has many comments
            if i == 0 and comments_this_post > 0:
                self.notifier.send(
                    f"▶️ *Fase 1 iniciada* — {self.page_name}\n"
                    f"Post 1: +{comments_this_post} comentarios · {self.stats['comments_scraped']} total\n"
                    f"Ritmo: esperando primer lote de 5 posts..."
                )
            if (i + 1) % 5 == 0 or comments_this_post > 200:
                elapsed = (time.time() - self.stats["start_time"]) / 60
                pct = (i + 1) / len(post_ids) * 100
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (len(post_ids) - i - 1) / rate if rate > 0 else 0
                err_info = f"⚠ Errores: {self.stats['errors']}"
                if self.stats.get("error_codes"):
                    top_codes = sorted(self.stats["error_codes"].items(), key=lambda x: -x[1])[:2]
                    err_info += " (" + ", ".join(f"#{c}={n}" for c, n in top_codes) + ")"
                self.notifier.send(
                    f"📊 *Fase 1* · {self.page_name}\n"
                    f"Posts: {self.stats['posts_scraped']}/{len(post_ids)} ({pct:.0f}%)\n"
                    f"Coment: {self.stats['comments_scraped']} · Replies: {self.stats['replies_scraped']}\n"
                    f"Views: {self.stats['views_total']:,} · {err_info}\n"
                    f"Ritmo: {rate:.1f} post/min · ETA: {eta:.0f} min\n"
                    f"Post actual: +{comments_this_post} coment"
                )

        elapsed = (time.time() - self.stats["start_time"]) / 60

        err_info = f"Errores: {self.stats['errors']}"
        if self.stats.get("error_codes"):
            top_codes = sorted(self.stats["error_codes"].items(), key=lambda x: -x[1])[:3]
            err_info += " (" + ", ".join(f"#{c}={n}" for c, n in top_codes) + ")"

        self.notifier.send(
            f"✅ *Fase 1 completa* — {self.page_name}\n"
            f"Posts: {self.stats['posts_scraped']} · Comentarios: {self.stats['comments_scraped']}\n"
            f"Replies: {self.stats['replies_scraped']} · Views: {self.stats['views_total']:,}\n"
            f"Tiempo: {elapsed:.0f} min · {err_info}"
        )

        return self.stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Graph API Scraper")
    parser.add_argument("--token", help="Page Access Token (or set FB_ACCESS_TOKEN in .env)")
    parser.add_argument("--page-id", default="395582594151511", help="Facebook Page ID (numeric)")
    parser.add_argument("--page-name", default="Santa Ana Alcaldía", help="Page name")
    parser.add_argument("--max", type=int, default=10000, help="Max posts")
    parser.add_argument("--comments", action="store_true", default=True, help="Extract comments (default: True)")
    parser.add_argument("--replies", action="store_true", default=True, help="Extract comment replies (default: True)")

    args = parser.parse_args()

    scraper = GraphAPIScraper(
        access_token=args.token,
        page_id=args.page_id,
        page_name=args.page_name,
    )

    stats = scraper.scrape(max_posts=args.max, get_comments=args.comments, get_replies=args.replies)
    print(f"\nCompleted: {stats}")


if __name__ == "__main__":
    main()