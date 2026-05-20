import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from playwright_stealth import Stealth

from src.fb_scraper.models import FBPostData, FBCommentData

logger = logging.getLogger(__name__)

FB_BASE = "https://www.facebook.com"

# Cookies mínimas necesarias para sesión autenticada de Facebook
REQUIRED_COOKIES = {"c_user", "xs"}
OPTIONAL_COOKIES = {"sb", "datr", "spin", "fr", "wd"}


class FacebookPlaywright:
    """
    Scraper de Facebook con Playwright.
    Soporta dos modos de autenticación:
      1. Cookies de sesión (recomendado): más estable, sin riesgo de checkpoint
      2. Email/password: fallback, más propenso a bloqueos
    """

    def __init__(
        self,
        email: str = "",
        password: str = "",
        proxy_url: str = "",
        headless: bool = False,
        cookies: Optional[Union[list, dict, str]] = None,
        cookies_file: str = "",
    ):
        self.email = email
        self.password = password
        self.proxy_url = proxy_url
        self.headless = headless
        self._cookies = self._parse_cookies(cookies, cookies_file)

    # ------------------------------------------------------------------ #
    # Cookie helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_cookies(
        cookies: Optional[Union[list, dict, str]],
        cookies_file: str,
    ) -> list[dict]:
        """
        Acepta cookies en varios formatos:
          - str:  "c_user=123; xs=abc; sb=xyz"
          - dict: {"c_user": "123", "xs": "abc"}
          - list: [{"name": "c_user", "value": "123", "domain": ".facebook.com"}, ...]
          - file path (cookies_file): JSON con cualquiera de los formatos anteriores
        """
        if cookies_file:
            path = Path(cookies_file)
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
                # El archivo puede guardar {"facebook": [...]} o directamente [...]
                if isinstance(raw, dict):
                    raw = raw.get("facebook", raw.get("cookies", list(raw.values())[0] if raw else []))
                return FacebookPlaywright._normalize_cookie_list(raw)
            else:
                logger.warning(f"Cookies file not found: {cookies_file}")

        if not cookies:
            return []

        if isinstance(cookies, str):
            # Formato header: "c_user=123; xs=abc"
            result = []
            for part in cookies.split(";"):
                part = part.strip()
                if "=" in part:
                    name, _, value = part.partition("=")
                    result.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".facebook.com",
                        "path": "/",
                        "sameSite": "Lax",
                    })
            return result

        if isinstance(cookies, dict):
            return [
                {"name": k, "value": v, "domain": ".facebook.com", "path": "/", "sameSite": "Lax"}
                for k, v in cookies.items()
            ]

        if isinstance(cookies, list):
            return FacebookPlaywright._normalize_cookie_list(cookies)

        return []

    @staticmethod
    def _normalize_cookie_list(lst: list) -> list[dict]:
        """Asegura que cada cookie tenga domain, path y sameSite válido."""
        result = []
        for c in lst:
            if isinstance(c, dict):
                cookie = dict(c)
                cookie.setdefault("domain", ".facebook.com")
                cookie.setdefault("path", "/")
                
                # Mapear sameSite a valores válidos para Playwright
                same = cookie.get("sameSite", "Lax")
                if same in ("no_restriction", "unspecified"):
                    cookie["sameSite"] = "None"
                elif same in ("lax", "Lax"):
                    cookie["sameSite"] = "Lax"
                elif same in ("strict", "Strict"):
                    cookie["sameSite"] = "Strict"
                else:
                    cookie["sameSite"] = "Lax"
                
                result.append(cookie)
        return result

    def _validate_cookies(self) -> bool:
        """Verifica que las cookies mínimas estén presentes."""
        names = {c.get("name", "") for c in self._cookies}
        missing = REQUIRED_COOKIES - names
        if missing:
            logger.warning(f"Missing required cookies: {missing}. Will try email/password login.")
            return False
        return True

    def save_cookies(self, context: BrowserContext, output_file: str = "cookies_saved.json"):
        """Guarda las cookies actuales del contexto para reutilizarlas."""
        try:
            cookies = context.cookies()
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump({"facebook": cookies}, f, indent=2)
            logger.info(f"Cookies saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    # ------------------------------------------------------------------ #
    # Browser / page setup
    # ------------------------------------------------------------------ #

    def _create_browser(self) -> tuple:
        launch_opts = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1366,768",
            ],
        }
        if self.proxy_url:
            launch_opts["proxy"] = {"server": self.proxy_url}

        p = sync_playwright().start()
        browser = p.chromium.launch(**launch_opts)
        return p, browser

    def _setup_context_with_cookies(self, browser: Browser) -> BrowserContext:
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="es_ES",
            timezone_id="America/El_Salvador",
        )
        if self._cookies:
            context.add_cookies(self._cookies)
            logger.info(f"Loaded {len(self._cookies)} cookies into context")
        return context

    def _setup_page(self, context: BrowserContext) -> Page:
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        return page

    def _human_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        time.sleep(min_s + (max_s - min_s) * (time.time() % 1))

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #

    def _verify_logged_in(self, page: Page) -> bool:
        """Navega a FB y verifica si hay sesión activa."""
        try:
            page.goto(FB_BASE, timeout=30000, wait_until="domcontentloaded")
            self._human_delay(2, 4)

            # Si hay un botón de login → no estamos autenticados
            login_visible = page.locator('input[name="email"], a[href*="/login"]').count()
            if login_visible > 0:
                # Doble check: si aparece el feed principal sí estamos dentro
                feed_visible = page.locator('[role="feed"], [data-pagelet="FeedUnit_0"]').count()
                if feed_visible == 0:
                    logger.warning("Session check: NOT logged in")
                    return False

            logger.info("Session check: logged in ✓")
            return True
        except Exception as e:
            logger.error(f"Session verification failed: {e}")
            return False

    def login_with_credentials(self, page: Page) -> bool:
        """Fallback: login con email y contraseña."""
        if not self.email or not self.password:
            logger.warning("No credentials provided for fallback login")
            return False

        try:
            page.goto(f"{FB_BASE}/login", timeout=30000)
            self._human_delay(2, 4)
            page.fill('input[name="email"]', self.email)
            self._human_delay(1, 2)
            page.fill('input[name="pass"]', self.password)
            self._human_delay(0.5, 1.5)
            page.click('button[name="login"]')
            self._human_delay(5, 8)

            if "checkpoint" in page.url or "login" in page.url:
                logger.error("Login blocked / checkpoint required")
                return False

            logger.info("Credential login successful")
            return True
        except Exception as e:
            logger.error(f"Credential login failed: {e}")
            return False

    # ------------------------------------------------------------------ #
    # Main scraping
    # ------------------------------------------------------------------ #

    def scrape_page_posts(
        self,
        page_name: str,
        max_posts: int = 200,
        max_scrolls: int = 500,
        save_cookies_to: str = "",
        progress_callback=None,
    ) -> list[FBPostData]:

        p, browser = self._create_browser()
        context = self._setup_context_with_cookies(browser)
        page = self._setup_page(context)
        posts: list[FBPostData] = []
        seen_ids: set[str] = set()

        try:
            # --- Auth ---
            has_cookies = bool(self._cookies) and self._validate_cookies()

            if has_cookies:
                logged_in = self._verify_logged_in(page)
                if not logged_in:
                    logger.warning("Cookies present but session invalid. Trying credentials...")
                    logged_in = self.login_with_credentials(page)
            else:
                logged_in = self.login_with_credentials(page)

            if not logged_in:
                logger.warning("Proceeding without authentication (public data only)")

            # Guarda cookies actualizadas si se solicitó
            if save_cookies_to:
                self.save_cookies(context, save_cookies_to)

            # --- Navigate to page ---
            target_url = (
                page_name
                if page_name.startswith("http")
                else f"{FB_BASE}/{page_name}"
            )
            logger.info(f"Navigating to {target_url}")
            page.goto(target_url, timeout=60000)
            self._human_delay(3, 6)
            self._reject_cookies(page)

            # --- Scroll & extract ---
            stale = 0
            last_count = 0

            for scroll in range(max_scrolls):
                if len(posts) >= max_posts:
                    break

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self._human_delay(2, 4)

                new_posts = self._extract_posts_from_page(page, page_name, seen_ids)
                for post in new_posts:
                    if post.post_id not in seen_ids:
                        seen_ids.add(post.post_id)
                        posts.append(post)

                if progress_callback:
                    progress_callback(len(posts), max_posts)

                # Detect stale (no new posts)
                if len(posts) == last_count:
                    stale += 1
                    if stale >= 10 and scroll > 20:
                        logger.info(f"No new posts after {scroll} scrolls. Stopping.")
                        break
                else:
                    stale = 0
                last_count = len(posts)

                logger.debug(f"Scroll {scroll}: {len(posts)} posts collected")

        except Exception as e:
            logger.error(f"Scraping error: {e}", exc_info=True)
        finally:
            browser.close()
            p.stop()

        logger.info(f"Total posts scraped: {len(posts)}")
        return posts

    # ------------------------------------------------------------------ #
    # Extraction helpers (unchanged from original)
    # ------------------------------------------------------------------ #

    def _reject_cookies(self, page: Page):
        try:
            buttons = page.query_selector_all(
                'button:has-text("Rechazar"), '
                'button:has-text("Denegar"), '
                'button:has-text("Decline"), '
                'div[role="button"]:has-text("Rechazar")'
            )
            for btn in buttons:
                try:
                    btn.click()
                    self._human_delay(0.5, 1)
                except Exception:
                    pass
        except Exception:
            pass

    def _extract_posts_from_page(
        self, page: Page, page_name: str, seen_ids: set
    ) -> list[FBPostData]:
        found = []

        post_elements = page.query_selector_all(
            'div[data-pagelet^="FeedUnit"], '
            'div[role="article"], '
            'div[class*="userContentWrapper"], '
            'div[class*="fbUserContent"]'
        )
        if not post_elements:
            post_elements = page.query_selector_all('div[data-testid="fbfeed_story"]')

        for el in post_elements:
            try:
                post_id = el.get_attribute("id") or el.get_attribute("data-pagelet") or ""
                if not post_id:
                    href = el.query_selector('a[href*="/posts/"]')
                    if href:
                        match = re.search(r"/posts/(\d+)", href.get_attribute("href") or "")
                        if match:
                            post_id = match.group(1)

                if not post_id or post_id in seen_ids:
                    continue

                message_el = el.query_selector(
                    'div[data-ad-preview="message"], '
                    'span[class*="d2edcug0"], '
                    'div[class*="ecm0bbzt"]'
                )
                message = message_el.inner_text().strip() if message_el else ""

                reactions = self._extract_reactions(el)
                comments_count = self._extract_comments_count(el)
                shares_count = self._extract_shares_count(el)
                timestamp = self._extract_timestamp(el)

                post = FBPostData(
                    post_id=post_id,
                    page_id=page_name,
                    message=message,
                    created_time=timestamp,
                    likes_count=reactions.get("likes", 0),
                    comments_count=comments_count,
                    shares_count=shares_count,
                    post_url=f"{FB_BASE}/{post_id}",
                    source="playwright",
                )
                found.append(post)

            except Exception as e:
                logger.debug(f"Error extracting post: {e}")

        return found

    def _extract_reactions(self, element) -> dict:
        counts = {"likes": 0}
        try:
            text = element.inner_text()
            like_match = re.search(r"(\d+[KM]?)\s*(Me gusta|Like|Reacciones)", text)
            if like_match:
                counts["likes"] = self._parse_number(like_match.group(1))
            total_match = re.search(r"(\d+[KM]?)\s*personas?\s*(le|han)?\s*dado", text)
            if total_match:
                counts["likes"] = max(counts["likes"], self._parse_number(total_match.group(1)))
        except Exception:
            pass
        return counts

    def _extract_comments_count(self, element) -> int:
        try:
            text = element.inner_text()
            match = re.search(r"(\d+[KM]?)\s*Comentarios?|Comentarios?\s*(\d+)", text)
            if match:
                return self._parse_number(match.group(1) or match.group(2))
        except Exception:
            pass
        return 0

    def _extract_shares_count(self, element) -> int:
        try:
            text = element.inner_text()
            match = re.search(r"(\d+[KM]?)\s*Veces\s*compartido|Compartir\s*(\d+)", text)
            if match:
                return self._parse_number(match.group(1) or match.group(2))
        except Exception:
            pass
        return 0

    def _extract_timestamp(self, element):
        try:
            time_el = element.query_selector(
                'a[href*="/posts/"] time, '
                'span[class*="timestamp"] span, '
                'abbr[data-utime]'
            )
            if time_el:
                utime = time_el.get_attribute("data-utime")
                if utime:
                    return datetime.fromtimestamp(int(utime))
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_number(text: str) -> int:
        text = text.strip().upper()
        multiplier = 1
        if "K" in text:
            multiplier = 1000
            text = text.replace("K", "")
        elif "M" in text:
            multiplier = 1_000_000
            text = text.replace("M", "")
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return 0