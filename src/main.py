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
import requests
import time
import random
from datetime import datetime

console = Console()


def extract_tiktok_comments(video_id: str, max_comments: int = None) -> list[dict]:
    """
    Extract comments for a TikTok video using the public API.

    Args:
        video_id: TikTok video ID (aweme_id)
        max_comments: Maximum number of comments to extract (None for all)

    Returns:
        List of comment dictionaries with keys matching Supabase tt_comments table
    """
    import logging
    logger = logging.getLogger(__name__)

    comments = []
    cursor = 0
    has_more = True

    while has_more and (max_comments is None or len(comments) < max_comments):
        try:
            # Calculate how many comments to fetch in this batch
            batch_size = 20  # TikTok API standard batch size
            if max_comments is not None:
                remaining = max_comments - len(comments)
                if remaining <= 0:
                    break
                batch_size = min(batch_size, remaining)

            # Make API request
            url = "https://www.tiktok.com/api/comment/list/"
            params = {
                "aweme_id": video_id,
                "count": str(batch_size),
                "cursor": str(cursor),
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                "Referer": "https://www.tiktok.com/",
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch comments for video {video_id}: HTTP {response.status_code}")
                break

            data = response.json()

            # Extract comments from response
            batch_comments = data.get("comments", [])
            has_more = data.get("has_more", False)
            cursor = data.get("cursor", 0)

            # Process each comment
            for comment in batch_comments:
                try:
                    # Extract comment data
                    comment_id = comment.get("cid")
                    text = comment.get("text", "")
                    create_time = comment.get("create_time")
                    like_count = comment.get("digg_count", 0)

                    # Extract author information
                    user_info = comment.get("user", {})
                    author_name = user_info.get("nickname", "") or user_info.get("unique_id", "")

                    # Convert timestamp
                    if create_time:
                        try:
                            created_time = datetime.fromtimestamp(int(create_time))
                        except (ValueError, TypeError):
                            created_time = None
                    else:
                        created_time = None

                    # Apply NLP analysis
                    analyzer = SentimentAnalyzer()
                    sentiment_label, sentiment_score = analyzer.analyze(text)
                    topic = get_main_topic(text)
                    zona = detect_zona(text)

                    # Build comment dictionary
                    comment_data = {
                        "comment_id": str(comment_id),
                        "video_id": str(video_id),
                        "message": text[:5000],  # Limit to match DB column size
                        "author_name": author_name[:100],  # Limit author name length
                        "created_time": created_time.isoformat() if created_time else None,
                        "like_count": like_count,
                        "sentiment": sentiment_label,
                        "sentiment_score": sentiment_score,
                        "topic_category": topic,
                        "zona": zona,
                    }

                    comments.append(comment_data)

                except Exception as e:
                    logger.warning(f"Error processing comment for video {video_id}: {e}")
                    continue

            # Add delay to avoid rate limiting
            time.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            logger.warning(f"Error fetching comments for video {video_id}: {e}")
            break

    return comments


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

    scraper = TikTokScraper(
        proxy_url=cfg.PROXY_URL,
        email=cfg.TT_EMAIL,
        password=cfg.TT_PASSWORD,
        cookies_file=cfg.TT_COOKIES_FILE,
    )
    videos = scraper.scrape_profile_videos(
        username=cfg.TT_USERNAME,
        max_videos=max_videos,
        progress_callback=progress_callback,
    )
    logger.info(f"Got {len(videos)} videos from TikTok")
    return videos


def scrape_tiktok_resilient(cfg: Config, storage: SupabaseStorage, max_videos: int, days_back: int, progress_callback):
    logger = logging.getLogger(__name__)

    if not cfg.TT_USERNAME:
        logger.error("No TT_USERNAME configured")
        return []

    from src.tiktok_scraper.resilient_scraper import TikTokResilientScraper

    scraper = TikTokResilientScraper(
        proxy_url=cfg.PROXY_URL,
        headless=False,
        email=cfg.TT_EMAIL,
        password=cfg.TT_PASSWORD,
        cookies_file=cfg.TT_COOKIES_FILE,
        max_retries=3,
    )
    videos = scraper.scrape_videos(
        username=cfg.TT_USERNAME,
        max_videos=max_videos,
        days_back=days_back,
        progress_callback=progress_callback,
    )
    logger.info(f"Got {len(videos)} videos from TikTok resilient scraper")
    return videos


def analyze_and_save_posts(items, storage: SupabaseStorage, analyzer: SentimentAnalyzer, platform: str, text_attr: str, extract_comments: bool = False):
    count = 0
    for item in items:
        text = getattr(item, text_attr, "")

        sentiment_label, sentiment_score = analyzer.analyze(text)

        topic = get_main_topic(text)
        zona = detect_zona(text)

        hashtags = []
        if platform == "tiktok" and hasattr(item, "hashtags"):
            hashtags = item.hashtags or []

        favorites_count = 0
        if platform == "tiktok" and hasattr(item, "favorites_count"):
            favorites_count = item.favorites_count or 0

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
            "favorites_count": favorites_count,
            "hashtags": ",".join(hashtags) if hashtags else "",
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

            if extract_comments and platform == "tiktok" and item.comments_count > 0:
                video_id = item.video_id
                comments = extract_tiktok_comments(video_id, max_comments=100)

                for comment in comments:
                    comment_success = storage.insert_tt_comment(comment)
                    if comment_success:
                        comment_problematicas = extract_problematicas(comment["message"], comment["sentiment"])
                        for prob in comment_problematicas:
                            prob["platform"] = platform
                            prob["post_id"] = post_data.get("post_id", "")
                            prob["comment_id"] = comment.get("comment_id", "")
                            storage.insert_problematica(prob)

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


def cmd_graph_scrape(args, cfg, storage):
    console.print(Panel("[bold green]📊 Graph API SCRAPER[/bold green]"))
    token = args.token or cfg.FB_ACCESS_TOKEN
    page_id = args.page_id or cfg.FB_PAGE_ID
    page_name = args.page_name or cfg.FB_PAGE_NAME

    if not token:
        console.print("[red]Error: No FB_ACCESS_TOKEN. Pásalo con --token o configúralo en .env[/red]")
        return

    console.print(f"[bold]Página:[/bold] {page_name}")
    console.print(f"[bold]Page ID:[/bold] {page_id}")
    console.print(f"[bold]Target:[/bold] {args.max} posts")

    from src.fb_scraper.graph_api_scraper import GraphAPIScraper

    scraper = GraphAPIScraper(
        access_token=token,
        page_id=page_id,
        page_name=page_name,
    )

    stats = scraper.scrape(
        max_posts=args.max,
        get_comments=args.comments,
    )

    console.print(f"\n[bold green]✅ Completado[/bold green]")
    console.print(f"Posts: {stats['posts_scraped']}")
    console.print(f"Comentarios: {stats['comments_scraped']}")


def cmd_deep_scrape(args, cfg, storage):
    console.print(Panel("[bold red]🕷️ DEEP SCRAPER - Extracción Completa[/bold red]"))
    console.print(f"[bold]Página ID:[/bold] {args.page_id}")
    console.print(f"[bold]Desde:[/bold] {args.start}")
    console.print(f"[bold]Target:[/bold] {args.max} posts")

    from src.fb_scraper.deep_scraper import FacebookDeepScraper

    scraper = FacebookDeepScraper(
        cookies_file=args.cookies_file,
        page_id=args.page_id,
        page_name=args.page_name,
        start_date=args.start,
        headless=args.headless,
    )

    stats = scraper.scrape(
        max_posts=args.max,
        checkpoint_every=args.checkpoint_every,
    )

    console.print(f"\n[bold green]✅ Deep scraping completado[/bold green]")
    console.print(f"Posts: {stats['posts_scraped']}")
    console.print(f"Comentarios: {stats['comments_scraped']}")
    console.print(f"Duplicados: {stats['posts_duplicated']}")


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
            saved = analyze_and_save_posts(videos, storage, analyzer, "tiktok", "description", extract_comments=False)
            console.print(f"[bold green]Saved {saved} TikTok videos to Supabase[/bold green]")


def cmd_scrape_resilient(args, cfg, storage):
    analyzer = SentimentAnalyzer()

    console.print(Panel("[bold red]🔒 TikTok Resilient Scraper - Anti-Ban Edition[/bold red]"))
    console.print(f"[bold]Usuario:[/bold] @{cfg.TT_USERNAME}")
    console.print(f"[bold]Días atrás:[/bold] {args.days}")
    console.print(f"[bold]Máx videos:[/bold] {args.max or 'Todos en rango'}")
    console.print(f"[bold]Extraer comentarios:[/bold] {args.comments}")

    max_videos = args.max if args.max > 0 else 2000

    tracker = ProgressTracker("Scraping TikTok Resilient", max_videos)
    videos = scrape_tiktok_resilient(
        cfg, storage, max_videos, args.days, tracker.update
    )
    tracker.stop()

    if videos:
        console.print(f"[green]Analyzing sentiment for {len(videos)} videos...[/green]")
        saved = analyze_and_save_posts(videos, storage, analyzer, "tiktok", "description", extract_comments=args.comments)
        console.print(f"[bold green]Saved {saved} TikTok videos to Supabase[/bold green]")
        console.print(f"[bold]Hashtags extraídos:[/bold] {sum(len(v.hashtags) for v in videos if v.hashtags)}")
    else:
        console.print("[yellow]No se encontraron videos. Intentando método alternativo...[/yellow]")


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

    graph_parser = subparsers.add_parser("graph-scrape", help="Scraping via Facebook Graph API (más estable)")
    graph_parser.add_argument("--token", default="", help="Page Access Token (o usa FB_ACCESS_TOKEN en .env)")
    graph_parser.add_argument("--page-id", default="395582594151511", help="Facebook Page ID")
    graph_parser.add_argument("--page-name", default="Jose Chicas", help="Nombre de la página")
    graph_parser.add_argument("--max", type=int, default=1000, help="Posts objetivo")
    graph_parser.add_argument("--comments", action="store_true", help="Extraer comentarios también")

    deep_parser = subparsers.add_parser("deep-scrape", help="Deep scraping - extracción completa con NLP y anti-ban")
    deep_parser.add_argument("--max", type=int, default=10000, help="Posts objetivo")
    deep_parser.add_argument("--start", default="2025-01-01", help="Fecha inicio (YYYY-MM-DD)")
    deep_parser.add_argument("--page-id", default="395582594151511", help="Facebook Page ID")
    deep_parser.add_argument("--page-name", default="Jose Chicas", help="Nombre de la página")
    deep_parser.add_argument("--headless", action="store_true", help="Modo headless")
    deep_parser.add_argument("--cookies-file", default="cookies.json", help="Archivo de cookies")
    deep_parser.add_argument("--checkpoint-every", type=int, default=50, help="Guardar checkpoint cada N posts")

    resilient_parser = subparsers.add_parser("scrape-resilient", help="Scraping TikTok resiliente con anti-ban")
    resilient_parser.add_argument(
        "--platform",
        choices=["tiktok"],
        default="tiktok",
        help="Platform to scrape",
    )
    resilient_parser.add_argument("--max", type=int, default=0, help="Max videos to scrape (0 = all in range)")
    resilient_parser.add_argument("--days", type=int, default=365, help="Days back to scrape (default: 365)")
    resilient_parser.add_argument("--comments", action="store_true", help="Also extract comments for each video")

    analyze_parser = subparsers.add_parser("analyze", help="Generate insights and metrics")
    analyze_parser.add_argument(
        "--platform",
        choices=["facebook", "tiktok", "all"],
        default="all",
        help="Platform to analyze",
    )

    subparsers.add_parser("status", help="Show database status")

    tt_login_parser = subparsers.add_parser("tt-login", help="Login manual a TikTok y guardar cookies de sesión")
    tt_login_parser.add_argument("--cookies", default="tiktok_cookies.json")
    tt_login_parser.add_argument("--user", default="")

    tt_brute_parser = subparsers.add_parser("scrape-tt", help="Scraping brute-force TikTok (multi-método)")
    tt_brute_parser.add_argument("--user", default="")
    tt_brute_parser.add_argument("--max", type=int, default=0)
    tt_brute_parser.add_argument("--days", type=int, default=365)
    tt_brute_parser.add_argument("--comments", action="store_true")
    tt_brute_parser.add_argument("--max-comments", type=int, default=0)
    tt_brute_parser.add_argument("--cookies", default="")
    tt_brute_parser.add_argument("--headless", action="store_true")

    args = parser.parse_args()

    setup_logging(args.log_level if hasattr(args, "log_level") else "info")

    if not args.command:
        parser.print_help()
        return

    cfg = Config()
    storage = SupabaseStorage()

    if args.command == "scrape":
        cmd_scrape(args, cfg, storage)
    elif args.command == "scrape-resilient":
        cmd_scrape_resilient(args, cfg, storage)
    elif args.command == "tt-login":
        from src.tiktok_scraper.bruteforce_scraper import login_and_save_cookies
        login_and_save_cookies(args.cookies or cfg.TT_COOKIES_FILE, args.user or cfg.TT_USERNAME)
    elif args.command == "scrape-tt":
        from src.tiktok_scraper.bruteforce_scraper import TikTokBruteForceScraper
        user = args.user or cfg.TT_USERNAME
        if not user:
            console.print("[red]Error: No TT_USERNAME configured[/red]")
            return
        max_v = args.max if args.max > 0 else 2000
        scraper = TikTokBruteForceScraper(
            username=user,
            cookies_file=args.cookies or cfg.TT_COOKIES_FILE,
            headless=args.headless,
        )
        tracker = ProgressTracker(f"Scraping @{user} (brute force)", max_v)
        videos = scraper.scrape_videos(max_videos=max_v, days_back=args.days, progress_callback=tracker.update)
        tracker.stop()
        if videos:
            from src.analyzer.sentiment import SentimentAnalyzer
            analyzer = SentimentAnalyzer()
            saved = analyze_and_save_posts(videos, storage, analyzer, "tiktok", "description", extract_comments=args.comments)
            console.print(f"[bold green]Saved {saved} TikTok videos to Supabase[/bold green]")
            if args.comments and videos:
                console.print(f"[bold]Extrayendo comentarios de {len(videos)} videos...[/bold]")
                comment_tracker = ProgressTracker("Extrayendo comentarios", len(videos))
                all_comments = scraper.scrape_all_comments(
                    videos,
                    max_comments_per_video=args.max_comments,
                    progress_callback=comment_tracker.update,
                )
                comment_tracker.stop()
                total_comments = 0
                for vid, comments in all_comments.items():
                    for c in comments:
                        data = c.to_dict()
                        data["sentiment"] = ""
                        data["sentiment_score"] = 0
                        if storage.insert_tt_comment(data):
                            total_comments += 1
                console.print(f"[bold green]Saved {total_comments} TikTok comments to Supabase[/bold green]")
        else:
            console.print("[yellow]No se encontraron videos con ningún método[/yellow]")
    elif args.command == "graph-scrape":
        cmd_graph_scrape(args, cfg, storage)
    elif args.command == "deep-scrape":
        cmd_deep_scrape(args, cfg, storage)
    elif args.command == "analyze":
        cmd_analyze(args, cfg, storage)
    elif args.command == "status":
        cmd_status(args, cfg, storage)


if __name__ == "__main__":
    main()
