#!/usr/bin/env python3
"""
TikTok Force Scraper - Versión agresiva para obtener datos de TikTok
Usa múltiples técnicas para evadir bloqueos
"""
import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from urllib.parse import quote

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

TT_BASE = "https://www.tiktok.com"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.0.0 Mobile/15E148 Safari/604.1",
]


class TikTokForceScraper:
    def __init__(self, proxy: str = "", use_selenium: bool = True, cookies_file: str = ""):
        self.proxy = proxy
        self.use_selenium = use_selenium
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

        if cookies_file:
            self._load_cookies(cookies_file)

    def _load_cookies(self, cookies_file: str):
        try:
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
            logger.info(f"Loaded cookies from {cookies_file}")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    def _human_delay(self, min_s=2, max_s=5):
        time.sleep(random.uniform(min_s, max_s))

    def _extract_hashtags(self, text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r'#(\w+)', text)

    def _setup_selenium(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")

        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })

    def method_1_api_aweme(self, username: str, cursor: int = 0) -> tuple:
        """Método 1: API pública de TikTok (aweme)"""
        videos = []
        next_cursor = 0

        try:
            url = "https://www.tiktok.com/api/aweme/v1/web/aweme/v3/web/item_list/"
            params = {
                "aid": 1988,
                "app_language": "es",
                "count": 30,
                "cursor": cursor,
                "sec_user_id": "",
                "source": "aweme",
                "unique_id": username,
            }

            response = self.session.get(url, params=params, timeout=15)
            if response.status_code != 200:
                logger.warning(f"API aweme failed: {response.status_code}")
                return videos, next_cursor

            data = response.json()
            items = data.get("aweme_list", [])

            for item in items:
                try:
                    video_id = item.get("aweme_id", "")
                    desc = item.get("desc", "")
                    create_time = item.get("create_time", 0)

                    try:
                        created = datetime.fromtimestamp(create_time)
                    except:
                        created = None

                    stats = item.get("statistics", {})
                    hashtags = self._extract_hashtags(desc)

                    video = {
                        "video_id": video_id,
                        "username": username,
                        "description": desc,
                        "create_time": created,
                        "likes_count": stats.get("digg_count", 0),
                        "comments_count": stats.get("comment_count", 0),
                        "shares_count": stats.get("share_count", 0),
                        "views_count": stats.get("play_count", 0),
                        "favorites_count": stats.get("collect_count", 0),
                        "video_url": f"{TT_BASE}/@{username}/video/{video_id}",
                        "hashtags": hashtags,
                    }
                    videos.append(video)

                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue

            next_cursor = data.get("cursor", 0)

        except Exception as e:
            logger.warning(f"API aweme error: {e}")

        return videos, next_cursor

    def method_2_api_noauth(self, username: str) -> List[dict]:
        """Método 2: API sin autenticación"""
        videos = []

        try:
            url = f"https://www.tiktok.com/api/user/{username}/list/"
            params = {
                "source": "search",
                "need_preview": "1",
            }

            response = self.session.get(url, params=params, timeout=15)
            if response.status_code != 200:
                return videos

            data = response.json()

            user_data = data.get("user", {})
            videos_data = user_data.get("videos", [])

            for video in videos_data:
                try:
                    video_id = video.get("id", "")
                    desc = video.get("desc", "")
                    create_time = video.get("createTime", 0)

                    stats = video.get("stats", {})
                    hashtags = self._extract_hashtags(desc)

                    try:
                        created = datetime.fromtimestamp(create_time) if create_time else None
                    except:
                        created = None

                    videos.append({
                        "video_id": str(video_id),
                        "username": username,
                        "description": desc,
                        "create_time": created,
                        "likes_count": stats.get("diggCount", 0),
                        "comments_count": stats.get("commentCount", 0),
                        "shares_count": stats.get("shareCount", 0),
                        "views_count": stats.get("playCount", 0),
                        "favorites_count": stats.get("collectCount", 0),
                        "video_url": f"{TT_BASE}/@{username}/video/{video_id}",
                        "hashtags": hashtags,
                    })

                except Exception as e:
                    continue

        except Exception as e:
            logger.warning(f"API noauth error: {e}")

        return videos

    def method_3_selenium_scroll(self, username: str, max_videos: int = 100) -> List[dict]:
        """Método 3: Selenium con scroll - más robusto"""
        videos = []

        if not self.driver:
            self._setup_selenium()

        try:
            self.driver.get(f"{TT_BASE}/@{username}")
            self._human_delay(8, 15)

            seen_ids = set()
            last_height = 0

            for scroll_attempt in range(50):
                if len(videos) >= max_videos:
                    break

                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                self._human_delay(3, 7)

                try:
                    page_source = self.driver.page_source

                    sigi_matches = re.findall(
                        r'<script[^>]*id="__UNIVERSAL_DATA_FOR_VIEW__"[^>]*>(.*?)</script>',
                        page_source,
                        re.DOTALL
                    )

                    for match in sigi_matches:
                        try:
                            data = json.loads(match)
                            items = data.get("default", {}).get("data", {}).get("items", [])

                            for item in items:
                                video_id = item.get("id", "")
                                if video_id in seen_ids:
                                    continue
                                seen_ids.add(video_id)

                                desc = item.get("desc", "")
                                stats = item.get("stats", {})

                                create_time = item.get("createTime", 0)
                                try:
                                    created = datetime.fromtimestamp(create_time)
                                except:
                                    created = None

                                videos.append({
                                    "video_id": str(video_id),
                                    "username": username,
                                    "description": desc,
                                    "create_time": created,
                                    "likes_count": stats.get("diggCount", 0),
                                    "comments_count": stats.get("commentCount", 0),
                                    "shares_count": stats.get("shareCount", 0),
                                    "views_count": stats.get("playCount", 0),
                                    "favorites_count": stats.get("collectCount", 0),
                                    "video_url": f"{TT_BASE}/@{username}/video/{video_id}",
                                    "hashtags": self._extract_hashtags(desc),
                                })

                        except json.JSONDecodeError:
                            continue

                except Exception as e:
                    logger.debug(f"Scroll error: {e}")

                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

                logger.info(f"Scroll {scroll_attempt + 1}: got {len(videos)} videos")

        except Exception as e:
            logger.error(f"Selenium error: {e}")

        return videos

    def method_4_mobile_api(self, username: str) -> List[dict]:
        """Método 4: API móvil (a veces más permisiva)"""
        videos = []

        try:
            url = "https://api16-normal-c-useast1a.tiktok.com/api/aweme/v1/web/aweme/v3/web/item_list/"
            params = {
                "aid": 1988,
                "app_name": "musically",
                "app_version": "260801",
                "device_platform": "iphone",
                "os_version": "14.4",
                "channel": "appstore",
                "device_type": "iPhone12,1",
                "count": 30,
                "cursor": 0,
                "sec_user_id": "",
                "source": "aweme",
                "unique_id": username,
            }

            headers = {
                "User-Agent": "TikTok/26.8.1 (iPhone; iOS 14.4; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15",
                "Accept-Language": "es-ES,es;q=0.9",
            }

            response = self.session.get(url, params=params, headers=headers, timeout=15)
            if response.status_code != 200:
                return videos

            data = response.json()
            items = data.get("aweme_list", [])

            for item in items:
                try:
                    video_id = item.get("aweme_id", "")
                    desc = item.get("desc", "")
                    stats = item.get("statistics", {})

                    create_time = item.get("create_time", 0)
                    try:
                        created = datetime.fromtimestamp(create_time)
                    except:
                        created = None

                    videos.append({
                        "video_id": video_id,
                        "username": username,
                        "description": desc,
                        "create_time": created,
                        "likes_count": stats.get("digg_count", 0),
                        "comments_count": stats.get("comment_count", 0),
                        "shares_count": stats.get("share_count", 0),
                        "views_count": stats.get("play_count", 0),
                        "favorites_count": stats.get("collect_count", 0),
                        "video_url": f"{TT_BASE}/@{username}/video/{video_id}",
                        "hashtags": self._extract_hashtags(desc),
                    })

                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"Mobile API error: {e}")

        return videos

    def scrape(self, username: str, max_videos: int = 200, days_back: int = 365) -> List[dict]:
        """Scraping con múltiples métodos y reintentos"""
        logger.info(f"Starting force scrape for @{username}")

        all_videos = []
        methods_tried = []

        cutoff_date = datetime.now() - timedelta(days=days_back)

        for attempt in range(3):
            logger.info(f"Attempt {attempt + 1}/3")

            if "aweme" not in methods_tried:
                logger.info("Trying API aweme method...")
                videos, cursor = self.method_1_api_aweme(username)
                all_videos.extend(videos)
                methods_tried.append("aweme")
                logger.info(f"Aweme API got {len(videos)} videos")

                while cursor and len(all_videos) < max_videos:
                    videos, cursor = self.method_1_api_aweme(username, cursor)
                    all_videos.extend(videos)
                    self._human_delay(2, 4)

            if len(all_videos) >= max_videos:
                break

            if "noauth" not in methods_tried:
                logger.info("Trying API noauth method...")
                self._human_delay(5, 10)
                videos = self.method_2_api_noauth(username)
                all_videos.extend(videos)
                methods_tried.append("noauth")
                logger.info(f"Noauth API got {len(videos)} videos")

            if len(all_videos) >= max_videos:
                break

            if "mobile" not in methods_tried:
                logger.info("Trying mobile API method...")
                self._human_delay(5, 10)
                videos = self.method_4_mobile_api(username)
                all_videos.extend(videos)
                methods_tried.append("mobile")
                logger.info(f"Mobile API got {len(videos)} videos")

            if len(all_videos) >= max_videos:
                break

            if "selenium" not in methods_tried:
                logger.info("Trying Selenium method...")
                self._human_delay(10, 20)
                videos = self.method_3_selenium_scroll(username, max_videos)
                all_videos.extend(videos)
                methods_tried.append("selenium")
                logger.info(f"Selenium got {len(videos)} videos")

            if len(all_videos) >= max_videos:
                break

            self._human_delay(30, 60)

        seen_ids = set()
        filtered_videos = []

        for v in all_videos:
            if v["video_id"] in seen_ids:
                continue
            seen_ids.add(v["video_id"])

            if v["create_time"] and v["create_time"] >= cutoff_date:
                filtered_videos.append(v)
            elif not v["create_time"]:
                filtered_videos.append(v)

        result = filtered_videos[:max_videos]
        logger.info(f"Total videos: {len(result)} (filtered from {len(all_videos)})")

        return result

    def get_comments(self, video_id: str, max_comments: int = 200) -> List[dict]:
        """Extraer comentarios de un video"""
        comments = []
        cursor = 0

        for attempt in range(3):
            try:
                url = "https://www.tiktok.com/api/comment/item/list/"
                params = {
                    "aweme_id": video_id,
                    "count": 20,
                    "cursor": cursor,
                }

                response = self.session.get(url, params=params, timeout=15)
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
                            created = datetime.fromtimestamp(create_time)
                        except:
                            created = None

                        comments.append({
                            "comment_id": item.get("cid", ""),
                            "video_id": video_id,
                            "message": item.get("text", ""),
                            "author_name": user.get("nickname", "") or user.get("unique_id", ""),
                            "author_unique_id": user.get("unique_id", ""),
                            "create_time": created,
                            "likes_count": item.get("digg_count", 0),
                        })

                    except Exception:
                        continue

                if not data.get("has_more", False):
                    break

                cursor = data.get("cursor", 0)

                if len(comments) >= max_comments:
                    break

                self._human_delay(1, 3)

            except Exception as e:
                logger.warning(f"Comment fetch error: {e}")
                self._human_delay(5, 10)

        return comments[:max_comments]

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    username = sys.argv[1] if len(sys.argv) > 1 else "alcaldiesa"
    max_videos = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    scraper = TikTokForceScraper()
    videos = scraper.scrape(username, max_videos=max_videos)

    print(f"\n{'='*50}")
    print(f"Got {len(videos)} videos from @{username}")
    print(f"{'='*50}")

    for v in videos[:5]:
        print(f"\nVideo: {v['video_id']}")
        print(f"Description: {v['description'][:80]}...")
        print(f"Views: {v['views_count']:,}")
        print(f"Likes: {v['likes_count']:,}")
        print(f"Comments: {v['comments_count']:,}")
        print(f"Hashtags: {v['hashtags']}")
        print(f"Date: {v['create_time']}")

    scraper.close()