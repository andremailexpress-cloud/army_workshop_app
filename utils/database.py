"""
YouTube Clone AI — Database Layer (SQLite)
DHD Data | Clients First. Perfection Always.

Stores channels, transcripts, style analyses, and generated scripts.
"""
import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    """SQLite database for persistent storage of all app data."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("DB_PATH", "data/youtube_clone.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------ #
    #  Schema                                                               #
    # ------------------------------------------------------------------ #

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS channels (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id  TEXT UNIQUE NOT NULL,
                    name        TEXT NOT NULL,
                    url         TEXT NOT NULL,
                    subscribers INTEGER DEFAULT 0,
                    video_count INTEGER DEFAULT 0,
                    description TEXT,
                    thumbnail   TEXT,
                    added_at    TEXT DEFAULT (datetime('now')),
                    last_scraped TEXT,
                    is_active   INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS videos (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id  TEXT NOT NULL,
                    video_id    TEXT UNIQUE NOT NULL,
                    title       TEXT NOT NULL,
                    url         TEXT NOT NULL,
                    duration    INTEGER DEFAULT 0,
                    view_count  INTEGER DEFAULT 0,
                    upload_date TEXT,
                    thumbnail   TEXT,
                    scraped_at  TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
                );

                CREATE TABLE IF NOT EXISTS transcripts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id    TEXT UNIQUE NOT NULL,
                    channel_id  TEXT NOT NULL,
                    transcript  TEXT NOT NULL,
                    word_count  INTEGER DEFAULT 0,
                    extracted_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS style_analyses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id  TEXT NOT NULL,
                    analysis    TEXT NOT NULL,
                    score       INTEGER DEFAULT 0,
                    grade       TEXT DEFAULT 'C',
                    videos_used INTEGER DEFAULT 0,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS generated_scripts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id  TEXT NOT NULL,
                    topic       TEXT NOT NULL,
                    title       TEXT,
                    script      TEXT NOT NULL,
                    description TEXT,
                    tags        TEXT,
                    thumbnail_idea TEXT,
                    cta         TEXT,
                    status      TEXT DEFAULT 'draft',
                    sent_to_telegram INTEGER DEFAULT 0,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS automation_jobs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id  TEXT NOT NULL,
                    job_type    TEXT NOT NULL,
                    status      TEXT DEFAULT 'pending',
                    started_at  TEXT,
                    finished_at TEXT,
                    result      TEXT,
                    error_msg   TEXT
                );
            """)

    # ------------------------------------------------------------------ #
    #  Channels                                                             #
    # ------------------------------------------------------------------ #

    def upsert_channel(self, channel: dict) -> int:
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO channels (channel_id, name, url, subscribers, video_count, description, thumbnail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    name=excluded.name,
                    subscribers=excluded.subscribers,
                    video_count=excluded.video_count,
                    description=excluded.description,
                    thumbnail=excluded.thumbnail,
                    last_scraped=datetime('now')
            """, (
                channel["channel_id"], channel["name"], channel["url"],
                channel.get("subscribers", 0), channel.get("video_count", 0),
                channel.get("description", ""), channel.get("thumbnail", ""),
            ))
            return conn.execute(
                "SELECT id FROM channels WHERE channel_id=?", (channel["channel_id"],)
            ).fetchone()[0]

    def get_channels(self, active_only: bool = True) -> list[dict]:
        with self._conn() as conn:
            q = "SELECT * FROM channels"
            if active_only:
                q += " WHERE is_active=1"
            q += " ORDER BY added_at DESC"
            return [dict(row) for row in conn.execute(q).fetchall()]

    def get_channel(self, channel_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM channels WHERE channel_id=?", (channel_id,)
            ).fetchone()
            return dict(row) if row else None

    def delete_channel(self, channel_id: str):
        with self._conn() as conn:
            conn.execute("UPDATE channels SET is_active=0 WHERE channel_id=?", (channel_id,))

    # ------------------------------------------------------------------ #
    #  Videos & Transcripts                                                #
    # ------------------------------------------------------------------ #

    def upsert_video(self, video: dict):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO videos (channel_id, video_id, title, url, duration, view_count, upload_date, thumbnail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    view_count=excluded.view_count
            """, (
                video["channel_id"], video["video_id"], video["title"], video["url"],
                video.get("duration", 0), video.get("view_count", 0),
                video.get("upload_date", ""), video.get("thumbnail", ""),
            ))

    def save_transcript(self, video_id: str, channel_id: str, transcript: str):
        word_count = len(transcript.split())
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO transcripts (video_id, channel_id, transcript, word_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    transcript=excluded.transcript,
                    word_count=excluded.word_count,
                    extracted_at=datetime('now')
            """, (video_id, channel_id, transcript, word_count))

    def get_transcripts(self, channel_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT t.video_id, t.transcript, t.word_count, v.title
                FROM transcripts t
                LEFT JOIN videos v ON t.video_id = v.video_id
                WHERE t.channel_id = ?
                ORDER BY t.extracted_at DESC
            """, (channel_id,)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  Style Analyses                                                       #
    # ------------------------------------------------------------------ #

    def save_analysis(self, channel_id: str, analysis: dict, score_data: dict, videos_used: int) -> int:
        with self._conn() as conn:
            cur = conn.execute("""
                INSERT INTO style_analyses (channel_id, analysis, score, grade, videos_used)
                VALUES (?, ?, ?, ?, ?)
            """, (
                channel_id,
                json.dumps(analysis),
                score_data.get("score", 0),
                score_data.get("grade", "C"),
                videos_used,
            ))
            return cur.lastrowid

    def get_latest_analysis(self, channel_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT * FROM style_analyses
                WHERE channel_id=?
                ORDER BY created_at DESC LIMIT 1
            """, (channel_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["analysis"] = json.loads(d["analysis"])
            return d

    # ------------------------------------------------------------------ #
    #  Generated Scripts                                                    #
    # ------------------------------------------------------------------ #

    def save_script(self, channel_id: str, script: dict) -> int:
        with self._conn() as conn:
            cur = conn.execute("""
                INSERT INTO generated_scripts
                    (channel_id, topic, title, script, description, tags, thumbnail_idea, cta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                channel_id,
                script.get("topic", ""),
                script.get("title", ""),
                script.get("script", ""),
                script.get("description", ""),
                json.dumps(script.get("tags", [])),
                script.get("thumbnail_idea", ""),
                script.get("cta", ""),
            ))
            return cur.lastrowid

    def get_scripts(self, channel_id: str = None, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            if channel_id:
                rows = conn.execute("""
                    SELECT * FROM generated_scripts
                    WHERE channel_id=?
                    ORDER BY created_at DESC LIMIT ?
                """, (channel_id, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM generated_scripts
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,)).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if d.get("tags"):
                    try:
                        d["tags"] = json.loads(d["tags"])
                    except Exception:
                        d["tags"] = []
                results.append(d)
            return results

    def mark_script_sent(self, script_id: int):
        with self._conn() as conn:
            conn.execute(
                "UPDATE generated_scripts SET sent_to_telegram=1, status='published' WHERE id=?",
                (script_id,)
            )

    # ------------------------------------------------------------------ #
    #  Stats                                                                #
    # ------------------------------------------------------------------ #

    def get_stats(self) -> dict:
        with self._conn() as conn:
            return {
                "channels": conn.execute("SELECT COUNT(*) FROM channels WHERE is_active=1").fetchone()[0],
                "videos": conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0],
                "transcripts": conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0],
                "analyses": conn.execute("SELECT COUNT(*) FROM style_analyses").fetchone()[0],
                "scripts": conn.execute("SELECT COUNT(*) FROM generated_scripts").fetchone()[0],
                "scripts_sent": conn.execute(
                    "SELECT COUNT(*) FROM generated_scripts WHERE sent_to_telegram=1"
                ).fetchone()[0],
            }

    # ------------------------------------------------------------------ #
    #  Internal                                                             #
    # ------------------------------------------------------------------ #

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
