#!/usr/bin/env python3
"""
Pipeline de Scraping en Tiempo Real con Notificaciones - Solo Facebook
Ejecuta scraping y envía alertas instantáneas a Telegram
"""

import time
import logging
from datetime import datetime
from src.config import Config
from src.storage.supabase_client import SupabaseStorage
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona, extract_problematicas
from src.notifications.telegram import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScraperPipeline:
    def __init__(self, max_posts: int = 100, batch_size: int = 10):
        self.cfg = Config()
        self.storage = SupabaseStorage()
        self.analyzer = SentimentAnalyzer()
        self.notifier = TelegramNotifier()
        self.max_posts = max_posts
        self.batch_size = batch_size

        self.stats = {
            'fb_scraped': 0,
            'fb_errors': 0,
            'start_time': None,
            'last_notification': None
        }

    def notify_progress(self, current: int, total: int, force: bool = False):
        now = time.time()

        should_notify = (
            force or
            current == total or
            (now - (self.stats.get('last_notification', 0)) > 30)
        )

        if should_notify and current > 0:
            elapsed = (now - self.stats['start_time']) / 60 if self.stats['start_time'] else 0
            self.stats['last_notification'] = now

            msg = f"""
*Facebook Scraping*

*Progreso:* {current}/{total}
*Total scrapeado:* {self.stats['fb_scraped']}
*Tiempo:* {elapsed:.1f} min
*Errores:* {self.stats['fb_errors']}
            """
            self.notifier.send(msg)

    def process_post(self, post: dict) -> bool:
        try:
            text = post.get('message', '')

            sentiment, score = self.analyzer.analyze(text)
            topic = get_main_topic(text)
            zona = detect_zona(text)

            post_data = {
                'post_id': post.get('post_id', ''),
                'page_id': post.get('page_id', ''),
                'page_name': post.get('page_name', ''),
                'message': post.get('message', '')[:10000],
                'created_time': post.get('created_time'),
                'likes_count': post.get('likes_count', 0),
                'loves_count': post.get('loves_count', 0),
                'hahas_count': post.get('hahas_count', 0),
                'wows_count': post.get('wows_count', 0),
                'sads_count': post.get('sads_count', 0),
                'angrys_count': post.get('angrys_count', 0),
                'comments_count': post.get('comments_count', 0),
                'shares_count': post.get('shares_count', 0),
                'views_count': post.get('views_count', 0),
                'post_url': post.get('post_url', ''),
                'sentiment': sentiment,
                'sentiment_score': score,
                'topic_category': topic,
                'zona': zona,
            }

            success = self.storage.insert_fb_post(post_data)

            if text and topic:
                problematicas = extract_problematicas(text, sentiment)
                for prob in problematicas:
                    self.storage.insert_problematica({
                        'platform': 'facebook',
                        'post_id': post.get('post_id', ''),
                        'topic': prob.get('topic', ''),
                        'zona': prob.get('zona', ''),
                        'message': prob.get('text_preview', ''),
                        'sentiment': sentiment,
                        'sentiment_score': score,
                    })

            return success

        except Exception as e:
            logger.error(f"Error processing post: {e}")
            return False

    def scrape_facebook(self, max_posts: int = None) -> int:
        max_posts = max_posts or self.max_posts

        if not self.cfg.has_facebook_login:
            logger.error("No hay credenciales de Facebook")
            self.notifier.notify_error("FB_CONFIG", "No hay credenciales configuradas")
            return 0

        self.notifier.send(f"*Facebook Scraping INICIADO*\n\n*Target:* {max_posts} posts\n*Cuenta:* {self.cfg.FB_EMAIL}")

        from src.fb_scraper.playwright_scraper import FacebookPlaywright

        try:
            scraper = FacebookPlaywright(
                email=self.cfg.FB_EMAIL,
                password=self.cfg.FB_PASSWORD,
                proxy_url=self.cfg.PROXY_URL,
            )

            page_name = self.cfg.FB_PAGE_NAME or self.cfg.FB_PAGE_URL
            self.stats['start_time'] = time.time()

            def progress_callback(current: int, total: int):
                self.notify_progress(current, total)

            posts = scraper.scrape_page_posts(
                page_name=page_name,
                max_posts=max_posts,
                progress_callback=progress_callback,
            )

            count = 0
            for i, post in enumerate(posts):
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

                if self.process_post(post_dict):
                    count += 1
                    self.stats['fb_scraped'] = count

                if count % 50 == 0:
                    self.notify_progress(count, len(posts), force=True)

            self.notify_progress(count, len(posts), force=True)
            self.notifier.notify_scraping_complete('facebook', count, len(posts))

            logger.info(f"Facebook: {count} posts guardados")
            return count

        except Exception as e:
            logger.error(f"Error en Facebook scraping: {e}")
            self.notifier.notify_error("FB_SCRAPER", str(e))
            self.stats['fb_errors'] += 1
            return 0

    def run_full_scrape(self, fb_target: int = 100):
        start = time.time()

        self.notifier.send(f"""
*SCRAPEO INICIADO*

*Facebook:* {fb_target} posts objetivo
*Inicio:* {datetime.now().strftime('%H:%M')}
        """)

        fb_count = self.scrape_facebook(fb_target)

        elapsed = (time.time() - start) / 60

        self.generate_metrics()

        summary = self.storage.get_executive_summary()

        self.notifier.send(f"""
*SCRAPEO COMPLETADO*

*Facebook:* {fb_count} posts
*Tiempo:* {elapsed:.1f} min

*Sentiment FB:*
Positivos: {summary.get('fb_positive', 0)}
Negativos: {summary.get('fb_negative', 0)}
        """)

        return fb_count

    def generate_metrics(self):
        from src.analyzer.executive_metrics import ExecutiveMetrics

        metrics_calc = ExecutiveMetrics(self.storage)

        fb_metrics = metrics_calc.generate_daily_metrics('facebook')
        if fb_metrics:
            self.storage.insert_daily_metric(fb_metrics)

        fb_insights = metrics_calc.generate_insights('facebook')
        for insight in fb_insights[:5]:
            self.storage.insert_insight(insight)

        logger.info("Métricas e insights generados")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Scraper Pipeline con Notificaciones (Facebook)')
    parser.add_argument('--fb-target', type=int, default=50, help='Posts de FB objetivo')
    parser.add_argument('--platform', choices=['facebook', 'all'], default='all')

    args = parser.parse_args()

    pipeline = ScraperPipeline()
    pipeline.scrape_facebook(args.fb_target)
    pipeline.generate_metrics()

    print("\nScraping completado!")
    print("Pipeline completado.")


if __name__ == '__main__':
    main()
