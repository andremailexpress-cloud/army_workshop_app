"""
YouTube Clone AI — Style DNA Page
DHD Data | Clients First. Perfection Always.

Deep AI analysis of a channel's content fingerprint.
"""
import os
import sys
import logging
from datetime import datetime

import streamlit as st

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import Database
from ai.analyzer import StyleAnalyzer

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Page config                                                         #
# ------------------------------------------------------------------ #

st.set_page_config(
    page_title="Style DNA — YouTube Clone AI",
    page_icon="🧬",
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
    .dna-chip {
        display: inline-block;
        background: #1e3a5f;
        color: #7eb8f7;
        font-size: 0.82rem;
        font-weight: 600;
        padding: 0.25rem 0.7rem;
        border-radius: 1rem;
        margin: 0.2rem 0.15rem;
        border: 1px solid #2a5a8f;
    }
    .dna-chip-green {
        background: #1a3a1a;
        color: #6fcf7a;
        border-color: #2a5a2a;
    }
    .dna-chip-orange {
        background: #3a2a0a;
        color: #f0a500;
        border-color: #5a4a1a;
    }
    .dna-chip-purple {
        background: #2a1a3a;
        color: #c07af0;
        border-color: #4a2a6a;
    }
    .grade-badge {
        display: inline-block;
        font-size: 2.5rem;
        font-weight: 900;
        padding: 0.4rem 1.2rem;
        border-radius: 0.6rem;
        line-height: 1;
    }
    .grade-S { background: linear-gradient(135deg,#b8860b,#ffd700); color:#1a1a1a; }
    .grade-A { background: linear-gradient(135deg,#1a5c1a,#2ecc71); color:#fff; }
    .grade-B { background: linear-gradient(135deg,#1a3a5c,#3498db); color:#fff; }
    .grade-C { background: linear-gradient(135deg,#4a3a00,#f39c12); color:#fff; }
    .grade-D { background: linear-gradient(135deg,#5c1a1a,#e74c3c); color:#fff; }
    .flow-step {
        background: #1e2a3a;
        border: 1px solid #2a4a6a;
        border-radius: 8px;
        padding: 0.5rem 0.7rem;
        text-align: center;
        font-size: 0.82rem;
        color: #aac8e8;
        font-weight: 600;
    }
    .flow-arrow {
        text-align: center;
        color: #556;
        font-size: 1.2rem;
        padding-top: 0.6rem;
    }
    .hook-box {
        background: #1a2a1a;
        border-left: 4px solid #2ecc71;
        padding: 0.9rem 1.1rem;
        border-radius: 0 8px 8px 0;
        font-style: italic;
        color: #ccc;
        margin-bottom: 0.6rem;
    }
    .phrase-item {
        background: #1e1e2e;
        border: 1px solid #333;
        border-radius: 6px;
        padding: 0.4rem 0.8rem;
        margin-bottom: 0.4rem;
        font-size: 0.88rem;
        color: #ddd;
    }
    .section-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #666;
        letter-spacing: 0.08em;
        margin-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

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
    st.markdown("- 📺 Channels")
    st.markdown("- 🧬 **Style DNA** ← you are here")
    st.markdown("- ✍️ Script Generator")
    st.markdown("- ⚙️ Automation")
    st.markdown("---")
    stats = db.get_stats()
    st.metric("Channels", stats.get("channels", 0))
    st.metric("Analyses", stats.get("analyses", 0))

# ------------------------------------------------------------------ #
#  Header                                                              #
# ------------------------------------------------------------------ #

st.title("Style DNA")
st.markdown(
    "<p class='page-subtitle'>Deep AI analysis of your channel's content fingerprint</p>",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ #
#  Channel selector                                                    #
# ------------------------------------------------------------------ #

channels = db.get_channels(active_only=True)

if not channels:
    st.info(
        "No channels found. Go to the **Channel Manager** page to add your first YouTube channel."
    )
    st.stop()

channel_options = {ch["name"]: ch["channel_id"] for ch in channels}
channel_names = list(channel_options.keys())

header_col, reanalyze_col = st.columns([4, 1])
with header_col:
    selected_name = st.selectbox(
        "Select Channel",
        options=channel_names,
        label_visibility="collapsed",
    )

selected_channel_id = channel_options[selected_name]

# ------------------------------------------------------------------ #
#  Load analysis                                                       #
# ------------------------------------------------------------------ #

def _run_analysis(channel_id: str, channel_name: str):
    """Run and persist style analysis for the given channel."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("ANTHROPIC_API_KEY is not set. Cannot run AI analysis.")
        return

    transcripts = db.get_transcripts(channel_id)
    if not transcripts:
        st.error(
            "No transcripts found for this channel. "
            "Go to Channel Manager and re-scrape the channel first."
        )
        return

    with st.spinner(f"Analyzing {channel_name} — this may take 30-60 seconds..."):
        try:
            analyzer = StyleAnalyzer(api_key=api_key)
            analysis = analyzer.analyze_channel(transcripts)
            if not analysis:
                st.error("AI analysis returned no data. Check your API key and try again.")
                return
            score_data = analyzer.score_content(analysis)
            db.save_analysis(channel_id, analysis, score_data, videos_used=len(transcripts))
            st.success(
                f"Analysis complete — Score: {score_data['score']}/100 (Grade: {score_data['grade']})"
            )
            st.rerun()
        except Exception as exc:
            logger.error(f"Style analysis failed: {exc}", exc_info=True)
            st.error(f"Analysis failed: {exc}")


latest = db.get_latest_analysis(selected_channel_id)

with reanalyze_col:
    if st.button("Re-analyze", type="secondary", use_container_width=True):
        _run_analysis(selected_channel_id, selected_name)

# ------------------------------------------------------------------ #
#  No analysis yet                                                     #
# ------------------------------------------------------------------ #

if not latest:
    st.warning(f"No style analysis found for **{selected_name}** yet.")
    if st.button("Run Analysis Now", type="primary"):
        _run_analysis(selected_channel_id, selected_name)
    st.stop()

# ------------------------------------------------------------------ #
#  Parse analysis data                                                 #
# ------------------------------------------------------------------ #

analysis = latest.get("analysis", {})
db_score = latest.get("score", 0)
db_grade = latest.get("grade", "C")
videos_used = latest.get("videos_used", 0)
analyzed_at = (latest.get("created_at") or "")[:16].replace("T", " ")

# Safe getters with defaults
channel_voice = analysis.get("channel_voice", {})
hook_patterns = analysis.get("hook_patterns", {})
content_structure = analysis.get("content_structure", {})
topic_clusters = analysis.get("topic_clusters", {})
title_patterns = analysis.get("title_patterns", {})
uniqueness = analysis.get("uniqueness_score", {})
storytelling = analysis.get("storytelling", {})
cta_patterns = analysis.get("cta_patterns", {})
audience = analysis.get("audience", {})

# ------------------------------------------------------------------ #
#  Analysis metadata banner                                            #
# ------------------------------------------------------------------ #

st.markdown(
    f"<div style='font-size:0.82rem;color:#666;margin-bottom:1rem;'>"
    f"Last analyzed: <strong style='color:#aaa;'>{analyzed_at}</strong> &nbsp;|&nbsp; "
    f"Videos used: <strong style='color:#aaa;'>{videos_used}</strong>"
    f"</div>",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ #
#  Tabs                                                                #
# ------------------------------------------------------------------ #

tabs = st.tabs([
    "Channel Voice",
    "Hook Pattern",
    "Content Structure",
    "Topic Clusters",
    "Title Formulas",
    "Score & Grade",
])

# ================================================================== #
#  TAB 1: Channel Voice                                                #
# ================================================================== #

with tabs[0]:
    st.subheader("Channel Voice")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='section-label'>Tone</div>", unsafe_allow_html=True)
        tone = channel_voice.get("tone") or "Not detected"
        st.markdown(f"<span class='dna-chip'>{tone}</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Speaking Style</div>", unsafe_allow_html=True)
        speaking_style = channel_voice.get("speaking_style") or "Not detected"
        st.markdown(f"<span class='dna-chip dna-chip-green'>{speaking_style}</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Vocabulary Level</div>", unsafe_allow_html=True)
        vocab = channel_voice.get("vocabulary_level") or "Not detected"
        st.markdown(f"<span class='dna-chip dna-chip-orange'>{vocab}</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Point of View</div>", unsafe_allow_html=True)
        pov = channel_voice.get("pov") or "Not detected"
        st.markdown(f"<span class='dna-chip dna-chip-purple'>{pov}</span>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='section-label'>Personality Traits</div>", unsafe_allow_html=True)
        traits = channel_voice.get("personality_traits") or []
        if traits:
            chips = "".join(f"<span class='dna-chip'>{t}</span>" for t in traits)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Signature Phrases</div>", unsafe_allow_html=True)
        phrases = channel_voice.get("signature_phrases") or []
        if phrases:
            for phrase in phrases:
                st.markdown(
                    f"<div class='phrase-item'>\"{ phrase }\"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

# ================================================================== #
#  TAB 2: Hook Pattern                                                 #
# ================================================================== #

with tabs[1]:
    st.subheader("Hook Pattern")

    hook_formula = hook_patterns.get("hook_formula") or "No hook formula detected."
    st.markdown("**Hook Formula**")
    st.info(hook_formula)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("<div class='section-label'>Hook Types Used</div>", unsafe_allow_html=True)
        hook_types = hook_patterns.get("hook_types") or []
        if hook_types:
            chips = "".join(f"<span class='dna-chip'>{h}</span>" for h in hook_types)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        avg_len = hook_patterns.get("avg_hook_length") or "Unknown"
        st.metric("Average Hook Length", avg_len)

    with col_b:
        st.markdown("<div class='section-label'>Hook Examples</div>", unsafe_allow_html=True)
        examples = hook_patterns.get("hook_examples") or []
        if examples:
            for i, ex in enumerate(examples, 1):
                with st.expander(f"Hook Example {i}", expanded=(i == 1)):
                    st.markdown(
                        f"<div class='hook-box'>{ex}</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown("<span style='color:#666;'>No examples extracted</span>", unsafe_allow_html=True)

# ================================================================== #
#  TAB 3: Content Structure                                            #
# ================================================================== #

with tabs[2]:
    st.subheader("Content Structure")

    meta_col1, meta_col2, meta_col3 = st.columns(3)
    with meta_col1:
        fmt = content_structure.get("format") or "Unknown"
        st.metric("Format", fmt)
    with meta_col2:
        avg_sections = content_structure.get("avg_sections") or "?"
        st.metric("Avg Sections", avg_sections)
    with meta_col3:
        pacing = content_structure.get("pacing") or "Unknown"
        st.metric("Pacing", pacing)

    st.markdown("---")
    st.markdown("**Section Flow**")

    section_flow = content_structure.get("section_flow") or []
    if section_flow:
        # Render as horizontal flow with arrows
        num_steps = len(section_flow)
        # Build alternating step + arrow columns
        flow_cols = st.columns(num_steps * 2 - 1)
        for i, step in enumerate(section_flow):
            with flow_cols[i * 2]:
                st.markdown(
                    f"<div class='flow-step'>{step}</div>",
                    unsafe_allow_html=True,
                )
            if i < num_steps - 1:
                with flow_cols[i * 2 + 1]:
                    st.markdown(
                        "<div class='flow-arrow'>→</div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.markdown("<span style='color:#666;'>No flow data detected</span>", unsafe_allow_html=True)

    st.markdown("---")
    transition_style = content_structure.get("transition_style") or "Not detected"
    st.markdown(f"**Transition Style:** {transition_style}")

# ================================================================== #
#  TAB 4: Topic Clusters                                               #
# ================================================================== #

with tabs[3]:
    st.subheader("Topic Clusters")

    cluster_col1, cluster_col2 = st.columns(2)

    with cluster_col1:
        st.markdown("<div class='section-label'>Main Themes</div>", unsafe_allow_html=True)
        main_themes = topic_clusters.get("main_themes") or []
        if main_themes:
            chips = "".join(f"<span class='dna-chip'>{t}</span>" for t in main_themes)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Content Pillars</div>", unsafe_allow_html=True)
        pillars = topic_clusters.get("content_pillars") or []
        if pillars:
            for p in pillars:
                st.markdown(
                    f"<span class='dna-chip dna-chip-green'>{p}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

    with cluster_col2:
        st.markdown("<div class='section-label'>Sub-Topics</div>", unsafe_allow_html=True)
        sub_topics = topic_clusters.get("sub_topics") or []
        if sub_topics:
            chips = "".join(f"<span class='dna-chip dna-chip-purple'>{s}</span>" for s in sub_topics)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Trending Angles</div>", unsafe_allow_html=True)
        trending = topic_clusters.get("trending_angles") or []
        if trending:
            for angle in trending:
                st.markdown(
                    f"<span class='dna-chip dna-chip-orange'>{angle}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

    # Audience section
    st.markdown("---")
    st.markdown("**Audience Profile**")
    aud_col1, aud_col2, aud_col3 = st.columns(3)
    with aud_col1:
        demographic = audience.get("target_demographic") or "Not specified"
        st.markdown(f"**Target Demographic**\n\n{demographic}")
    with aud_col2:
        pain_points = audience.get("pain_points_addressed") or []
        st.markdown("**Pain Points Addressed**")
        for pp in pain_points:
            st.markdown(f"- {pp}")
        if not pain_points:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)
    with aud_col3:
        aspirations = audience.get("aspiration_targets") or []
        st.markdown("**Audience Aspirations**")
        for asp in aspirations:
            st.markdown(f"- {asp}")
        if not aspirations:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

# ================================================================== #
#  TAB 5: Title Formulas                                               #
# ================================================================== #

with tabs[4]:
    st.subheader("Title Formulas")

    tf_col1, tf_col2 = st.columns(2)

    with tf_col1:
        st.markdown("<div class='section-label'>Title Formulas</div>", unsafe_allow_html=True)
        formulas = title_patterns.get("title_formulas") or []
        if formulas:
            for i, formula in enumerate(formulas, 1):
                st.markdown(
                    f"<div class='phrase-item'><strong>{i}.</strong> {formula}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("<span style='color:#666;'>No formulas detected</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Number Usage</div>", unsafe_allow_html=True)
        number_usage = title_patterns.get("number_usage") or "Unknown"
        st.markdown(
            f"<span class='dna-chip dna-chip-orange'>{number_usage}</span>",
            unsafe_allow_html=True,
        )

        curiosity_gap = title_patterns.get("curiosity_gap", False)
        st.markdown(
            f"<br><div class='section-label'>Curiosity Gap</div>"
            f"<span class='dna-chip {'dna-chip-green' if curiosity_gap else ''}'>{'Yes' if curiosity_gap else 'No'}</span>",
            unsafe_allow_html=True,
        )

    with tf_col2:
        st.markdown("<div class='section-label'>Power Words</div>", unsafe_allow_html=True)
        power_words = title_patterns.get("power_words") or []
        if power_words:
            chips = "".join(f"<span class='dna-chip dna-chip-purple'>{w}</span>" for w in power_words)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Storytelling Approach</div>", unsafe_allow_html=True)
        story_structure = storytelling.get("story_structure") or "Not detected"
        st.markdown(f"<span class='dna-chip'>{story_structure}</span>", unsafe_allow_html=True)

        st.markdown("<br><div class='section-label'>Emotional Triggers</div>", unsafe_allow_html=True)
        triggers = storytelling.get("emotional_triggers") or []
        if triggers:
            chips = "".join(f"<span class='dna-chip dna-chip-orange'>{t}</span>" for t in triggers)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#666;'>None detected</span>", unsafe_allow_html=True)

# ================================================================== #
#  TAB 6: Score & Grade                                                #
# ================================================================== #

with tabs[5]:
    st.subheader("Clone Score & Grade")

    originality = uniqueness.get("originality", 0)
    production = uniqueness.get("production_value", 0)
    consistency = uniqueness.get("consistency", 0)
    notes = uniqueness.get("notes") or "No notes available."

    # Overall grade badge
    grade_css = f"grade-{db_grade}" if db_grade in ("S", "A", "B", "C", "D") else "grade-C"
    st.markdown(
        f"<div style='text-align:center;margin-bottom:1.5rem;'>"
        f"<div style='font-size:0.9rem;color:#888;margin-bottom:0.4rem;'>Overall Grade</div>"
        f"<span class='grade-badge {grade_css}'>{db_grade}</span>"
        f"<div style='font-size:1.5rem;font-weight:700;color:#fff;margin-top:0.5rem;'>{db_score}/100</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Score metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(
            "Originality",
            f"{originality}/10",
            help="How unique and original the channel's content is.",
        )
    with m2:
        st.metric(
            "Production Value",
            f"{production}/10",
            help="Perceived production quality based on content.",
        )
    with m3:
        st.metric(
            "Consistency",
            f"{consistency}/10",
            help="How consistent the channel's style and output is.",
        )

    st.markdown("---")
    st.markdown("**What Makes This Channel Stand Out**")
    st.markdown(
        f"<div style='background:#1e2a1e;border-left:4px solid #2ecc71;padding:0.9rem 1.1rem;"
        f"border-radius:0 8px 8px 0;color:#ccc;'>{notes}</div>",
        unsafe_allow_html=True,
    )

    # CTA patterns
    st.markdown("---")
    st.markdown("**CTA Patterns**")
    cta_col1, cta_col2 = st.columns(2)
    with cta_col1:
        cta_types = cta_patterns.get("cta_types") or []
        st.markdown("<div class='section-label'>CTA Types</div>", unsafe_allow_html=True)
        if cta_types:
            chips = "".join(f"<span class='dna-chip'>{c}</span>" for c in cta_types)
            st.markdown(chips, unsafe_allow_html=True)

        cta_placement = cta_patterns.get("cta_placement") or "Unknown"
        cta_style = cta_patterns.get("cta_style") or "Unknown"
        st.markdown(
            f"<br><div class='section-label'>Placement</div>"
            f"<span class='dna-chip dna-chip-orange'>{cta_placement}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='section-label'>Style</div>"
            f"<span class='dna-chip dna-chip-green'>{cta_style}</span>",
            unsafe_allow_html=True,
        )
    with cta_col2:
        cta_examples = cta_patterns.get("cta_examples") or []
        st.markdown("<div class='section-label'>CTA Examples</div>", unsafe_allow_html=True)
        if cta_examples:
            for ex in cta_examples:
                st.markdown(f"<div class='phrase-item'>\"{ex}\"</div>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#666;'>None extracted</span>", unsafe_allow_html=True)

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
