#!/usr/bin/env python3
"""
Scraper Resiliente con Deduplicación - Solo Facebook
- No duplica posts aunque use diferentes cuentas
- Continúa desde donde quedó
- Envía notificaciones a Telegram
"""

import time
import logging
from datetime import datetime
from src.config import Config
from src.storage.supabase_client import SupabaseStorage
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona
from src.notifications.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResilientScraper:
    def __init__(self):
        self.cfg = Config()
        self.storage = SupabaseStorage()
        self.analyzer = SentimentAnalyzer()
        self.notifier = TelegramNotifier()

        self.stats = {
            'scraped': 0,
            'duplicates': 0,
            'errors': 0,
            'start_time': None
        }

    def check_and_insert(self, post: dict) -> bool:
        post_id = post.get('post_id')

        try:
            if self.storage.post_exists(post_id):
                self.stats['duplicates'] += 1
                return False

            text = post.get('message', '')

            sentiment, score = self.analyzer.analyze(text)
            topic = get_main_topic(text)
            zona = detect_zona(text)

            post['sentiment'] = sentiment
            post['sentiment_score'] = score
            post['topic_category'] = topic
            post['zona'] = zona

            success = self.storage.insert_fb_post(post)

            if success:
                self.stats['scraped'] += 1
                return True
            return False

        except Exception as e:
            logger.error(f"Error checking/inserting post {post_id}: {e}")
            self.stats['errors'] += 1
            return False

    def scrape_with_checkpoints(self, max_posts: int, batch_callback: int = 50):
        self.notifier.send(f"*Scraper Resiliente INICIADO*\n\n*Target:* {max_posts} posts\n*Deduplicación:* ACTIVA")

        self.stats['start_time'] = time.time()

        count = self._scrape_facebook(max_posts, batch_callback)

        elapsed = (time.time() - self.stats['start_time']) / 60

        self.notifier.send(f"""
*SCRAPING COMPLETADO*

*Nuevos posts:* {self.stats['scraped']}
*Duplicados obviados:* {self.stats['duplicates']}
*Errores:* {self.stats['errors']}
*Tiempo:* {elapsed:.1f} min
        """)

        return self.stats['scraped']

    def _scrape_facebook(self, max_posts: int, batch_callback: int) -> int:
        if not self.cfg.has_facebook_login:
            logger.error("No hay credenciales de Facebook")
            return 0

        from src.fb_scraper.playwright_scraper import FacebookPlaywright

        try:
            scraper = FacebookPlaywright(
                email=self.cfg.FB_EMAIL,
                password=self.cfg.FB_PASSWORD,
                headless=False
            )

            page_name = self.cfg.FB_PAGE_NAME or self.cfg.FB_PAGE_URL

            posts = scraper.scrape_page_posts(
                page_name=page_name,
                max_posts=max_posts
            )

            count = 0
            for post in posts:
                post_dict = {
                    'post_id': post.post_id,
                    'page_id': post.page_id,
                    'page_name': post.page_name,
                    'message': post.message,
                    'created_time': post.created_time.isoformat() if post.created_time else None,
                    'likes_count': post.likes_count,
                    'loves_count': post.loves_count,
                    'hahas_count': post.hahas_count,
                    'wows_count': post.wows_count,
                    'sads_count': post.sads_count,
                    'angrys_count': post.angrys_count,
                    'comments_count': post.comments_count,
                    'shares_count': post.shares_count,
                    'post_url': post.post_url,
                }

                inserted = self.check_and_insert(post_dict)
                count += 1

                if count % batch_callback == 0:
                    elapsed = (time.time() - self.stats['start_time']) / 60
                    self.notifier.send(f"FB: {count}/{len(posts)} | Nuevos: {self.stats['scraped']} | Dup: {self.stats['duplicates']}")

            return self.stats['scraped']

        except Exception as e:
            logger.error(f"Error en scraping FB: {e}")
            self.notifier.notify_error("FB_ERROR", str(e))
            return 0

    def generate_metrics(self):
        from src.analyzer.executive_metrics import ExecutiveMetrics

        metrics_calc = ExecutiveMetrics(self.storage)

        metrics = metrics_calc.generate_daily_metrics("facebook")
        if metrics:
            self.storage.insert_daily_metric(metrics)

        insights = metrics_calc.generate_insights("facebook")
        for insight in insights[:5]:
            self.storage.insert_insight(insight)

        self.notifier.notify_analysis_done(
            platform='facebook',
            posts=self.stats['scraped'],
            insights=10
        )

        return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Scraper Resiliente con Deduplicación (Facebook)')
    parser.add_argument('--max', type=int, default=100, help='Posts objetivo')
    parser.add_argument('--batch', type=int, default=25, help='Notificar cada N posts')

    args = parser.parse_args()

    scraper = ResilientScraper()
    scraper.scrape_with_checkpoints(args.max, args.batch)
    scraper.generate_metrics()

    print(f"\nCompletado: {scraper.stats['scraped']} nuevos, {scraper.stats['duplicates']} duplicados")


if __name__ == '__main__':
    main()
