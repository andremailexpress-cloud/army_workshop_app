"""
YouTube Clone AI — Channel Manager Page
DHD Data | Clients First. Perfection Always.

Add, track, and manage YouTube channels for style cloning.
"""
import os
import sys
import logging
from datetime import datetime

import streamlit as st

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import Database
from scrapers.youtube import YouTubeScraper
from ai.analyzer import StyleAnalyzer

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Page config                                                         #
# ------------------------------------------------------------------ #

st.set_page_config(
    page_title="Channel Manager — YouTube Clone AI",
    page_icon="📺",
    layout="wide",
)

# ------------------------------------------------------------------ #
#  CSS                                                                 #
# ------------------------------------------------------------------ #

st.markdown("""
<style>
    .page-subtitle {
        color: #888;
        font-size: 1.05rem;
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
    }
    .channel-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e0e0e0;
    }
    .channel-meta {
        font-size: 0.82rem;
        color: #888;
        margin-bottom: 0.5rem;
    }
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #ccc;
        border-bottom: 1px solid #333;
        padding-bottom: 0.4rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
#  Session state                                                       #
# ------------------------------------------------------------------ #

if "adding_channel" not in st.session_state:
    st.session_state.adding_channel = False

if "analyzing_channel" not in st.session_state:
    st.session_state.analyzing_channel = None

if "remove_confirm" not in st.session_state:
    st.session_state.remove_confirm = {}

# ------------------------------------------------------------------ #
#  Resources (cached)                                                  #
# ------------------------------------------------------------------ #

@st.cache_resource
def get_db() -> Database:
    return Database(os.getenv("DB_PATH", "data/youtube_clone.db"))

db = get_db()

# ------------------------------------------------------------------ #
#  Sidebar                                                             #
# ------------------------------------------------------------------ #

with st.sidebar:
    st.markdown("## YouTube Clone AI")
    st.markdown("---")
    st.markdown("**Navigation**")
    st.markdown("- 📺 **Channels** ← you are here")
    st.markdown("- 🧬 Style DNA")
    st.markdown("- ✍️ Script Generator")
    st.markdown("- ⚙️ Automation")
    st.markdown("---")
    stats = db.get_stats()
    st.markdown("**Quick Stats**")
    st.metric("Active Channels", stats.get("channels", 0))
    st.metric("Videos Indexed", stats.get("videos", 0))
    st.metric("Analyses Run", stats.get("analyses", 0))

# ------------------------------------------------------------------ #
#  Header                                                              #
# ------------------------------------------------------------------ #

st.title("Channel Manager")
st.markdown(
    "<p class='page-subtitle'>Add and track YouTube channels to clone</p>",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ #
#  Pipeline helpers                                                    #
# ------------------------------------------------------------------ #

def _run_add_channel(url: str, videos_to_analyze: int) -> tuple[bool, str]:
    """
    Scrape channel metadata + videos, fetch transcripts,
    and persist everything to the database.
    Returns (success, message).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    try:
        scraper = YouTubeScraper()
        progress = st.progress(0, text="Fetching channel metadata...")

        channel_data = scraper.get_channel_info(url)
        if not channel_data:
            return False, "Could not fetch channel info. Check the URL or @handle and try again."

        db.upsert_channel(channel_data)
        channel_id = channel_data["channel_id"]
        progress.progress(20, text="Channel metadata saved. Fetching videos...")

        videos = scraper.get_channel_videos(channel_id, limit=videos_to_analyze)
        if not videos:
            return False, "Channel found but no videos could be retrieved."

        for v in videos:
            db.upsert_video(v)
        progress.progress(50, text=f"{len(videos)} videos indexed. Fetching transcripts...")

        transcript_count = 0
        for i, video in enumerate(videos):
            try:
                transcript = scraper.get_transcript(video["video_id"])
                if transcript:
                    db.save_transcript(video["video_id"], channel_id, transcript)
                    transcript_count += 1
            except Exception as exc:
                logger.warning(f"Transcript fetch failed for {video['video_id']}: {exc}")
            pct = 50 + int((i + 1) / len(videos) * 40)
            progress.progress(pct, text=f"Transcripts: {transcript_count}/{i+1} videos processed...")

        progress.progress(100, text="Done!")
        return True, (
            f"Successfully added **{channel_data['name']}** — "
            f"{len(videos)} videos indexed, {transcript_count} transcripts saved."
        )
    except Exception as exc:
        logger.error(f"add_channel failed: {exc}", exc_info=True)
        return False, f"An error occurred: {exc}"


def _run_analyze_channel(channel_id: str, channel_name: str) -> tuple[bool, str]:
    """
    Run StyleAnalyzer on stored transcripts and persist the analysis.
    Returns (success, message).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return False, "ANTHROPIC_API_KEY is not set. Cannot run AI analysis."

    try:
        transcripts = db.get_transcripts(channel_id)
        if not transcripts:
            return False, "No transcripts found for this channel. Add the channel first to index videos."

        analyzer = StyleAnalyzer(api_key=api_key)
        analysis = analyzer.analyze_channel(transcripts)
        if not analysis:
            return False, "AI analysis returned no results. Check your API key and try again."

        score_data = analyzer.score_content(analysis)
        db.save_analysis(channel_id, analysis, score_data, videos_used=len(transcripts))
        return True, (
            f"Analysis complete for **{channel_name}** — "
            f"Score: {score_data['score']}/100 (Grade: {score_data['grade']})"
        )
    except Exception as exc:
        logger.error(f"analyze_channel failed: {exc}", exc_info=True)
        return False, f"Analysis failed: {exc}"


# ================================================================== #
#  Main layout — two columns                                           #
# ================================================================== #

col_left, col_right = st.columns([1, 1.4], gap="large")

# ------------------------------------------------------------------ #
#  LEFT — Add New Channel                                              #
# ------------------------------------------------------------------ #

with col_left:
    st.markdown('<div class="section-title">Add New Channel</div>', unsafe_allow_html=True)

    with st.form("add_channel_form", clear_on_submit=True):
        channel_url = st.text_input(
            "YouTube URL or @handle",
            placeholder="https://youtube.com/@MrBeast  or  @mkbhd",
            help="Paste the full channel URL or just the @handle.",
        )
        videos_count = st.number_input(
            "Videos to analyze",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
            help="How many recent videos to scrape and analyze.",
        )
        submit = st.form_submit_button(
            "Add Channel & Start Analysis",
            type="primary",
            use_container_width=True,
        )

    if submit:
        if not channel_url.strip():
            st.error("Please enter a YouTube URL or @handle.")
        else:
            st.session_state.adding_channel = True
            with st.spinner("Connecting to YouTube..."):
                success, message = _run_add_channel(
                    channel_url.strip(), int(videos_count)
                )
            st.session_state.adding_channel = False
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.markdown("---")
    st.markdown("**Tips**")
    st.markdown(
        "- Use the full URL: `https://youtube.com/@handle`\n"
        "- Or just the handle: `@mkbhd`\n"
        "- More videos = richer style analysis\n"
        "- Analysis runs automatically after adding"
    )

# ------------------------------------------------------------------ #
#  RIGHT — Active Channels                                             #
# ------------------------------------------------------------------ #

with col_right:
    st.markdown('<div class="section-title">Active Channels</div>', unsafe_allow_html=True)

    channels = db.get_channels(active_only=True)

    if not channels:
        st.info(
            "No channels added yet.\n\n"
            "Use the form on the left to add your first YouTube channel. "
            "The app will scrape videos, extract transcripts, and build a Style DNA profile automatically."
        )
    else:
        for ch in channels:
            channel_id = ch["channel_id"]

            with st.container(border=True):
                # Channel header
                header_col, btn_col = st.columns([3, 1])
                with header_col:
                    st.markdown(
                        f"<div class='channel-name'>{ch.get('name', 'Unknown Channel')}</div>",
                        unsafe_allow_html=True,
                    )

                # Metadata row
                subscribers = ch.get("subscribers", 0)
                sub_display = (
                    f"{subscribers / 1_000_000:.1f}M"
                    if subscribers >= 1_000_000
                    else f"{subscribers / 1_000:.0f}K"
                    if subscribers >= 1_000
                    else str(subscribers)
                )
                video_count = ch.get("video_count", 0)
                last_scraped = ch.get("last_scraped") or ch.get("added_at", "")
                last_scraped_display = last_scraped[:10] if last_scraped else "Never"

                st.markdown(
                    f"<div class='channel-meta'>"
                    f"Subscribers: <strong>{sub_display}</strong> &nbsp;|&nbsp; "
                    f"Videos: <strong>{video_count}</strong> &nbsp;|&nbsp; "
                    f"Last scraped: <strong>{last_scraped_display}</strong>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Latest analysis score
                latest = db.get_latest_analysis(channel_id)
                if latest:
                    score = latest.get("score", 0)
                    grade = latest.get("grade", "?")
                    analyzed_at = (latest.get("created_at") or "")[:10]
                    st.markdown(
                        f"<span style='font-size:0.8rem;color:#aaa;'>"
                        f"Style DNA Score: <strong style='color:#7eb8f7;'>{score}/100 (Grade {grade})</strong>"
                        f" — analyzed {analyzed_at}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<span style='font-size:0.8rem;color:#f0a500;'>"
                        "No style analysis yet</span>",
                        unsafe_allow_html=True,
                    )

                # Action buttons
                action_col1, action_col2, action_col3 = st.columns([2, 2, 1])

                with action_col1:
                    analyze_key = f"analyze_{channel_id}"
                    if st.button(
                        "Analyze Now",
                        key=analyze_key,
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state.analyzing_channel = channel_id
                        with st.spinner(f"Running AI analysis for {ch['name']}..."):
                            ok, msg = _run_analyze_channel(channel_id, ch["name"])
                        st.session_state.analyzing_channel = None
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

                with action_col2:
                    rescrape_key = f"rescrape_{channel_id}"
                    if st.button(
                        "Re-scrape",
                        key=rescrape_key,
                        use_container_width=True,
                    ):
                        with st.spinner(f"Re-scraping {ch['name']}..."):
                            ok, msg = _run_add_channel(ch.get("url", ""), 10)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

                with action_col3:
                    remove_key = f"remove_{channel_id}"
                    confirm_key = f"confirm_{channel_id}"

                    if st.session_state.remove_confirm.get(channel_id):
                        if st.button(
                            "Confirm?",
                            key=confirm_key,
                            type="secondary",
                            use_container_width=True,
                        ):
                            db.delete_channel(channel_id)
                            st.session_state.remove_confirm[channel_id] = False
                            st.success(f"Removed {ch['name']}.")
                            st.rerun()
                    else:
                        if st.button(
                            "Remove",
                            key=remove_key,
                            use_container_width=True,
                        ):
                            st.session_state.remove_confirm[channel_id] = True
                            st.rerun()

# ------------------------------------------------------------------ #
#  Footer                                                              #
# ------------------------------------------------------------------ #

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#555;font-size:0.8rem;'>"
    "DHD Data | Clients First. Perfection Always."
    "</p>",
    unsafe_allow_html=True,
)
