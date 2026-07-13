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
    CAPTCHA_TIMEOUT = int(os.getenv("CAPTCHA_TIMEOUT", "600"))

    PROXY_URL = os.getenv("PROXY_URL", "")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    DATA_DIR = os.environ.get(
        "DATA_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
    )
    OUTPUT_DIR = os.environ.get(
        "OUTPUT_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs"),
    )

    @property
    def FACEBOOK_DB(self):
        return os.environ.get("FACEBOOK_DB") or os.path.join(self.DATA_DIR, "facebook.db")

    @property
    def TIKTOK_DB(self):
        return os.environ.get("TIKTOK_DB") or os.path.join(self.DATA_DIR, "tiktok.db")

    @property
    def EXTERNOS_DB(self):
        return os.environ.get("EXTERNOS_DB") or os.path.join(self.DATA_DIR, "externos.db")

    # -- Constantes de clasificación (SSOT, antes en dashboard/config.py) --
    FB_PAGES_OFICIALES = [
        "Alcaldía de Santa Ana",
        "Gustavo Acevedo",
    ]

    FB_REACTIONS = [
        "likes_count", "loves_count", "cares_count",
        "hahas_count", "wows_count", "sads_count", "angrys_count",
    ]

    TK_ENGAGEMENT = ["views", "likes", "shares", "favorites_count", "comments_count"]

    TK_ACCOUNTS = {
        1: "Alcaldía de Santa Ana",
        3: "Gustavo Acevedo",
    }

    MIN_COMENTARIOS_MUESTRA = 15

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


def ensure_dirs(cfg=None):
    """Crea DATA_DIR y OUTPUT_DIR si no existen. Llamar explícitamente."""
    cfg = cfg or Config()
    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
