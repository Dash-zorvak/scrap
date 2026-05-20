import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable
from urllib.parse import quote

import requests
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth

from src.tiktok_scraper.models import TTPostData, TTCommentData
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona

logger = logging.getLogger(__name__)

TT_BASE = "https://www.tiktok.com"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]


class TikTokResilientScraper:
    def __init__(
        self,
        proxy_url: str = "",
        headless: bool = False,
        email: str = "",
        password: str = "",
        cookies_file: str = "",
        max_retries: int = 5,
        checkpoint_file: str = "tiktok_checkpoint.json",
    ):
        self.proxy_url = proxy_url
        self.headless = headless
        self.email = email
        self.password = password
        self.cookies_file = cookies_file
        self.max_retries = max_retries
        self.checkpoint_file = checkpoint_file
        self.sentiment_analyzer = SentimentAnalyzer()

    def _load_checkpoint(self) -> Dict:
        try:
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_checkpoint(self, data: Dict):
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

    def _human_delay(self, min_s: float = 3.0, max_s: float = 7.0):
        delay = random.uniform(min_s, max_s)
        logger.debug(f"Sleeping {delay:.2f}s")
        time.sleep(delay)

    def _random_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    def _extract_hashtags(self, description: str) -> List[str]:
        if not description:
            return []
        hashtags = re.findall(r'#(\w+)', description)
        return list(set(hashtags))

    def _filter_by_date(self, post: TTPostData, days_back: int = 365) -> bool:
        if not post.create_time:
            return True
        cutoff = datetime.now() - timedelta(days=days_back)
        return post.create_time >= cutoff

    def _create_playwright_browser(self):
        launch_opts = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
            ],
        }
        if self.proxy_url:
            launch_opts["proxy"] = {"server": self.proxy_url}

        p = sync_playwright().start()
        browser = p.chromium.launch(**launch_opts)
        return p, browser

    def _setup_context(self, browser: Browser) -> BrowserContext:
        context = browser.new_context(
            viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
            user_agent=self._random_user_agent(),
            locale="es-SV",
            timezone_id="America/El_Salvador",
        )
        if self.cookies_file:
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
                logger.info(f"Loaded cookies from {self.cookies_file}")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
        return context

    def _setup_page(self, context: BrowserContext) -> Page:
        page = context.new_page()
        stealth(page)
        return page

    def _extract_sigi_data(self, page: Page) -> Optional[dict]:
        try:
            for script_id in ['__UNIVERSAL_DATA_FOR_VIEW__', 'SIGI_STATE']:
                data = page.evaluate(f"""
                    () => {{
                        try {{
                            const el = document.getElementById('{script_id}');
                            if (el) return JSON.parse(el.textContent);
                        }} catch(e) {{}}
                        return null;
                    }}
                """)
                if data:
                    return data
        except Exception as e:
            logger.debug(f"Failed to extract SIGI: {e}")
        return None

    def _parse_video_from_sigi(self, sigi: dict, username: str) -> List[TTPostData]:
        videos = []
        try:
            items = sigi.get("ItemModule", {})
            if not items:
                for key in ["videoList", "user"]:
                    section = sigi.get(key, {})
                    if isinstance(section, dict):
                        items.update(section)

            for vid_id, data in items.items():
                if not isinstance(data, dict):
                    continue

                video_id = str(data.get("id", vid_id))
                desc = data.get("desc", "") or data.get("description", "") or ""
                create_time = data.get("createTime", 0)

                try:
                    created = datetime.fromtimestamp(create_time) if create_time else None
                except:
                    created = None

                stats = data.get("stats", {}) or {}

                hashtags = self._extract_hashtags(desc)

                video = TTPostData(
                    video_id=video_id,
                    username=username,
                    description=desc.strip(),
                    create_time=created,
                    likes_count=int(stats.get("diggCount", stats.get("likeCount", 0))),
                    comments_count=int(stats.get("commentCount", 0)),
                    shares_count=int(stats.get("shareCount", 0)),
                    views_count=int(stats.get("playCount", stats.get("viewCount", 0))),
                    favorites_count=int(stats.get("collectCount", stats.get("favoritesCount", 0))),
                    video_url=f"{TT_BASE}/@{username}/video/{video_id}",
                    hashtags=hashtags,
                    source="sigi_state",
                )
                videos.append(video)

        except Exception as e:
            logger.warning(f"Error parsing SIGI: {e}")

        return videos

    def _method_api_fetch(self, username: str, cursor: int = 0) -> tuple[List[TTPostData], int]:
        videos = []
        next_cursor = 0

        try:
            url = f"https://www.tiktok.com/api/post/item_list/?aid=1988&app_language=es-SV&count=35&cursor={cursor}&secUid=&sig_info=&uniqueId={username}"
            headers = {
                "User-Agent": self._random_user_agent(),
                "Referer": f"{TT_BASE}/@{username}",
                "Accept": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                logger.warning(f"API failed: {response.status_code}")
                return videos, next_cursor

            data = response.json()
            items = data.get("itemList", [])

            for item in items:
                try:
                    video_id = str(item.get("id", ""))
                    desc = item.get("desc", "") or ""
                    create_time = item.get("createTime", 0)

                    try:
                        created = datetime.fromtimestamp(create_time) if create_time else None
                    except:
                        created = None

                    stats = item.get("stats", {})
                    music = item.get("music", {})

                    hashtags = self._extract_hashtags(desc)

                    video = TTPostData(
                        video_id=video_id,
                        username=username,
                        description=desc.strip(),
                        create_time=created,
                        likes_count=int(stats.get("diggCount", 0)),
                        comments_count=int(stats.get("commentCount", 0)),
                        shares_count=int(stats.get("shareCount", 0)),
                        views_count=int(stats.get("playCount", 0)),
                        favorites_count=int(stats.get("collectCount", 0)),
                        video_url=f"{TT_BASE}/@{username}/video/{video_id}",
                        hashtags=hashtags,
                        source="api",
                    )
                    videos.append(video)

                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue

            next_cursor = data.get("cursor", 0)

        except Exception as e:
            logger.warning(f"API fetch error: {e}")

        return videos, next_cursor

    def _method_web_scrape(self, username: str, max_scrolls: int = 50) -> List[TTPostData]:
        videos = []

        try:
            playwright, browser = self._create_playwright_browser()
            try:
                context = self._setup_context(browser)
                page = self._setup_page(context)

                page.goto(f"{TT_BASE}/@{username}", timeout=60000, wait_until="networkidle")
                self._human_delay(5, 10)

                sigi = self._extract_sigi_data(page)
                if sigi:
                    videos.extend(self._parse_video_from_sigi(sigi, username))
                    logger.info(f"Got {len(videos)} videos from initial SIGI")

                last_height = 0
                stale_count = 0

                for scroll in range(max_scrolls):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    self._human_delay(3, 6)

                    sigi = self._extract_sigi_data(page)
                    if sigi:
                        new_videos = self._parse_video_from_sigi(sigi, username)
                        for v in new_videos:
                            if v.video_id not in [x.video_id for x in videos]:
                                videos.append(v)

                    current_height = page.evaluate("document.body.scrollHeight")
                    if current_height == last_height:
                        stale_count += 1
                        if stale_count >= 5:
                            break
                    else:
                        stale_count = 0
                    last_height = current_height

            finally:
                try:
                    browser.close()
                except:
                    pass
                try:
                    playwright.stop()
                except:
                    pass

        except Exception as e:
            logger.error(f"Web scrape error: {e}")

        return videos

    def _fetch_video_details_api(self, video_id: str) -> Optional[dict]:
        for attempt in range(3):
            try:
                url = f"https://www.tiktok.com/api/item/detail/?aid=1988&app_language=es-SV&itemId={video_id}"
                headers = {
                    "User-Agent": self._random_user_agent(),
                    "Referer": f"{TT_BASE}/",
                }
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("itemInfo", {}).get("itemStruct"):
                        return data["itemInfo"]["itemStruct"]
            except:
                time.sleep(2 ** attempt)
        return None

    def _get_video_comments_api(self, video_id: str, max_comments: int = 200) -> List[TTCommentData]:
        comments = []
        cursor = 0

        for attempt in range(self.max_retries):
            try:
                url = f"https://www.tiktok.com/api/comment/list/?aid=1988&app_language=es-SV&aweme_id={video_id}&count=20&cursor={cursor}"
                headers = {
                    "User-Agent": self._random_user_agent(),
                    "Referer": f"{TT_BASE}/",
                }

                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code != 200:
                    self._human_delay(5, 10)
                    continue

                data = response.json()
                items = data.get("comments", [])

                for item in items:
                    try:
                        user = item.get("user", {})
                        create_time = item.get("create_time", 0)

                        try:
                            created = datetime.fromtimestamp(create_time) if create_time else None
                        except:
                            created = None

                        comment = TTCommentData(
                            comment_id=str(item.get("cid", "")),
                            video_id=video_id,
                            message=item.get("text", "")[:5000],
                            author_name=user.get("nickname", "") or user.get("unique_id", ""),
                            author_unique_id=user.get("unique_id", ""),
                            author_avatar=user.get("avatar_thumb", {}).get("url_list", [""])[0] if user.get("avatar_thumb") else "",
                            create_time=created,
                            likes_count=int(item.get("digg_count", 0)),
                            reply_count=int(item.get("reply_count", 0)),
                        )
                        comments.append(comment)

                    except Exception as e:
                        continue

                if not data.get("has_more", False):
                    break

                cursor = data.get("cursor", 0)

                if len(comments) >= max_comments:
                    break

                time.sleep(random.uniform(1, 3))

            except Exception as e:
                logger.warning(f"Comment fetch error: {e}")
                self._human_delay(5, 10)

        return comments[:max_comments]

    def scrape_videos(
        self,
        username: str,
        max_videos: int = 500,
        days_back: int = 365,
        progress_callback: Callable[[int, int], None] = None,
    ) -> List[TTPostData]:
        logger.info(f"Starting resilient scrape for @{username}")
        checkpoint = self._load_checkpoint()
        seen_ids = set(checkpoint.get("seen_ids", []))

        all_videos = []
        methods_tried = []

        for attempt in range(self.max_retries):
            logger.info(f"Attempt {attempt + 1}/{self.max_retries}")

            if "api" not in methods_tried:
                logger.info("Trying API method...")
                videos, cursor = self._method_api_fetch(username, 0)
                for v in videos:
                    if v.video_id not in seen_ids:
                        if self._filter_by_date(v, days_back):
                            seen_ids.add(v.video_id)
                            all_videos.append(v)
                methods_tried.append("api")
                logger.info(f"API got {len(videos)} videos")

                while cursor and len(all_videos) < max_videos * 2:
                    videos, cursor = self._method_api_fetch(username, cursor)
                    for v in videos:
                        if v.video_id not in seen_ids:
                            if self._filter_by_date(v, days_back):
                                seen_ids.add(v.video_id)
                                all_videos.append(v)
                    if progress_callback:
                        progress_callback(len(all_videos), max_videos)

            if len(all_videos) >= max_videos:
                break

            if "web" not in methods_tried:
                logger.info("Trying Web scrape method...")
                self._human_delay(10, 20)
                videos = self._method_web_scrape(username)
                for v in videos:
                    if v.video_id not in seen_ids:
                        if self._filter_by_date(v, days_back):
                            seen_ids.add(v.video_id)
                            all_videos.append(v)
                methods_tried.append("web")
                logger.info(f"Web scrape got {len(videos)} videos")

                if progress_callback:
                    progress_callback(len(all_videos), max_videos)

            if len(all_videos) >= max_videos:
                break

            self._human_delay(30, 60)

        filtered = [v for v in all_videos if self._filter_by_date(v, days_back)]
        result = filtered[:max_videos]

        self._save_checkpoint({"seen_ids": list(seen_ids), "last_run": datetime.now().isoformat()})

        logger.info(f"Total videos scraped: {len(result)} (filtered from {len(all_videos)})")
        return result

    def get_video_comments(
        self,
        video_id: str,
        max_comments: int = 200,
    ) -> List[TTCommentData]:
        logger.info(f"Fetching comments for video {video_id}")
        return self._get_video_comments_api(video_id, max_comments)

    def analyze_comment(self, comment: TTCommentData) -> dict:
        text = comment.message
        sentiment_label, sentiment_score = self.sentiment_analyzer.analyze(text)
        topic = get_main_topic(text)
        zona = detect_zona(text)

        return {
            "sentiment": sentiment_label,
            "sentiment_score": sentiment_score,
            "topic_category": topic,
            "zona": zona,
        }