import json
import logging
import re
import time
from datetime import datetime
from typing import Optional, List, Dict

from playwright.sync_api import sync_playwright, Page, Browser
from playwright_stealth import Stealth

from src.tiktok_scraper.models import TTPostData, TTCommentData
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona, extract_problematicas

logger = logging.getLogger(__name__)

TT_BASE = "https://www.tiktok.com"


class TikTokScraper:
    def __init__(
        self,
        proxy_url: str = "",
        headless: bool = False,
        email: str = "",
        password: str = "",
        cookies_file: str = "",
    ):
        self.proxy_url = proxy_url
        self.headless = headless
        self.email = email
        self.password = password
        self.cookies_file = cookies_file

    def _create_browser(self) -> Browser:
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
        return browser

    def _setup_page(self, browser: Browser) -> Page:
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="es",
            timezone_id="America/El_Salvador",
        )
        
        # Load cookies if provided
        if self.cookies_file:
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
                logger.info(f"Loaded cookies from {self.cookies_file}")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
        
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        return page

    def _human_delay(self, min_s: float = 2.0, max_s: float = 4.0):
        time.sleep(min_s + (max_s - min_s) * (time.time() % 1))

    def login(self, page: Page) -> bool:
        if not self.email or not self.password:
            logger.warning("No TikTok login credentials")
            return False
        
        try:
            logger.info("Navigating to TikTok login...")
            page.goto(f"{TT_BASE}/login", timeout=30000)
            self._human_delay(3, 5)
            
            page.wait_for_load_state("networkidle")
            
            email_input = page.locator('input[name="username"], input[type="text"]').first
            if email_input.is_visible():
                email_input.fill(self.email)
                self._human_delay(1, 2)
                
                pass_input = page.locator('input[type="password"]').first
                if pass_input.is_visible():
                    pass_input.fill(self.password)
                    self._human_delay(0.5, 1)
                    
                    page.keyboard.press("Enter")
                    self._human_delay(5, 8)
                    
                    if "verify" in page.url.lower() or "captcha" in page.url.lower():
                        logger.warning("TikTok login requires verification")
                        return False
                    
                    logger.info("TikTok login successful")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"TikTok login failed: {e}")
            return False

    def _extract_sigi_state(self, page: Page) -> Optional[dict]:
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
            return data
        except Exception as e:
            logger.debug(f"Failed to extract SIGI_STATE: {e}")
            return None

    def _extract_from_sigi(
        self, sigi: dict, username: str, seen_ids: set
    ) -> list[TTPostData]:
        found = []

        try:
            items = {}
            modules = sigi.get("ItemModule", {})
            if modules:
                items = modules
            else:
                for key in ("videoList", "user", "twitter"):
                    section = sigi.get(key, {})
                    if isinstance(section, dict):
                        items.update(section)

            for vid, data in items.items():
                if not isinstance(data, dict):
                    continue
                video_id = str(data.get("id", vid))
                if video_id in seen_ids:
                    continue

                desc = data.get("desc", "") or data.get("description", "") or ""
                create_time = data.get("createTime", 0)
                created = (
                    datetime.fromtimestamp(create_time)
                    if create_time and isinstance(create_time, (int, float))
                    else None
                )

                stats = data.get("stats", {}) or data.get("statistics", {}) or {}

                video = TTPostData(
                    video_id=video_id,
                    username=username,
                    description=desc.strip(),
                    create_time=created,
                    likes_count=int(stats.get("diggCount", stats.get("likeCount", 0))),
                    comments_count=int(stats.get("commentCount", stats.get("commentCount", 0))),
                    shares_count=int(stats.get("shareCount", stats.get("shareCount", 0))),
                    views_count=int(stats.get("playCount", stats.get("viewCount", 0))),
                    video_url=f"{TT_BASE}/@{username}/video/{video_id}",
                    source="playwright_json",
                )
                found.append(video)

        except Exception as e:
            logger.warning(f"Error extracting SIGI_STATE data: {e}")

        return found

    def _extract_from_html(self, page: Page, username: str, seen_ids: set) -> list[TTPostData]:
        found = []

        try:
            html = page.content()
            matches = re.findall(
                r'<script[^>]*id="__UNIVERSAL_DATA_FOR_VIEW__"[^>]*>(.*?)</script>',
                html, re.DOTALL
            )
            for match in matches:
                try:
                    data = json.loads(match)
                    items = self._extract_from_sigi(data, username, seen_ids)
                    found.extend(items)
                except json.JSONDecodeError:
                    continue

            if not found:
                matches = re.findall(
                    r'<script[^>]*id="SIGI_STATE"[^>]*>(.*?)</script>',
                    html, re.DOTALL
                )
                for match in matches:
                    try:
                        data = json.loads(match)
                        items = self._extract_from_sigi(data, username, seen_ids)
                        found.extend(items)
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.debug(f"HTML extraction failed: {e}")

        return found

    def scrape_profile_videos(
        self,
        username: str,
        max_videos: int = 500,
        progress_callback=None,
    ) -> list[TTPostData]:
        browser = self._create_browser()
        page = self._setup_page(browser)
        videos = []
        seen_ids = set()

        try:
            # Login first if credentials provided
            if self.email and self.password:
                self.login(page)
            
            url = f"{TT_BASE}/@{username}"
            logger.info(f"Navigating to {url}")
            page.goto(url, timeout=60000, wait_until="networkidle")
            self._human_delay(5, 8)

            sigi = self._extract_sigi_state(page)
            if sigi:
                items = self._extract_from_sigi(sigi, username, seen_ids)
                for v in items:
                    if v.video_id not in seen_ids:
                        seen_ids.add(v.video_id)
                        videos.append(v)
                if progress_callback:
                    progress_callback(len(videos), max_videos)
                logger.info(f"Extracted {len(videos)} videos from initial SIGI_STATE")

            if not videos:
                items = self._extract_from_html(page, username, seen_ids)
                for v in items:
                    if v.video_id not in seen_ids:
                        seen_ids.add(v.video_id)
                        videos.append(v)
                if progress_callback:
                    progress_callback(len(videos), max_videos)

            logger.info(f"Starting scroll for more videos (have {len(videos)})")

            last_height = 0
            stale_scrolls = 0

            for scroll in range(200):
                if len(videos) >= max_videos:
                    break

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self._human_delay(3, 6)

                sigi = self._extract_sigi_state(page)
                if sigi:
                    items = self._extract_from_sigi(sigi, username, seen_ids)
                    for v in items:
                        if v.video_id not in seen_ids:
                            seen_ids.add(v.video_id)
                            videos.append(v)

                if progress_callback:
                    progress_callback(len(videos), max_videos)

                current_height = page.evaluate("document.body.scrollHeight")
                if current_height == last_height:
                    stale_scrolls += 1
                    if stale_scrolls >= 8:
                        logger.info(f"No more new content after {scroll} scrolls")
                        break
                else:
                    stale_scrolls = 0
                last_height = current_height

            logger.info(f"Total videos scraped: {len(videos)}")

        except Exception as e:
            logger.error(f"Error scraping TikTok profile: {e}")

        finally:
            browser.close()

        return videos

    def extract_video_comments(self, video_id: str, max_comments: int = None) -> list[dict]:
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

                import requests
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
                                from datetime import datetime
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
