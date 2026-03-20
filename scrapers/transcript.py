"""
YouTube Clone AI — Transcript Extractor
DHD Data | Clients First. Perfection Always.

Pulls full transcripts from YouTube videos.
Tries youtube-transcript-api first, falls back to yt-dlp subtitles.
"""
import subprocess
import json
import os
import re
import logging
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


class TranscriptExtractor:
    """
    Extracts transcripts from YouTube videos.
    Strategy:
      1. youtube-transcript-api (fast, no download)
      2. yt-dlp auto-subs (fallback)
    """

    def get_transcript(self, video_id: str) -> Optional[str]:
        """Return full transcript text for a video ID."""
        # Strategy 1: youtube-transcript-api
        transcript = self._via_transcript_api(video_id)
        if transcript:
            return transcript

        # Strategy 2: yt-dlp subtitles
        transcript = self._via_yt_dlp(video_id)
        if transcript:
            return transcript

        logger.warning(f"No transcript available for {video_id}")
        return None

    def get_transcript_url(self, url: str) -> Optional[str]:
        """Extract transcript from a full YouTube URL."""
        video_id = self._extract_video_id(url)
        if not video_id:
            return None
        return self.get_transcript(video_id)

    # ------------------------------------------------------------------ #
    #  Strategy 1: youtube-transcript-api                                  #
    # ------------------------------------------------------------------ #

    def _via_transcript_api(self, video_id: str) -> Optional[str]:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            segments = [seg["text"] for seg in transcript_list]
            return " ".join(segments)
        except Exception as e:
            logger.debug(f"transcript-api failed for {video_id}: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Strategy 2: yt-dlp subtitles                                        #
    # ------------------------------------------------------------------ #

    def _via_yt_dlp(self, video_id: str) -> Optional[str]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "sub")
            cmd = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--sub-format", "json3",
                "--skip-download",
                "--no-warnings",
                "-o", out_path,
                url,
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=60)
                # find generated .json3 file
                for fname in os.listdir(tmpdir):
                    if fname.endswith(".json3"):
                        fpath = os.path.join(tmpdir, fname)
                        return self._parse_json3(fpath)
            except Exception as e:
                logger.debug(f"yt-dlp subtitle failed for {video_id}: {e}")
            return None

    def _parse_json3(self, filepath: str) -> Optional[str]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            parts = []
            for event in data.get("events", []):
                for seg in event.get("segs", []):
                    text = seg.get("utf8", "").strip()
                    if text and text != "\n":
                        parts.append(text)
            raw = " ".join(parts)
            # clean up artifacts
            raw = re.sub(r"\s+", " ", raw)
            raw = re.sub(r"\[.*?\]", "", raw)  # remove [Music] [Applause] etc
            return raw.strip() if raw.strip() else None
        except Exception as e:
            logger.debug(f"json3 parse error: {e}")
            return None

    # ------------------------------------------------------------------ #
    #  Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r"(?:v=|youtu\.be/|/embed/|/v/)([A-Za-z0-9_\-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
