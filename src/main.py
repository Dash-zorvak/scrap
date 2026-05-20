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
        get_comments=args.comments,
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
        console.print(f"[bold green]Saved {saved} Facebook posts to Supabase[/bold green]")


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

    console.print(f"[bold green]Análisis completado. Dashboard actualizado en Supabase.[/bold green]")


def cmd_status(args, cfg, storage):
    summary = storage.get_executive_summary()

    table = Table(title="Supabase Database Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="bold")

    table.add_row("Facebook posts", str(summary.get("fb_posts", 0)))
    table.add_row("Facebook comments", str(summary.get("fb_comments", 0)))

    fb_total = summary.get("fb_positive", 0) + summary.get("fb_negative", 0)

    if fb_total > 0:
        fb_pos_pct = (summary.get("fb_positive", 0) / fb_total) * 100
        table.add_row("FB Positive %", f"{fb_pos_pct:.1f}%")

    console.print(table)


def cmd_verify(args, cfg, storage):
    if not storage.local:
        console.print("[red]Error: Local backup not configured[/red]")
        return

    console.print(Panel("[bold cyan]Verificando sincronización Supabase  Local[/bold cyan]"))

    result = storage.verify_sync()
    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return

    table = Table(title="Estado de Sincronización")
    table.add_column("Tabla", style="cyan")
    table.add_column("Supabase", justify="right", style="bold")
    table.add_column("Local", justify="right", style="bold")
    table.add_column("Diferencia", justify="right")
    table.add_column("Estado", justify="center")

    all_match = True
    for tbl, info in result.items():
        sup = info.get("supabase", -1)
        loc = info.get("local", -1)
        diff = info.get("diff")
        match = info.get("match")

        sup_str = str(sup) if sup >= 0 else "[red]error[/red]"
        loc_str = str(loc) if loc >= 0 else "[red]error[/red]"

        if match is True:
            status = "[green]OK[/green]"
        elif match is False:
            status = f"[red]ERROR ({diff:+d})[/red]"
            all_match = False
        else:
            status = "[yellow]?[/yellow]"
            all_match = False

        diff_str = f"{diff:+d}" if diff is not None else "[yellow]?[/yellow]"
        table.add_row(tbl, sup_str, loc_str, diff_str, status)

        if match is False and "only_in_supabase" in info:
            missing = info.get("missing_from_local", [])
            if missing:
                table.add_row(
                    f"  faltan en local",
                    "",
                    "",
                    "",
                    f"[red]{info['only_in_supabase']} IDs[/red]",
                )

    console.print(table)

    if all_match:
        console.print("[bold green]Todas las tablas están sincronizadas[/bold green]")
    else:
        console.print(
            "[yellow]Hay diferencias entre Supabase y el backup local[/yellow]"
        )
        console.print(
            "[dim]Ejecuta un scrapeo completo para re-sincronizar[/dim]"
        )

    console.print(f"\n[dim]Backup local: {storage.local.db_path}[/dim]")


def cmd_sync(args, cfg, storage):
    if not storage.local:
        console.print("[red]Error: Local backup not configured[/red]")
        return

    console.print(Panel("[bold cyan]Sincronizando Supabase  Local Backup[/bold cyan]"))

    local = storage.local
    tables = [
        ("fb_posts", "post_id"),
        ("fb_comments", "comment_id"),
    ]

    local_inserter_map = {
        "fb_posts": local.insert_fb_post,
        "fb_comments": local.insert_fb_comment,
    }

    for table_name, id_col in tables:
        console.print(f"\n[bold]Sincronizando {table_name}...[/bold]")

        supabase_count = 0
        try:
            supabase_count = storage.client.table(table_name).select("*", count="exact").execute().count
        except Exception as e:
            console.print(f"[red]Error getting count for {table_name}: {e}[/red]")
            continue

        local_count = local.count(table_name)
        if supabase_count <= local_count:
            console.print(f"  [green]Ya sincronizado ({local_count} registros)[/green]")
            continue

        missing = supabase_count - local_count
        console.print(f"  Supabase: {supabase_count}, Local: {local_count}  {missing} pendientes")

        synced = 0
        batch_size = 100
        offset = 0

        with Progress(
            TextColumn(f"[progress.description]{{task.description}}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"  Descargando {missing} registros...", total=missing)

            while offset < supabase_count:
                try:
                    rows = storage.client.table(table_name).select("*").order(id_col, desc=True).range(offset, offset + batch_size - 1).execute().data
                except Exception as e:
                    console.print(f"  [red]Error fetching {table_name}: {e}[/red]")
                    break

                if not rows:
                    break

                local_inserter = local_inserter_map[table_name]
                for row in rows:
                    local_inserter(row)
                    synced += 1
                    progress.update(task, advance=1)

                offset += batch_size

        console.print(f"  [green] {synced} registros sincronizados[/green]")

    console.print("\n[bold green]Sincronización completada[/bold green]")


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

    scrape_parser = subparsers.add_parser("scrape", help="Scrape social media data to Supabase")
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
    graph_parser.add_argument("--comments", action="store_true", help="Extraer comentarios también")

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

    verify_parser = subparsers.add_parser("verify", help="Verify sync between Supabase and local backup")
    subparsers.add_parser("sync", help="Sync existing Supabase data to local backup")
    estimate_parser = subparsers.add_parser("estimate", help="Estimate scrape time for target posts")
    estimate_parser.add_argument("--target", type=int, default=20000, help="Target number of posts")

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
    elif args.command == "verify":
        cmd_verify(args, cfg, storage)
    elif args.command == "sync":
        cmd_sync(args, cfg, storage)
    elif args.command == "status":
        cmd_status(args, cfg, storage)
    elif args.command == "estimate":
        cmd_estimate(args, cfg, storage)


if __name__ == "__main__":
    main()
