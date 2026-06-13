#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import time as time_module
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
from src.intelligence.cambridge_index import run_all_detectors, SuppressionEngine

logger = logging.getLogger(__name__)
console = Console()


def timer(func):
    """Decorator that wraps a command function with elapsed time reporting."""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        cmd_name = func.__name__.replace("cmd_", "").replace("_", "-")
        console.print(f"[dim]⏱ Inicio: {datetime.now().strftime('%H:%M:%S')}[/dim]")
        t0 = time_module.time()
        result = func(*args, **kwargs)
        elapsed = time_module.time() - t0
        mins, secs = divmod(int(elapsed), 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            console.print(f"[bold green]✅ {cmd_name} completado en {hrs}h {mins}m {secs}s[/bold green]")
        elif mins > 0:
            console.print(f"[bold green]✅ {cmd_name} completado en {mins}m {secs}s[/bold green]")
        else:
            console.print(f"[bold green]✅ {cmd_name} completado en {secs}s[/bold green]")
        return result
    return wrapper


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


def _resolve_page(args, cfg):
    if getattr(args, "page", None) is not None:
        return cfg.get_page(args.page)
    page_id = getattr(args, "page_id", None) or cfg.FB_PAGE_ID
    page_name = getattr(args, "page_name", None) or cfg.FB_PAGE_NAME
    page_url = getattr(args, "page_url", None) or cfg.FB_PAGE_URL
    result = {"id": page_id, "name": page_name, "url": page_url}
    result["has_id"] = bool(page_id and not page_id.startswith("http"))
    return result


@timer
def cmd_graph_scrape(args, cfg, storage):
    console.print(Panel("[bold green]Graph API SCRAPER[/bold green]"))
    page = _resolve_page(args, cfg)
    token = args.token or cfg.FB_ACCESS_TOKEN
    page_id = page.get("id", "")
    page_name = page.get("name", "?")

    if not page.get("has_id"):
        console.print("[yellow]Esta página no tiene un ID numérico — Graph API no es compatible[/yellow]")
        console.print("[yellow]Usá 'deep-scrape' o 'scrape' para páginas públicas[/yellow]")
        return

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


@timer
def cmd_extract_comments(args, cfg, storage):
    console.print(Panel("[bold yellow]EXTRACT COMMENTS — Fase 2 sobre posts existentes[/bold yellow]"))
    posts = storage.get_fb_posts(limit=10000)
    total = sum(1 for p in posts if p.get("post_url", "").startswith("http"))
    console.print(f"[dim]Posts en DB: {len(posts)} · Con URL válida: {total}[/dim]")

    from src.fb_scraper.deep_scraper import FacebookDeepScraper
    scraper = FacebookDeepScraper(
        cookies_file=args.cookies_file or cfg.FB_COOKIES_FILE or "cookies.json",
        email=cfg.FB_EMAIL,
        password=cfg.FB_PASSWORD,
        headless=getattr(args, "headless", False),
    )
    stats = scraper.extract_comments_from_db(max_posts=args.max)
    console.print(f"\n[bold green]✓ Hecho:[/bold green] {stats['posts_scraped']} posts, {stats['comments_scraped']} comentarios, {stats['errors']} errores")


def cmd_deep_scrape(args, cfg, storage):
    console.print(Panel("[bold red]DEEP SCRAPER - Extracción Completa[/bold red]"))
    page = _resolve_page(args, cfg)
    page_id = page.get("id", "")
    page_name = page.get("name", "?")
    page_url = page.get("url", "")

    search_keyword = getattr(args, "search", "")
    cli_page_url = getattr(args, "page_url", "")

    page_urls = None
    if search_keyword:
        page_urls = []
    elif cli_page_url:
        page_urls = [cli_page_url]
    elif cfg.deep_page_urls:
        page_urls = cfg.deep_page_urls
    else:
        p_url = page.get("url", "")
        if p_url:
            page_urls = [p_url]
        elif page_id:
            page_urls = [f"https://www.facebook.com/{page_id}"]

    if search_keyword:
        console.print(f"[bold]Búsqueda:[/bold] {search_keyword}")
    elif page_urls:
        console.print(f"[bold]Páginas ({len(page_urls)}):[/bold]")
        for u in page_urls:
            console.print(f"  • {u}")
    else:
        console.print(f"[bold]Page ID:[/bold] {page_id}")
    console.print(f"[bold]Target:[/bold] {args.max} posts por página")
    console.print(f"[bold]Headless:[/bold] {'sí' if args.headless else 'no'}")

    from src.fb_scraper.deep_scraper import FacebookDeepScraper

    scraper = FacebookDeepScraper(
        page_url=page_url or f"https://www.facebook.com/{page_id}",
        page_name=page_name,
        search_keyword=search_keyword,
        page_urls=page_urls,
        cookies_file=args.cookies_file,
        email=cfg.FB_EMAIL,
        password=cfg.FB_PASSWORD,
        headless=args.headless,
    )

    stats = scraper.scrape(
        max_posts=args.max,
        checkpoint_every=args.checkpoint_every,
    )

    console.print(f"\n[bold green]Deep scraping completado[/bold green]")
    console.print(f"Posts: {stats['posts_scraped']}")
    console.print(f"Duplicados: {stats['posts_duplicated']}")


@timer
def cmd_enrich(args, cfg, storage):
    """Enrich NULL-date posts in externos.db (standalone, resumible)."""
    console.print(Panel("[bold cyan]ENRICH — Fechas faltantes en externos.db[/bold cyan]"))
    from src.fb_scraper.deep_scraper import run_enrich_cli
    count = run_enrich_cli(
        cookies_file=args.cookies_file or cfg.FB_COOKIES_FILE or "cookies.json",
        headless=args.headless,
        email=cfg.FB_EMAIL,
        password=cfg.FB_PASSWORD,
        max_posts=args.max,
    )
    console.print(f"\n[bold green]✓ Enrichment: {count} posts enriquecidos[/bold green]")


@timer
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





@timer
def cmd_analyze(args, cfg, storage):
    console.print(Panel("[bold yellow]Generating analysis and insights...[/bold yellow]"))

    if not getattr(args, "no_reclassify", False):
        from src.analyzer.topic_detection import get_main_topic, detect_zona
        posts = storage.get_fb_posts(limit=10000)
        updated = 0
        for p in posts:
            topic = get_main_topic(p.get("message", ""))
            zona = detect_zona(p.get("message", ""))
            needs_update = False
            if topic and topic != p.get("topic_category", ""):
                p["topic_category"] = topic
                needs_update = True
            if zona and zona != p.get("zona", ""):
                p["zona"] = zona
                needs_update = True
            if needs_update:
                storage.insert_fb_post(p)
                updated += 1
        if updated:
            console.print(f"[green]Reclassified {updated} posts (topic/zona)[/green]")

    from src.analyzer.topic_detection import extract_problematicas
    all_posts = storage.get_fb_posts(limit=10000)
    problematica_count = 0
    for p in all_posts:
        probs = extract_problematicas(p.get("message", ""), p.get("sentiment", ""))
        for prob in probs:
            storage.insert_problematica({
                "platform": "facebook",
                "post_id": p.get("post_id", ""),
                "topic": prob.get("topic", ""),
                "zona": prob.get("zona", ""),
                "message": prob.get("text_preview", ""),
                "sentiment": p.get("sentiment", ""),
                "sentiment_score": p.get("sentiment_score", 0),
            })
            problematica_count += 1
    if problematica_count:
        console.print(f"[green]Extracted {problematica_count} problematicas[/green]")

    metrics_calc = ExecutiveMetrics(storage)

    fb_metrics = metrics_calc.generate_daily_metrics("facebook")
    if fb_metrics:
        storage.insert_daily_metric(fb_metrics)
        console.print(f"[green]Facebook metrics: NSI={fb_metrics.get('nsi')}, CAI={fb_metrics.get('cai')}[/green]")

    fb_insights = metrics_calc.generate_insights("facebook")
    for insight in fb_insights[:5]:
        storage.insert_insight(insight)
    console.print(f"[green]Generated {len(fb_insights)} Facebook insights[/green]")

    posts = storage.get_fb_posts(limit=10000)
    intelligence = run_all_detectors(posts, SuppressionEngine())
    alert_count = len(intelligence["alerts"])
    if alert_count > 0:
        console.print(f"[bold red]⚠ {alert_count} alertas generadas[/bold red]")
        for a in intelligence["alerts"][:3]:
            color = {4: "red", 3: "red", 2: "yellow", 1: "dim"}.get(a["severity"], "dim")
            console.print(f"  [bold {color}]{a['title']}[/bold {color}]")
    console.print(f"[bold green]Análisis completado.[/bold green]")


@timer
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





@timer
def cmd_phase3(args, cfg, storage):
    console.print(Panel("[bold cyan]PHASE 3 RESUME — Complete Comment Extraction[/bold cyan]"))
    page = _resolve_page(args, cfg)
    page_id = page.get("id", "")
    page_name = page.get("name", "?")
    if not page.get("has_id"):
        console.print("[yellow]Phase 3 solo funciona con Graph API (requiere page_id numérico)[/yellow]")
        return
    console.print(f"[bold]Página:[/bold] {page_name} ({page_id})")
    from src.fb_scraper.phase3_resume import Phase3Resumer

    resumer = Phase3Resumer(access_token=cfg.FB_ACCESS_TOKEN, page_id=page_id)
    stats = resumer.run(
        get_replies=not getattr(args, "no_replies", False),
        checkpoint_every=getattr(args, "checkpoint_every", 50),
    )
    console.print(f"[green]Done: {stats['posts_processed']} posts, {stats['comments_scraped']} comments, {stats['replies_scraped']} replies, {stats['errors']} errors[/green]")


@timer
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


@timer
def cmd_nlp(args, cfg, storage):
    from src.analyzer.nlp_pipeline import process_pending, process_all_collocations, process_latent_topics
    console.print(Panel("[bold magenta]NLP PIPELINE — Deep Text Analysis[/bold magenta]"))
    batch = args.batch or 500
    console.print(f"[bold]Batch size:[/bold] {batch}")
    stats = process_pending(storage, batch_size=batch)
    console.print(f"[green]Posts processed:[/green] {stats['posts']}")
    console.print(f"[green]Comments processed:[/green] {stats['comments']}")
    if stats['errors']:
        console.print(f"[red]Errors:[/red] {stats['errors']}")
    if args.collocations:
        console.print("[yellow]Extracting collocations from corpus...[/yellow]")
        coll = process_all_collocations(storage)
        n = len(coll.get("bigrams", {}).get("ngrams", {}))
        console.print(f"[green]{n} bigrams extracted[/green]")
    if args.topics:
        console.print(f"[yellow]Extracting {args.n_topics} latent topics (LDA)...[/yellow]")
        topics = process_latent_topics(storage, n_topics=args.n_topics)
        n_t = len(topics.get("topics", []))
        console.print(f"[green]{n_t} topics extracted from {topics.get('n_docs', 0)} documents[/green]")
    pending_posts = storage.count_nlp_pending("post")
    pending_comments = storage.count_nlp_pending("comment")
    if pending_posts + pending_comments > 0:
        console.print(f"[dim]Pending: {pending_posts} posts, {pending_comments} comments[/dim]")
    else:
        console.print(f"[bold green]All items processed[/bold green]")


@timer
def cmd_estimate(args, cfg, storage):
    import importlib.util
    spec = importlib.util.spec_from_file_location("estimation", os.path.join(os.path.dirname(__file__), "analyzer", "estimation.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    target = getattr(args, "target", 20000)
    results, total_min, total_hr, cpp, tc = mod.calc_metrics(target)
    console.print(Panel(f"[bold cyan]TIME ESTIMATION — {target:,} Posts[/bold cyan]"))
    console.print(mod.format_table(results, total_min, total_hr, cpp, tc, target))


@timer
def cmd_cambridge(args, cfg, storage):
    from src.intelligence.cambridge_index import run_all_detectors, SuppressionEngine
    import json

    console.print(Panel("[bold magenta]Cambridge Index — Alertas Predictivas[/bold magenta]"))

    posts = storage.get_fb_posts(limit=10000)
    if not posts:
        console.print("[yellow]No hay datos para analizar[/yellow]")
        return

    engine = SuppressionEngine()
    result = run_all_detectors(posts, engine)
    alerts = result.get("alerts", [])
    ts = result.get("topic_sensitivity", {})

    console.print(f"[bold]Posts analizados:[/bold] {len(posts)}")
    console.print(f"[bold]Alertas activas:[/bold] {len(alerts)}")

    if args.json:
        console.print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return

    if alerts:
        table = Table(title="Alertas Cambridge")
        table.add_column("Severidad", style="bold")
        table.add_column("Tipo", style="cyan")
        table.add_column("Título", style="white")
        table.add_column("Score", justify="right")
        sev_colors = {1: "dim", 2: "yellow", 3: "red", 4: "bold red"}
        for a in alerts:
            color = sev_colors.get(a.get("severity", 1), "dim")
            table.add_row(
                f"[{color}]{'★' * a.get('severity', 1)}[/{color}]",
                a.get("type", ""),
                a.get("title", "")[:50],
                str(round(a.get("score", 0), 2)),
            )
        console.print(table)

    if ts:
        base_vals = {k: v.get("adjusted", v.get("base", 1.0)) for k, v in ts.items()}
        table2 = Table(title="Sensibilidad por Tópico")
        table2.add_column("Tópico", style="cyan")
        table2.add_column("TS", justify="right")
        table2.add_column("Posts", justify="right")
        ts_color = lambda v: "red" if v >= 1.4 else "yellow" if v >= 1.2 else "green"
        for topic, val in sorted(base_vals.items(), key=lambda x: -x[1]):
            info = ts.get(topic, {})
            adj = info.get("adjusted", info.get("base", 1.0))
            table2.add_row(
                topic or "unknown",
                f"[{ts_color(adj)}]{adj:.2f}[/{ts_color(adj)}]",
                str(info.get("posts", 0)),
            )
        console.print(table2)

    summary = result.get("alert_summary", {})
    if summary:
        suppressed = summary.get("suppressed", 0)
        console.print(f"\n[bold]Resumen:[/bold] {summary.get('total', 0)} alertas, {suppressed} suprimidas")


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
    graph_parser.add_argument("--page-id", default="", help="Facebook Page ID (usa FB_PAGES o FB_PAGE_ID de .env)")
    graph_parser.add_argument("--page-name", default="", help="Nombre de la página")
    graph_parser.add_argument("--page", type=int, default=None, help="Índice de página en FB_PAGES (0-based)")
    graph_parser.add_argument("--max", type=int, default=1000, help="Posts objetivo")
    graph_parser.add_argument("--comments", action="store_true", default=True, help="Extraer comentarios también")
    graph_parser.add_argument("--replies", action="store_true", default=True, help="Extraer replies también")
    graph_parser.add_argument("--no-comments", dest="comments", action="store_false", help="Saltar comentarios")
    graph_parser.add_argument("--no-replies", dest="replies", action="store_false", help="Saltar replies")

    deep_parser = subparsers.add_parser("deep-scrape", help="Deep scraping - extracción completa con NLP y anti-ban")
    deep_parser.add_argument("--max", type=int, default=10000, help="Posts objetivo")
    deep_parser.add_argument("--search", default="", help="Buscar posts por keyword (ej: 'Jose Chicas')")
    deep_parser.add_argument("--page-id", default="", help="Facebook Page ID (usa FB_PAGES o FB_PAGE_ID de .env)")
    deep_parser.add_argument("--page-name", default="", help="Nombre de la página")
    deep_parser.add_argument("--page-url", default="", help="URL completa de la página (para páginas sin ID numérico)")
    deep_parser.add_argument("--page", type=int, default=None, help="Índice de página en FB_PAGES (0-based)")
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
    analyze_parser.add_argument("--reclassify", dest="no_reclassify", action="store_false", default=False, help="Re-run topic/zone detection on all posts")
    analyze_parser.add_argument("--no-reclassify", dest="no_reclassify", action="store_true", help="Skip reclassification")

    subparsers.add_parser("status", help="Show database status")
    subparsers.add_parser("reset", help="Purge all data from database")
    nlp_parser = subparsers.add_parser("nlp", help="Run NLP pipeline (emotions, entities, collocations)")
    nlp_parser.add_argument("--batch", type=int, default=500, help="Batch size to process")
    nlp_parser.add_argument("--collocations", action="store_true", default=True, help="Extract collocations from corpus")
    nlp_parser.add_argument("--no-collocations", dest="collocations", action="store_false", help="Skip collocation extraction")
    nlp_parser.add_argument("--topics", action="store_true", default=True, help="Extract latent topics (LDA)")
    nlp_parser.add_argument("--no-topics", dest="topics", action="store_false", help="Skip latent topic extraction")
    nlp_parser.add_argument("--n-topics", type=int, default=8, help="Number of latent topics")
    estimate_parser = subparsers.add_parser("estimate", help="Estimate scrape time for target posts")
    estimate_parser.add_argument("--target", type=int, default=20000, help="Target number of posts")
    phase3_parser = subparsers.add_parser("phase3", help="Resume Phase 3 - complete comment extraction")
    phase3_parser.add_argument("--no-replies", action="store_true", help="Skip reply threads")
    phase3_parser.add_argument("--checkpoint-every", type=int, default=50, help="Checkpoint every N posts")
    phase3_parser.add_argument("--page", type=int, default=None, help="Índice de página en FB_PAGES (0-based)")
    phase3_parser.add_argument("--page-id", default="", help="Facebook Page ID")
    phase3_parser.add_argument("--page-name", default="", help="Nombre de la página")

    extract_parser = subparsers.add_parser("extract-comments", help="Extraer comentarios de posts ya existentes en DB (Fase 2)")
    extract_parser.add_argument("--max", type=int, default=500, help="Posts a procesar")
    extract_parser.add_argument("--cookies-file", default="", help="Archivo de cookies")
    extract_parser.add_argument("--headless", action="store_true", help="Modo headless")

    cambridge_parser = subparsers.add_parser("cambridge", help="Cambridge Index - alertas predictivas y sensibilidad por tópico")
    cambridge_parser.add_argument("--days", type=int, default=30, help="Ventana de análisis en días")
    cambridge_parser.add_argument("--json", action="store_true", help="Output JSON en lugar de tabla")

    enrich_parser = subparsers.add_parser("enrich", help="Enriquecer fechas NULL en externos.db (resumible)")
    enrich_parser.add_argument("--max", type=int, default=0, help="Máximo de posts a procesar (0 = todos)")
    enrich_parser.add_argument("--cookies-file", default="cookies.json", help="Archivo de cookies")
    enrich_parser.add_argument("--headless", action="store_true", help="Modo headless (sin ventana)")

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
    elif args.command == "extract-comments":
        cmd_extract_comments(args, cfg, storage)
    elif args.command == "deep-scrape":
        cmd_deep_scrape(args, cfg, storage)
    elif args.command == "enrich":
        cmd_enrich(args, cfg, storage)
    elif args.command == "analyze":
        cmd_analyze(args, cfg, storage)
    elif args.command == "reset":
        cmd_reset(args, cfg, storage)
    elif args.command == "nlp":
        cmd_nlp(args, cfg, storage)
    elif args.command == "phase3":
        cmd_phase3(args, cfg, storage)
    elif args.command == "status":
        cmd_status(args, cfg, storage)
    elif args.command == "estimate":
        cmd_estimate(args, cfg, storage)
    elif args.command == "cambridge":
        cmd_cambridge(args, cfg, storage)


if __name__ == "__main__":
    main()
