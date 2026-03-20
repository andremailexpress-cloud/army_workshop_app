"""
YouTube Clone AI — On-Demand Pipeline
DHD Data | Clients First. Perfection Always.

Provides a high-level Pipeline class used by the Streamlit UI to run the full
clone workflow synchronously on demand:
  add_channel → analyze_channel → generate_content (or full_pipeline for all three).
"""

import logging
from typing import Optional

from .database import Database
from .telegram_utils import TelegramNotifier
from ai.analyzer import StyleAnalyzer
from ai.generator import ScriptGenerator
from scrapers.youtube import YouTubeScraper
from scrapers.transcript import TranscriptExtractor

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Orchestrates the full YouTube clone workflow on demand.

    Typical usage (UI flow):
        p = Pipeline(api_key="...", db_path="data/youtube_clone.db")
        result = p.add_channel("https://www.youtube.com/@mkbhd")
        analysis = p.analyze_channel(result["channel_id"])
        scripts = p.generate_content(result["channel_id"], topics=["5G explained"])
    """

    def __init__(self, api_key: str, db_path: str = None):
        """
        Args:
            api_key:  Anthropic API key for Claude.
            db_path:  Path to the SQLite database file. Falls back to the
                      Database class default (data/youtube_clone.db) if None.
        """
        self.api_key = api_key
        self.db_path = db_path

        self.db = Database(db_path=db_path)
        self.scraper = YouTubeScraper()
        self.extractor = TranscriptExtractor()
        self.analyzer = StyleAnalyzer(api_key=api_key)
        self.generator = ScriptGenerator(api_key=api_key)

        logger.info("Pipeline initialised")

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def add_channel(self, url: str, max_videos: int = 15) -> dict:
        """
        Scrape a YouTube channel, persist metadata, videos, and transcripts.

        Args:
            url:        Any YouTube channel URL, @handle, or channel ID.
            max_videos: Maximum number of videos to scrape for transcripts.

        Returns:
            {
                "success":           bool,
                "channel_id":        str | None,
                "channel_name":      str | None,
                "videos_found":      int,
                "transcripts_found": int,
                "error":             str | None,
            }
        """
        logger.info(f"add_channel: start — url={url} max_videos={max_videos}")

        result = {
            "success": False,
            "channel_id": None,
            "channel_name": None,
            "videos_found": 0,
            "transcripts_found": 0,
            "error": None,
        }

        try:
            resolved_url = self.scraper.resolve_channel_url(url)

            # ---- 1. Channel metadata ----------------------------------------
            channel_meta = self.scraper.get_channel_info(resolved_url)
            if not channel_meta:
                result["error"] = (
                    "Could not retrieve channel info. "
                    "Check the URL and ensure yt-dlp is installed."
                )
                logger.warning(f"add_channel: get_channel_info returned None for {url}")
                return result

            channel_id = channel_meta.channel_id
            if not channel_id:
                result["error"] = "yt-dlp did not return a channel ID for this URL."
                logger.warning(f"add_channel: empty channel_id for {url}")
                return result

            self.db.upsert_channel({
                "channel_id": channel_id,
                "name": channel_meta.channel_name,
                "url": resolved_url,
                "subscribers": channel_meta.subscriber_count,
                "video_count": channel_meta.video_count,
                "description": channel_meta.description,
                "thumbnail": channel_meta.thumbnail,
            })
            logger.info(
                f"add_channel: channel persisted — id={channel_id} "
                f"name={channel_meta.channel_name}"
            )

            # ---- 2. Video list -----------------------------------------------
            videos = self.scraper.get_videos(resolved_url, max_videos=max_videos)
            videos_found = 0
            transcripts_found = 0

            for video in videos:
                try:
                    self.db.upsert_video({
                        "channel_id": channel_id,
                        "video_id": video.video_id,
                        "title": video.title,
                        "url": video.url,
                        "duration": video.duration,
                        "view_count": video.view_count,
                        "upload_date": video.upload_date,
                        "thumbnail": video.thumbnail,
                    })
                    videos_found += 1
                except Exception as exc:
                    logger.error(
                        f"add_channel: failed to upsert video {video.video_id}: {exc}"
                    )

            logger.info(f"add_channel: {videos_found} videos saved for {channel_id}")

            # ---- 3. Transcripts ----------------------------------------------
            existing_transcripts = self.db.get_transcripts(channel_id)
            existing_ids = {t["video_id"] for t in existing_transcripts}

            for video in videos:
                if video.video_id in existing_ids:
                    logger.debug(
                        f"add_channel: skipping transcript for {video.video_id} — already stored"
                    )
                    continue
                try:
                    transcript_text = self.extractor.get_transcript(video.video_id)
                    if transcript_text:
                        self.db.save_transcript(
                            video_id=video.video_id,
                            channel_id=channel_id,
                            transcript=transcript_text,
                        )
                        transcripts_found += 1
                        logger.debug(
                            f"add_channel: transcript saved for {video.video_id}"
                        )
                    else:
                        logger.debug(
                            f"add_channel: no transcript available for {video.video_id}"
                        )
                except Exception as exc:
                    logger.error(
                        f"add_channel: transcript extraction failed for "
                        f"{video.video_id}: {exc}"
                    )

            logger.info(
                f"add_channel: done — channel={channel_id} "
                f"videos={videos_found} transcripts={transcripts_found}"
            )

            result.update({
                "success": True,
                "channel_id": channel_id,
                "channel_name": channel_meta.channel_name,
                "videos_found": videos_found,
                "transcripts_found": transcripts_found,
            })

        except Exception as exc:
            logger.error(f"add_channel: unexpected error — {exc}", exc_info=True)
            result["error"] = str(exc)

        return result

    # ------------------------------------------------------------------ #

    def analyze_channel(self, channel_id: str) -> dict:
        """
        Run a full style analysis on all stored transcripts for a channel.

        Args:
            channel_id: The channel_id string stored in the DB.

        Returns:
            {
                "success":  bool,
                "analysis": dict | None,
                "score":    int,
                "grade":    str,
                "error":    str | None,
            }
        """
        logger.info(f"analyze_channel: start — {channel_id}")

        result = {
            "success": False,
            "analysis": None,
            "score": 0,
            "grade": "D",
            "error": None,
        }

        try:
            channel = self.db.get_channel(channel_id)
            if not channel:
                result["error"] = f"Channel '{channel_id}' not found in database."
                logger.warning(f"analyze_channel: channel not found — {channel_id}")
                return result

            transcripts = self.db.get_transcripts(channel_id)
            if not transcripts:
                result["error"] = (
                    "No transcripts available for this channel. "
                    "Run add_channel first to scrape transcripts."
                )
                logger.warning(
                    f"analyze_channel: no transcripts for {channel_id}"
                )
                return result

            logger.info(
                f"analyze_channel: running StyleAnalyzer on "
                f"{len(transcripts)} transcript(s) for {channel_id}"
            )

            analysis = self.analyzer.analyze_channel(transcripts)
            if not analysis:
                result["error"] = (
                    "Style analysis returned no result. "
                    "Check API key and transcript quality."
                )
                logger.error(
                    f"analyze_channel: StyleAnalyzer returned None for {channel_id}"
                )
                return result

            score_data = self.analyzer.score_content(analysis)
            self.db.save_analysis(
                channel_id=channel_id,
                analysis=analysis,
                score_data=score_data,
                videos_used=len(transcripts),
            )

            logger.info(
                f"analyze_channel: done — {channel_id} "
                f"score={score_data.get('score')} grade={score_data.get('grade')}"
            )

            result.update({
                "success": True,
                "analysis": analysis,
                "score": score_data.get("score", 0),
                "grade": score_data.get("grade", "C"),
            })

        except Exception as exc:
            logger.error(f"analyze_channel: unexpected error — {exc}", exc_info=True)
            result["error"] = str(exc)

        return result

    # ------------------------------------------------------------------ #

    def generate_content(
        self,
        channel_id: str,
        topics: list,
        length_minutes: int = 10,
    ) -> list:
        """
        Generate video scripts for the given topics, cloned from the channel's style.

        Args:
            channel_id:     The channel_id string stored in the DB.
            topics:         List of topic strings to generate scripts for.
            length_minutes: Target video length per script (default 10).

        Returns:
            List of script dicts. Each dict contains at minimum:
                topic, title, script, description, tags, hook, cta, estimated_duration.
            Returns an empty list if generation fails entirely.
        """
        logger.info(
            f"generate_content: start — channel={channel_id} "
            f"topics={topics} length={length_minutes}m"
        )

        if not topics:
            logger.warning("generate_content: no topics provided — returning empty list")
            return []

        analysis_row = self.db.get_latest_analysis(channel_id)
        if not analysis_row:
            logger.error(
                f"generate_content: no style analysis found for {channel_id}. "
                "Run analyze_channel first."
            )
            return []

        style_dna = analysis_row["analysis"]
        channel = self.db.get_channel(channel_id)
        channel_name = channel["name"] if channel else channel_id

        scripts = []
        for topic in topics:
            try:
                logger.info(f"generate_content: generating script — topic='{topic}'")
                script = self.generator.generate_script(
                    style_dna=style_dna,
                    topic=topic,
                    length_minutes=length_minutes,
                )
                if not script:
                    logger.warning(
                        f"generate_content: ScriptGenerator returned None for topic='{topic}'"
                    )
                    continue

                script_id = self.db.save_script(channel_id=channel_id, script=script)
                script["id"] = script_id
                script["channel_id"] = channel_id
                script["channel_name"] = channel_name

                scripts.append(script)
                logger.debug(
                    f"generate_content: script saved id={script_id} topic='{topic}'"
                )

            except Exception as exc:
                logger.error(
                    f"generate_content: failed for topic='{topic}': {exc}",
                    exc_info=True,
                )

        logger.info(
            f"generate_content: done — channel={channel_id} "
            f"requested={len(topics)} generated={len(scripts)}"
        )
        return scripts

    # ------------------------------------------------------------------ #

    def full_pipeline(
        self,
        url: str,
        topics: list,
        max_videos: int = 15,
    ) -> dict:
        """
        Run the complete workflow in sequence:
          1. add_channel   (scrape + transcripts)
          2. analyze_channel (style DNA)
          3. generate_content (scripts)

        Args:
            url:        YouTube channel URL or @handle.
            topics:     List of topic strings for script generation.
            max_videos: Maximum videos to scrape for transcripts.

        Returns:
            {
                "success":           bool,
                "channel_id":        str | None,
                "channel_name":      str | None,
                "videos_found":      int,
                "transcripts_found": int,
                "analysis":          dict | None,
                "score":             int,
                "grade":             str,
                "scripts":           list[dict],
                "error":             str | None,
                "step_failed":       str | None,   # which step failed, if any
            }
        """
        logger.info(
            f"full_pipeline: start — url={url} "
            f"topics={topics} max_videos={max_videos}"
        )

        result = {
            "success": False,
            "channel_id": None,
            "channel_name": None,
            "videos_found": 0,
            "transcripts_found": 0,
            "analysis": None,
            "score": 0,
            "grade": "D",
            "scripts": [],
            "error": None,
            "step_failed": None,
        }

        # ---- Step 1: Add channel -----------------------------------------
        logger.info("full_pipeline: step 1 — add_channel")
        add_result = self.add_channel(url=url, max_videos=max_videos)
        result["videos_found"] = add_result["videos_found"]
        result["transcripts_found"] = add_result["transcripts_found"]
        result["channel_id"] = add_result["channel_id"]
        result["channel_name"] = add_result["channel_name"]

        if not add_result["success"]:
            result["error"] = add_result["error"]
            result["step_failed"] = "add_channel"
            logger.error(f"full_pipeline: add_channel failed — {add_result['error']}")
            return result

        channel_id = add_result["channel_id"]

        if add_result["transcripts_found"] == 0:
            # Warn but do not abort — existing transcripts may already be in DB
            logger.warning(
                "full_pipeline: no new transcripts found; will try analyzing existing ones"
            )

        # ---- Step 2: Analyze ------------------------------------------------
        logger.info("full_pipeline: step 2 — analyze_channel")
        analyze_result = self.analyze_channel(channel_id=channel_id)
        result["analysis"] = analyze_result["analysis"]
        result["score"] = analyze_result["score"]
        result["grade"] = analyze_result["grade"]

        if not analyze_result["success"]:
            result["error"] = analyze_result["error"]
            result["step_failed"] = "analyze_channel"
            logger.error(
                f"full_pipeline: analyze_channel failed — {analyze_result['error']}"
            )
            return result

        # ---- Step 3: Generate -----------------------------------------------
        logger.info("full_pipeline: step 3 — generate_content")
        scripts = self.generate_content(
            channel_id=channel_id,
            topics=topics,
        )
        result["scripts"] = scripts

        if not scripts:
            result["error"] = (
                "Script generation returned no results. "
                "Check topics and API key."
            )
            result["step_failed"] = "generate_content"
            logger.warning(f"full_pipeline: generate_content returned no scripts")
            # Partial success — analysis succeeded even if generation failed
            return result

        result["success"] = True
        logger.info(
            f"full_pipeline: completed successfully — channel={channel_id} "
            f"scripts={len(scripts)}"
        )
        return result
