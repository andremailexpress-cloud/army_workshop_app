"""
YouTube Clone AI — YouTube Channel Scraper
DHD Data | Clients First. Perfection Always.

Pulls channel metadata and video list using yt-dlp.
"""
import subprocess
import json
import re
import time
import random
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VideoMeta:
    video_id: str
    title: str
    url: str
    duration: int = 0          # seconds
    view_count: int = 0
    like_count: int = 0
    upload_date: str = ""
    description: str = ""
    thumbnail: str = ""
    tags: list = field(default_factory=list)


@dataclass
class ChannelMeta:
    channel_id: str
    channel_name: str
    channel_url: str
    subscriber_count: int = 0
    video_count: int = 0
    description: str = ""
    thumbnail: str = ""


class YouTubeScraper:
    """
    Scrapes YouTube channel metadata and video lists via yt-dlp.
    No API key required.
    """

    def __init__(self, max_videos: int = 20, delay: tuple = (1, 3)):
        self.max_videos = max_videos
        self.delay = delay

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_channel_info(self, channel_url: str) -> Optional[ChannelMeta]:
        """Return basic channel metadata."""
        try:
            cmd = [
                "yt-dlp",
                "--dump-single-json",
                "--flat-playlist",
                "--playlist-end", "1",
                "--no-warnings",
                channel_url,
            ]
            result = self._run(cmd)
            if not result:
                return None

            data = json.loads(result)
            # yt-dlp returns either a playlist or single entry
            entries = data.get("entries", [data])
            uploader = data.get("uploader") or data.get("channel") or "Unknown"
            channel_id = data.get("channel_id") or data.get("uploader_id") or ""

            return ChannelMeta(
                channel_id=channel_id,
                channel_name=uploader,
                channel_url=channel_url,
                subscriber_count=data.get("channel_follower_count", 0) or 0,
                video_count=data.get("playlist_count", 0) or 0,
                description=data.get("description", "") or "",
                thumbnail=data.get("thumbnail", "") or "",
            )
        except Exception as e:
            logger.error(f"get_channel_info failed: {e}")
            return None

    def get_videos(self, channel_url: str, max_videos: int = None) -> list[VideoMeta]:
        """Return list of VideoMeta for the channel's latest videos."""
        limit = max_videos or self.max_videos
        try:
            cmd = [
                "yt-dlp",
                "--dump-single-json",
                "--flat-playlist",
                "--playlist-end", str(limit),
                "--no-warnings",
                channel_url,
            ]
            result = self._run(cmd)
            if not result:
                return []

            data = json.loads(result)
            entries = data.get("entries") or [data]

            videos = []
            for entry in entries:
                if not entry:
                    continue
                vid_id = entry.get("id") or entry.get("video_id", "")
                url = entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={vid_id}"
                videos.append(VideoMeta(
                    video_id=vid_id,
                    title=entry.get("title", "Unknown"),
                    url=url,
                    duration=entry.get("duration", 0) or 0,
                    view_count=entry.get("view_count", 0) or 0,
                    like_count=entry.get("like_count", 0) or 0,
                    upload_date=entry.get("upload_date", "") or "",
                    description=entry.get("description", "") or "",
                    thumbnail=entry.get("thumbnail", "") or "",
                    tags=entry.get("tags", []) or [],
                ))
            return videos
        except Exception as e:
            logger.error(f"get_videos failed: {e}")
            return []

    def resolve_channel_url(self, raw_input: str) -> str:
        """
        Accept @handle, /channel/ID, /c/name, or plain URL and
        return a normalized yt-dlp-compatible URL.
        """
        raw = raw_input.strip()
        if raw.startswith("http"):
            return raw
        if raw.startswith("@"):
            return f"https://www.youtube.com/{raw}"
        if re.match(r"^[A-Za-z0-9_\-]{2,}$", raw):
            return f"https://www.youtube.com/@{raw}"
        return raw

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _run(self, cmd: list[str]) -> Optional[str]:
        time.sleep(random.uniform(*self.delay))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode != 0:
                logger.warning(f"yt-dlp stderr: {proc.stderr[:200]}")
                return None
            return proc.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timed out")
            return None
        except FileNotFoundError:
            logger.error("yt-dlp not found — install with: pip install yt-dlp")
            return None
