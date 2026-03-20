"""
YouTube Clone AI — Home / Dashboard
DHD Data | Clients First. Perfection Always.

Main entry point for the Streamlit multi-page application.
Displays live DB statistics, recent scripts, active channels,
quick-generate form, automation status, and onboarding when empty.
"""
import os
import sys
import logging
from datetime import datetime

import streamlit as st

# Ensure project root is on sys.path so utils/* are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.database import Database
from utils.telegram_utils import TelegramNotifier

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Page config                                                         #
# ------------------------------------------------------------------ #

st.set_page_config(
    page_title="YouTube Clone AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ #
#  Custom CSS                                                          #
# ------------------------------------------------------------------ #

st.markdown("""
<style>
    /* ---- global dark base ---- */
    [data-testid="stAppViewContainer"] {
        background-color: #0d0d14;
        color: #e0e0e0;
    }
    [data-testid="stSidebar"] {
        background-color: #12121e;
        border-right: 1px solid #1e1e2e;
    }

    /* ---- gradient hero header ---- */
    .hero-header {
        background: linear-gradient(135deg, #6c3fc9 0%, #c8344c 55%, #e67e22 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3rem;
        font-weight: 900;
        line-height: 1.1;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        color: #888;
        font-size: 1.1rem;
        margin-top: 0;
        margin-bottom: 1.8rem;
        letter-spacing: 0.03em;
    }

    /* ---- metric cards ---- */
    [data-testid="stMetric"] {
        background: #1a1a2e;
        border: 1px solid #2a2a3e;
        border-radius: 12px;
        padding: 1rem 1.2rem;
    }
    [data-testid="stMetricLabel"] { color: #999 !important; font-size: 0.8rem; }
    [data-testid="stMetricValue"] { color: #e0e0e0 !important; font-size: 1.7rem; font-weight: 700; }

    /* ---- section headers ---- */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e0e0e0;
        border-bottom: 2px solid #252535;
        padding-bottom: 0.4rem;
        margin-top: 1.4rem;
        margin-bottom: 1rem;
    }

    /* ---- script cards ---- */
    .script-card {
        background: #14142a;
        border: 1px solid #252545;
        border-left: 4px solid #7c3aed;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.7rem;
    }
    .script-card-title {
        font-size: 1rem;
        font-weight: 600;
        color: #ddd;
        margin-bottom: 0.2rem;
    }
    .script-card-meta {
        font-size: 0.78rem;
        color: #777;
    }

    /* ---- channel mini cards ---- */
    .channel-card {
        background: #16162a;
        border: 1px solid #252545;
        border-radius: 8px;
        padding: 0.6rem 0.9rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .channel-name {
        font-weight: 600;
        color: #ddd;
        font-size: 0.92rem;
    }
    .channel-meta {
        font-size: 0.75rem;
        color: #666;
    }

    /* ---- status badge ---- */
    .status-running {
        display: inline-block;
        background: #00c853;
        color: #000;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.15rem 0.6rem;
        border-radius: 1rem;
        letter-spacing: 0.06em;
    }
    .status-stopped {
        display: inline-block;
        background: #d50000;
        color: #fff;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.15rem 0.6rem;
        border-radius: 1rem;
        letter-spacing: 0.06em;
    }

    /* ---- onboarding steps ---- */
    .onboard-step {
        background: #1a1a2e;
        border: 1px solid #2a2a3e;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .onboard-num {
        font-size: 1.6rem;
        font-weight: 900;
        color: #7c3aed;
        margin-right: 0.5rem;
    }

    /* ---- footer ---- */
    .footer-text {
        text-align: center;
        color: #444;
        font-size: 0.78rem;
        margin-top: 2.5rem;
        padding-top: 1rem;
        border-top: 1px solid #1e1e2e;
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

# ------------------------------------------------------------------ #
#  Database initialisation                                             #
# ------------------------------------------------------------------ #

@st.cache_resource
def get_db() -> Database:
    return Database()


try:
    db = get_db()
    _db_ok = True
except Exception as _db_err:
    st.error(f"Database initialisation failed: {_db_err}")
    db = None
    _db_ok = False

# ------------------------------------------------------------------ #
#  Helper utilities                                                    #
# ------------------------------------------------------------------ #

TOPIC_PRESETS = [
    "Education", "Business", "Motivation", "Tech",
    "Finance", "Lifestyle", "Health", "Productivity",
    "Entrepreneurship", "Self-Improvement",
]


def _safe_stats() -> dict:
    default = {
        "channels": 0, "videos": 0, "transcripts": 0,
        "analyses": 0, "scripts": 0, "scripts_sent": 0,
    }
    if not _db_ok:
        return default
    try:
        return db.get_stats()
    except Exception:
        return default


def _safe_get_scripts(limit: int = 5) -> list[dict]:
    if not _db_ok:
        return []
    try:
        return db.get_scripts(limit=limit)
    except Exception:
        return []


def _safe_get_channels(active_only: bool = True) -> list[dict]:
    if not _db_ok:
        return []
    try:
        return db.get_channels(active_only=active_only)
    except Exception:
        return []


def _safe_get_latest_analysis(channel_id: str):
    if not _db_ok:
        return None
    try:
        return db.get_latest_analysis(channel_id)
    except Exception:
        return None


def _send_test_telegram() -> tuple[bool, str]:
    """Send a test Telegram message using saved environment credentials."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return False, "Telegram token or chat ID not configured. Set them in Automation settings."
    try:
        notifier = TelegramNotifier(token=token, chat_id=chat_id)
        sent = notifier.send_alert(
            "YouTube Clone AI test message — dashboard is live!"
        )
        if sent:
            return True, "Test message sent successfully."
        return False, "Telegram API returned an error. Check your token and chat ID."
    except Exception as exc:
        return False, f"Send failed: {exc}"


def _generate_quick_script(channel_id: str, topic: str):
    """Trigger a single-channel generate job via the scheduler if running."""
    scheduler = st.session_state.get("scheduler_instance")
    if scheduler is None:
        st.warning("Automation scheduler is not running. Start it on the Automation page first.")
        return

    with st.spinner(f"Generating script on topic: {topic}..."):
        result = scheduler.run_now(channel_id=channel_id, job_type="generate")

    if result["success"]:
        st.success(f"Script generated. Check the Scripts page for the full output.")
    else:
        st.error(f"Generation failed: {result['message']}")


# ================================================================== #
#  HEADER                                                              #
# ================================================================== #

st.markdown(
    '<h1 class="hero-header">YouTube Clone AI</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="hero-subtitle">Clone ANY Channel. Automate Everything. Dominate.</p>',
    unsafe_allow_html=True,
)

# ================================================================== #
#  STATS ROW                                                           #
# ================================================================== #

stats = _safe_stats()
channels_list = _safe_get_channels(active_only=True)
is_db_empty = len(channels_list) == 0

sc1, sc2, sc3, sc4, sc5 = st.columns(5)
sc1.metric("Active Channels",      stats["channels"])
sc2.metric("Videos Scraped",       stats["videos"])
sc3.metric("Transcripts Extracted", stats["transcripts"])
sc4.metric("Analyses Done",        stats["analyses"])
sc5.metric("Scripts Generated",    stats["scripts"])

st.markdown("---")

# ================================================================== #
#  ONBOARDING (shown only when DB is empty)                           #
# ================================================================== #

if is_db_empty:
    st.markdown(
        '<div class="section-header">Welcome to YouTube Clone AI</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "No channels have been added yet. Follow the steps below to get started:"
    )

    steps = [
        (
            "1",
            "Add a Channel",
            "Go to the **Channels** page and paste any YouTube channel URL. "
            "The app will scrape its metadata immediately.",
        ),
        (
            "2",
            "Scrape Videos & Transcripts",
            "Use the **Scrape** button on the channel card to pull recent videos "
            "and extract their transcripts automatically.",
        ),
        (
            "3",
            "Analyse the Style",
            "Run the **Analyse** action to let Claude build a Style DNA profile "
            "of the channel — tone, hooks, structure, and topics.",
        ),
        (
            "4",
            "Generate Scripts",
            "With an analysis in place, open the **Scripts** page or use the "
            "Quick Generate panel on the right. Claude will write a full "
            "production-ready script in that channel's exact voice.",
        ),
        (
            "5",
            "Automate Everything",
            "Head to the **Automation** page, configure your Telegram bot, "
            "and click **Start Automation**. The scheduler will handle scraping, "
            "analysis, script generation, and Telegram delivery on autopilot.",
        ),
    ]

    for num, title, body in steps:
        st.markdown(
            f'<div class="onboard-step">'
            f'<span class="onboard-num">{num}</span>'
            f'<strong style="color:#ddd;">{title}</strong>'
            f'<p style="color:#888;margin:0.4rem 0 0 0;font-size:0.88rem;">{body}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

# ================================================================== #
#  MAIN CONTENT — 2 columns                                           #
# ================================================================== #

left_col, right_col = st.columns([2, 1], gap="large")

# ------------------------------------------------------------------ #
#  LEFT — Recent Scripts + Active Channels                            #
# ------------------------------------------------------------------ #

with left_col:

    # --- Recent Scripts ------------------------------------------- #
    st.markdown(
        '<div class="section-header">Recent Scripts</div>',
        unsafe_allow_html=True,
    )

    recent_scripts = _safe_get_scripts(limit=5)

    if recent_scripts:
        # Build a quick lookup for channel names
        channel_name_map: dict[str, str] = {
            ch["channel_id"]: ch["name"] for ch in _safe_get_channels(active_only=False)
        }

        for s in recent_scripts:
            ch_name = channel_name_map.get(s.get("channel_id", ""), s.get("channel_id", "Unknown"))
            title = s.get("title") or s.get("topic", "Untitled")
            topic = s.get("topic", "")
            created = (s.get("created_at") or "")[:10]
            preview = (s.get("script") or "")[:300]

            st.markdown(
                f'<div class="script-card">'
                f'<div class="script-card-title">{title}</div>'
                f'<div class="script-card-meta">'
                f'Topic: {topic} &nbsp;|&nbsp; Channel: {ch_name} &nbsp;|&nbsp; {created}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            with st.expander("View preview"):
                if preview:
                    st.write(preview + ("..." if len(s.get("script", "")) > 300 else ""))
                else:
                    st.write("No script content available.")
    else:
        st.info("No scripts generated yet. Add a channel and run the pipeline to get started.")

    # --- Active Channels ------------------------------------------ #
    st.markdown(
        '<div class="section-header">Active Channels</div>',
        unsafe_allow_html=True,
    )

    if channels_list:
        for ch in channels_list:
            last_scraped = (ch.get("last_scraped") or "Never")[:10]
            subs = ch.get("subscribers", 0)
            subs_str = f"{subs:,}" if subs else "—"
            analysis = _safe_get_latest_analysis(ch["channel_id"])
            grade_badge = (
                f'<span style="color:#7c3aed;font-weight:700;">Grade: {analysis["grade"]}</span>'
                if analysis
                else '<span style="color:#555;">No analysis</span>'
            )
            st.markdown(
                f'<div class="channel-card">'
                f'<div>'
                f'<div class="channel-name">{ch["name"]}</div>'
                f'<div class="channel-meta">'
                f'Subs: {subs_str} &nbsp;|&nbsp; Last scraped: {last_scraped} &nbsp;|&nbsp; {grade_badge}'
                f'</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No active channels. Use the Channels page to add one.")

# ------------------------------------------------------------------ #
#  RIGHT — Quick Generate + Automation Status + Telegram              #
# ------------------------------------------------------------------ #

with right_col:

    # --- Quick Generate ------------------------------------------- #
    st.markdown(
        '<div class="section-header">Quick Generate</div>',
        unsafe_allow_html=True,
    )

    with st.form("quick_generate_form"):
        channel_options = {ch["name"]: ch["channel_id"] for ch in channels_list}

        if channel_options:
            selected_channel_name = st.selectbox(
                "Channel",
                options=list(channel_options.keys()),
                help="Select the channel whose style you want to clone.",
            )
            topic_input = st.text_input(
                "Topic",
                placeholder="e.g. How to build passive income in 2025",
                help="Enter the specific topic for the script.",
            )
            gen_submitted = st.form_submit_button("Generate", type="primary")
        else:
            st.info("Add a channel first to enable quick generation.")
            gen_submitted = False
            selected_channel_name = None
            topic_input = ""

    if gen_submitted and selected_channel_name and topic_input:
        channel_id = channel_options[selected_channel_name]
        _generate_quick_script(channel_id=channel_id, topic=topic_input)
    elif gen_submitted:
        if not selected_channel_name:
            st.warning("Please select a channel.")
        if not topic_input:
            st.warning("Please enter a topic.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Automation Status ---------------------------------------- #
    st.markdown(
        '<div class="section-header">Automation Status</div>',
        unsafe_allow_html=True,
    )

    is_running = st.session_state.get("scheduler_running", False)
    scheduler_instance = st.session_state.get("scheduler_instance")

    if is_running:
        st.markdown(
            '<span class="status-running">&#9654; RUNNING</span>',
            unsafe_allow_html=True,
        )
        if scheduler_instance:
            try:
                status = scheduler_instance.get_status()
                jobs = status.get("jobs", {})
                if jobs:
                    next_times = [
                        j["next_run"][:16].replace("T", " ")
                        for j in jobs.values()
                        if j.get("next_run")
                    ]
                    if next_times:
                        st.caption(f"Next job: {min(next_times)} UTC")
            except Exception:
                pass
    else:
        st.markdown(
            '<span class="status-stopped">&#9632; STOPPED</span>',
            unsafe_allow_html=True,
        )
        st.caption("Go to the Automation page to start the scheduler.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Send Test Telegram --------------------------------------- #
    st.markdown(
        '<div class="section-header">Telegram</div>',
        unsafe_allow_html=True,
    )

    token_configured = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    chat_configured = bool(os.getenv("TELEGRAM_CHAT_ID"))

    if token_configured and chat_configured:
        st.caption("Bot and chat ID are configured.")
    else:
        st.caption(
            "Telegram not configured. "
            "Set token and chat ID on the Automation page."
        )

    if st.button("Send Test Telegram", use_container_width=True):
        success, msg = _send_test_telegram()
        if success:
            st.success(msg)
        else:
            st.error(msg)

# ================================================================== #
#  FOOTER                                                              #
# ================================================================== #

st.markdown(
    '<div class="footer-text">DHD Data | Clients First. Perfection Always.</div>',
    unsafe_allow_html=True,
)
