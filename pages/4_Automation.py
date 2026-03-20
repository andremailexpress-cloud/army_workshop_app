"""
YouTube Clone AI — Automation Page
DHD Data | Clients First. Perfection Always.

Autonomous operation configuration and monitoring.
"""
import os
import sys
import logging
from datetime import datetime

import streamlit as st

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import Database
from utils.telegram_utils import TelegramNotifier

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Page config                                                         #
# ------------------------------------------------------------------ #

st.set_page_config(
    page_title="Automation — YouTube Clone AI",
    page_icon="⚙️",
    layout="wide",
)

# ------------------------------------------------------------------ #
#  CSS                                                                 #
# ------------------------------------------------------------------ #

st.markdown("""
<style>
    .status-badge-running {
        display: inline-block;
        background: linear-gradient(135deg, #00c853, #00e676);
        color: #fff;
        font-size: 1.4rem;
        font-weight: 700;
        padding: 0.45rem 1.4rem;
        border-radius: 2rem;
        letter-spacing: 0.08em;
        box-shadow: 0 2px 12px rgba(0,200,83,0.35);
    }
    .status-badge-stopped {
        display: inline-block;
        background: linear-gradient(135deg, #d50000, #ff1744);
        color: #fff;
        font-size: 1.4rem;
        font-weight: 700;
        padding: 0.45rem 1.4rem;
        border-radius: 2rem;
        letter-spacing: 0.08em;
        box-shadow: 0 2px 12px rgba(213,0,0,0.35);
    }
    .section-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #e0e0e0;
        border-bottom: 2px solid #333;
        padding-bottom: 0.4rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .channel-trigger-card {
        background: #1e1e2e;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }
    .telegram-msg-card {
        background: #1a2a1a;
        border-left: 3px solid #00c853;
        padding: 0.6rem 0.9rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.5rem;
        font-size: 0.85rem;
        color: #ccc;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
#  Session state initialisation                                        #
# ------------------------------------------------------------------ #

if "scheduler_running" not in st.session_state:
    st.session_state.scheduler_running = False

if "scheduler_instance" not in st.session_state:
    st.session_state.scheduler_instance = None

if "automation_settings" not in st.session_state:
    st.session_state.automation_settings = {
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        "scrape_frequency": "Every 6h",
        "generation_frequency": "Every 12h",
        "max_scripts_per_run": 3,
        "auto_topics": ["Education", "Business", "Motivation"],
    }

# ------------------------------------------------------------------ #
#  DB                                                                  #
# ------------------------------------------------------------------ #

@st.cache_resource
def get_db() -> Database:
    return Database()

db = get_db()

# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

TOPIC_CATEGORIES = [
    "Education", "Business", "Motivation", "Tech",
    "Finance", "Lifestyle", "Health",
]

SCRAPE_FREQ_MAP = {
    "Every 6h": 6,
    "Every 12h": 12,
    "Daily": 24,
}

GEN_FREQ_MAP = {
    "Every 12h": 12,
    "Daily": 24,
    "Weekly": 168,
}


def _get_scheduler_or_none():
    """Return cached scheduler instance if it exists."""
    return st.session_state.get("scheduler_instance")


def _start_scheduler(settings: dict):
    """Instantiate and start the AutomationScheduler."""
    try:
        from utils.scheduler import AutomationScheduler
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("ANTHROPIC_API_KEY is not set in environment. Cannot start scheduler.")
            return False

        scheduler = AutomationScheduler(
            api_key=api_key,
            telegram_token=settings.get("telegram_token") or None,
            telegram_chat_id=settings.get("telegram_chat_id") or None,
        )
        scheduler.start()
        st.session_state.scheduler_instance = scheduler
        st.session_state.scheduler_running = True
        return True
    except Exception as exc:
        st.error(f"Failed to start scheduler: {exc}")
        logger.error(f"Scheduler start error: {exc}", exc_info=True)
        return False


def _stop_scheduler():
    """Stop and clear the scheduler instance."""
    scheduler = _get_scheduler_or_none()
    if scheduler:
        try:
            scheduler.stop()
        except Exception as exc:
            logger.warning(f"Scheduler stop warning: {exc}")
    st.session_state.scheduler_instance = None
    st.session_state.scheduler_running = False


def _scripts_generated_today() -> int:
    try:
        with db._conn() as conn:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT COUNT(*) FROM generated_scripts WHERE created_at LIKE ?",
                (f"{today}%",),
            ).fetchone()
            return row[0] if row else 0
    except Exception:
        return 0


def _last_job_time() -> str:
    try:
        with db._conn() as conn:
            row = conn.execute(
                "SELECT finished_at FROM automation_jobs "
                "WHERE finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1"
            ).fetchone()
            if row and row[0]:
                return row[0][:16].replace("T", " ")
            return "Never"
    except Exception:
        return "Never"


def _next_run_time() -> str:
    scheduler = _get_scheduler_or_none()
    if scheduler and st.session_state.scheduler_running:
        try:
            status = scheduler.get_status()
            jobs = status.get("jobs", {})
            times = []
            for job_info in jobs.values():
                nxt = job_info.get("next_run")
                if nxt:
                    times.append(nxt[:16].replace("T", " "))
            if times:
                return min(times)
        except Exception:
            pass
    return "—"


def _get_recent_automation_jobs(limit: int = 20) -> list[dict]:
    try:
        with db._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM automation_jobs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def _get_last_telegram_scripts(limit: int = 5) -> list[dict]:
    try:
        with db._conn() as conn:
            rows = conn.execute("""
                SELECT gs.title, gs.topic, gs.channel_id, gs.created_at,
                       c.name AS channel_name
                FROM generated_scripts gs
                LEFT JOIN channels c ON gs.channel_id = c.channel_id
                WHERE gs.sent_to_telegram = 1
                ORDER BY gs.created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def _run_channel_pipeline(channel_id: str, channel_name: str):
    """Run scrape + analyze + generate for a single channel."""
    scheduler = _get_scheduler_or_none()
    if scheduler is None:
        st.warning("Scheduler not running. Start automation first to use manual triggers.")
        return

    with st.spinner(f"Running full pipeline for {channel_name}..."):
        for job_type in ("scrape", "analyze", "generate"):
            result = scheduler.run_now(channel_id=channel_id, job_type=job_type)
            if result["success"]:
                st.success(f"{job_type.capitalize()} completed for {channel_name}.")
            else:
                st.error(f"{job_type.capitalize()} failed for {channel_name}: {result['message']}")
                break


def _run_all_jobs():
    """Trigger every active channel through the full pipeline."""
    scheduler = _get_scheduler_or_none()
    if scheduler is None:
        st.warning("Scheduler not running. Start automation first to use manual triggers.")
        return

    channels = db.get_channels(active_only=True)
    if not channels:
        st.info("No active channels found.")
        return

    for ch in channels:
        _run_channel_pipeline(ch["channel_id"], ch["name"])

    st.success(f"All jobs completed for {len(channels)} channel(s).")


# ================================================================== #
#  RENDER                                                              #
# ================================================================== #

# -- Header --------------------------------------------------------- #
st.title("Automation")
st.markdown(
    "<p style='color:#888;font-size:1.05rem;margin-top:-0.5rem;'>"
    "Set it and forget it — autonomous content generation"
    "</p>",
    unsafe_allow_html=True,
)

# -- Status badge --------------------------------------------------- #
is_running = st.session_state.scheduler_running
badge_html = (
    '<span class="status-badge-running">&#9654; RUNNING</span>'
    if is_running
    else '<span class="status-badge-stopped">&#9632; STOPPED</span>'
)
st.markdown(f"**Scheduler Status:** {badge_html}", unsafe_allow_html=True)

st.markdown("---")

# -- Top metrics ---------------------------------------------------- #
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Scripts Generated Today", _scripts_generated_today())
with col2:
    st.metric("Last Run", _last_job_time())
with col3:
    st.metric("Next Run", _next_run_time())

st.markdown("---")

# -- Start / Stop toggle -------------------------------------------- #
toggle_label = "Stop Automation" if is_running else "Start Automation"
toggle_type = "primary" if not is_running else "secondary"

if st.button(toggle_label, type=toggle_type, use_container_width=False):
    if is_running:
        _stop_scheduler()
        st.success("Automation stopped.")
        st.rerun()
    else:
        settings = st.session_state.automation_settings
        started = _start_scheduler(settings)
        if started:
            st.success("Automation started. Scheduler is now running in the background.")
            st.rerun()

st.markdown("---")

# ================================================================== #
#  Settings section                                                    #
# ================================================================== #

st.markdown('<div class="section-header">Settings</div>', unsafe_allow_html=True)

with st.form("automation_settings_form"):
    saved = st.session_state.automation_settings

    col_a, col_b = st.columns(2)

    with col_a:
        telegram_token = st.text_input(
            "Telegram Bot Token",
            value=saved.get("telegram_token", ""),
            type="password",
            placeholder="123456:ABC-DEF...",
            help="BotFather token. Leave empty to disable Telegram notifications.",
        )
        scrape_frequency = st.selectbox(
            "Scraping Frequency",
            options=list(SCRAPE_FREQ_MAP.keys()),
            index=list(SCRAPE_FREQ_MAP.keys()).index(
                saved.get("scrape_frequency", "Every 6h")
            ),
        )
        max_scripts = st.number_input(
            "Max Scripts per Channel per Run",
            min_value=1,
            max_value=5,
            value=int(saved.get("max_scripts_per_run", 3)),
        )

    with col_b:
        telegram_chat_id = st.text_input(
            "Telegram Chat ID",
            value=saved.get("telegram_chat_id", ""),
            placeholder="-100123456789",
            help="Your chat or group ID. Use @userinfobot to find it.",
        )
        generation_frequency = st.selectbox(
            "Generation Frequency",
            options=list(GEN_FREQ_MAP.keys()),
            index=list(GEN_FREQ_MAP.keys()).index(
                saved.get("generation_frequency", "Every 12h")
            ),
        )
        auto_topics = st.multiselect(
            "Auto-Topics",
            options=TOPIC_CATEGORIES,
            default=saved.get("auto_topics", ["Education", "Business", "Motivation"]),
            help="Topics used when the scheduler auto-generates scripts.",
        )

    save_clicked = st.form_submit_button("Save Settings", type="primary")

if save_clicked:
    st.session_state.automation_settings = {
        "telegram_token": telegram_token,
        "telegram_chat_id": telegram_chat_id,
        "scrape_frequency": scrape_frequency,
        "generation_frequency": generation_frequency,
        "max_scripts_per_run": int(max_scripts),
        "auto_topics": auto_topics,
    }
    # Persist token/chat_id to env vars for sub-modules that read os.getenv
    if telegram_token:
        os.environ["TELEGRAM_BOT_TOKEN"] = telegram_token
    if telegram_chat_id:
        os.environ["TELEGRAM_CHAT_ID"] = telegram_chat_id

    st.success("Settings saved.")

st.markdown("---")

# ================================================================== #
#  Manual Triggers section                                             #
# ================================================================== #

st.markdown('<div class="section-header">Manual Triggers</div>', unsafe_allow_html=True)

if st.button("Run All Jobs Now", type="primary"):
    _run_all_jobs()

st.markdown("**Per-Channel Actions:**")

channels = db.get_channels(active_only=True)

if not channels:
    st.info("No active channels yet. Add channels on the Channels page first.")
else:
    for ch in channels:
        with st.container():
            st.markdown(
                f'<div class="channel-trigger-card">'
                f'<strong>{ch["name"]}</strong>'
                f'<span style="color:#888;font-size:0.82rem;margin-left:0.6rem;">'
                f'{ch["channel_id"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            btn_key = f"trigger_{ch['channel_id']}"
            if st.button(
                f"Scrape + Analyze + Generate — {ch['name']}",
                key=btn_key,
            ):
                _run_channel_pipeline(ch["channel_id"], ch["name"])

st.markdown("---")

# ================================================================== #
#  Recent Telegram Messages                                            #
# ================================================================== #

st.markdown('<div class="section-header">Last 5 Scripts Sent to Telegram</div>', unsafe_allow_html=True)

telegram_scripts = _get_last_telegram_scripts(limit=5)

if telegram_scripts:
    for msg in telegram_scripts:
        channel_name = msg.get("channel_name") or msg.get("channel_id", "Unknown")
        title = msg.get("title") or msg.get("topic", "Untitled")
        created = (msg.get("created_at") or "")[:16].replace("T", " ")
        st.markdown(
            f'<div class="telegram-msg-card">'
            f'<strong>{title}</strong><br>'
            f'<span style="color:#888;">Channel: {channel_name} &nbsp;|&nbsp; Sent: {created}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.info("No scripts have been sent to Telegram yet.")

st.markdown("---")

# ================================================================== #
#  Job History table                                                   #
# ================================================================== #

st.markdown('<div class="section-header">Job History (Last 20)</div>', unsafe_allow_html=True)

jobs = _get_recent_automation_jobs(limit=20)

if jobs:
    import pandas as pd

    df = pd.DataFrame(jobs)

    # Friendly column names
    rename_map = {
        "id": "ID",
        "channel_id": "Channel",
        "job_type": "Job Type",
        "status": "Status",
        "started_at": "Started",
        "finished_at": "Finished",
        "result": "Result",
        "error_msg": "Error",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Truncate result/error for readability
    for col in ("Result", "Error"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: (str(x)[:80] + "...") if x and len(str(x)) > 80 else x
            )

    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No automation jobs recorded yet. Jobs appear here once the scheduler runs.")

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#555;font-size:0.8rem;'>"
    "DHD Data | Clients First. Perfection Always."
    "</p>",
    unsafe_allow_html=True,
)
