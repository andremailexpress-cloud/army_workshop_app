"""
YouTube Clone AI — Script Generator Page
DHD Data | Clients First. Perfection Always.

Generate viral scripts cloned from any channel's style.
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
from ai.generator import ScriptGenerator

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Page config                                                         #
# ------------------------------------------------------------------ #

st.set_page_config(
    page_title="Script Generator — YouTube Clone AI",
    page_icon="✍️",
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
    .script-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f0f0f0;
        line-height: 1.25;
        margin-bottom: 0.5rem;
    }
    .hook-card {
        background: #1a2a3a;
        border: 1px solid #2a4a6a;
        border-left: 4px solid #3498db;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        margin-bottom: 0.7rem;
        color: #ccc;
        font-size: 0.9rem;
    }
    .hook-type-badge {
        display: inline-block;
        background: #1a3a5c;
        color: #7eb8f7;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 0.8rem;
        margin-bottom: 0.4rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .title-item {
        background: #1e1e2e;
        border: 1px solid #2a2a3e;
        border-radius: 6px;
        padding: 0.55rem 0.9rem;
        margin-bottom: 0.4rem;
        font-size: 0.9rem;
        color: #ddd;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .title-number {
        color: #556;
        font-weight: 700;
        min-width: 1.5rem;
    }
    .placeholder-box {
        background: #111824;
        border: 2px dashed #2a3a4a;
        border-radius: 12px;
        padding: 3rem 2rem;
        text-align: center;
        color: #445;
    }
    .history-item {
        background: #1a1a2a;
        border: 1px solid #2a2a3a;
        border-radius: 8px;
        padding: 0.6rem 0.9rem;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
    }
    .history-title {
        color: #ccc;
        font-weight: 600;
    }
    .history-meta {
        color: #555;
        font-size: 0.78rem;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
#  Session state                                                       #
# ------------------------------------------------------------------ #

if "generated_script" not in st.session_state:
    st.session_state.generated_script = None

if "generated_hooks" not in st.session_state:
    st.session_state.generated_hooks = []

if "generated_titles" not in st.session_state:
    st.session_state.generated_titles = []

if "generation_channel_id" not in st.session_state:
    st.session_state.generation_channel_id = None

if "generation_topic" not in st.session_state:
    st.session_state.generation_topic = ""

if "saved_script_id" not in st.session_state:
    st.session_state.saved_script_id = None

if "generating" not in st.session_state:
    st.session_state.generating = False

# ------------------------------------------------------------------ #
#  Resources (cached)                                                  #
# ------------------------------------------------------------------ #

@st.cache_resource
def get_db() -> Database:
    return Database(os.getenv("DB_PATH", "data/youtube_clone.db"))

db = get_db()

# ------------------------------------------------------------------ #
#  Header                                                              #
# ------------------------------------------------------------------ #

st.title("Script Generator")
st.markdown(
    "<p class='page-subtitle'>Generate viral scripts cloned from any channel's style</p>",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ #
#  Load channels                                                       #
# ------------------------------------------------------------------ #

channels = db.get_channels(active_only=True)

if not channels:
    st.info(
        "No channels found. Add channels on the **Channel Manager** page first, "
        "then run a Style DNA analysis before generating scripts."
    )
    st.stop()

channel_map = {ch["name"]: ch["channel_id"] for ch in channels}
channel_names = list(channel_map.keys())

# ================================================================== #
#  Two-column layout: sidebar panel + main                            #
# ================================================================== #

sidebar_col, main_col = st.columns([1, 2.2], gap="large")

# ------------------------------------------------------------------ #
#  LEFT: Generation controls                                           #
# ------------------------------------------------------------------ #

with sidebar_col:
    st.markdown("### Generation Settings")

    selected_channel_name = st.selectbox(
        "Channel Style to Clone",
        options=channel_names,
        help="Scripts will be written in this channel's exact style.",
    )
    selected_channel_id = channel_map[selected_channel_name]

    # Check if analysis exists
    latest_analysis = db.get_latest_analysis(selected_channel_id)
    if not latest_analysis:
        st.warning(
            f"No Style DNA analysis for **{selected_channel_name}** yet. "
            "Go to the Style DNA page and run analysis first."
        )

    st.markdown("---")

    topic_1 = st.text_input(
        "What's the video about?",
        placeholder="e.g. How to make $10K/month with affiliate marketing",
        help="Main topic or idea for the video.",
    )

    with st.expander("Add more topics / angles"):
        topic_2 = st.text_area(
            "Secondary angle or sub-topic",
            placeholder="e.g. Focus on beginners who have no following yet",
            height=80,
        )
        topic_3 = st.text_area(
            "Additional context or hook idea",
            placeholder="e.g. Start with a shocking stat about passive income",
            height=80,
        )

    length_minutes = st.slider(
        "Target Video Length (minutes)",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
    )

    extra_instructions = st.text_area(
        "Extra Instructions (optional)",
        placeholder="e.g. Include 3 case studies, use humor, end with a strong CTA",
        height=100,
    )

    st.markdown("")

    generate_btn = st.button(
        "Generate Script",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.generating,
    )

# ------------------------------------------------------------------ #
#  Generation logic                                                    #
# ------------------------------------------------------------------ #

def _build_full_topic(t1: str, t2: str, t3: str) -> str:
    parts = [t1.strip()]
    if t2.strip():
        parts.append(t2.strip())
    if t3.strip():
        parts.append(t3.strip())
    return "\n\n".join(parts)


def _do_generate(
    channel_id: str,
    channel_name: str,
    topic: str,
    length_minutes: int,
    instructions: str,
) -> bool:
    """Run all three generation calls and store results in session state."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("ANTHROPIC_API_KEY is not set. Cannot generate scripts.")
        return False

    analysis_row = db.get_latest_analysis(channel_id)
    if not analysis_row:
        st.error(
            f"No Style DNA analysis found for **{channel_name}**. "
            "Run analysis on the Style DNA page first."
        )
        return False

    style_dna = analysis_row["analysis"]
    generator = ScriptGenerator(api_key=api_key)

    progress = st.progress(0, text="Generating full script...")
    try:
        script_result = generator.generate_script(
            style_dna=style_dna,
            topic=topic,
            length_minutes=length_minutes,
            instructions=instructions or "",
        )
        if not script_result:
            st.error("Script generation failed. Check your API key and try again.")
            progress.empty()
            return False

        progress.progress(50, text="Generating hook variations...")
        hooks = generator.generate_hooks(style_dna=style_dna, topic=topic)

        progress.progress(80, text="Generating title bank...")
        titles = generator.generate_titles(style_dna=style_dna, topic=topic)

        progress.progress(100, text="Done!")
        progress.empty()

        st.session_state.generated_script = script_result
        st.session_state.generated_hooks = hooks
        st.session_state.generated_titles = titles
        st.session_state.generation_channel_id = channel_id
        st.session_state.generation_topic = topic
        st.session_state.saved_script_id = None
        return True

    except Exception as exc:
        logger.error(f"Generation error: {exc}", exc_info=True)
        st.error(f"Generation failed: {exc}")
        progress.empty()
        return False


if generate_btn:
    if not topic_1.strip():
        with main_col:
            st.error("Please enter a topic for the video before generating.")
    else:
        st.session_state.generating = True
        full_topic = _build_full_topic(topic_1, topic_2 if 'topic_2' in dir() else "", topic_3 if 'topic_3' in dir() else "")
        with main_col:
            success = _do_generate(
                channel_id=selected_channel_id,
                channel_name=selected_channel_name,
                topic=full_topic,
                length_minutes=length_minutes,
                instructions=extra_instructions,
            )
        st.session_state.generating = False
        if success:
            st.rerun()

# ================================================================== #
#  MAIN AREA: Results                                                  #
# ================================================================== #

with main_col:

    script_data = st.session_state.generated_script

    # ---------------------------------------------------------------- #
    #  Placeholder when nothing generated yet                           #
    # ---------------------------------------------------------------- #

    if script_data is None:
        st.markdown(
            "<div class='placeholder-box'>"
            "<div style='font-size:3rem;margin-bottom:0.8rem;'>✍️</div>"
            "<div style='font-size:1.1rem;color:#667;font-weight:600;margin-bottom:0.6rem;'>"
            "Your script will appear here</div>"
            "<div style='font-size:0.88rem;color:#445;'>"
            "Select a channel, enter a topic, and click <strong style='color:#556;'>Generate Script</strong>."
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("**How it works**")
        how_col1, how_col2, how_col3 = st.columns(3)
        with how_col1:
            st.info("1. Add a YouTube channel and run Style DNA analysis")
        with how_col2:
            st.info("2. Enter your topic and configure video settings")
        with how_col3:
            st.info("3. Click Generate — Claude clones the style and writes the full script")

    # ---------------------------------------------------------------- #
    #  Generated content                                                 #
    # ---------------------------------------------------------------- #

    else:
        title = script_data.get("title") or "Untitled Script"
        script_body = script_data.get("script") or ""
        description = script_data.get("description") or ""
        tags = script_data.get("tags") or []
        thumbnail_idea = script_data.get("thumbnail_idea") or ""
        cta = script_data.get("cta") or ""
        estimated_duration = script_data.get("estimated_duration") or ""
        hook_text = script_data.get("hook") or ""

        # Title
        st.markdown(
            f"<div class='script-title'>{title}</div>",
            unsafe_allow_html=True,
        )

        meta_parts = []
        if estimated_duration:
            meta_parts.append(f"Duration: **{estimated_duration}**")
        if st.session_state.generation_channel_id:
            ch_name = next(
                (c["name"] for c in channels if c["channel_id"] == st.session_state.generation_channel_id),
                "Unknown",
            )
            meta_parts.append(f"Style: **{ch_name}**")
        if meta_parts:
            st.markdown(" | ".join(meta_parts))

        # Action buttons row
        action_row_col1, action_row_col2, action_row_col3 = st.columns([2, 2, 2])

        with action_row_col1:
            if st.button("Save to Library", type="primary", use_container_width=True):
                if st.session_state.saved_script_id is None:
                    try:
                        save_payload = dict(script_data)
                        save_payload["topic"] = st.session_state.generation_topic
                        script_id = db.save_script(
                            st.session_state.generation_channel_id,
                            save_payload,
                        )
                        st.session_state.saved_script_id = script_id
                        st.success(f"Script saved to library (ID: {script_id})")
                    except Exception as exc:
                        st.error(f"Save failed: {exc}")
                else:
                    st.info(f"Already saved (ID: {st.session_state.saved_script_id})")

        with action_row_col2:
            if st.button("Send to Telegram", use_container_width=True):
                notifier = TelegramNotifier()
                if not notifier.is_configured:
                    st.warning(
                        "Telegram is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID "
                        "in environment variables or on the Automation page."
                    )
                else:
                    sent = notifier.send_script(script_data, channel_name=ch_name if 'ch_name' in dir() else "")
                    if sent:
                        if st.session_state.saved_script_id:
                            db.mark_script_sent(st.session_state.saved_script_id)
                        st.success("Script sent to Telegram!")
                    else:
                        st.error("Failed to send to Telegram. Check your bot token and chat ID.")

        with action_row_col3:
            if st.button("Generate New Script", use_container_width=True):
                st.session_state.generated_script = None
                st.session_state.generated_hooks = []
                st.session_state.generated_titles = []
                st.session_state.saved_script_id = None
                st.rerun()

        st.markdown("---")

        # ------------------------------------------------------------ #
        #  Three tabs                                                    #
        # ------------------------------------------------------------ #

        tab_script, tab_hooks, tab_titles = st.tabs([
            "Full Script",
            "Hook Variations",
            "Title Bank",
        ])

        # ---- Full Script tab ---------------------------------------- #

        with tab_script:
            if hook_text:
                st.markdown("**Opening Hook**")
                st.markdown(
                    f"<div style='background:#1a2a1a;border-left:4px solid #2ecc71;"
                    f"padding:0.8rem 1rem;border-radius:0 8px 8px 0;color:#ccc;"
                    f"font-style:italic;margin-bottom:1rem;'>{hook_text}</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("**Full Script**")
            st.text_area(
                "script_content",
                value=script_body,
                height=400,
                label_visibility="collapsed",
                key="script_display",
            )

            # Download button
            st.download_button(
                label="Download Script (.txt)",
                data=f"TITLE: {title}\n\nHOOK:\n{hook_text}\n\nSCRIPT:\n{script_body}\n\nDESCRIPTION:\n{description}\n\nCTA:\n{cta}",
                file_name=f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

            if description:
                with st.expander("YouTube Description"):
                    st.text_area(
                        "description_content",
                        value=description,
                        height=150,
                        label_visibility="collapsed",
                    )

            if thumbnail_idea:
                with st.expander("Thumbnail Idea"):
                    st.info(thumbnail_idea)

            if cta:
                with st.expander("Call to Action"):
                    st.success(cta)

            if tags:
                with st.expander(f"Tags ({len(tags)})"):
                    st.markdown(", ".join(f"`{t}`" for t in tags))

        # ---- Hook Variations tab ------------------------------------- #

        with tab_hooks:
            hooks = st.session_state.generated_hooks

            if not hooks:
                st.info(
                    "No hook variations were generated. "
                    "Try regenerating the script to get hook alternatives."
                )
            else:
                st.markdown(
                    f"**{len(hooks)} Hook Variations** — optimized for {selected_channel_name}'s style"
                )
                st.markdown("---")
                for i, hook in enumerate(hooks, 1):
                    hook_type = hook.get("type") or "Hook"
                    hook_text_v = hook.get("hook") or ""

                    with st.container(border=True):
                        badge_col, _ = st.columns([2, 5])
                        with badge_col:
                            st.markdown(
                                f"<span class='hook-type-badge'>{hook_type}</span>",
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f"<div class='hook-card' style='margin:0;border:none;background:transparent;padding:0;'>"
                            f"{hook_text_v}</div>",
                            unsafe_allow_html=True,
                        )
                        # Copy via text area (Streamlit doesn't have native copy-to-clipboard)
                        with st.expander(f"Copy Hook {i}"):
                            st.text_area(
                                f"hook_copy_{i}",
                                value=hook_text_v,
                                height=80,
                                label_visibility="collapsed",
                                key=f"hook_ta_{i}",
                            )

        # ---- Title Bank tab ----------------------------------------- #

        with tab_titles:
            titles = st.session_state.generated_titles

            if not titles:
                st.info(
                    "No title variations were generated. "
                    "Try regenerating to get title alternatives."
                )
            else:
                st.markdown(f"**{len(titles)} Title Variations** for your topic")
                st.markdown("---")

                for i, t_text in enumerate(titles, 1):
                    col_num, col_title, col_copy = st.columns([0.4, 5, 1.2])
                    with col_num:
                        st.markdown(
                            f"<span style='color:#556;font-weight:700;font-size:1rem;'>{i}.</span>",
                            unsafe_allow_html=True,
                        )
                    with col_title:
                        st.markdown(
                            f"<div style='padding-top:0.2rem;font-size:0.92rem;color:#ddd;'>{t_text}</div>",
                            unsafe_allow_html=True,
                        )
                    with col_copy:
                        with st.popover("Copy"):
                            st.text_area(
                                f"title_copy_{i}",
                                value=t_text,
                                height=68,
                                label_visibility="collapsed",
                                key=f"title_ta_{i}",
                            )

# ================================================================== #
#  Generation History (collapsed)                                      #
# ================================================================== #

st.markdown("---")

with st.expander("Generation History (last 20 scripts)", expanded=False):
    history = db.get_scripts(limit=20)

    if not history:
        st.info("No scripts generated yet. Your history will appear here after you generate your first script.")
    else:
        ch_lookup = {ch["channel_id"]: ch["name"] for ch in channels}

        for item in history:
            item_ch = ch_lookup.get(item.get("channel_id", ""), item.get("channel_id", "Unknown"))
            item_title = item.get("title") or item.get("topic") or "Untitled"
            item_topic = item.get("topic") or ""
            item_date = (item.get("created_at") or "")[:16].replace("T", " ")
            item_status = item.get("status") or "draft"
            sent = item.get("sent_to_telegram", 0)

            status_color = "#2ecc71" if item_status == "published" else "#f0a500"
            sent_badge = (
                " <span style='color:#3498db;font-size:0.72rem;'>✈ Sent</span>"
                if sent
                else ""
            )

            st.markdown(
                f"<div class='history-item'>"
                f"<div class='history-title'>{item_title}{sent_badge}</div>"
                f"<div class='history-meta'>"
                f"Channel: <strong>{item_ch}</strong> &nbsp;|&nbsp; "
                f"Topic: {item_topic[:60]}{'...' if len(item_topic) > 60 else ''} &nbsp;|&nbsp; "
                f"<span style='color:{status_color};'>{item_status.upper()}</span> &nbsp;|&nbsp; "
                f"{item_date}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

# ------------------------------------------------------------------ #
#  Footer                                                              #
# ------------------------------------------------------------------ #

st.markdown(
    "<p style='text-align:center;color:#555;font-size:0.8rem;margin-top:1rem;'>"
    "DHD Data | Clients First. Perfection Always."
    "</p>",
    unsafe_allow_html=True,
)
