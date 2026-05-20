import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)
    
    def send(self, message: str, parse_mode: str = "Markdown") -> bool:
        if not self.enabled:
            logger.warning("Telegram notifications disabled (no token/chat_id)")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Telegram notification sent: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def notify_scraping_complete(self, platform: str, count: int, total: int) -> bool:
        emoji = "📘" if platform == "facebook" else "🎵"
        message = f"""
{emoji} *Scraping Completado*

*Plataforma:* {platform.upper()}
*Items scrapeados:* {count}/{total}
*Hora:* {self._current_time()}
        """
        return self.send(message)
    
    def notify_analysis_complete(self, platform: str, posts_analyzed: int, insights_generated: int) -> bool:
        message = f"""
📊 *Análisis Completado*

*Plataforma:* {platform.upper()}
*Posts analizados:* {posts_analyzed}
*Insights generados:* {insights_generated}
*Hora:* {self._current_time()}
        """
        return self.send(message)
    
    def notify_critical_alert(self, alert_type: str, description: str) -> bool:
        message = f"""
🚨 *ALERTA CRÍTICA*

*Tipo:* {alert_type}
*Descripción:* {description}
*Hora:* {self._current_time()}
        """
        return self.send(message)
    
    def notify_daily_summary(self, fb_posts: int, nsi: float, top_issue: str) -> bool:
        nsi_emoji = "🟢" if nsi > 0 else "🔴" if nsi < 0 else "🟡"
        message = f"""
📋 *RESUMEN DIARIO*

*Facebook:* {fb_posts:,} posts
*NSI:* {nsi_emoji} {nsi}
*Tema más crítico:* {top_issue}
*Hora:* {self._current_time()}
        """
        return self.send(message)
    
    def notify_error(self, error_type: str, description: str) -> bool:
        message = f"""
❌ *ERROR*

*Tipo:* {error_type}
*Descripción:* {description}
*Hora:* {self._current_time()}
        """
        return self.send(message)
    
    @staticmethod
    def _current_time() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M")


# Funciones de conveniencia
def notify_scraping_done(platform: str, count: int, total: int):
    notifier = TelegramNotifier()
    notifier.notify_scraping_complete(platform, count, total)

def notify_analysis_done(platform: str, posts: int, insights: int):
    notifier = TelegramNotifier()
    notifier.notify_analysis_complete(platform, posts, insights)

def notify_alert(alert_type: str, description: str):
    notifier = TelegramNotifier()
    notifier.notify_critical_alert(alert_type, description)

def notify_daily(fb_posts: int, nsi: float, top_issue: str):
    notifier = TelegramNotifier()
    notifier.notify_daily_summary(fb_posts, nsi, top_issue)

def notify_error(error_type: str, description: str):
    notifier = TelegramNotifier()
    notifier.notify_error(error_type, description)