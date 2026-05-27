#!/usr/bin/env python3
"""
Deep Scraper - Extracción desde feed vía Playwright
=====================================================
Usado para páginas SIN acceso a Graph API.
Extrae posts scrolleando el feed, expandiendo comentarios inline
(sin navegar a permalinks que disparan captcha).

Flujo:
  1. Autenticación: cookies → email/password → guarda cookies frescas
  2. Scroll del feed extrayendo posts del DOM
  3. Por cada post: expande comentarios inline y extrae
  4. Checkpoint por URL de post
"""

import hashlib
import json
import logging
import os
import random
import subprocess
from playwright_stealth import Stealth
import re
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from src.storage.supabase_client import SupabaseStorage
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona
from src.notifications.telegram import TelegramNotifier
from src.config import Config

logger = logging.getLogger(__name__)

FB_BASE = "https://www.facebook.com"

REQUIRED_COOKIES = {"c_user", "xs"}


class TimeoutGuard:
    """Hard kill timer for hung Playwright processes."""
    def __init__(self, seconds: int = 120):
        self.seconds = seconds
        self._old = None

    def __enter__(self):
        self._old = signal.signal(signal.SIGALRM, self._handler)
        signal.alarm(self.seconds)
        return self

    def __exit__(self, *args):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self._old)

    @staticmethod
    def _handler(signum, frame):
        raise TimeoutError(f"Scraper timed out after {signum}s — browser process likely dead")


class DeepAnalyzer:
    """Análisis NLP para cada post y comentario."""

    def __init__(self):
        self.sentiment = SentimentAnalyzer()

    def analyze(self, text: str) -> Dict[str, Any]:
        if not text or len(text.strip()) < 3:
            return self._empty_analysis()
        sentiment, score = self.sentiment.analyze(text)
        return {
            "sentiment": sentiment,
            "sentiment_score": score,
            "topic_category": get_main_topic(text),
            "zona": detect_zona(text),
            "hashtags": re.findall(r"#(\w+)", text.lower()),
            "mentions": re.findall(r"@(\w+)", text),
            "word_count": len(text.split()),
            "char_count": len(text),
        }

    def _empty_analysis(self) -> Dict:
        return {
            "sentiment": "neutral", "sentiment_score": 0,
            "topic_category": "", "zona": "",
            "hashtags": [], "mentions": [],
            "word_count": 0, "char_count": 0,
        }


class CheckpointManager:
    """Checkpoints para persistencia y recuperación."""

    def __init__(self, platform: str = "facebook"):
        self.checkpoint_file = f"data/{platform}_checkpoint.json"
        Path("data").mkdir(exist_ok=True)

    def save(self, state: Dict[str, Any]):
        state["last_updated"] = datetime.now().isoformat()
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)
        logger.info(f"Checkpoint saved: {self.checkpoint_file}")

    def load(self) -> Optional[Dict[str, Any]]:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading checkpoint: {e}")
        return None

    def get_scraped_post_ids(self) -> Set[str]:
        state = self.load()
        if state:
            return set(state.get("scraped_post_ids", []))
        return set()


class AntiBan:
    """Anti-ban: delays humanos, detección, backoff."""

    def __init__(self):
        self.ban_detected = False
        self.last_request_time = 0

    def human_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        time.sleep(min_s + (max_s - min_s) * random.random())

    def progressive_delay(self, count: int):
        base = 1.5
        if count < 10:
            return base + random.uniform(0.5, 1)
        elif count < 30:
            return base + random.uniform(1, 2)
        else:
            return base + random.uniform(1.5, 3)

    def detect_ban(self, page: Page) -> bool:
        try:
            url = page.url.lower()
            if any(s in url for s in ["checkpoint", "captcha", "blocked", "challenge"]):
                logger.warning(f"BAN DETECTED via URL: {url}")
                self.ban_detected = True
                return True

            visible_challenge = page.locator(
                '#captcha, '
                'div[class*="checkpoint"], '
                'div[aria-label*="captcha"], '
                'form[action*="captcha"]'
            ).first
            if visible_challenge.count() > 0:
                logger.warning("BAN DETECTED: visible challenge element")
                self.ban_detected = True
                return True

            text = page.content().lower()
            signs = [
                "has been temporarily blocked", "has been restricted",
                "verifica tu identidad", "bloqueado temporalmente",
            ]
            for s in signs:
                if s in text:
                    self.ban_detected = True
                    logger.warning(f"BAN DETECTED: {s}")
                    return True
            return False
        except Exception as e:
            logger.debug(f"Ban check error: {e}")
            return False


class FacebookDeepScraper:
    """
    Scraper Facebook vía Playwright.
    Dos modos:
      - search_keyword: busca posts públicos por keyword (ej: "Jose Chicas")
      - page_url: extrae posts de una página específica (si es accesible)
    """

    def __init__(
        self,
        page_url: str = "",
        page_name: str = "",
        search_keyword: str = "",
        page_urls: Optional[list] = None,
        cookies_file: str = "",
        email: str = "",
        password: str = "",
        headless: bool = False,
    ):
        self.page_url = page_url
        self.page_name = page_name
        self.search_keyword = search_keyword
        self.cookies_file = cookies_file
        self.email = email
        self.password = password
        self.headless = headless

        if page_urls is not None:
            self.page_urls = page_urls
        elif Config().deep_page_urls:
            self.page_urls = Config().deep_page_urls
        else:
            self.page_urls = []

        self.storage = SupabaseStorage()
        self.analyzer = DeepAnalyzer()
        self.notifier = TelegramNotifier()
        self.checkpoint = CheckpointManager("facebook")
        self.antiban = AntiBan()

        self.stats = {
            "posts_scraped": 0,
            "posts_duplicated": 0,
            "comments_scraped": 0,
            "errors": 0,
            "start_time": None,
            "checkpoints_saved": 0,
        }
        self._pending_engagement = []  # (post_id, post_url)

    # ── Browser lifecycle ──────────────────────────────────────

    def _create_browser(self):
        from playwright.sync_api import sync_playwright
        launch_opts = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--window-size=1366,768",
            ],
        }
        p = sync_playwright().start()
        browser = p.chromium.launch(**launch_opts)
        return p, browser

    def _load_cookies(self, context: BrowserContext):
        if not self.cookies_file:
            return
        path = Path(self.cookies_file)
        if not path.exists():
            logger.warning(f"Cookies file not found: {self.cookies_file}")
            return
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                raw = raw.get("facebook", raw.get("cookies", []))
            if isinstance(raw, list):
                mapped = []
                for c in raw:
                    ss = c.get("sameSite")
                    if ss is None:
                        c["sameSite"] = "None"
                    elif isinstance(ss, str):
                        s = ss.lower()
                        if s == "no_restriction":
                            c["sameSite"] = "None"
                        elif s in ("strict", "lax"):
                            c["sameSite"] = s.capitalize()
                    mapped.append(c)
                context.add_cookies(mapped)
                logger.info(f"Loaded {len(mapped)} cookies from {self.cookies_file}")
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")

    def _save_cookies(self, context: BrowserContext):
        if not self.cookies_file:
            return
        try:
            cookies = context.cookies()
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")

    def _authenticate(self, page: Page, context: BrowserContext) -> bool:
        """Intenta autenticar: cookies primero, email/password como fallback."""
        self._load_cookies(context)

        page.goto(FB_BASE, timeout=30000, wait_until="domcontentloaded")
        self.antiban.human_delay(2, 4)

        cookies = context.cookies()
        cookie_names = {c["name"] for c in cookies}
        if REQUIRED_COOKIES.issubset(cookie_names):
            logger.info("Session valid via cookies")
            self._save_cookies(context)
            return True

        logger.warning("Cookies expired — trying email/password login")
        if not self.email or not self.password:
            logger.error("No credentials available for login")
            return False

        try:
            page.goto(f"{FB_BASE}/login", timeout=30000)
            self.antiban.human_delay(3, 5)

            email_input = page.locator('input[name="email"], input[id="email"], input[autocomplete="username"]').first
            email_input.fill(self.email)
            self.antiban.human_delay(1, 2)

            pass_input = page.locator('input[name="pass"], input[id="pass"], input[autocomplete="current-password"]').first
            pass_input.fill(self.password)
            self.antiban.human_delay(1, 2)

            login_btn = page.locator(
                'button[name="login"], '
                'button[id="loginbutton"], '
                'button[type="submit"]'
            ).first
            login_btn.click()
            page.wait_for_load_state("networkidle", timeout=30000)
            self.antiban.human_delay(3, 5)

            if "checkpoint" in page.url or "login" in page.url:
                logger.error("Login blocked / checkpoint required")
                return False

            logger.info("Login successful")
            self._save_cookies(context)
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    # ── Post extraction via JavaScript (robust against DOM changes) ──

    def _scrape_search_results(self, page, seen_ids: set, max_posts: int) -> list:
        """Extrae posts del feed via JS: busca enlaces /posts/ y sube al contenedor padre."""
        js_extract = """
        () => {
            function postIdFromMessage(msg) {
                let h1 = 0, h2 = 0;
                const s = msg.substring(0, 500);
                for (let i = 0; i < s.length; i++) {
                    const c = s.charCodeAt(i);
                    h1 = ((h1 << 5) - h1) + c; h1 |= 0;
                    h2 = ((h2 << 7) - h2) + c; h2 |= 0;
                }
                return 'deep_' + ((h1 >>> 0).toString(16).padStart(8,'0') + (h2 >>> 0).toString(16).padStart(8,'0')).substring(0,16);
            }

            function parseNum(s) {
                if (!s) return 0;
                s = s.trim();
                let mult = 1;
                if (/mil/i.test(s) || /K/i.test(s)) { mult = 1000; s = s.replace(/mil/i, '').replace(/K/i, '').trim(); }
                if (/M/i.test(s)) { mult = 1000000; s = s.replace(/M/i, '').trim(); }
                s = s.replace(/\\./g, '').replace(',', '.');
                const n = parseFloat(s);
                return isNaN(n) ? 0 : Math.round(n * mult);
            }

            // Find ALL unique post links on the page
            const linkSet = new Set();
            const linkEls = document.querySelectorAll('a[href*="/posts/"], a[href*="story.php"], a[href*="story_fbid"]');
            for (const link of linkEls) {
                const href = link.getAttribute('href') || link.href || '';
                const m = href.match(/\\/posts\\/([a-zA-Z0-9_.-]+)/) || href.match(/story_fbid=([a-zA-Z0-9_-]+)/);
                if (m) linkSet.add(m[1]);
            }

            const posts = [];
            const seenIds = new Set();

            for (const postId of linkSet) {
                if (seenIds.has(postId)) continue;
                seenIds.add(postId);

                // Find the link element for this postId
                const link = document.querySelector('a[href*="/posts/' + postId + '"], a[href*="story_fbid=' + postId + '"]');
                if (!link) continue;

                const href = link.getAttribute('href') || link.href || '';
                const postUrl = href.startsWith('http') ? href : 'https://www.facebook.com' + href;

                // Walk up to find the post container (max 15 levels)
                let container = link.parentElement;
                for (let i = 0; i < 15 && container; i++) {
                    if (container.getAttribute('role') === 'article') break;
                    container = container.parentElement;
                }
                if (!container) continue;

                const innerText = container.innerText || '';

                // --- Message ---
                let message = '';
                const msgEls = container.querySelectorAll('div[dir="auto"]');
                for (const msgEl of msgEls) {
                    const t = msgEl.innerText.trim();
                    if (t.length > 15 && !t.startsWith('http')) { message = t; break; }
                }
                if (!message) message = (container.innerText || '').substring(0, 500).trim();
                if (message.length < 5) continue;

                // --- Author ---
                let author = '';
                const anchors = container.querySelectorAll('a');
                for (const a of anchors) {
                    const t = a.innerText.trim();
                    if (t && t.length < 50 && t.length > 2 && !t.startsWith('http') && !/^\\d+$/.test(t)
                        && t !== 'Seguir' && t !== 'Facebook') {
                        author = t; break;
                    }
                }

                // --- Timestamp (múltiples selectores de respaldo) ---
                let created = null;
                const tsSelectors = [
                    'abbr[data-utime]',
                    'span[data-utime]',
                    'time[datetime]',
                    'abbr[title]',
                ];
                for (const sel of tsSelectors) {
                    const el = container.querySelector(sel);
                    if (!el) continue;
                    if (sel === 'time[datetime]') {
                        const dt = el.getAttribute('datetime');
                        if (dt) { const ms = Date.parse(dt); if (!isNaN(ms)) { created = ms; break; } }
                    } else if (sel === 'abbr[title]') {
                        const t = el.getAttribute('title');
                        if (t) { const ms = Date.parse(t); if (!isNaN(ms)) { created = ms; break; } }
                    } else {
                        const u = el.getAttribute('data-utime') || el.getAttribute('utime');
                        if (u) { created = parseInt(u) * 1000; break; }
                    }
                }

                // --- Fallback: tiempo relativo en texto del contenedor ---
                if (!created) {
                    const lower = innerText.toLowerCase();
                    const relTime = lower.match(/(\d+)\s*(min|minutos?|horas?|días?|día|semanas?|sem|mes|meses?|años?|año)\s*/);
                    if (relTime) {
                        const num = parseInt(relTime[1]);
                        const unit = relTime[2];
                        const now = Date.now();
                        if (unit.startsWith('min')) created = now - num * 60 * 1000;
                        else if (unit.startsWith('h')) created = now - num * 3600 * 1000;
                        else if (unit.startsWith('d') || unit.startsWith('sem')) {
                            const multiplier = unit.startsWith('sem') ? 7 : 1;
                            created = now - num * multiplier * 86400 * 1000;
                        }
                        else if (unit.startsWith('mes')) created = now - num * 30 * 86400 * 1000;
                        else if (unit.startsWith('a')) created = now - num * 365 * 86400 * 1000;
                    }
                }

                // --- Engagement: aria-labels dentro del contenedor ---
                let lk=0, lv=0, hh=0, wo=0, sd=0, ag=0, cc=0, sc=0, vw=0;
                const ariaLabels = container.querySelectorAll('[aria-label]');
                for (const al of ariaLabels) {
                    const label = al.getAttribute('aria-label') || '';
                    const ll = label.toLowerCase();
                    const nM = label.match(/([\\d,.]+)\\s*(mil|k|m)?/i);
                    if (!nM) continue;
                    const val = parseNum(nM[1] + (nM[2] || ''));
                    if (val === 0) continue;
                    if (ll.includes('me gusta') || ll.includes('like')) lk = Math.max(lk, val);
                    else if (ll.includes('me encanta') || ll.includes('love')) lv = Math.max(lv, val);
                    else if (ll.includes('haha') || ll.includes('me divierte')) hh = Math.max(hh, val);
                    else if (ll.includes('wow') || ll.includes('me sorprende')) wo = Math.max(wo, val);
                    else if (ll.includes('triste') || ll.includes('me entristece')) sd = Math.max(sd, val);
                    else if (ll.includes('enojo') || ll.includes('me enfada')) ag = Math.max(ag, val);
                    else if (ll.includes('comentario') || ll.includes('comment')) cc = Math.max(cc, val);
                    else if (ll.includes('compartido') || ll.includes('shares?')) sc = Math.max(sc, val);
                    else if (ll.includes('vista') || ll.includes('views?')) vw = Math.max(vw, val);
                }

                // --- Fallback: texto del contenedor para comments/shares/views ---
                const lower = innerText.toLowerCase();
                if (!cc) {
                    const m = lower.match(/([\\d,.]+(?:mil|k|m)?)\\s*(comentario|comment)/i);
                    if (m) cc = parseNum(m[1]);
                }
                if (!sc) {
                    const m = lower.match(/([\\d,.]+(?:mil|k|m)?)\\s*(compartido|shares?)/i);
                    if (m) sc = parseNum(m[1]);
                }
                if (!vw) {
                    const m = lower.match(/([\\d,.]+(?:mil|k|m)?)\\s*(vistas?|views?|reproducciones?|visualizaciones?|reprodujo|plays?)/i);
                    if (m) vw = parseNum(m[1]);
                }

                posts.push({
                    postId, postUrl, message, author, created,
                    lk, lv, hh, wo, sd, ag, cc, sc, vw
                });
            }

            return posts;
        }
        """
        raw_posts = page.evaluate(js_extract)
        logger.info(f"JS extraction found {len(raw_posts)} raw posts")
        if raw_posts:
            logger.info(f"  First raw msg: {(raw_posts[0].get('message') or '')[:80]}")
        results = []
        dup_counter = 0

        for data in raw_posts:
            post_id = data.get("postId", "")
            msg_preview = (data.get("message") or "")[:80]
            if not post_id:
                logger.debug(f"  Skipping (no postId): {msg_preview}")
                continue
            if post_id in seen_ids:
                dup_counter += 1
                post_id = f"{post_id}_{dup_counter}"
                if post_id in seen_ids:
                    logger.debug(f"  Skipping (seen after rebase): {msg_preview}")
                    continue
            seen_ids.add(post_id)

            message = (data.get("message") or "")[:10000]
            author = data.get("author") or self.search_keyword or "Search Result"
            created_ts = data.get("created")
            created_time = datetime.fromtimestamp(created_ts / 1000) if created_ts else None

            analysis = self.analyzer.analyze(message)

            post_url = data.get("postUrl", "") or (f"{FB_BASE}/posts/{post_id}" if not post_id.startswith("deep_") else "")
            page_id = data.get("postUrl", "").rstrip("/").split("/")[-2] if "/posts/" in post_url else f"page:{self.page_name or self.search_keyword}"

            results.append({
                "post_id": post_id,
                "page_id": page_id,
                "page_name": author,
                "message": message,
                "created_time": created_time,
                "likes_count": data.get("lk", 0) or 0,
                "loves_count": data.get("lv", 0) or 0,
                "hahas_count": data.get("hh", 0) or 0,
                "wows_count": data.get("wo", 0) or 0,
                "sads_count": data.get("sd", 0) or 0,
                "angrys_count": data.get("ag", 0) or 0,
                "comments_count": data.get("cc", 0) or 0,
                "shares_count": data.get("sc", 0) or 0,
                "views_count": data.get("vw", 0) or 0,
                "post_url": post_url,
                "source": "deep_scraper",
                **analysis,
            })

        return results

    @staticmethod
    def _parse_number(text: str) -> int:
        text = text.strip().upper()
        m = 1
        if "K" in text:
            m = 1000
            text = text.replace("K", "")
        elif "M" in text:
            m = 1_000_000
            text = text.replace("M", "")
        try:
            return int(float(text) * m)
        except ValueError:
            return 0

    # ── Inline comment extraction ──────────────────────────────

    def _expand_comments_inline(self, page: Page):
        """Expande comentarios en el feed sin navegar."""
        patterns = [
            "Ver más comentarios", "View more comments",
            "Ver las respuestas", "View replies",
            "Ver más respuestas", "View more replies",
        ]
        for _ in range(30):
            clicked = False
            for text in patterns:
                try:
                    btns = page.locator(
                        f'button:has-text("{text}"), div[role="button"]:has-text("{text}"), a:has-text("{text}")'
                    ).all()
                    for btn in btns:
                        try:
                            if btn.is_visible():
                                btn.click()
                                self.antiban.human_delay(1, 2)
                                clicked = True
                        except Exception:
                            pass
                except Exception:
                    pass
            if not clicked:
                break

    def _extract_all_comments(self, page: Page, post_id: str = "") -> List[Dict]:
        """Expande y extrae TODOS los comentarios visibles en la página actual."""
        comments = []
        seen_sigs = set()

        for _ in range(3):
            self._expand_comments_inline(page)
            self.antiban.human_delay(1, 2)

        try:
            containers = page.query_selector_all('[data-commentid]')

            for el in containers:
                try:
                    raw = el.inner_text().strip()
                    if not raw or len(raw) < 5:
                        continue
                    sig = hashlib.md5(raw.encode()).hexdigest()
                    if sig in seen_sigs:
                        continue
                    seen_sigs.add(sig)

                    comment_id = el.get_attribute("data-commentid") or f"df_{sig[:12]}"

                    author = ""
                    for sel in ['a[href*="/user/"]', 'a[href*="/profile/"]', 'strong', 'span[role="link"]']:
                        sub = el.query_selector(sel)
                        if sub:
                            t = sub.inner_text().strip()
                            if t and len(t) < 100:
                                author = t
                                break

                    msg = raw
                    for sel in ['div[dir="auto"]', 'span[dir="auto"]']:
                        sub = el.query_selector(sel)
                        if sub:
                            t = sub.inner_text().strip()
                            if len(t) > 5:
                                msg = t
                                break

                    likes = 0
                    spans = el.query_selector_all('span[aria-label*="me gusta"], span[aria-label*="like"]')
                    for sp in spans:
                        m = re.search(r"(\d+)", sp.inner_text())
                        if m:
                            likes = int(m.group(1))

                    analysis = self.analyzer.analyze(msg)

                    # Extract timestamp from comment container
                    comment_created = None
                    try:
                        ts_el = el.query_selector('abbr[data-utime]')
                        if ts_el:
                            ut = ts_el.get_attribute('data-utime')
                            if ut:
                                comment_created = datetime.fromtimestamp(int(ut))
                    except Exception:
                        pass

                    comments.append({
                        "comment_id": comment_id,
                        "post_id": post_id,
                        "message": msg[:5000],
                        "author_name": author or "Anonymous",
                        "created_time": comment_created,
                        "like_count": likes,
                        **analysis,
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Error extracting comments: {e}")

        return comments

    # ── Main scrape ────────────────────────────────────────────

    def _get_target_url(self) -> str:
        if self.search_keyword:
            return f"{FB_BASE}/search/posts?q={self.search_keyword.replace(' ', '%20')}"
        if self.page_url.startswith("http"):
            return self.page_url
        return f"{FB_BASE}/{self.page_url}"

    def scrape(self, max_posts: int = 500, checkpoint_every: int = 25):
        from rich.console import Console
        console = Console()

        targets = self.page_urls if self.page_urls else ([self._get_target_url()] if self._get_target_url() else [])
        if not targets:
            logger.error("No target URLs configured — set DEEP_PAGE_URLS in .env or pass --page-url")
            return self.stats

        self.notifier.send(f"""
🕷️ *DEEP SCRAPER INICIADO*
*Páginas:* {len(targets)}
*Posts c/u:* {max_posts}
        """)

        self.stats["start_time"] = time.time()
        processed = self.checkpoint.get_scraped_post_ids()

        p, browser = self._create_browser()
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        try:
            if not self._authenticate(page, context):
                logger.error("Authentication failed")
                return self.stats

            eng_done = 0

            for idx, target in enumerate(targets):
                page_label = target.rstrip("/").split("/")[-1]
                console.print(f"\n[bold cyan]🌐 [{idx+1}/{len(targets)}] {page_label}[/bold cyan]")
                console.print(f"[dim]{target}[/dim]")

                page.goto(target, timeout=60000, wait_until="domcontentloaded")
                self.antiban.human_delay(5, 8)

                state = {"scraped_post_ids": list(processed), "stats": self.stats, "target": target}
                seen_ids = set(processed)
                stale = 0
                scrolled = 0
                crashed = False

                # Initial batch
                for post in self._scrape_search_results(page, seen_ids, max_posts):
                    post_id = post["post_id"]
                    if post_id in processed:
                        self.stats["posts_duplicated"] += 1
                        continue
                    ok = self.storage.insert_fb_post(post)
                    if ok:
                        processed.add(post_id)
                        self.stats["posts_scraped"] += 1
                if self.stats["posts_scraped"] > 0:
                    console.print(f"[green]  Initial batch: {self.stats['posts_scraped']} posts[/green]")

                # Scroll loop
                while self.stats["posts_scraped"] < max_posts:
                    if self.antiban.detect_ban(page):
                        self._handle_captcha(page, context, target)
                        state["scraped_post_ids"] = list(processed)
                        state["stats"] = self.stats
                        self.checkpoint.save(state)
                        self.antiban.human_delay(10, 20)
                        continue

                    delay = self.antiban.progressive_delay(scrolled)
                    try:
                        page.keyboard.press("End")
                    except Exception as e:
                        logger.warning(f"Keyboard scroll failed: {e}")
                        try:
                            page.evaluate("window.scrollBy(0, 800)")
                        except Exception as e2:
                            state["stats"] = self.stats
                            self.checkpoint.save(state)
                            crashed = True
                            logger.error(f"Browser/connection lost during scroll: {e2}")
                            break
                    page.wait_for_timeout(int(delay * 1000))
                    scrolled += 1

                    posts_on_page = 0
                    for post in self._scrape_search_results(page, seen_ids, max_posts):
                        post_id = post["post_id"]
                        if post_id in processed:
                            self.stats["posts_duplicated"] += 1
                            continue

                        ok = self.storage.insert_fb_post(post)
                        if ok:
                            processed.add(post_id)
                            self.stats["posts_scraped"] += 1
                            posts_on_page += 1
                            # Store full post dict for engagement phase update
                            pu = post.get("post_url", "")
                            if pu and pu.startswith("http"):
                                self._pending_engagement.append(dict(post))

                            if self.stats["posts_scraped"] % checkpoint_every == 0:
                                state["scraped_post_ids"] = list(processed)
                                state["stats"] = self.stats
                                self.checkpoint.save(state)
                                self.stats["checkpoints_saved"] += 1

                    if posts_on_page == 0:
                        stale += 1
                    else:
                        stale = 0

                    if stale >= 15:
                        logger.info(f"No new posts after {scrolled} scrolls — stopping {page_label}")
                        break

                    if scrolled % 10 == 0:
                        console.print(f"[dim]  Scroll {scrolled}: {self.stats['posts_scraped']} posts[/dim]")

                console.print(f"[green]✓ {page_label}: {self.stats['posts_scraped']} posts acumulados[/green]")

        except Exception as e:
            logger.error(f"Scraping error: {e}", exc_info=True)
            self.notifier.notify_error("DEEP_SCRAPER_ERROR", str(e))
            crashed = True

        else:
            # ── Phase 2: visit individual posts for engagement ──
            eng_done = 0
            if self._pending_engagement:
                total_eng = len(self._pending_engagement)
                console.print(f"\n[bold cyan]🔍 Visitando {total_eng} posts individuales para engagement...[/bold cyan]")
                self.notifier.send(f"🔍 *Recolectando engagement:* {total_eng} posts")
                for post_data in self._pending_engagement:
                    try:
                        eng = self._scrape_post_engagement(page, post_data["post_url"])
                        if eng:
                            post_data["likes_count"] = eng.get("lk", 0)
                            post_data["loves_count"] = eng.get("lv", 0)
                            post_data["hahas_count"] = eng.get("hh", 0)
                            post_data["wows_count"] = eng.get("wo", 0)
                            post_data["sads_count"] = eng.get("sd", 0)
                            post_data["angrys_count"] = eng.get("ag", 0)
                            post_data["comments_count"] = eng.get("cc", 0)
                            post_data["shares_count"] = eng.get("sc", 0)
                            post_data["views_count"] = eng.get("vw", 0)
                            self.storage.insert_fb_post(post_data)
                            eng_done += 1

                        # Extract all comments from this post
                        pid = post_data.get("post_id", "")
                        comments = self._extract_all_comments(page, pid)
                        for c in comments:
                            self.storage.insert_fb_comment(c)
                        self.stats["comments_scraped"] += len(comments)
                        if comments:
                            console.print(f"[dim]  → {len(comments)} comentarios extraídos[/dim]")

                        if eng_done % 10 == 0:
                            console.print(f"[dim]  Progreso: {eng_done}/{total_eng} posts, {self.stats['comments_scraped']} comentarios[/dim]")
                        self.antiban.human_delay(1, 3)
                    except Exception as e:
                        logger.debug(f"Engagement/comments failed for {post_data.get('post_url','')}: {e}")
                console.print(f"[green]✓ Engagement recolectado de {eng_done} posts[/green]")

        finally:
            try:
                browser.close()
            except Exception:
                pass
            try:
                p.stop()
            except Exception:
                pass

        # ── Fetch final stats from DB ──
        final_posts = self.storage.get_fb_posts(limit=10000)
        total_lk = sum(p.get("likes_count", 0) or 0 for p in final_posts)
        total_lv = sum(p.get("loves_count", 0) or 0 for p in final_posts)
        total_hh = sum(p.get("hahas_count", 0) or 0 for p in final_posts)
        total_cc = sum(p.get("comments_count", 0) or 0 for p in final_posts)
        total_sc = sum(p.get("shares_count", 0) or 0 for p in final_posts)
        total_vw = sum(p.get("views_count", 0) or 0 for p in final_posts)

        elapsed = (time.time() - self.stats["start_time"]) / 60
        self.checkpoint.save({"scraped_post_ids": list(processed), "stats": self.stats, "target": "multi"})

        if crashed:
            self.notifier.send(f"""
⚠️ *DEEP SCRAPER INTERRUMPIDO*
*Posts:* {self.stats["posts_scraped"]} | *Comentarios:* {self.stats["comments_scraped"]}
*Tiempo:* {elapsed:.1f} min
            """)
        else:
            self.notifier.send(f"""
✅ *DEEP SCRAPER COMPLETADO*
*Posts:* {self.stats["posts_scraped"]} | *Comentarios:* {self.stats["comments_scraped"]}
*Engagement:* {eng_done} posts | *LK:* {total_lk} | *LV:* {total_lv}
*CC:* {total_cc} | *SC:* {total_sc} | *VW:* {total_vw}
*Tiempo:* {elapsed:.1f} min
            """)

        return self.stats

    def _handle_captcha(self, page, context, target: str):
        """Telegram + foreground + espera a que el usuario resuelva el captcha."""
        from rich.console import Console
        console = Console()
        page_url = page.url
        console.print(f"[bold red]🔴 CAPTCHA en {target}[/bold red]")

        self.notifier.send(f"""
⚠️ *CAPTCHA DETECTADO*
*Página:* {target}
*URL actual:* {page_url}
Resuélvelo manualmente en el navegador.
        """)

        try:
            subprocess.run([
                "osascript", "-e",
                'tell application "System Events" to set frontmost of every process whose name contains "Chrom" to true'
            ], timeout=5)
        except Exception:
            pass

        console.print("[yellow]⏳ Esperando que resuelvas el captcha...[/yellow]")
        max_wait = 600
        waited = 0
        while waited < max_wait:
            time.sleep(3)
            waited += 3
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
                if not self.antiban.detect_ban(page):
                    console.print("[bold green]✅ Captcha resuelto[/bold green]")
                    self.notifier.send("✅ *Captcha resuelto* — reanudando")
                    return
            except Exception:
                pass
            if waited % 30 == 0:
                console.print(f"[yellow]⏳ {waited}s esperando captcha...[/yellow]")

        logger.warning("Captcha wait timeout — stopping")
        self.notifier.send("⏰ *Tiempo agotado* — captcha no resuelto en 10 min")

    def _scrape_post_engagement(self, page, post_url: str) -> Optional[dict]:
        """Visita un post individual y extrae reacciones, comments, shares, views."""
        try:
            page.goto(post_url, timeout=30000, wait_until="domcontentloaded")
            self.antiban.human_delay(2, 4)

            js = """
            () => {
                function parseNum(s) {
                    if (!s) return 0;
                    s = s.trim();
                    let mult = 1;
                    if (/mil/i.test(s) || /K/i.test(s)) { mult = 1000; s = s.replace(/mil/i, '').replace(/K/i, '').trim(); }
                    if (/M/i.test(s)) { mult = 1000000; s = s.replace(/M/i, '').trim(); }
                    s = s.replace(/\\./g, '').replace(',', '.');
                    const n = parseFloat(s);
                    return isNaN(n) ? 0 : Math.round(n * mult);
                }

                let lk=0, lv=0, hh=0, wo=0, sd=0, ag=0, cc=0, sc=0, vw=0;
                const els = document.querySelectorAll('[aria-label]');
                for (const el of els) {
                    const label = el.getAttribute('aria-label') || '';
                    const ll = label.toLowerCase();
                    const m = label.match(/([\\d,.]+)\\s*(mil|k|m)?/i);
                    if (!m) continue;
                    const val = parseNum(m[1] + (m[2] || ''));
                    if (val === 0) continue;
                    if (ll.includes('me gusta') || ll.includes('like')) lk = Math.max(lk, val);
                    else if (ll.includes('me encanta') || ll.includes('love')) lv = Math.max(lv, val);
                    else if (ll.includes('haha') || ll.includes('me divierte')) hh = Math.max(hh, val);
                    else if (ll.includes('wow') || ll.includes('me sorprende')) wo = Math.max(wo, val);
                    else if (ll.includes('triste') || ll.includes('me entristece')) sd = Math.max(sd, val);
                    else if (ll.includes('enojo') || ll.includes('me enfada')) ag = Math.max(ag, val);
                    else if (ll.includes('comentario') || ll.includes('comment')) cc = Math.max(cc, val);
                    else if (ll.includes('compartido') || ll.includes('shares?')) sc = Math.max(sc, val);
                    else if (ll.includes('vista') || ll.includes('views?')) vw = Math.max(vw, val);
                }

                // Fallback por texto
                const txt = document.body.innerText.toLowerCase();
                if (!cc) { const m = txt.match(/([\\d,.]+(?:mil|k|m)?)\\s*(comentario|comment)/i); if (m) cc = parseNum(m[1]); }
                if (!sc) { const m = txt.match(/([\\d,.]+(?:mil|k|m)?)\\s*(compartido|shares?)/i); if (m) sc = parseNum(m[1]); }
                if (!vw) { const m = txt.match(/([\\d,.]+(?:mil|k|m)?)\\s*(vistas?|views?|reproducciones?|visualizaciones?|reprodujo|plays?)/i); if (m) vw = parseNum(m[1]); }

                return { lk, lv, hh, wo, sd, ag, cc, sc, vw };
            }
            """
            return page.evaluate(js)
        except Exception as e:
            logger.debug(f"Engagement scrape failed for {post_url}: {e}")
            return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deep Scraper - Extracción desde feed")
    parser.add_argument("--page-url", default="", help="URL completa de la página")
    parser.add_argument("--page-name", default="", help="Nombre de la página")
    parser.add_argument("--max", type=int, default=500, help="Posts objetivo")
    parser.add_argument("--headless", action="store_true", help="Modo headless")
    parser.add_argument("--cookies-file", default="cookies.json", help="Archivo de cookies")

    args = parser.parse_args()
    cfg = Config()

    deep_urls = cfg.deep_page_urls

    if args.page_url:
        urls = [(args.page_url, args.page_name or args.page_url)]
    elif deep_urls:
        urls = [(u, u.rstrip("/").split("/")[-1]) for u in deep_urls]
    else:
        urls = [(cfg.FB_PAGE_URL, cfg.FB_PAGE_NAME or "Página")]

    total_posts = 0
    total_comments = 0

    for page_url, page_name in urls:
        print(f"\n{'='*50}")
        print(f"Scrapeando: {page_name}")
        print(f"{'='*50}")

        scraper = FacebookDeepScraper(
            page_url=page_url,
            page_name=page_name,
            cookies_file=args.cookies_file,
            email=cfg.FB_EMAIL,
            password=cfg.FB_PASSWORD,
            headless=args.headless,
        )

        stats = scraper.scrape(max_posts=args.max)

        print(f"\nResultados para {page_name}:")
        print(f"  Posts extraídos: {stats['posts_scraped']}")
        print(f"  Comentarios extraídos: {stats['comments_scraped']}")
        print(f"  Duplicados: {stats['posts_duplicated']}")
        print(f"  Errores: {stats['errors']}")

        total_posts += stats["posts_scraped"]
        total_comments += stats["comments_scraped"]

    print(f"\n{'='*50}")
    print("RESUMEN GLOBAL")
    print(f"{'='*50}")
    print(f"Total páginas: {len(urls)}")
    print(f"Total posts: {total_posts}")
    print(f"Total comentarios: {total_comments}")


if __name__ == "__main__":
    main()
