# YouTube Clone AI

Clone any YouTube channel's style, automate script generation, and deliver content via Telegram — fully autonomous.

## What It Does

- **Reverse-engineers channel style** — scrapes videos, extracts transcripts, and uses Claude to build a Style DNA profile covering tone, hooks, structure, pacing, and topic clusters.
- **Generates production-ready scripts** — creates full YouTube scripts in the cloned channel's exact voice for any topic you provide, complete with titles, hooks, CTAs, tags, and thumbnail ideas.
- **Runs autonomously** — an APScheduler background scheduler scrapes channels, re-analyzes styles, batch-generates scripts, and delivers them directly to a Telegram chat on a configurable schedule — no manual intervention needed.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy the example environment file
cp .env.example .env

# 3. Fill in your credentials
#    Open .env and set at minimum:
#      ANTHROPIC_API_KEY=sk-ant-...
#    Optional (for Telegram delivery):
#      TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
#      TELEGRAM_CHAT_ID=-100123456789
```

## Running the App

```bash
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501` by default.

## Features

| Feature | Description |
|---|---|
| **Channel Analysis** | Scrapes video metadata and transcripts; Claude builds a Style DNA profile with a clone score (0–100) and letter grade. |
| **Script Generation** | Generates full scripts on any topic in the target channel's voice. Batch generation supported (up to 5 per run). |
| **Telegram Automation** | Every generated script can be automatically delivered to a Telegram chat with title, hook, CTA, tags, and duration. |
| **Autonomous Scheduling** | APScheduler runs scraping (every 6 h), style analysis (every 12 h), script generation (every 24 h), and daily stats summaries — all configurable from the UI. |
| **Multi-Channel Support** | Manage multiple channels simultaneously; each gets its own style analysis and independent generation queue. |
| **Job History** | Every automation job is logged to SQLite with status, timestamps, and error messages for full auditability. |

## Tech Stack

- **Frontend** — Streamlit (multi-page app)
- **AI** — Anthropic Claude API (`anthropic` SDK)
- **Database** — SQLite via the standard library (`sqlite3`)
- **Scheduling** — APScheduler (`BackgroundScheduler`)
- **Scraping** — yt-dlp, youtube-transcript-api
- **Notifications** — Telegram Bot API (`requests`)
- **Language** — Python 3.11+

## Project Structure

```
youtube_clone_ai/
├── streamlit_app.py          # Home / Dashboard (entry point)
├── pages/
│   ├── 1_Channels.py         # Channel management
│   ├── 2_Scripts.py          # Generated scripts library
│   ├── 3_Analysis.py         # Style DNA viewer
│   └── 4_Automation.py       # Scheduler config & job history
├── utils/
│   ├── database.py           # SQLite ORM layer
│   ├── scheduler.py          # AutomationScheduler (APScheduler)
│   └── telegram_utils.py     # TelegramNotifier
├── ai/
│   ├── analyzer.py           # StyleAnalyzer (Claude)
│   └── generator.py          # ScriptGenerator (Claude)
├── scrapers/
│   ├── youtube.py            # YouTubeScraper (yt-dlp)
│   └── transcript.py         # TranscriptExtractor
├── data/                     # SQLite database files (git-ignored)
├── requirements.txt
└── .env.example
```

---

DHD Data | Clients First. Perfection Always.
