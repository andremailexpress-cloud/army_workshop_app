"""
YouTube Clone AI — Telegram Notifier
DHD Data | Clients First. Perfection Always.

Sends generated scripts and alerts via Telegram Bot API.
Adapted from DealScout's telegram_utils.py.
"""
import os
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends messages and documents to a Telegram chat."""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self._bot = None

    @property
    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_script(self, script: dict, channel_name: str = "") -> bool:
        """Send a generated script to Telegram."""
        if not self.is_configured:
            logger.warning("Telegram not configured — skipping")
            return False

        title = script.get("title", "Untitled")
        topic = script.get("topic", "")
        hook = script.get("hook", "")
        cta = script.get("cta", "")
        tags = script.get("tags", [])
        duration = script.get("estimated_duration", "")

        msg = (
            f"🎬 *NEW SCRIPT GENERATED*\n\n"
            f"📺 Channel Style: {channel_name}\n"
            f"📌 Topic: {topic}\n\n"
            f"🏷️ *Title:*\n{title}\n\n"
            f"🎣 *Hook:*\n{hook[:300]}...\n\n"
            f"📢 *CTA:* {cta}\n\n"
            f"⏱️ Estimated Duration: {duration}\n"
            f"🔖 Tags: {', '.join(tags[:8])}\n\n"
            f"_Full script available in dashboard_"
        )

        return self._send_message(msg)

    def send_analysis_complete(self, channel_name: str, score: int, grade: str) -> bool:
        """Notify when a style analysis completes."""
        if not self.is_configured:
            return False

        msg = (
            f"✅ *STYLE ANALYSIS COMPLETE*\n\n"
            f"📺 Channel: {channel_name}\n"
            f"🎯 Clone Score: {score}/100 (Grade: {grade})\n\n"
            f"_Ready to generate scripts in this style_"
        )
        return self._send_message(msg)

    def send_alert(self, message: str) -> bool:
        """Send a plain alert message."""
        if not self.is_configured:
            return False
        return self._send_message(f"⚡ {message}")

    def send_daily_summary(self, stats: dict) -> bool:
        """Send daily automation summary."""
        if not self.is_configured:
            return False

        msg = (
            f"📊 *DAILY SUMMARY*\n\n"
            f"📺 Active Channels: {stats.get('channels', 0)}\n"
            f"📹 Videos Scraped: {stats.get('videos', 0)}\n"
            f"📝 Transcripts: {stats.get('transcripts', 0)}\n"
            f"🔬 Analyses Run: {stats.get('analyses', 0)}\n"
            f"✍️ Scripts Generated: {stats.get('scripts', 0)}\n"
            f"📤 Scripts Sent: {stats.get('scripts_sent', 0)}\n"
        )
        return self._send_message(msg)

    # ------------------------------------------------------------------ #
    #  Internal                                                             #
    # ------------------------------------------------------------------ #

    def _send_message(self, text: str) -> bool:
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }, timeout=10)
            if resp.status_code == 200:
                return True
            logger.error(f"Telegram API error: {resp.status_code} — {resp.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
