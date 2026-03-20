"""
YouTube Clone AI — Autonomous Scheduler / Pipeline
DHD Data | Clients First. Perfection Always.

APScheduler-based background automation that continuously scrapes channels,
analyzes styles, generates scripts, and dispatches Telegram notifications.
"""
import logging
import json
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .database import Database
from .telegram_utils import TelegramNotifier
from ai.analyzer import StyleAnalyzer
from ai.generator import ScriptGenerator
from scrapers.youtube import YouTubeScraper
from scrapers.transcript import TranscriptExtractor

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Singleton                                                           #
# ------------------------------------------------------------------ #

_scheduler_instance: Optional["AutomationScheduler"] = None


def get_scheduler(
    api_key: str = None,
    telegram_token: str = None,
    telegram_chat_id: str = None,
    db_path: str = None,
) -> "AutomationScheduler":
    """
    Return the module-level singleton AutomationScheduler.
    On first call all arguments are required; subsequent calls
    return the existing instance regardless of arguments.
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        if not api_key:
            raise ValueError(
                "api_key is required when creating the scheduler for the first time."
            )
        _scheduler_instance = AutomationScheduler(
            api_key=api_key,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
            db_path=db_path,
        )
    return _scheduler_instance


# ------------------------------------------------------------------ #
#  AutomationScheduler                                                 #
# ------------------------------------------------------------------ #


class AutomationScheduler:
    """
    Autonomous background scheduler that drives the full clone pipeline:

      - Every  6 h  → scrape active channels for new videos + transcripts
      - Every 12 h  → run StyleAnalyzer on channels that need (re-)analysis
      - Every 24 h  → generate 3 scripts per channel and send via Telegram
      - Daily 08:00 → send stats summary to Telegram
    """

    # ---------------------------------------------------------------- #
    #  Init                                                              #
    # ---------------------------------------------------------------- #

    def __init__(
        self,
        api_key: str,
        telegram_token: str = None,
        telegram_chat_id: str = None,
        db_path: str = None,
    ):
        self.api_key = api_key
        self.db_path = db_path

        # Core dependencies
        self.db = Database(db_path=db_path)
        self.telegram = TelegramNotifier(token=telegram_token, chat_id=telegram_chat_id)
        self.analyzer = StyleAnalyzer(api_key=api_key)
        self.generator = ScriptGenerator(api_key=api_key)
        self.scraper = YouTubeScraper()
        self.extractor = TranscriptExtractor()

        # APScheduler
        self._scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1},
            timezone="UTC",
        )
        self._running = False

        logger.info("AutomationScheduler initialised")

    # ---------------------------------------------------------------- #
    #  Lifecycle                                                         #
    # ---------------------------------------------------------------- #

    def start(self) -> None:
        """Register all jobs and start the background scheduler."""
        if self._running:
            logger.warning("Scheduler is already running — ignoring start()")
            return

        # scrape_job: every 6 hours
        self._scheduler.add_job(
            func=self._run_scrape_job,
            trigger=IntervalTrigger(hours=6),
            id="scrape_job",
            name="Scrape active channels",
            replace_existing=True,
        )

        # analyze_job: every 12 hours
        self._scheduler.add_job(
            func=self._run_analyze_job,
            trigger=IntervalTrigger(hours=12),
            id="analyze_job",
            name="Analyze channel styles",
            replace_existing=True,
        )

        # generate_job: every 24 hours
        self._scheduler.add_job(
            func=self._run_generate_job,
            trigger=IntervalTrigger(hours=24),
            id="generate_job",
            name="Generate scripts",
            replace_existing=True,
        )

        # daily_summary_job: every day at 08:00 UTC
        self._scheduler.add_job(
            func=self._run_daily_summary_job,
            trigger=CronTrigger(hour=8, minute=0),
            id="daily_summary_job",
            name="Daily Telegram summary",
            replace_existing=True,
        )

        self._scheduler.start()
        self._running = True
        logger.info(
            "AutomationScheduler started — scrape/6h, analyze/12h, generate/24h, summary/08:00"
        )
        self.telegram.send_alert("AutomationScheduler started — YouTube Clone AI is live.")

    def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if not self._running:
            logger.warning("Scheduler is not running — ignoring stop()")
            return
        self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("AutomationScheduler stopped")
        self.telegram.send_alert("AutomationScheduler stopped.")

    # ---------------------------------------------------------------- #
    #  Manual trigger                                                    #
    # ---------------------------------------------------------------- #

    def run_now(self, channel_id: str, job_type: str) -> dict:
        """
        Manually trigger a specific job for a single channel.

        Args:
            channel_id: The channel_id string stored in the DB.
            job_type:   One of 'scrape', 'analyze', 'generate'.

        Returns:
            dict with keys: success (bool), message (str), result (any)
        """
        logger.info(f"Manual trigger — job_type={job_type} channel_id={channel_id}")
        dispatch = {
            "scrape": self._scrape_channel,
            "analyze": self._analyze_channel,
            "generate": self._generate_for_channel,
        }
        fn = dispatch.get(job_type)
        if fn is None:
            return {
                "success": False,
                "message": f"Unknown job_type '{job_type}'. Valid: scrape, analyze, generate",
                "result": None,
            }

        try:
            result = fn(channel_id)
            return {"success": True, "message": f"{job_type} completed", "result": result}
        except Exception as exc:
            logger.error(f"run_now failed — {job_type}/{channel_id}: {exc}", exc_info=True)
            return {"success": False, "message": str(exc), "result": None}

    # ---------------------------------------------------------------- #
    #  Status                                                            #
    # ---------------------------------------------------------------- #

    def get_status(self) -> dict:
        """Return a dict describing scheduler and job states."""
        status = {
            "running": self._running,
            "jobs": {},
        }
        for job in self._scheduler.get_jobs():
            next_run = job.next_run_time
            status["jobs"][job.id] = {
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger),
            }
        return status

    # ---------------------------------------------------------------- #
    #  Scheduled job runners (top-level, iterate channels)              #
    # ---------------------------------------------------------------- #

    def _run_scrape_job(self) -> None:
        logger.info("=== scrape_job started ===")
        channels = self.db.get_channels(active_only=True)
        if not channels:
            logger.info("scrape_job: no active channels found")
            return
        for ch in channels:
            try:
                self._scrape_channel(ch["channel_id"])
            except Exception as exc:
                logger.error(
                    f"scrape_job: unhandled error for {ch['channel_id']}: {exc}",
                    exc_info=True,
                )
        logger.info("=== scrape_job finished ===")

    def _run_analyze_job(self) -> None:
        logger.info("=== analyze_job started ===")
        channels = self.db.get_channels(active_only=True)
        if not channels:
            logger.info("analyze_job: no active channels found")
            return
        for ch in channels:
            try:
                # Only analyze channels that have transcripts but no recent analysis,
                # OR whose transcript count has grown since last analysis.
                transcripts = self.db.get_transcripts(ch["channel_id"])
                if not transcripts:
                    logger.debug(
                        f"analyze_job: skipping {ch['channel_id']} — no transcripts"
                    )
                    continue
                latest = self.db.get_latest_analysis(ch["channel_id"])
                if latest:
                    videos_used = latest.get("videos_used", 0)
                    if len(transcripts) <= videos_used:
                        logger.debug(
                            f"analyze_job: skipping {ch['channel_id']} — no new transcripts"
                        )
                        continue
                self._analyze_channel(ch["channel_id"])
            except Exception as exc:
                logger.error(
                    f"analyze_job: unhandled error for {ch['channel_id']}: {exc}",
                    exc_info=True,
                )
        logger.info("=== analyze_job finished ===")

    def _run_generate_job(self) -> None:
        logger.info("=== generate_job started ===")
        channels = self.db.get_channels(active_only=True)
        if not channels:
            logger.info("generate_job: no active channels found")
            return
        for ch in channels:
            try:
                analysis_row = self.db.get_latest_analysis(ch["channel_id"])
                if not analysis_row:
                    logger.debug(
                        f"generate_job: skipping {ch['channel_id']} — no analysis yet"
                    )
                    continue
                self._generate_for_channel(ch["channel_id"])
            except Exception as exc:
                logger.error(
                    f"generate_job: unhandled error for {ch['channel_id']}: {exc}",
                    exc_info=True,
                )
        logger.info("=== generate_job finished ===")

    def _run_daily_summary_job(self) -> None:
        logger.info("=== daily_summary_job started ===")
        try:
            stats = self.db.get_stats()
            stats["date"] = datetime.utcnow().strftime("%Y-%m-%d")
            self.telegram.send_daily_summary(stats)
            logger.info(f"daily_summary_job: summary sent — {stats}")
        except Exception as exc:
            logger.error(f"daily_summary_job failed: {exc}", exc_info=True)
        logger.info("=== daily_summary_job finished ===")

    # ---------------------------------------------------------------- #
    #  Per-channel workers                                              #
    # ---------------------------------------------------------------- #

    def _scrape_channel(self, channel_id: str) -> dict:
        """
        Fetch latest videos and transcripts for one channel.

        Returns:
            dict with videos_found (int) and transcripts_found (int)
        """
        logger.info(f"_scrape_channel: start — {channel_id}")

        channel = self.db.get_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel not found in DB: {channel_id}")

        channel_url = channel["url"]
        videos_found = 0
        transcripts_found = 0

        # Fetch video list
        videos = self.scraper.get_videos(channel_url)
        if not videos:
            logger.warning(f"_scrape_channel: no videos returned for {channel_id}")
            return {"videos_found": 0, "transcripts_found": 0}

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

                # Pull transcript if we don't already have one
                existing = self.db.get_transcripts(channel_id)
                existing_ids = {t["video_id"] for t in existing}
                if video.video_id not in existing_ids:
                    transcript_text = self.extractor.get_transcript(video.video_id)
                    if transcript_text:
                        self.db.save_transcript(
                            video_id=video.video_id,
                            channel_id=channel_id,
                            transcript=transcript_text,
                        )
                        transcripts_found += 1
                        logger.debug(
                            f"_scrape_channel: saved transcript for {video.video_id}"
                        )
            except Exception as exc:
                logger.error(
                    f"_scrape_channel: error processing video {video.video_id}: {exc}",
                    exc_info=True,
                )

        # Update last_scraped timestamp
        self.db.upsert_channel({
            "channel_id": channel_id,
            "name": channel["name"],
            "url": channel_url,
            "subscribers": channel.get("subscribers", 0),
            "video_count": channel.get("video_count", 0),
            "description": channel.get("description", ""),
            "thumbnail": channel.get("thumbnail", ""),
        })

        logger.info(
            f"_scrape_channel: done — {channel_id} "
            f"videos={videos_found} transcripts={transcripts_found}"
        )
        return {"videos_found": videos_found, "transcripts_found": transcripts_found}

    def _analyze_channel(self, channel_id: str) -> dict:
        """
        Run StyleAnalyzer on a channel's transcripts and persist the result.

        Returns:
            dict with analysis (dict), score (int), grade (str)
        """
        logger.info(f"_analyze_channel: start — {channel_id}")

        channel = self.db.get_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel not found in DB: {channel_id}")

        transcripts = self.db.get_transcripts(channel_id)
        if not transcripts:
            raise ValueError(f"No transcripts available for channel: {channel_id}")

        analysis = self.analyzer.analyze_channel(transcripts)
        if not analysis:
            raise RuntimeError(f"StyleAnalyzer returned no result for {channel_id}")

        score_data = self.analyzer.score_content(analysis)
        self.db.save_analysis(
            channel_id=channel_id,
            analysis=analysis,
            score_data=score_data,
            videos_used=len(transcripts),
        )

        # Notify via Telegram
        self.telegram.send_analysis_complete(
            channel_name=channel["name"],
            score=score_data.get("score", 0),
            grade=score_data.get("grade", "C"),
        )

        logger.info(
            f"_analyze_channel: done — {channel_id} "
            f"score={score_data.get('score')} grade={score_data.get('grade')}"
        )
        return {
            "analysis": analysis,
            "score": score_data.get("score", 0),
            "grade": score_data.get("grade", "C"),
        }

    def _generate_for_channel(self, channel_id: str) -> list[dict]:
        """
        Auto-select 3 topics and generate one script per topic.
        Saves each script to the DB and sends it via Telegram.

        Returns:
            list of script dicts
        """
        logger.info(f"_generate_for_channel: start — {channel_id}")

        channel = self.db.get_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel not found in DB: {channel_id}")

        analysis_row = self.db.get_latest_analysis(channel_id)
        if not analysis_row:
            raise ValueError(f"No style analysis found for channel: {channel_id}")

        analysis = analysis_row["analysis"]
        topics = self._auto_select_topics(analysis, n=3)
        if not topics:
            raise ValueError(
                f"Could not determine topics from analysis for channel: {channel_id}"
            )

        logger.info(f"_generate_for_channel: auto-selected topics={topics}")

        scripts = self.generator.batch_generate(
            style_dna=analysis,
            topics=topics,
            length_minutes=10,
        )

        saved_scripts = []
        for script in scripts:
            try:
                script_id = self.db.save_script(channel_id=channel_id, script=script)
                script["id"] = script_id

                # Send to Telegram
                sent = self.telegram.send_script(
                    script=script, channel_name=channel["name"]
                )
                if sent:
                    self.db.mark_script_sent(script_id)

                saved_scripts.append(script)
                logger.debug(
                    f"_generate_for_channel: saved script id={script_id} "
                    f"topic={script.get('topic')} sent={sent}"
                )
            except Exception as exc:
                logger.error(
                    f"_generate_for_channel: error saving script for "
                    f"{channel_id}/{script.get('topic')}: {exc}",
                    exc_info=True,
                )

        logger.info(
            f"_generate_for_channel: done — {channel_id} "
            f"generated={len(scripts)} saved={len(saved_scripts)}"
        )
        return saved_scripts

    # ---------------------------------------------------------------- #
    #  Private helpers                                                   #
    # ---------------------------------------------------------------- #

    def _auto_select_topics(self, analysis: dict, n: int = 3) -> list[str]:
        """
        Pick n topics from the analysis dict.

        Priority order:
          1. topic_clusters.trending_angles   (most engagement)
          2. topic_clusters.sub_topics
          3. topic_clusters.main_themes
          4. topic_clusters.content_pillars   (fallback)
        """
        topic_clusters = analysis.get("topic_clusters", {})

        pool: list[str] = []

        for key in ("trending_angles", "sub_topics", "main_themes", "content_pillars"):
            items = topic_clusters.get(key, [])
            if isinstance(items, list):
                pool.extend([str(t) for t in items if t])

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for t in pool:
            if t not in seen:
                seen.add(t)
                unique.append(t)

        selected = unique[:n]

        if not selected:
            logger.warning("_auto_select_topics: could not derive topics from analysis")

        return selected
