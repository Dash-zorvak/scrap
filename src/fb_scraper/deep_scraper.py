#!/usr/bin/env python3
"""
Deep Scraper - Extracción desde feed vía Playwright
=====================================================
Usado para páginas externas SIN acceso de administrador.
Extrae posts + comentarios inline desde el feed scrolleado,
sin navegar a páginas individuales de posts.

NO extrae shares ni views (Facebook no los expone en el DOM del feed).
NO desglosa reacciones individuales — solo total_reactions (suma).

Almacena en externos.db (SQLite directo, sin ORM).

Flujo:
  1. Autenticación: cookies → email/password → cookies frescas
  2. Scroll del feed extrayendo posts + comentarios inline
  3. Checkpoint por URL de post
"""

import hashlib
import json
import logging
import os
import random
import re
import signal
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from playwright_stealth import Stealth

from src.notifications.telegram import TelegramNotifier
from src.config import Config

logger = logging.getLogger(__name__)

FB_BASE = "https://www.facebook.com"
REQUIRED_COOKIES = {"c_user", "xs"}
EXTERNAL_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "externos.db"


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


class CheckpointManager:
    """Checkpoints para persistencia y recuperación."""

    def __init__(self, platform: str = "externos"):
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
    Scraper Facebook vía Playwright para páginas externas.
    Extrae posts + comentarios inline desde el feed scrolleado.
    Sin navegación a páginas individuales.
    Guarda en externos.db (SQLite directo).
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

        cfg = Config()
        if page_urls is not None:
            self.page_urls = page_urls
        elif cfg.deep_page_urls:
            self.page_urls = cfg.deep_page_urls
        else:
            self.page_urls = []

        # Date range from config
        self.scrape_since = self._parse_date(cfg.SCRAPE_SINCE)
        scrape_until_str = cfg.SCRAPE_UNTIL
        self.scrape_until = self._parse_date(scrape_until_str) if scrape_until_str else datetime.now()
        self.cutoff_tolerance = int(getattr(cfg, "CUTOFF_TOLERANCE", "10"))

        self.notifier = TelegramNotifier()
        self.checkpoint = CheckpointManager("externos")
        self.antiban = AntiBan()

        self.stats = {
            "posts_scraped": 0,
            "posts_duplicated": 0,
            "comments_scraped": 0,
            "comments_duplicated": 0,
            "errors": 0,
            "start_time": None,
            "checkpoints_saved": 0,
        }

        self._init_db()

        # Tracking for tolerance-based cutoff
        self._last_extraction_raw_count = 0
        self._last_extraction_oor_count = 0

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse YYYY-MM-DD to datetime."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            logger.warning(f"Invalid date '{date_str}', defaulting to 2025-01-01")
            return datetime(2025, 1, 1)

    # ── DB initialization ──────────────────────────────────────

    def _init_db(self):
        EXTERNAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(EXTERNAL_DB_PATH))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS external_posts (
                post_id         TEXT PRIMARY KEY,
                page_name       TEXT,
                page_url        TEXT,
                message         TEXT,
                created_time    DATETIME,
                total_reactions INTEGER DEFAULT 0,
                comments_count  INTEGER DEFAULT 0,
                post_url        TEXT,
                source          TEXT DEFAULT 'deep_scraper_externo',
                scraped_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS external_comments (
                comment_id   TEXT PRIMARY KEY,
                post_id      TEXT,
                message      TEXT,
                author_name  TEXT DEFAULT 'Anónimo',
                created_time DATETIME,
                scraped_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
        logger.info(f"DB initialized: {EXTERNAL_DB_PATH}")

    def _save_post(self, post: Dict[str, Any]) -> bool:
        try:
            conn = sqlite3.connect(str(EXTERNAL_DB_PATH))
            conn.execute("""
                INSERT OR REPLACE INTO external_posts
                (post_id, page_name, page_url, message, created_time,
                 total_reactions, comments_count, post_url, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post["post_id"],
                post.get("page_name", ""),
                post.get("page_url", ""),
                post.get("message", "")[:10000],
                post.get("created_time"),
                post.get("total_reactions", 0),
                post.get("comments_count", 0),
                post.get("post_url", ""),
                "deep_scraper_externo",
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving post: {e}")
            return False

    def _save_comment(self, comment: Dict[str, Any]) -> bool:
        try:
            conn = sqlite3.connect(str(EXTERNAL_DB_PATH))
            conn.execute("""
                INSERT OR REPLACE INTO external_comments
                (comment_id, post_id, message, author_name, created_time)
                VALUES (?, ?, ?, ?, ?)
            """, (
                comment["comment_id"],
                comment.get("post_id", ""),
                comment.get("message", "")[:5000],
                comment.get("author_name", "Anónimo"),
                comment.get("created_time"),
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving comment: {e}")
            return False

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
            page.goto(f"{FB_BASE}/login", timeout=60000, wait_until="networkidle")
            self.antiban.human_delay(3, 5)

            email_input = page.locator('input[name="email"], input[autocomplete="username"]').first
            email_input.fill(self.email)
            self.antiban.human_delay(1, 2)

            pass_input = page.locator('input[name="pass"], input[autocomplete="current-password"]').first
            pass_input.fill(self.password)
            self.antiban.human_delay(1, 2)

            login_btn = page.locator(
                'div[role="button"]:has-text("Iniciar sesión"), '
                'div[role="button"]:has-text("Log in"), '
                'div[role="button"]:has-text("Entrar"), '
                'input[type="submit"], '
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

    # ── Post extraction via JavaScript ─────────────────────────

    def _scrape_search_results(self, page, seen_ids: set, max_posts: int) -> List[Dict]:
        """
        Extrae posts + comentarios inline del feed via JS.
        Retorna lista de dicts, cada uno con:
          - post_id, page_name, page_url, message, created_time
          - total_reactions (suma de todas las reacciones)
          - comments_count, post_url
          - comments: lista de dicts con message, author_name, created_time
        """
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
                s = s.replace(/\\./g, '').replace(',', '.');
                const n = parseFloat(s);
                return isNaN(n) ? 0 : Math.round(n * mult);
            }

            // Find ALL unique post URLs on the page
            const urlSet = new Map();
            const linkEls = document.querySelectorAll('a[href*=\"/posts/\"], a[href*=\"story.php\"], a[href*=\"story_fbid\"], a[href*=\"photos/\"], a[href*=\"/videos/\"], a[href*=\"/reel/\"]');
            for (const link of linkEls) {
                const href = (link.getAttribute('href') || link.href || '').split('?')[0];
                if (!href) continue;
                // Extract canonical post ID from href
                const m = href.match(/\\/posts\\/([a-zA-Z0-9_.-]+)/) || href.match(/story_fbid=([a-zA-Z0-9_-]+)/);
                if (m) {
                    const canonical = m[1];
                    if (!urlSet.has(canonical)) {
                        urlSet.set(canonical, href.startsWith('http') ? href : 'https://www.facebook.com' + href);
                    }
                }
            }

            const posts = [];
            const sharedCommentSigs = new Set();

            for (const [postId, postUrl] of urlSet) {

                // Walk up to find the post container
                let container = link.parentElement;
                for (let i = 0; i < 15 && container; i++) {
                    if (container.getAttribute('role') === 'article') break;
                    container = container.parentElement;
                }
                if (!container) continue;

                const innerText = container.innerText || '';

                // --- Message ---
                let message = '';
                const msgEls = container.querySelectorAll('div[dir=\"auto\"]');
                for (const msgEl of msgEls) {
                    const t = msgEl.innerText.trim();
                    if (t.length > 15 && !t.startsWith('http')) { message = t; break; }
                }
                if (!message) message = (container.innerText || '').substring(0, 500).trim();
                if (message.length < 5) continue;

                // --- Author (page_name) ---
                let author = '';
                let authorUrl = '';
                const anchors = container.querySelectorAll('a');
                const junkNames = new Set(['seguir', 'facebook', 'compartir', 'indicador de estado online', 'activo', 'me gusta', 'seguido', 'siguiendo', 'responder', 'reaccionar', 'enviar', 'compartir en', 'opciones', 'más', 'menos', 'ver más', 'ver menos', 'ver todo', 'ocultar', 'eliminar', 'editar', 'denunciar', 'compartir ahora', 'copiar enlace']);
                for (const a of anchors) {
                    const raw = a.innerText;
                    if (!raw) continue;
                    const t = raw.replace(/\\n/g, ' ').replace(/\\s+/g, ' ').trim();
                    const ahref = a.getAttribute('href') || '';
                    if (t && t.length < 50 && t.length > 2 && !t.startsWith('http') && !/^\\d+$/.test(t)
                        && !junkNames.has(t.toLowerCase())) {
                        author = t;
                        if (ahref && ahref.startsWith('http')) authorUrl = ahref;
                        else if (ahref && ahref.startsWith('/')) authorUrl = 'https://www.facebook.com' + ahref;
                        break;
                    }
                }

                // --- Timestamp ---
                let created = null;
                const tsSelectors = [
                    'abbr[data-utime]',
                    'span[data-utime]',
                    'time[datetime]',
                    'abbr[title]',
                    'span[data-tooltip-content]',
                    '[data-utime]',
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
                    } else if (sel === 'span[data-tooltip-content]') {
                        const t = el.getAttribute('data-tooltip-content');
                        if (t) { const ms = Date.parse(t); if (!isNaN(ms)) { created = ms; break; } }
                    } else {
                        const u = el.getAttribute('data-utime') || el.getAttribute('utime');
                        if (u) { created = parseInt(u) * 1000; break; }
                    }
                }

                // Fallback: relative time (improved regex)
                if (!created) {
                    const lower = innerText.toLowerCase();
                    const relTime = lower.match(/(\\d+)\\s*(seg|segundos?|min|minutos?|horas?|días?|día|semanas?|sem|mes|meses?|años?|año)\\s*/);
                    if (relTime) {
                        const num = parseInt(relTime[1]);
                        const unit = relTime[2];
                        const now = Date.now();
                        if (unit.startsWith('seg')) created = now - num * 1000;
                        else if (unit.startsWith('min')) created = now - num * 60 * 1000;
                        else if (unit.startsWith('h')) created = now - num * 3600 * 1000;
                        else if (unit.startsWith('d') || unit.startsWith('sem')) {
                            const multiplier = unit.startsWith('sem') ? 7 : 1;
                            created = now - num * multiplier * 86400 * 1000;
                        }
                        else if (unit.startsWith('mes')) created = now - num * 30 * 86400 * 1000;
                        else if (unit.startsWith('a')) created = now - num * 365 * 86400 * 1000;
                    }
                }

                // Fallback: parse postUrl for date fragments (Facebook sometimes encodes dates)
                if (!created) {
                    const dateMatch = postUrl.match(/\\/(\\d{4})\\/(\\d{1,2})\\/(\\d{1,2})\\//);
                    if (dateMatch) {
                        created = new Date(parseInt(dateMatch[1]), parseInt(dateMatch[2]) - 1, parseInt(dateMatch[3])).getTime();
                        if (isNaN(created)) created = null;
                    }
                }

                // --- Engagement: total_reactions (suma) ---
                let totalReactions = 0;
                const ariaLabels = container.querySelectorAll('[aria-label]');
                for (const al of ariaLabels) {
                    const label = al.getAttribute('aria-label') || '';
                    const ll = label.toLowerCase();
                    const nM = label.match(/([\\d,.]+)\\s*(mil|k|M)?/);
                    if (!nM) continue;
                    const val = parseNum(nM[1] + (nM[2] || ''));
                    if (val === 0) continue;
                    if (ll.includes('me gusta') || ll.includes('like') ||
                        ll.includes('me encanta') || ll.includes('love') ||
                        ll.includes('haha') || ll.includes('me divierte') ||
                        ll.includes('wow') || ll.includes('me sorprende') ||
                        ll.includes('triste') || ll.includes('me entristece') ||
                        ll.includes('enojo') || ll.includes('me enfada')) {
                        totalReactions = Math.max(totalReactions, val);
                    }
                }

                // --- comments_count ---
                let commentsCount = 0;
                for (const al of ariaLabels) {
                    const label = al.getAttribute('aria-label') || '';
                    const ll = label.toLowerCase();
                    const nM = label.match(/([\\d,.]+)\\s*(mil|k|M)?/);
                    if (!nM) continue;
                    const val = parseNum(nM[1] + (nM[2] || ''));
                    if (val === 0) continue;
                    if (ll.includes('comentario') || ll.includes('comment')) {
                        commentsCount = Math.max(commentsCount, val);
                    }
                }
                if (!commentsCount) {
                    const m = innerText.match(/([\\d,.]+(?:mil|k|M)?)\\s+(comentario|comment)/i);
                    if (m) commentsCount = parseNum(m[1]);
                }

                // --- Inline comments extraction ---
                const comments = [];
                const seenCommentSigs = new Set();

                // Find all div[dir="auto"] within container that look like comments
                const dirEls = container.querySelectorAll('div[dir=\"auto\"]');
                for (const de of dirEls) {
                    const t = de.innerText.trim();
                    if (t.length < 5 || t.length > 1000) continue;
                    if (t === message || t === message.substring(0, 100)) continue;

                    // Walk up to find author link
                    let el = de.parentElement;
                    let commentAuthor = '';
                    for (let i = 0; i < 5 && el; i++) {
                        // Try multiple selector strategies
                        const authorLink = el.querySelector(
                            'a[href*=\"/user/\"], a[href*=\"/profile/\"], a[role=\"link\"], a[href*=\"/groups/\"], strong a, h4 a'
                        );
                        if (authorLink) {
                            const at = authorLink.innerText.trim();
                            if (at.length > 0 && at.length < 50 && at !== author) {
                                commentAuthor = at;
                                break;
                            }
                        }
                        // Try span with author name
                        const nameSpan = el.querySelector('span[dir=\"auto\"] strong, strong:only-child');
                        if (nameSpan) {
                            const at = nameSpan.innerText.trim();
                            if (at.length > 0 && at.length < 50 && at !== author) {
                                commentAuthor = at;
                                break;
                            }
                        }
                        el = el.parentElement;
                    }
                    if (!commentAuthor) {
                        commentAuthor = 'Anónimo';
                    }

                    // Deduplicate by message + author
                    const sig = t.substring(0, 60) + '|' + commentAuthor;
                    if (seenCommentSigs.has(sig)) continue;
                    seenCommentSigs.add(sig);

                    // Find timestamp
                    let commentTs = null;
                    const tsEl = de.parentElement.querySelector('abbr[data-utime], span[data-utime]');
                    if (tsEl) {
                        const ut = tsEl.getAttribute('data-utime');
                        if (ut) commentTs = parseInt(ut) * 1000;
                    }

                    comments.push({
                        message: t.substring(0, 5000),
                        author: commentAuthor,
                        created: commentTs,
                    });
                }

                posts.push({
                    postId,
                    pageName: author,
                    pageUrl: authorUrl,
                    message,
                    created,
                    totalReactions,
                    commentsCount,
                    postUrl,
                    comments,
                });
            }

            return posts;
        }
        """
        raw_posts = page.evaluate(js_extract)
        logger.info(f"JS extraction: {len(raw_posts)} raw posts from feed")

        results = []
        self._last_extraction_raw_count = len(raw_posts)
        self._last_extraction_oor_count = 0

        for data in raw_posts:
            post_id = data.get("postId", "")
            msg_preview = (data.get("message") or "")[:80]
            if not post_id:
                continue
            if post_id in seen_ids:
                logger.debug(f"  Skipping duplicate post: {post_id}")
                continue
            seen_ids.add(post_id)

            message = (data.get("message") or "")[:10000]
            author = data.get("pageName") or self.search_keyword or "Search Result"
            created_ts = data.get("created")
            created_time = datetime.fromtimestamp(created_ts / 1000) if created_ts else None

            # Filter by date range [scrape_since, scrape_until]
            if created_time:
                if created_time < self.scrape_since or created_time > self.scrape_until:
                    logger.debug(f"  Skipping post outside date range: {created_time}")
                    self._last_extraction_oor_count += 1
                    continue
            else:
                # Posts without timestamp cannot be judged; count as in-range
                pass

            post_url = data.get("postUrl", "") or (f"{FB_BASE}/posts/{post_id}" if not post_id.startswith("deep_") else "")
            page_url = data.get("pageUrl", "")

            # Filter out comment-like items
            total_eng = data.get("totalReactions", 0) or 0
            msg_lower = message.lower().strip()
            if total_eng == 0 and len(message) < 40 and ("me gusta" in msg_lower or "responder" in msg_lower):
                logger.debug(f"  Filtered out (comment-like): {message[:60]}")
                continue

            # Extract inline comments
            raw_comments = data.get("comments", [])
            comments_out = []
            for rc in raw_comments:
                c_msg = rc.get("message", "")
                c_author = rc.get("author", "") or "Anónimo"
                c_ts = rc.get("created")
                c_created = datetime.fromtimestamp(c_ts / 1000) if c_ts else None
                cid = hashlib.md5(f"{post_id}|{c_msg}|{c_author}".encode()).hexdigest()
                comments_out.append({
                    "comment_id": cid,
                    "post_id": post_id,
                    "message": c_msg,
                    "author_name": c_author,
                    "created_time": c_created,
                })

            results.append({
                "post_id": post_id,
                "page_name": author,
                "page_url": page_url,
                "message": message,
                "created_time": created_time,
                "total_reactions": data.get("totalReactions", 0) or 0,
                "comments_count": data.get("commentsCount", 0) or 0,
                "post_url": post_url,
                "comments": comments_out,
            })

        return results

    # ── Inline comment expansion ───────────────────────────────

    def _expand_comments_inline(self, page: Page):
        """Expande comentarios en el feed sin navegar a página individual."""
        patterns = [
            "Ver más comentarios", "View more comments",
            "Ver las respuestas", "View replies",
            "Ver más respuestas", "View more replies",
        ]
        for _ in range(15):
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
                                self.antiban.human_delay(0.5, 1.5)
                                clicked = True
                        except Exception:
                            pass
                except Exception:
                    pass
            if not clicked:
                break

    # ── Captcha handler ────────────────────────────────────────

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

    # ── Target URL resolution ──────────────────────────────────

    def _get_target_url(self) -> str:
        if self.search_keyword:
            return f"{FB_BASE}/search/posts?q={self.search_keyword.replace(' ', '%20')}"
        if self.page_url.startswith("http"):
            return self.page_url
        return f"{FB_BASE}/{self.page_url}"

    # ── Main scrape ────────────────────────────────────────────

    def scrape(self, max_posts: int = 500, checkpoint_every: int = 25):
        from rich.console import Console
        console = Console()

        targets = self.page_urls if self.page_urls else ([self._get_target_url()] if self._get_target_url() else [])
        if not targets:
            logger.error("No target URLs configured — set DEEP_PAGE_URLS or EXTERNAL_PAGE_URLS in .env, or pass --page-url")
            return self.stats

        self.notifier.send(f"""
🕷️ *DEEP SCRAPER INICIADO (externos)*
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

            for idx, target in enumerate(targets):
                page_label = target.rstrip("/").split("/")[-1]
                console.print(f"\n[bold cyan]🌐 [{idx+1}/{len(targets)}] {page_label}[/bold cyan]")
                console.print(f"[dim]{target}[/dim]")

                page.goto(target, timeout=60000, wait_until="domcontentloaded")
                self.antiban.human_delay(5, 8)

                state = {"scraped_post_ids": list(processed), "stats": self.stats, "target": target}
                seen_ids = set(processed)
                stale = 0
                oor_streak = 0
                scrolled = 0
                crashed = False

                # Initial batch
                for post in self._scrape_search_results(page, seen_ids, max_posts):
                    post_id = post["post_id"]
                    if post_id in processed:
                        self.stats["posts_duplicated"] += 1
                        continue
                    ok = self._save_post(post)
                    if ok:
                        processed.add(post_id)
                        self.stats["posts_scraped"] += 1
                        # Save inline comments
                        for c in post.get("comments", []):
                            self._save_comment(c)
                            self.stats["comments_scraped"] += 1

                if self.stats["posts_scraped"] > 0:
                    console.print(f"[green]  Initial batch: {self.stats['posts_scraped']} posts, {self.stats['comments_scraped']} comments[/green]")

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

                    # Expand comments inline before extraction
                    self._expand_comments_inline(page)
                    page.wait_for_timeout(1500)

                    posts_on_page = 0
                    for post in self._scrape_search_results(page, seen_ids, max_posts):
                        post_id = post["post_id"]
                        if post_id in processed:
                            self.stats["posts_duplicated"] += 1
                            continue

                        ok = self._save_post(post)
                        if ok:
                            processed.add(post_id)
                            self.stats["posts_scraped"] += 1
                            posts_on_page += 1

                            # Save inline comments
                            for c in post.get("comments", []):
                                self._save_comment(c)
                                self.stats["comments_scraped"] += 1

                            if self.stats["posts_scraped"] % checkpoint_every == 0:
                                state["scraped_post_ids"] = list(processed)
                                state["stats"] = self.stats
                                self.checkpoint.save(state)
                                self.stats["checkpoints_saved"] += 1

                    if posts_on_page == 0:
                        stale += 1
                        # Track out-of-range streak: if most extracted posts are OOR
                        if self._last_extraction_raw_count > 0 and self._last_extraction_oor_count > 0:
                            oor_ratio = self._last_extraction_oor_count / self._last_extraction_raw_count
                            if oor_ratio >= 0.7:
                                oor_streak += 1
                                logger.debug(f"  OOR streak: {oor_streak}/{self.cutoff_tolerance} ({self._last_extraction_oor_count}/{self._last_extraction_raw_count} posts OOR)")
                            else:
                                oor_streak = 0
                        else:
                            oor_streak = 0
                    else:
                        stale = 0
                        oor_streak = 0

                    if stale >= 15:
                        logger.info(f"No new posts after {scrolled} scrolls — stopping {page_label}")
                        break

                    if oor_streak >= self.cutoff_tolerance:
                        logger.info(f"All posts out of date range for {oor_streak} consecutive scrolls — stopping {page_label}")
                        break

                    if scrolled % 10 == 0:
                        console.print(f"[dim]  Scroll {scrolled}: {self.stats['posts_scraped']} posts, {self.stats['comments_scraped']} comments[/dim]")

                console.print(f"[green]✓ {page_label}: {self.stats['posts_scraped']} posts, {self.stats['comments_scraped']} comments[/green]")

        except Exception as e:
            logger.error(f"Scraping error: {e}", exc_info=True)
            self.notifier.notify_error("DEEP_SCRAPER_ERROR", str(e))
            crashed = True

        finally:
            try:
                browser.close()
            except Exception:
                pass
            try:
                p.stop()
            except Exception:
                pass

        # ── Final stats ──
        elapsed = (time.time() - self.stats["start_time"]) / 60

        # Get date range from DB
        date_range = "N/A"
        try:
            conn = sqlite3.connect(str(EXTERNAL_DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT MIN(created_time), MAX(created_time) FROM external_posts WHERE created_time IS NOT NULL")
            row = cur.fetchone()
            if row and row[0]:
                date_range = f"{row[0]} → {row[1]}"
            conn.close()
        except Exception:
            pass

        self.checkpoint.save({"scraped_post_ids": list(processed), "stats": self.stats, "target": "multi"})

        summary = (
            f"📊 *DEEP SCRAPER (externos) — RESUMEN*\n"
            f"*Páginas:* {len(targets)}\n"
            f"*Posts nuevos:* {self.stats['posts_scraped']}\n"
            f"*Duplicados:* {self.stats['posts_duplicated']}\n"
            f"*Comentarios:* {self.stats['comments_scraped']}\n"
            f"*Rango fechas:* {date_range}\n"
            f"*Tiempo:* {elapsed:.1f} min"
        )

        if crashed:
            self.notifier.send(f"⚠️ *DEEP SCRAPER INTERRUMPIDO*\n{summary}")
        else:
            self.notifier.send(f"✅ *DEEP SCRAPER COMPLETADO*\n{summary}")

        # Console summary
        console.print(f"\n[bold cyan]═══ RESUMEN ═══[/bold cyan]")
        console.print(f"  Páginas:       {len(targets)}")
        console.print(f"  Posts nuevos:  {self.stats['posts_scraped']}")
        console.print(f"  Duplicados:    {self.stats['posts_duplicated']}")
        console.print(f"  Comentarios:   {self.stats['comments_scraped']}")
        console.print(f"  Rango fechas:  {date_range}")
        console.print(f"  Tiempo:        {elapsed:.1f} min")
        console.print(f"  BD:            {EXTERNAL_DB_PATH}")

        return self.stats

    def extract_comments_from_db(self, max_posts: int = 500):
        """
        DEPRECATED: En la versión actual, los comentarios se extraen
        inline durante el scrape. Este método se mantiene por compatibilidad.
        """
        logger.warning("extract_comments_from_db is deprecated. Comments are now extracted inline during scrape().")
        return self.stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deep Scraper - Extracción desde feed (externos)")
    parser.add_argument("--page-url", default="", help="URL completa de la página")
    parser.add_argument("--page-name", default="", help="Nombre de la página")
    parser.add_argument("--max", type=int, default=500, help="Posts objetivo")
    parser.add_argument("--headless", action="store_true", help="Modo headless")
    parser.add_argument("--cookies-file", default="cookies.json", help="Archivo de cookies")

    args = parser.parse_args()
    cfg = Config()

    # Resolver URLs: CLI > EXTERNAL_PAGE_URLS > DEEP_PAGE_URLS > FB_PAGE_URL
    external_urls_raw = os.getenv("EXTERNAL_PAGE_URLS", "")
    if external_urls_raw:
        try:
            external_urls = json.loads(external_urls_raw)
        except json.JSONDecodeError:
            external_urls = [u.strip() for u in external_urls_raw.split(",") if u.strip()]
    else:
        external_urls = []

    if args.page_url:
        urls = [(args.page_url, args.page_name or args.page_url)]
    elif external_urls:
        urls = [(u, u.rstrip("/").split("/")[-1]) for u in external_urls]
    elif cfg.deep_page_urls:
        urls = [(u, u.rstrip("/").split("/")[-1]) for u in cfg.deep_page_urls]
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
    print(f"BD externos: {EXTERNAL_DB_PATH}")


if __name__ == "__main__":
    main()
