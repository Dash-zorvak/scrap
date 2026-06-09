import json
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    FB_PAGE_URL = os.getenv("FB_PAGE_URL", "")
    FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
    FB_PAGE_NAME = os.getenv("FB_PAGE_NAME", "")

    @property
    def deep_page_urls(self):
        raw = os.getenv("DEEP_PAGE_URLS", "[]")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return [u.strip() for u in raw.split(",") if u.strip()]
    FB_EMAIL = os.getenv("FB_EMAIL", "")
    FB_PASSWORD = os.getenv("FB_PASSWORD", "")
    FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "")

    REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "10"))
    DAYS_BACK = int(os.getenv("DAYS_BACK", "730"))
    MAX_POSTS = int(os.getenv("MAX_POSTS", "20000"))

    # Date range for scraping
    SCRAPE_SINCE = os.getenv("SCRAPE_SINCE", "2025-01-01")
    SCRAPE_UNTIL = os.getenv("SCRAPE_UNTIL", "")  # empty = today

    # How many consecutive out-of-range posts before stopping scroll
    # (Facebook feed is not strictly chronological, so tolerate some)
    CUTOFF_TOLERANCE = int(os.getenv("CUTOFF_TOLERANCE", "10"))

    PROXY_URL = os.getenv("PROXY_URL", "")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

    @property
    def has_facebook_login(self):
        return bool(self.FB_EMAIL and self.FB_PASSWORD)

    @property
    def pages(self):
        raw = os.getenv("FB_PAGES", "")
        if raw:
            try:
                pages = json.loads(raw)
                if pages:
                    return pages
            except json.JSONDecodeError:
                pass
        if self.FB_PAGE_ID and self.FB_PAGE_NAME:
            return [{"id": self.FB_PAGE_ID, "name": self.FB_PAGE_NAME, "url": self.FB_PAGE_URL}]
        if self.FB_PAGE_URL and not self.FB_PAGE_ID:
            return [{"url": self.FB_PAGE_URL, "name": self.FB_PAGE_NAME or self.FB_PAGE_URL}]
        return []

    def get_page(self, index=0):
        ps = self.pages
        if index < len(ps):
            return ps[index]
        return {"id": self.FB_PAGE_ID, "name": self.FB_PAGE_NAME, "url": self.FB_PAGE_URL}

    def resolve_page(self, page_id=None, page_name=None):
        if page_id and page_name:
            return {"id": page_id, "name": page_name}
        for p in self.pages:
            if p.get("id") == (page_id or self.FB_PAGE_ID):
                return p
        return self.get_page(0)
