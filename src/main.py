#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.panel import Panel

from src.config import Config
from src.storage.supabase_client import SupabaseStorage
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona, extract_problematicas
from src.analyzer.executive_metrics import ExecutiveMetrics

console = Console()

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def setup_logging(level: str = "info"):
    logging.basicConfig(
        level=LOG_LEVELS.get(level, logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )


def scrape_facebook(cfg: Config, storage: SupabaseStorage, max_posts: int, progress_callback):
    logger = logging.getLogger(__name__)

    if not cfg.has_facebook_login:
        logger.error("FB_EMAIL and FB_PASSWORD required for Playwright scraping")
        return []

    from src.fb_scraper.playwright_scraper import FacebookPlaywright

    fb_scr = FacebookPlaywright(
        email=cfg.FB_EMAIL,
        password=cfg.FB_PASSWORD,
        proxy_url=cfg.PROXY_URL,
    )
    page_name = cfg.FB_PAGE_NAME or cfg.FB_PAGE_URL
    if not page_name:
        logger.error("FB_PAGE_NAME is required")
        return []

    posts = fb_scr.scrape_page_posts(
        page_name=page_name,
        max_posts=max_posts,
        progress_callback=progress_callback,
    )
    logger.info(f"Got {len(posts)} posts from Playwright")
    return posts


def scrape_tiktok(cfg: Config, storage: SupabaseStorage, max_videos: int, progress_callback):
    logger = logging.getLogger(__name__)

    if not cfg.TT_USERNAME:
        logger.error("No TT_USERNAME configured")
        return []

    from src.tiktok_scraper.scraper import TikTokScraper

    scraper = TikTokScraper(proxy_url=cfg.PROXY_URL)
    videos = scraper.scrape_profile_videos(
        username=cfg.TT_USERNAME,
        max_videos=max_videos,
        progress_callback=progress_callback,
    )
    logger.info(f"Got {len(videos)} videos from TikTok")
    return videos


def analyze_and_save_posts(items, storage: SupabaseStorage, analyzer: SentimentAnalyzer, platform: str, text_attr: str):
    count = 0
    for item in items:
        text = getattr(item, text_attr, "")
        
        sentiment_label, sentiment_score = analyzer.analyze(text)
        
        topic = get_main_topic(text)
        zona = detect_zona(text)
        
        post_data = {
            "post_id": item.post_id if platform == "facebook" else item.video_id,
            "page_id": item.page_id if platform == "facebook" else "",
            "page_name": item.page_name if platform == "facebook" else "",
            "message": item.message if platform == "facebook" else "",
            "description": item.description if platform == "tiktok" else "",
            "username": item.username if platform == "tiktok" else "",
            "created_time": item.created_time.isoformat() if item.created_time else None,
            "create_time": item.create_time.isoformat() if hasattr(item, 'create_time') and item.create_time else None,
            "likes_count": item.likes_count,
            "loves_count": getattr(item, "loves_count", 0),
            "hahas_count": getattr(item, "hahas_count", 0),
            "wows_count": getattr(item, "wows_count", 0),
            "sads_count": getattr(item, "sads_count", 0),
            "angrys_count": getattr(item, "angrys_count", 0),
            "comments_count": item.comments_count,
            "shares_count": getattr(item, "shares_count", 0),
            "views_count": getattr(item, "views_count", 0),
            "post_url": getattr(item, "post_url", ""),
            "video_url": getattr(item, "video_url", ""),
            "sentiment": sentiment_label,
            "sentiment_score": sentiment_score,
            "topic_category": topic,
            "zona": zona,
        }
        
        if platform == "facebook":
            success = storage.insert_fb_post(post_data)
        else:
            success = storage.insert_tt_post(post_data)
        
        if success:
            count += 1
            
            problematicas = extract_problematicas(text, sentiment_label)
            for prob in problematicas:
                storage.insert_problematica({
                    "platform": platform,
                    "post_id": post_data.get("post_id", ""),
                    "topic": prob.get("topic", ""),
                    "zona": prob.get("zona", ""),
                    "message": prob.get("text_preview", ""),
                    "sentiment": sentiment_label,
                    "sentiment_score": sentiment_score,
                })
    
    return count


class ProgressTracker:
    def __init__(self, task_desc: str, total: int):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        self.task = self.progress.add_task(task_desc, total=total)
        self.progress.start()

    def update(self, current: int, total: int):
        self.progress.update(self.task, completed=current, total=total)

    def stop(self):
        self.progress.stop()


def cmd_scrape(args, cfg, storage):
    analyzer = SentimentAnalyzer()

    if args.platform in ("facebook", "all"):
        console.print(Panel("[bold blue]Scraping Facebook...[/bold blue]"))

        tracker = ProgressTracker("Scraping Facebook", args.max or cfg.MAX_POSTS)
        posts = scrape_facebook(cfg, storage, args.max or cfg.MAX_POSTS, tracker.update)
        tracker.stop()

        if posts:
            console.print(f"[green]Analyzing sentiment for {len(posts)} posts...[/green]")
            saved = analyze_and_save_posts(posts, storage, analyzer, "facebook", "message")
            console.print(f"[bold green]Saved {saved} Facebook posts to Supabase[/bold green]")

    if args.platform in ("tiktok", "all"):
        console.print(Panel("[bold purple]Scraping TikTok...[/bold purple]"))

        tracker = ProgressTracker("Scraping TikTok", args.max or cfg.MAX_POSTS)
        videos = scrape_tiktok(cfg, storage, args.max or cfg.MAX_POSTS, tracker.update)
        tracker.stop()

        if videos:
            console.print(f"[green]Analyzing sentiment for {len(videos)} videos...[/green]")
            saved = analyze_and_save_posts(videos, storage, analyzer, "tiktok", "description")
            console.print(f"[bold green]Saved {saved} TikTok videos to Supabase[/bold green]")


def cmd_analyze(args, cfg, storage):
    console.print(Panel("[bold yellow]Generating analysis and insights...[/bold yellow]"))
    
    metrics_calc = ExecutiveMetrics(storage)
    
    if args.platform in ("facebook", "all"):
        fb_metrics = metrics_calc.generate_daily_metrics("facebook")
        if fb_metrics:
            storage.insert_daily_metric(fb_metrics)
            console.print(f"[green]Facebook metrics: NSI={fb_metrics.get('nsi')}, CAI={fb_metrics.get('cai')}[/green]")
        
        fb_insights = metrics_calc.generate_insights("facebook")
        for insight in fb_insights[:5]:
            storage.insert_insight(insight)
        console.print(f"[green]Generated {len(fb_insights)} Facebook insights[/green]")
    
    if args.platform in ("tiktok", "all"):
        tt_metrics = metrics_calc.generate_daily_metrics("tiktok")
        if tt_metrics:
            storage.insert_daily_metric(tt_metrics)
            console.print(f"[green]TikTok metrics: NSI={tt_metrics.get('nsi')}, CAI={tt_metrics.get('cai')}[/green]")
        
        tt_insights = metrics_calc.generate_insights("tiktok")
        for insight in tt_insights[:5]:
            storage.insert_insight(insight)
        console.print(f"[green]Generated {len(tt_insights)} TikTok insights[/green]")
    
    console.print(f"[bold green]Análisis completado. Dashboard actualizado en Supabase.[/bold green]")


def cmd_status(args, cfg, storage):
    summary = storage.get_executive_summary()
    
    table = Table(title="Supabase Database Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="bold")
    
    table.add_row("Facebook posts", str(summary.get("fb_posts", 0)))
    table.add_row("TikTok videos", str(summary.get("tt_posts", 0)))
    table.add_row("Facebook comments", str(summary.get("fb_comments", 0)))
    table.add_row("TikTok comments", str(summary.get("tt_comments", 0)))
    
    fb_total = summary.get("fb_positive", 0) + summary.get("fb_negative", 0)
    tt_total = summary.get("tt_positive", 0) + summary.get("tt_negative", 0)
    
    if fb_total > 0:
        fb_pos_pct = (summary.get("fb_positive", 0) / fb_total) * 100
        table.add_row("FB Positive %", f"{fb_pos_pct:.1f}%")
    
    if tt_total > 0:
        tt_pos_pct = (summary.get("tt_positive", 0) / tt_total) * 100
        table.add_row("TT Positive %", f"{tt_pos_pct:.1f}%")
    
    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Scrapeo Social v2.0 - Analítica Ejecutiva para Alcaldías"
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS.keys(),
        default="info",
        help="Logging level",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    scrape_parser = subparsers.add_parser("scrape", help="Scrape social media data to Supabase")
    scrape_parser.add_argument(
        "--platform",
        choices=["facebook", "tiktok", "all"],
        default="all",
        help="Platform to scrape",
    )
    scrape_parser.add_argument("--max", type=int, default=0, help="Max items to scrape")

    analyze_parser = subparsers.add_parser("analyze", help="Generate insights and metrics")
    analyze_parser.add_argument(
        "--platform",
        choices=["facebook", "tiktok", "all"],
        default="all",
        help="Platform to analyze",
    )

    subparsers.add_parser("status", help="Show database status")

    args = parser.parse_args()

    setup_logging(args.log_level if hasattr(args, "log_level") else "info")

    if not args.command:
        parser.print_help()
        return

    cfg = Config()
    storage = SupabaseStorage()

    if args.command == "scrape":
        cmd_scrape(args, cfg, storage)
    elif args.command == "analyze":
        cmd_analyze(args, cfg, storage)
    elif args.command == "status":
        cmd_status(args, cfg, storage)


if __name__ == "__main__":
    main()
