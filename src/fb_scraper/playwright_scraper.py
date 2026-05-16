import logging
import re
import time
from datetime import datetime
from typing import Optional

from playwright.sync_api import sync_playwright, Page, Browser
from playwright_stealth import Stealth

from src.fb_scraper.models import FBPostData, FBCommentData

logger = logging.getLogger(__name__)

FB_BASE = "https://www.facebook.com"


class FacebookPlaywright:
    def __init__(
        self,
        email: str = "",
        password: str = "",
        proxy_url: str = "",
        headless: bool = False,
    ):
        self.email = email
        self.password = password
        self.proxy_url = proxy_url
        self.headless = headless

    def _create_browser(self) -> Browser:
        launch_opts = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        }
        if self.proxy_url:
            launch_opts["proxy"] = {"server": self.proxy_url}

        p = sync_playwright().start()
        browser = p.chromium.launch(**launch_opts)
        return browser

    def _setup_page(self, browser: Browser) -> Page:
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
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        return page

    def _human_delay(self, min_s: float = 1.0, max_s: float = 3.0):
        time.sleep(min_s + (max_s - min_s) * (time.time() % 1))

    def login(self, page: Page) -> bool:
        if not self.email or not self.password:
            logger.warning("No Facebook login credentials provided")
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
                logger.error("Facebook login blocked or checkpoint required")
                return False

            logger.info("Facebook login successful")
            return True

        except Exception as e:
            logger.error(f"Facebook login failed: {e}")
            return False

    def scrape_page_posts(
        self,
        page_name: str,
        max_posts: int = 200,
        max_scrolls: int = 500,
        progress_callback=None,
    ) -> list[FBPostData]:
        browser = self._create_browser()
        page = self._setup_page(browser)
        posts = []
        seen_ids = set()

        try:
            if self.email:
                self.login(page)

            page.goto(f"{FB_BASE}/{page_name}", timeout=60000)
            self._human_delay(3, 6)
            self._reject_cookies(page)

            for scroll in range(max_scrolls):
                if len(posts) >= max_posts:
                    break

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self._human_delay(2, 4)

                new_posts = self._extract_posts_from_page(page, page_name, seen_ids)
                for p in new_posts:
                    if p.post_id not in seen_ids:
                        seen_ids.add(p.post_id)
                        posts.append(p)

                if progress_callback:
                    progress_callback(len(posts), max_posts)

                if not new_posts:
                    logger.info(f"No new posts found at scroll {scroll}")
                    if scroll > 20:
                        break

        except Exception as e:
            logger.error(f"Error during scraping: {e}")

        finally:
            browser.close()

        return posts

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
            post_elements = page.query_selector_all(
                'div[data-testid="fbfeed_story"]'
            )

        for el in post_elements:
            try:
                post_id = el.get_attribute("id") or el.get_attribute("data-pagelet") or ""
                if not post_id:
                    href = el.query_selector('a[href*="/posts/"]')
                    if href:
                        match = re.search(r'/posts/(\d+)', href.get_attribute("href") or "")
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
                continue

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
            multiplier = 1000000
            text = text.replace("M", "")
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return 0
