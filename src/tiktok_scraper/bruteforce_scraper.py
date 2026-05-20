"""
TikTok Brute Force Scraper - Multi-method aggressive scraper
Usa 7+ métodos para extraer datos de TikTok evadiendo bloqueos.
"""
import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Callable, Tuple
from urllib.parse import quote

import httpx
import requests
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

TT_BASE = "https://www.tiktok.com"

def _get_ua() -> UserAgent:
    try:
        return UserAgent()
    except:
        return None

UA = _get_ua()

# ──────────────────────────────────────────────
# Configuración de métodos
# ──────────────────────────────────────────────

class MethodConfig:
    """Configuración por método de scraping"""
    api_delay: Tuple[float, float] = (2.0, 5.0)
    max_retries: int = 5
    backoff_base: float = 2.0
    timeout: int = 30

# ──────────────────────────────────────────────
# Modelos internos
# ──────────────────────────────────────────────

class BFTTPost:
    def __init__(self, data: dict):
        self.video_id: str = str(data.get("video_id", data.get("id", "")))
        self.username: str = data.get("username", data.get("author", ""))
        self.description: str = data.get("description", data.get("desc", "")) or ""
        self.create_time: Optional[datetime] = None
        ct = data.get("create_time", data.get("createTime", 0))
        if ct and isinstance(ct, (int, float)) and ct > 0:
            self.create_time = datetime.fromtimestamp(ct)
        elif isinstance(ct, str):
            try:
                self.create_time = datetime.fromisoformat(ct)
            except:
                pass

        self.likes_count: int = int(data.get("likes_count", data.get("diggCount", data.get("digg_count", 0))))
        self.comments_count: int = int(data.get("comments_count", data.get("commentCount", data.get("comment_count", 0))))
        self.shares_count: int = int(data.get("shares_count", data.get("shareCount", data.get("share_count", 0))))
        self.views_count: int = int(data.get("views_count", data.get("playCount", data.get("play_count", data.get("viewCount", 0)))))
        self.favorites_count: int = int(data.get("favorites_count", data.get("collectCount", data.get("collect_count", 0))))

        self.hashtags: List[str] = data.get("hashtags", []) or re.findall(r'#(\w+)', self.description)
        self.video_url: str = data.get("video_url", f"{TT_BASE}/@{self.username}/video/{self.video_id}")
        self.source: str = data.get("source", "unknown")

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "username": self.username,
            "description": self.description,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "shares_count": self.shares_count,
            "views_count": self.views_count,
            "favorites_count": self.favorites_count,
            "hashtags": self.hashtags,
            "video_url": self.video_url,
            "source": self.source,
        }


class BFTTComment:
    def __init__(self, data: dict):
        self.comment_id: str = str(data.get("comment_id", data.get("cid", "")))
        self.video_id: str = str(data.get("video_id", ""))
        self.message: str = data.get("message", data.get("text", "")) or ""
        self.author_name: str = data.get("author_name", "") or data.get("user", {}).get("nickname", "") or ""
        self.author_unique_id: str = data.get("author_unique_id", "") or data.get("user", {}).get("unique_id", "")
        self.create_time: Optional[datetime] = None
        ct = data.get("create_time", data.get("createTime", 0))
        if ct and isinstance(ct, (int, float)) and ct > 0:
            self.create_time = datetime.fromtimestamp(ct)
        self.likes_count: int = int(data.get("likes_count", data.get("digg_count", 0)))
        self.reply_count: int = int(data.get("reply_count", 0))

    def to_dict(self) -> dict:
        return {
            "comment_id": self.comment_id,
            "video_id": self.video_id,
            "message": self.message[:5000],
            "author_name": self.author_name[:100],
            "author_unique_id": self.author_unique_id,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "likes_count": self.likes_count,
            "reply_count": self.reply_count,
        }


# ──────────────────────────────────────────────
# Scraper principal
# ──────────────────────────────────────────────

class TikTokBruteForceScraper:
    def __init__(
        self,
        username: str,
        cookies_file: str = "",
        proxy: str = "",
        headless: bool = False,
        data_dir: str = "",
    ):
        self.username = username
        self.cookies_file = cookies_file
        self.proxy = proxy
        self.headless = headless
        self.data_dir = data_dir or str(Path(__file__).parent.parent.parent / "data")

        self.session_cookies: Dict[str, str] = {}
        self._load_cookies()

        self.httpx_client: Optional[httpx.AsyncClient] = None
        self.playwright_instance = None
        self.browser = None

    # ── Cookie Management ────────────────────

    def _load_cookies(self):
        if self.cookies_file and Path(self.cookies_file).exists():
            try:
                raw = json.loads(Path(self.cookies_file).read_text())
                if isinstance(raw, list):
                    for c in raw:
                        if c.get("name") in ("sessionid", "sid_tt", "uid_tt", "ttwid"):
                            self.session_cookies[c["name"]] = c["value"]
                elif isinstance(raw, dict):
                    self.session_cookies = raw
                logger.info(f"Loaded {len(self.session_cookies)} session cookies")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")

    def _has_session(self) -> bool:
        return "sessionid" in self.session_cookies or "sid_tt" in self.session_cookies

    def _cookie_header(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self.session_cookies.items())

    @staticmethod
    def _random_ua() -> str:
        if UA:
            try:
                return UA.random
            except:
                pass
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        ]
        return random.choice(agents)

    def _random_headers(self, referer: str = "") -> dict:
        headers = {
            "User-Agent": self._random_ua(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if self._has_session():
            headers["Cookie"] = self._cookie_header()
        if referer:
            headers["Referer"] = referer
        else:
            headers["Referer"] = f"{TT_BASE}/@{self.username}"
        return headers

    def _human_delay(self, min_s: float = 3.0, max_s: float = 8.0):
        delay = random.uniform(min_s, max_s)
        logger.debug(f"Delay: {delay:.1f}s")
        time.sleep(delay)

    def _filter_by_date(self, post: BFTTPost, days_back: int = 365) -> bool:
        if not post.create_time:
            return True
        cutoff = datetime.now() - timedelta(days=days_back)
        return post.create_time >= cutoff

    # ══════════════════════════════════════════
    #  METHOD 1: API con session cookies
    # ══════════════════════════════════════════

    def _method_api_session(self, cursor: int = 0, count: int = 35) -> Tuple[List[BFTTPost], int]:
        videos = []
        next_cursor = 0

        if not self._has_session():
            logger.warning("Method 1 (API session): no session cookies available")
            return videos, next_cursor

        try:
            url = f"{TT_BASE}/api/post/item_list/"
            params = {
                "aid": "1988",
                "app_language": "es",
                "app_name": "tiktok_web",
                "browser_language": "es",
                "browser_name": "Mozilla",
                "browser_online": "true",
                "browser_platform": "MacIntel",
                "browser_version": "135",
                "channel": "tiktok_web",
                "cookie_enabled": "true",
                "count": str(count),
                "cursor": str(cursor),
                "device_id": str(random.randint(7000000000000000000, 7999999999999999999)),
                "device_platform": "web_pc",
                "focus_state": "true",
                "history_len": str(random.randint(1, 10)),
                "is_fullscreen": "false",
                "is_page_visible": "true",
                "os": "mac",
                "priority_region": "",
                "referer": "",
                "region": "sv",
                "root_referer": TT_BASE,
                "screen_height": "1080",
                "screen_width": "1920",
                "secUid": "",
                "source": "6",
                "uniqueId": self.username,
                "webcast_language": "es",
                "msToken": "",
            }
            headers = self._random_headers(referer=f"{TT_BASE}/@{self.username}")

            resp = requests.get(url, params=params, headers=headers, timeout=30)
            logger.info(f"Method 1 status: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("itemList", [])
                for item in items:
                    item["username"] = self.username
                    item["source"] = "api_session"
                    videos.append(BFTTPost(item))
                next_cursor = data.get("cursor", 0)
                logger.info(f"Method 1: got {len(items)} videos")
            elif resp.status_code == 401:
                logger.warning("Method 1: session expired, need re-login")
            elif resp.status_code == 429:
                logger.warning("Method 1: rate limited")
            else:
                logger.warning(f"Method 1: unexpected status {resp.status_code}")
                logger.debug(f"Response: {resp.text[:500]}")

        except Exception as e:
            logger.warning(f"Method 1 error: {e}")

        return videos, next_cursor

    # ══════════════════════════════════════════
    #  METHOD 2: API vía item/detail (video individual)
    # ══════════════════════════════════════════

    def _method_item_detail(self, video_id: str) -> Optional[BFTTPost]:
        try:
            url = f"{TT_BASE}/api/item/detail/"
            params = {
                "aid": "1988",
                "app_language": "es",
                "app_name": "tiktok_web",
                "itemId": video_id,
            }
            headers = self._random_headers(referer=f"{TT_BASE}/video/{video_id}")

            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                item = data.get("itemInfo", {}).get("itemStruct")
                if item:
                    item["username"] = self.username
                    item["source"] = "item_detail"
                    return BFTTPost(item)
        except Exception as e:
            logger.debug(f"Method 2 error for {video_id}: {e}")
        return None

    # ══════════════════════════════════════════
    #  METHOD 3: API móvil
    # ══════════════════════════════════════════

    def _method_mobile_api(self, cursor: int = 0) -> Tuple[List[BFTTPost], int]:
        videos = []
        next_cursor = 0

        try:
            url = "https://api16-normal-c-useast1a.tiktok.com/aweme/v1/web/aweme/v3/web/item_list/"
            params = {
                "aid": "1988",
                "app_name": "musically",
                "app_version": "35.0.0",
                "device_platform": "iphone",
                "os_version": "17.4",
                "channel": "appstore",
                "device_type": "iPhone15,2",
                "count": 30,
                "cursor": cursor,
                "sec_user_id": "",
                "source": "aweme",
                "unique_id": self.username,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                "Accept": "application/json",
                "Accept-Language": "es-ES,es;q=0.9",
                "Referer": f"{TT_BASE}/@{self.username}",
            }

            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("aweme_list", [])
                for item in items:
                    stats = item.get("statistics", {})
                    post_data = {
                        "video_id": item.get("aweme_id", ""),
                        "username": self.username,
                        "description": item.get("desc", ""),
                        "create_time": item.get("create_time", 0),
                        "likes_count": stats.get("digg_count", 0),
                        "comments_count": stats.get("comment_count", 0),
                        "shares_count": stats.get("share_count", 0),
                        "views_count": stats.get("play_count", 0),
                        "favorites_count": stats.get("collect_count", 0),
                        "source": "mobile_api",
                    }
                    videos.append(BFTTPost(post_data))
                next_cursor = data.get("cursor", 0)
                logger.info(f"Method 3 (mobile): got {len(items)} videos")
        except Exception as e:
            logger.warning(f"Method 3 error: {e}")

        return videos, next_cursor

    # ══════════════════════════════════════════
    #  METHOD 4: Playwright con stealth
    # ══════════════════════════════════════════

    def _method_playwright(self, max_scrolls: int = 100) -> List[BFTTPost]:
        videos = []
        seen_ids = set()

        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth

            with sync_playwright() as p:
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
                if self.proxy:
                    launch_opts["proxy"] = {"server": self.proxy}

                browser = p.chromium.launch(**launch_opts)
                context = browser.new_context(
                    viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
                    user_agent=self._random_ua(),
                    locale="es-SV",
                    timezone_id="America/El_Salvador",
                    permissions=[],
                )

                if self.cookies_file and Path(self.cookies_file).exists():
                    try:
                        cookies = json.loads(Path(self.cookies_file).read_text())
                        if isinstance(cookies, list):
                            context.add_cookies(cookies)
                    except:
                        pass

                page = context.new_page()
                Stealth().apply_stealth_sync(page)

                logger.info(f"PW: Navigating to @{self.username}")
                page.goto(f"{TT_BASE}/@{self.username}", timeout=60000, wait_until="networkidle")
                self._human_delay(5, 10)

                def _extract_from_page() -> List[BFTTPost]:
                    found = []
                    try:
                        data = page.evaluate("""
                            () => {
                                try {
                                    const el = document.getElementById('__UNIVERSAL_DATA_FOR_VIEW__');
                                    if (el) return JSON.parse(el.textContent);
                                } catch(e) {}
                                try {
                                    const el = document.getElementById('SIGI_STATE');
                                    if (el) return JSON.parse(el.textContent);
                                } catch(e) {}
                                try {
                                    if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;
                                } catch(e) {}
                                return null;
                            }
                        """)
                        if data:
                            items = data.get("ItemModule", {}) or data.get("default", {}).get("data", {}).get("items", [])
                            if isinstance(items, dict):
                                items = items.values()
                            for item in items:
                                if isinstance(item, dict):
                                    item["username"] = self.username
                                    item["source"] = "playwright_json"
                                    p = BFTTPost(item)
                                    if p.video_id and p.video_id not in seen_ids:
                                        seen_ids.add(p.video_id)
                                        found.append(p)
                    except:
                        pass
                    return found

                videos.extend(_extract_from_page())
                logger.info(f"PW initial: {len(videos)} videos")

                last_height = 0
                stale = 0
                for scroll in range(max_scrolls):
                    if len(videos) >= 2000:
                        break

                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    self._human_delay(3, 7)

                    new_videos = _extract_from_page()
                    for v in new_videos:
                        if v.video_id not in seen_ids:
                            seen_ids.add(v.video_id)
                            videos.append(v)

                    current_height = page.evaluate("document.body.scrollHeight")
                    if current_height == last_height:
                        stale += 1
                        if stale >= 10:
                            break
                    else:
                        stale = 0
                    last_height = current_height

                    if scroll % 10 == 0:
                        logger.info(f"PW scroll {scroll}: {len(videos)} videos")

                browser.close()

        except Exception as e:
            logger.warning(f"Method 4 (playwright) error: {e}")

        return videos

    # ══════════════════════════════════════════
    #  METHOD 5: Selenium con evasión
    # ══════════════════════════════════════════

    def _method_selenium(self, max_scrolls: int = 80) -> List[BFTTPost]:
        videos = []
        seen_ids = set()

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            opts = Options()
            if self.headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument(f"--user-agent={self._random_ua()}")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)

            if self.proxy:
                opts.add_argument(f"--proxy-server={self.proxy}")

            driver = webdriver.Chrome(options=opts)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es']});
                """
            })

            logger.info(f"Selenium: loading @{self.username}")
            driver.get(f"{TT_BASE}/@{self.username}")
            self._human_delay(8, 15)

            last_height = 0
            stale = 0

            for scroll in range(max_scrolls):
                if len(videos) >= 2000:
                    break

                try:
                    page_source = driver.page_source
                    sigi_matches = re.findall(
                        r'<script[^>]*id="__UNIVERSAL_DATA_FOR_VIEW__"[^>]*>(.*?)</script>',
                        page_source, re.DOTALL
                    )
                    for match in sigi_matches:
                        try:
                            data = json.loads(match)
                            items = data.get("default", {}).get("data", {}).get("items", [])
                            for item in items:
                                vid = str(item.get("id", ""))
                                if vid and vid not in seen_ids:
                                    seen_ids.add(vid)
                                    item["username"] = self.username
                                    item["source"] = "selenium"
                                    videos.append(BFTTPost(item))
                        except:
                            continue
                except:
                    pass

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                self._human_delay(3, 7)

                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    stale += 1
                    if stale >= 8:
                        break
                else:
                    stale = 0
                last_height = new_height

                if scroll % 10 == 0:
                    logger.info(f"Selenium scroll {scroll}: {len(videos)} videos")

            driver.quit()

        except Exception as e:
            logger.warning(f"Method 5 (selenium) error: {e}")

        return videos

    # ══════════════════════════════════════════
    #  METHOD 6: RSS Feed
    # ══════════════════════════════════════════

    def _method_rss(self) -> List[BFTTPost]:
        videos = []
        try:
            url = f"{TT_BASE}/@{self.username}/rss"
            headers = {"User-Agent": self._random_ua()}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(resp.content)
                    ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
                    for entry in root.findall(".//atom:entry", ns):
                        video_id = ""
                        link_el = entry.find("atom:link", ns)
                        if link_el is not None:
                            href = link_el.get("href", "")
                            video_id = href.split("/video/")[-1] if "/video/" in href else ""
                        title = entry.findtext("atom:title", "", ns)
                        published = entry.findtext("atom:published", "", ns)
                        if video_id:
                            ct = None
                            if published:
                                try:
                                    ct = datetime.fromisoformat(published.replace("Z", "+00:00"))
                                except:
                                    pass
                            videos.append(BFTTPost({
                                "video_id": video_id,
                                "username": self.username,
                                "description": title,
                                "create_time": ct.timestamp() if ct else 0,
                                "source": "rss",
                            }))
                except ET.ParseError:
                    pass
                logger.info(f"Method 6 (RSS): got {len(videos)} videos")
        except Exception as e:
            logger.debug(f"Method 6 error: {e}")
        return videos

    # ══════════════════════════════════════════
    #  METHOD 7: Feed API (endpoint alternativo)
    # ══════════════════════════════════════════

    def _method_feed_api(self, cursor: int = 0) -> Tuple[List[BFTTPost], int]:
        videos = []
        next_cursor = 0

        try:
            url = f"{TT_BASE}/api/aweme/v1/web/aweme/v3/web/item_list/"
            params = {
                "aid": "1988",
                "count": 30,
                "cursor": cursor,
                "sec_user_id": "",
                "type": "0",
                "unique_id": self.username,
            }
            headers = self._random_headers(referer=f"{TT_BASE}/@{self.username}")

            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("aweme_list", [])
                for item in items:
                    stats = item.get("statistics", {})
                    post_data = {
                        "video_id": item.get("aweme_id", ""),
                        "username": self.username,
                        "description": item.get("desc", ""),
                        "create_time": item.get("create_time", 0),
                        "likes_count": stats.get("digg_count", 0),
                        "comments_count": stats.get("comment_count", 0),
                        "shares_count": stats.get("share_count", 0),
                        "views_count": stats.get("play_count", 0),
                        "favorites_count": stats.get("collect_count", 0),
                        "source": "feed_api",
                    }
                    videos.append(BFTTPost(post_data))
                next_cursor = data.get("cursor", 0)
                logger.info(f"Method 7 (feed API): got {len(items)} videos")
        except Exception as e:
            logger.debug(f"Method 7 error: {e}")

        return videos, next_cursor

    # ══════════════════════════════════════════
    #  METHOD 8: búsqueda por hashtag del usuario
    # ══════════════════════════════════════════

    def _method_search(self, cursor: int = 0) -> Tuple[List[BFTTPost], int]:
        videos = []
        next_cursor = 0

        try:
            url = f"{TT_BASE}/api/search/item/full/"
            params = {
                "aid": "1988",
                "app_language": "es",
                "count": 20,
                "cursor": cursor,
                "keyword": f"@{self.username}",
                "search_source": "search_sug",
                "type": "1",
            }
            headers = self._random_headers()

            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("item_list", [])
                for item in items:
                    item["username"] = self.username
                    item["source"] = "search"
                    videos.append(BFTTPost(item))
                next_cursor = data.get("cursor", 0)
                logger.info(f"Method 8 (search): got {len(items)} videos")
        except Exception as e:
            logger.debug(f"Method 8 error: {e}")

        return videos, next_cursor

    # ══════════════════════════════════════════
    #  COMMENT EXTRACTION
    # ══════════════════════════════════════════

    def get_comments(self, video_id: str, max_comments: int = 0) -> List[BFTTComment]:
        comments = []
        cursor = 0
        has_more = True

        for attempt in range(5):
            if not has_more:
                break
            if max_comments > 0 and len(comments) >= max_comments:
                break

            try:
                batch = min(50, max_comments - len(comments)) if max_comments > 0 else 50
                url = f"{TT_BASE}/api/comment/list/"
                params = {
                    "aid": "1988",
                    "app_language": "es",
                    "app_name": "tiktok_web",
                    "aweme_id": video_id,
                    "count": str(batch),
                    "cursor": str(cursor),
                    "device_platform": "web_pc",
                }
                headers = self._random_headers(referer=f"{TT_BASE}/video/{video_id}")

                resp = requests.get(url, params=params, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("comments", [])
                    for item in items:
                        item["video_id"] = video_id
                        comments.append(BFTTComment(item))
                    has_more = data.get("has_more", False)
                    cursor = data.get("cursor", 0)
                    logger.debug(f"Comments for {video_id}: {len(items)} (total: {len(comments)}, more: {has_more})")
                elif resp.status_code == 429:
                    wait = min(2 ** attempt * 10, 120)
                    logger.warning(f"Comment rate limit, waiting {wait}s")
                    time.sleep(wait)
                    continue
                else:
                    logger.warning(f"Comment fetch status {resp.status_code} for {video_id}")
                    break

                time.sleep(random.uniform(1.0, 3.0))

            except Exception as e:
                logger.warning(f"Comment error for {video_id}: {e}")
                time.sleep(2 ** attempt * 5)

        return comments

    # ══════════════════════════════════════════
    #  ORQUESTADOR PRINCIPAL
    # ══════════════════════════════════════════

    def scrape_videos(
        self,
        max_videos: int = 500,
        days_back: int = 365,
        progress_callback: Optional[Callable] = None,
    ) -> List[BFTTPost]:
        logger.info(f"\n{'='*60}")
        logger.info(f"TIKTOK BRUTE FORCE SCRAPER")
        logger.info(f"Target: @{self.username}")
        logger.info(f"Max videos: {max_videos}")
        logger.info(f"Days back: {days_back}")
        logger.info(f"Has session: {self._has_session()}")
        logger.info(f"{'='*60}\n")

        all_videos: Dict[str, BFTTPost] = {}
        methods_used: List[str] = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # ── Phase 1: Try all API methods ──

        api_methods = [
            ("api_session", self._method_api_session),
            ("mobile_api", self._method_mobile_api),
            ("feed_api", self._method_feed_api),
            ("search", self._method_search),
        ]

        for method_name, method_func in api_methods:
            if len(all_videos) >= max_videos:
                break

            logger.info(f"\n>>> Phase 1: Trying {method_name}...")
            cursor = 0
            method_videos = 0
            api_attempts = 0

            while len(all_videos) < max_videos * 2:
                items, cursor = method_func(cursor)
                if not items:
                    break

                for v in items:
                    if v.video_id and v.video_id not in all_videos:
                        if self._filter_by_date(v, days_back):
                            all_videos[v.video_id] = v

                method_videos += len(items)
                methods_used.append(method_name)

                if progress_callback:
                    progress_callback(len(all_videos), max_videos)

                if cursor <= 0 or cursor is None:
                    break

                api_attempts += 1
                if api_attempts >= 30:
                    break

                self._human_delay(2, 5)

            logger.info(f"  {method_name}: {method_videos} videos → total unique: {len(all_videos)}")
            self._human_delay(5, 10)

        # ── Phase 2: Playwright (browser) ──

        if len(all_videos) < max_videos:
            logger.info(f"\n>>> Phase 2: Trying Playwright...")
            pw_videos = self._method_playwright(max_scrolls=60)
            for v in pw_videos:
                if v.video_id and v.video_id not in all_videos:
                    if self._filter_by_date(v, days_back):
                        all_videos[v.video_id] = v
            methods_used.append("playwright")
            logger.info(f"  Playwright: {len(pw_videos)} → total: {len(all_videos)}")
            if progress_callback:
                progress_callback(len(all_videos), max_videos)
            self._human_delay(10, 20)

        # ── Phase 3: Selenium ──

        if len(all_videos) < max_videos:
            logger.info(f"\n>>> Phase 3: Trying Selenium...")
            sel_videos = self._method_selenium(max_scrolls=50)
            for v in sel_videos:
                if v.video_id and v.video_id not in all_videos:
                    if self._filter_by_date(v, days_back):
                        all_videos[v.video_id] = v
            methods_used.append("selenium")
            logger.info(f"  Selenium: {len(sel_videos)} → total: {len(all_videos)}")
            if progress_callback:
                progress_callback(len(all_videos), max_videos)

        # ── Phase 4: RSS fallback ──

        if len(all_videos) < max_videos:
            logger.info(f"\n>>> Phase 4: Trying RSS...")
            rss_videos = self._method_rss()
            still_needed = []
            for v in rss_videos:
                if v.video_id and v.video_id not in all_videos:
                    if self._filter_by_date(v, days_back):
                        still_needed.append(v)
            if still_needed and self._has_session():
                logger.info(f"  RSS got {len(still_needed)} new IDs, fetching details...")
                for i, v in enumerate(still_needed):
                    if len(all_videos) >= max_videos:
                        break
                    detail = self._method_item_detail(v.video_id)
                    if detail and detail.views_count > 0:
                        all_videos[v.video_id] = detail
                    if i % 10 == 0:
                        self._human_delay(1, 3)
            elif still_needed:
                for v in still_needed:
                    all_videos[v.video_id] = v
            methods_used.append("rss")
            logger.info(f"  RSS: {len(still_needed)} → total: {len(all_videos)}")

        # ── Final filter & sort ──

        result = sorted(
            [v for v in all_videos.values() if self._filter_by_date(v, days_back)],
            key=lambda x: x.create_time or datetime.min,
            reverse=True,
        )

        result = result[:max_videos]

        logger.info(f"\n{'='*60}")
        logger.info(f"SCRAPING COMPLETE")
        logger.info(f"Total unique videos: {len(result)}")
        logger.info(f"Methods used: {', '.join(set(methods_used))}")
        logger.info(f"Date range: {result[-1].create_time if result else 'N/A'} → {result[0].create_time if result else 'N/A'}")
        logger.info(f"{'='*60}")

        return result

    def scrape_all_comments(
        self,
        videos: List[BFTTPost],
        max_comments_per_video: int = 0,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, List[BFTTComment]]:
        logger.info(f"\n{'='*60}")
        logger.info(f"EXTRACTING COMMENTS FOR {len(videos)} VIDEOS")
        logger.info(f"{'='*60}\n")

        all_comments: Dict[str, List[BFTTComment]] = {}
        total = len(videos)

        for i, video in enumerate(videos):
            if video.comments_count == 0:
                logger.debug(f"  [{i+1}/{total}] {video.video_id}: 0 comments (skipping)")
                all_comments[video.video_id] = []
                if progress_callback:
                    progress_callback(i + 1, total)
                continue

            logger.info(f"  [{i+1}/{total}] Comments for {video.video_id} (est. {video.comments_count})")
            comments = self.get_comments(video.video_id, max_comments_per_video)
            all_comments[video.video_id] = comments

            if progress_callback:
                progress_callback(i + 1, total)

            delay = random.uniform(3.0, 8.0)
            if i < total - 1:
                logger.debug(f"  Waiting {delay:.1f}s before next video")
                time.sleep(delay)

        total_comments = sum(len(c) for c in all_comments.values())
        logger.info(f"\nTotal comments extracted: {total_comments}")
        return all_comments


# ══════════════════════════════════════════
#  SESSION LOGIN HELPER
# ══════════════════════════════════════════

def login_and_save_cookies(cookies_path: str, username: str = ""):
    """
    Abre navegador para que el usuario haga login manual en TikTok.
    Guarda cookies después de login exitoso.
    """
    print("\n" + "="*60)
    print("TIKTOK LOGIN - Captura de Cookies de Sesión")
    print("="*60)
    print("\n1. Se abrirá una ventana del navegador")
    print("2. Inicia sesión en TikTok manualmente")
    print("3. Las cookies se guardarán automáticamente\n")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=TikTokBruteForceScraper._random_ua(),
        )
        page = context.new_page()

        target = f"{TT_BASE}/@{username}" if username else TT_BASE
        page.goto(target, timeout=30000)
        print(f"✓ Navegador abierto: {target}")
        print("\n⏳ Inicia sesión manualmente (tienes 120 segundos)...")

        # Esperar a que el usuario haga login
        for sec in range(120, 0, -1):
            if sec % 10 == 0 or sec <= 5:
                print(f"   Esperando... {sec}s restantes", end="\r")
            time.sleep(1)

        print("\n\n✓ Guardando cookies...")

        cookies = context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        # Guardar ambos formatos
        Path(cookies_path).write_text(json.dumps(cookies, indent=2))
        print(f"✓ Cookies guardadas en: {cookies_path}")

        session_cookies_path = str(Path(cookies_path).parent / "tiktok_session.json")
        Path(session_cookies_path).write_text(json.dumps(cookie_dict, indent=2))
        print(f"✓ Session cookies guardadas en: {session_cookies_path}")

        has_session = "sessionid" in cookie_dict or "sid_tt" in cookie_dict
        print(f"\n✓ Session ID encontrada: {'SÍ' if has_session else 'NO'}")

        if has_session:
            print("✓ El scraper ahora puede usar estas cookies para autenticarse")
        else:
            print("⚠️ No se encontró sessionid - prueba a iniciar sesión de nuevo")

        browser.close()
        print("\n✓ Listo!")


# ══════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="TikTok Brute Force Scraper")
    sub = parser.add_subparsers(dest="cmd")

    scrape_p = sub.add_parser("scrape", help="Scrape videos")
    scrape_p.add_argument("--user", default="alcaldiasa", help="TikTok username")
    scrape_p.add_argument("--max", type=int, default=500, help="Max videos")
    scrape_p.add_argument("--days", type=int, default=365, help="Days back")
    scrape_p.add_argument("--cookies", default="", help="Cookies file path")
    scrape_p.add_argument("--comments", action="store_true", help="Extract comments")
    scrape_p.add_argument("--headless", action="store_true", help="Headless mode")

    login_p = sub.add_parser("login", help="Login to TikTok and save cookies")
    login_p.add_argument("--cookies", default="tiktok_cookies.json", help="Cookies output path")
    login_p.add_argument("--user", default="", help="TikTok username to visit")

    args = parser.parse_args()

    if args.cmd == "login":
        login_and_save_cookies(args.cookies, args.user)
    elif args.cmd == "scrape":
        scraper = TikTokBruteForceScraper(
            username=args.user,
            cookies_file=args.cookies,
            headless=args.headless,
        )
        videos = scraper.scrape_videos(max_videos=args.max, days_back=args.days)

        print(f"\n✓ Scraped {len(videos)} videos from @{args.user}")
        for v in videos[:5]:
            print(f"  {v.video_id}: {v.description[:60]}... | ❤️{v.likes_count} 👁️{v.views_count}")

        if args.comments and videos:
            print(f"\nExtracting comments...")
            all_comments = scraper.scrape_all_comments(videos[:10])  # limit for testing
            total = sum(len(c) for c in all_comments.values())
            print(f"✓ Extracted {total} comments")
    else:
        parser.print_help()
