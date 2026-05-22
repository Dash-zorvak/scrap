#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

from src.config import Config
from src.storage.supabase_client import SupabaseStorage
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona, extract_problematicas
from src.analyzer.executive_metrics import ExecutiveMetrics

logger = logging.getLogger(__name__)
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


def analyze_and_save_posts(items, storage, analyzer):
    count = 0
    for item in items:
        text = item.message or ""

        sentiment_label, sentiment_score = analyzer.analyze(text)
        topic = get_main_topic(text)
        zona = detect_zona(text)

        post_data = {
            "post_id": item.post_id,
            "page_id": item.page_id or "",
            "page_name": item.page_name or "",
            "message": item.message or "",
            "created_time": item.created_time.isoformat() if item.created_time else None,
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
            "sentiment": sentiment_label,
            "sentiment_score": sentiment_score,
            "topic_category": topic,
            "zona": zona,
        }

        success = storage.insert_fb_post(post_data)

        if success:
            count += 1

            problematicas = extract_problematicas(text, sentiment_label)
            for prob in problematicas:
                storage.insert_problematica({
                    "platform": "facebook",
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
    console.print(Panel("[bold green]Graph API SCRAPER[/bold green]"))
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
        get_comments=getattr(args, "comments", True),
        get_replies=getattr(args, "replies", True),
    )

    console.print(f"\n[bold green]Completado[/bold green]")
    console.print(f"Posts: {stats['posts_scraped']}")
    console.print(f"Comentarios: {stats['comments_scraped']}")


def cmd_deep_scrape(args, cfg, storage):
    console.print(Panel("[bold red]DEEP SCRAPER - Extracción Completa[/bold red]"))
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

    console.print(f"\n[bold green]Deep scraping completado[/bold green]")
    console.print(f"Posts: {stats['posts_scraped']}")
    console.print(f"Comentarios: {stats['comments_scraped']}")
    console.print(f"Duplicados: {stats['posts_duplicated']}")


def cmd_scrape(args, cfg, storage):
    analyzer = SentimentAnalyzer()

    console.print(Panel("[bold blue]Scraping Facebook...[/bold blue]"))

    if not cfg.has_facebook_login:
        console.print("[red]FB_EMAIL and FB_PASSWORD required for Playwright scraping[/red]")
        return

    from src.fb_scraper.playwright_scraper import FacebookPlaywright

    fb_scr = FacebookPlaywright(
        email=cfg.FB_EMAIL,
        password=cfg.FB_PASSWORD,
        proxy_url=cfg.PROXY_URL,
    )
    page_name = cfg.FB_PAGE_NAME or cfg.FB_PAGE_URL
    if not page_name:
        console.print("[red]FB_PAGE_NAME is required[/red]")
        return

    tracker = ProgressTracker("Scraping Facebook", args.max or cfg.MAX_POSTS)
    posts = fb_scr.scrape_page_posts(
        page_name=page_name,
        max_posts=args.max or cfg.MAX_POSTS,
        progress_callback=tracker.update,
    )
    tracker.stop()

    if posts:
        console.print(f"[green]Analyzing sentiment for {len(posts)} posts...[/green]")
        saved = analyze_and_save_posts(posts, storage, analyzer)
        console.print(f"[bold green]Saved {saved} Facebook posts[/bold green]")


def _export_dashboard_data(storage):
    """Export SQLite data to dashboard/data.js."""
    import json
    from collections import defaultdict
    from datetime import datetime

    posts = storage.get_fb_posts(limit=10000)
    comments = storage.get_fb_comments(limit=50000)

    total = len(posts)
    total_reactions = sum(p.get("likes_count", 0) + p.get("loves_count", 0) + p.get("hahas_count", 0)
                          + p.get("wows_count", 0) + p.get("sads_count", 0) + p.get("angrys_count", 0) for p in posts)
    total_comments = sum(p.get("comments_count", 0) for p in posts)
    total_shares = sum(p.get("shares_count", 0) for p in posts)
    total_views = sum(p.get("views_count", 0) for p in posts)

    rd = {
        "likes": sum(p.get("likes_count", 0) for p in posts),
        "loves": sum(p.get("loves_count", 0) for p in posts),
        "hahas": sum(p.get("hahas_count", 0) for p in posts),
        "wows": sum(p.get("wows_count", 0) for p in posts),
        "sads": sum(p.get("sads_count", 0) for p in posts),
        "angrys": sum(p.get("angrys_count", 0) for p in posts),
    }

    n = total_reactions or 1
    net_sentiment = (rd["likes"] + rd["loves"] - rd["angrys"] - rd["sads"]) / n
    controversy = (rd["angrys"] + rd["sads"]) / n
    effectiveness = (rd["likes"] + rd["loves"]) / n
    engagement = ((total_reactions + total_comments + total_shares) / max(total_views, 1)) * 100
    risk = controversy * (total_views / max(total_reactions, 1))

    indices = {
        "engagement": round(engagement, 2),
        "netSentiment": round(net_sentiment, 4),
        "controversy": round(controversy, 4),
        "effectiveness": round(effectiveness, 4),
        "riskReputacional": round(risk, 2),
    }

    topic_names = ["uncategorized", "medio_ambiente", "educacion", "empleo", "movilidad",
                   "seguridad", "servicios_publicos", "obras_publicas", "salud", "corrupcion", "transparencia"]
    topics = {}
    for tn in topic_names:
        tp = [p for p in posts if p.get("topic_category", "uncategorized") == tn]
        likes = sum(p.get("likes_count", 0) for p in tp)
        loves = sum(p.get("loves_count", 0) for p in tp)
        hahas = sum(p.get("hahas_count", 0) for p in tp)
        wows = sum(p.get("wows_count", 0) for p in tp)
        sads = sum(p.get("sads_count", 0) for p in tp)
        angrys = sum(p.get("angrys_count", 0) for p in tp)
        tr = likes + loves + hahas + wows + sads + angrys
        sent_pos = sum(1 for p in tp if p.get("sentiment") == "positive")
        sent_neu = sum(1 for p in tp if p.get("sentiment") == "neutral")
        sent_neg = sum(1 for p in tp if p.get("sentiment") == "negative")
        topics[tn] = {
            "count": len(tp), "likes": likes, "loves": loves, "hahas": hahas, "wows": wows,
            "sads": sads, "angrys": angrys,
            "comments": sum(p.get("comments_count", 0) for p in tp),
            "shares": sum(p.get("shares_count", 0) for p in tp),
            "views": sum(p.get("views_count", 0) for p in tp),
            "sentiment_pos": sent_pos, "sentiment_neu": sent_neu, "sentiment_neg": sent_neg,
            "total_reactions": tr,
            "net_sentiment": round((likes + loves - angrys - sads) / max(tr, 1), 4),
            "controversy": round((angrys + sads) / max(tr, 1), 4),
            "effectiveness": round((likes + loves) / max(tr, 1), 4),
        }

    zone_names = ["Este", "unknown", "Norte", "Centro", "Sur", "Oeste"]
    zones = {}
    for zn in zone_names:
        zp = [p for p in posts if p.get("zona", "unknown") == zn]
        zones[zn] = {
            "count": len(zp),
            "likes": sum(p.get("likes_count", 0) for p in zp),
            "loves": sum(p.get("loves_count", 0) for p in zp),
            "angrys": sum(p.get("angrys_count", 0) for p in zp),
            "sads": sum(p.get("sads_count", 0) for p in zp),
            "comments": sum(p.get("comments_count", 0) for p in zp),
            "shares": sum(p.get("shares_count", 0) for p in zp),
            "views": sum(p.get("views_count", 0) for p in zp),
        }

    monthly = {}
    for p in posts:
        ct = p.get("created_time")
        if ct:
            try:
                dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
                key = dt.strftime("%Y-%m")
                if key not in monthly:
                    monthly[key] = {"posts": 0, "reactions": 0, "comments": 0, "shares": 0,
                                    "views": 0, "likes": 0, "loves": 0, "angrys": 0, "sads": 0}
                monthly[key]["posts"] += 1
                monthly[key]["reactions"] += (p.get("likes_count", 0) + p.get("loves_count", 0) + p.get("hahas_count", 0)
                                              + p.get("wows_count", 0) + p.get("sads_count", 0) + p.get("angrys_count", 0))
                monthly[key]["comments"] += p.get("comments_count", 0)
                monthly[key]["shares"] += p.get("shares_count", 0)
                monthly[key]["views"] += p.get("views_count", 0)
                monthly[key]["likes"] += p.get("likes_count", 0)
                monthly[key]["loves"] += p.get("loves_count", 0)
                monthly[key]["angrys"] += p.get("angrys_count", 0)
                monthly[key]["sads"] += p.get("sads_count", 0)
            except (ValueError, TypeError):
                pass

    yearly = {}
    for p in posts:
        ct = p.get("created_time")
        if ct:
            try:
                dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
                key = dt.strftime("%Y")
                if key not in yearly:
                    yearly[key] = {"pos": 0, "neu": 0, "neg": 0, "angrys": 0}
                s = p.get("sentiment", "")
                if s == "positive":
                    yearly[key]["pos"] += 1
                elif s == "negative":
                    yearly[key]["neg"] += 1
                else:
                    yearly[key]["neu"] += 1
                yearly[key]["angrys"] += p.get("angrys_count", 0)
            except (ValueError, TypeError):
                pass

    top_posts = sorted(posts, key=lambda p: p.get("likes_count", 0) + p.get("comments_count", 0) * 2, reverse=True)[:50]
    top_posts_data = []
    for p in top_posts:
        top_posts_data.append({
            "id": p.get("post_id", ""),
            "message": (p.get("message", "") or "")[:200],
            "created": p.get("created_time", ""),
            "topic": p.get("topic_category", ""),
            "zona": p.get("zona", ""),
            "sentiment": p.get("sentiment", ""),
            "likes": p.get("likes_count", 0),
            "loves": p.get("loves_count", 0),
            "hahas": p.get("hahas_count", 0),
            "wows": p.get("wows_count", 0),
            "sads": p.get("sads_count", 0),
            "angrys": p.get("angrys_count", 0),
            "comments": p.get("comments_count", 0),
            "shares": p.get("shares_count", 0),
            "views": p.get("views_count", 0),
        })

    dates = [p.get("created_time") for p in posts if p.get("created_time")]
    date_range = {"from": min(dates) if dates else datetime.now().isoformat(),
                  "to": max(dates) if dates else datetime.now().isoformat()}

    dash_data = {
        "page": "Jose Chicas — San Salvador Este",
        "totalPosts": total,
        "totalReactions": total_reactions,
        "totalComments": total_comments,
        "totalShares": total_shares,
        "totalViews": total_views,
        "reactionDistribution": rd,
        "indices": indices,
        "topics": topics,
        "zones": zones,
        "monthly": monthly,
        "yearly": yearly,
        "topPosts": top_posts_data,
        "keywordInsights": {},
        "topKeywords": {},
        "topBigrams": {},
        "controversialPosts": [],
        "dateRange": date_range,
    }

    dash_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "data.js")
    with open(dash_path, "w", encoding="utf-8") as f:
        f.write(f"const DASH_DATA = {json.dumps(dash_data, ensure_ascii=False)};\n")
        f.write(f"const MONTHLY_DATA = {json.dumps(monthly, ensure_ascii=False)};\n")
        f.write('const fmt = n => n.toLocaleString("es-SV");\n')
        f.write('const pct = n => (n*100).toFixed(2)+"%";\n')
        f.write('const short = n => n>=1e6?(n/1e6).toFixed(1)+"M":n>=1e3?(n/1e3).toFixed(1)+"K":String(n);\n')

    logger.info(f"Dashboard data exported to {dash_path}")
    return len(posts)


def cmd_analyze(args, cfg, storage):
    console.print(Panel("[bold yellow]Generating analysis and insights...[/bold yellow]"))

    metrics_calc = ExecutiveMetrics(storage)

    fb_metrics = metrics_calc.generate_daily_metrics("facebook")
    if fb_metrics:
        storage.insert_daily_metric(fb_metrics)
        console.print(f"[green]Facebook metrics: NSI={fb_metrics.get('nsi')}, CAI={fb_metrics.get('cai')}[/green]")

    fb_insights = metrics_calc.generate_insights("facebook")
    for insight in fb_insights[:5]:
        storage.insert_insight(insight)
    console.print(f"[green]Generated {len(fb_insights)} Facebook insights[/green]")

    exported = _export_dashboard_data(storage)
    console.print(f"[bold green]Dashboard data exported: {exported} posts → dashboard/data.js[/bold green]")
    console.print(f"[bold green]Análisis completado.[/bold green]")


def cmd_status(args, cfg, storage):
    summary = storage.get_executive_summary()

    table = Table(title="Database Status (SQLite)")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="bold")

    table.add_row("Facebook posts", str(summary.get("fb_posts", 0)))
    table.add_row("Facebook comments", str(summary.get("fb_comments", 0)))

    fb_total = summary.get("fb_positive", 0) + summary.get("fb_negative", 0)

    if fb_total > 0:
        fb_pos_pct = (summary.get("fb_positive", 0) / fb_total) * 100
        table.add_row("FB Positive %", f"{fb_pos_pct:.1f}%")

    console.print(table)





def cmd_phase3(args, cfg, storage):
    console.print(Panel("[bold cyan]PHASE 3 RESUME — Complete Comment Extraction[/bold cyan]"))
    from src.fb_scraper.phase3_resume import Phase3Resumer

    resumer = Phase3Resumer(access_token=cfg.FB_ACCESS_TOKEN, page_id=cfg.FB_PAGE_ID)
    stats = resumer.run(
        get_replies=not getattr(args, "no_replies", False),
        checkpoint_every=getattr(args, "checkpoint_every", 50),
    )
    console.print(f"[green]Done: {stats['posts_processed']} posts, {stats['comments_scraped']} comments, {stats['replies_scraped']} replies, {stats['errors']} errors[/green]")


def cmd_reset(args, cfg, storage):
    console.print(Panel("[bold red]⚠ RESET — Purge all data[/bold red]"))
    console.print("[yellow]Deleting all data from: fb_posts, fb_comments, problematicas, insights, daily_metrics[/yellow]")
    console.print("[yellow]This will also delete the local SQLite backup![/yellow]")
    confirm = input("Type 'RESET' to confirm: ")
    if confirm != "RESET":
        console.print("[green]Cancelled.[/green]")
        return
    ok = storage.purge_all()
    if ok:
        console.print("[bold green]All data purged successfully.[/bold green]")
    else:
        console.print("[red]Error during purge.[/red]")


def cmd_estimate(args, cfg, storage):
    import importlib.util
    spec = importlib.util.spec_from_file_location("estimation", os.path.join(os.path.dirname(__file__), "analyzer", "estimation.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    target = getattr(args, "target", 20000)
    results, total_min, total_hr, cpp, tc = mod.calc_metrics(target)
    console.print(Panel(f"[bold cyan]TIME ESTIMATION — {target:,} Posts[/bold cyan]"))
    console.print(mod.format_table(results, total_min, total_hr, cpp, tc, target))


def main():
    parser = argparse.ArgumentParser(
        description="Scrapeo Social - Analítica Ejecutiva para Alcaldías"
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS.keys(),
        default="info",
        help="Logging level",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    scrape_parser = subparsers.add_parser("scrape", help="Scrape social media data")
    scrape_parser.add_argument(
        "--platform",
        choices=["facebook", "all"],
        default="all",
        help="Platform to scrape",
    )
    scrape_parser.add_argument("--max", type=int, default=0, help="Max items to scrape")

    graph_parser = subparsers.add_parser("graph-scrape", help="Scraping via Facebook Graph API (más estable)")
    graph_parser.add_argument("--token", default="", help="Page Access Token (o usa FB_ACCESS_TOKEN en .env)")
    graph_parser.add_argument("--page-id", default="395582594151511", help="Facebook Page ID")
    graph_parser.add_argument("--page-name", default="Jose Chicas", help="Nombre de la página")
    graph_parser.add_argument("--max", type=int, default=1000, help="Posts objetivo")
    graph_parser.add_argument("--comments", action="store_true", default=True, help="Extraer comentarios también")
    graph_parser.add_argument("--replies", action="store_true", default=True, help="Extraer replies también")
    graph_parser.add_argument("--no-comments", dest="comments", action="store_false", help="Saltar comentarios")
    graph_parser.add_argument("--no-replies", dest="replies", action="store_false", help="Saltar replies")

    deep_parser = subparsers.add_parser("deep-scrape", help="Deep scraping - extracción completa con NLP y anti-ban")
    deep_parser.add_argument("--max", type=int, default=10000, help="Posts objetivo")
    deep_parser.add_argument("--start", default="2025-01-01", help="Fecha inicio (YYYY-MM-DD)")
    deep_parser.add_argument("--page-id", default="395582594151511", help="Facebook Page ID")
    deep_parser.add_argument("--page-name", default="Jose Chicas", help="Nombre de la página")
    deep_parser.add_argument("--headless", action="store_true", help="Modo headless")
    deep_parser.add_argument("--cookies-file", default="cookies.json", help="Archivo de cookies")
    deep_parser.add_argument("--checkpoint-every", type=int, default=50, help="Guardar checkpoint cada N posts")

    analyze_parser = subparsers.add_parser("analyze", help="Generate insights and metrics")
    analyze_parser.add_argument(
        "--platform",
        choices=["facebook", "all"],
        default="all",
        help="Platform to analyze",
    )

    subparsers.add_parser("status", help="Show database status")
    subparsers.add_parser("reset", help="Purge all data from database")
    subparsers.add_parser("export-dashboard", help="Export SQLite data to dashboard/data.js")
    estimate_parser = subparsers.add_parser("estimate", help="Estimate scrape time for target posts")
    estimate_parser.add_argument("--target", type=int, default=20000, help="Target number of posts")
    phase3_parser = subparsers.add_parser("phase3", help="Resume Phase 3 - complete comment extraction")
    phase3_parser.add_argument("--no-replies", action="store_true", help="Skip reply threads")
    phase3_parser.add_argument("--checkpoint-every", type=int, default=50, help="Checkpoint every N posts")

    args = parser.parse_args()

    setup_logging(args.log_level if hasattr(args, "log_level") else "info")

    if not args.command:
        parser.print_help()
        return

    cfg = Config()
    storage = SupabaseStorage()

    if args.command == "scrape":
        cmd_scrape(args, cfg, storage)
    elif args.command == "graph-scrape":
        cmd_graph_scrape(args, cfg, storage)
    elif args.command == "deep-scrape":
        cmd_deep_scrape(args, cfg, storage)
    elif args.command == "analyze":
        cmd_analyze(args, cfg, storage)
    elif args.command == "reset":
        cmd_reset(args, cfg, storage)
    elif args.command == "export-dashboard":
        exported = _export_dashboard_data(storage)
        console.print(f"[bold green]Dashboard exported: {exported} posts → dashboard/data.js[/bold green]")
    elif args.command == "phase3":
        cmd_phase3(args, cfg, storage)
    elif args.command == "status":
        cmd_status(args, cfg, storage)
    elif args.command == "estimate":
        cmd_estimate(args, cfg, storage)


if __name__ == "__main__":
    main()
