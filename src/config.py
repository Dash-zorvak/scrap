import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    FB_PAGE_URL = os.getenv("FB_PAGE_URL", "")
    FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
    FB_PAGE_NAME = os.getenv("FB_PAGE_NAME", "")
    FB_EMAIL = os.getenv("FB_EMAIL", "")
    FB_PASSWORD = os.getenv("FB_PASSWORD", "")
    FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "")

    REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "10"))
    DAYS_BACK = int(os.getenv("DAYS_BACK", "730"))
    MAX_POSTS = int(os.getenv("MAX_POSTS", "20000"))

    PROXY_URL = os.getenv("PROXY_URL", "")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

    @property
    def has_facebook_login(self):
        return bool(self.FB_EMAIL and self.FB_PASSWORD)
