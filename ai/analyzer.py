"""
YouTube Clone AI — Style Analyzer
DHD Data | Clients First. Perfection Always.

Feeds transcripts to Claude and extracts the channel's complete
content DNA: tone, hooks, structure, topics, CTAs, pacing.
"""
import json
import os
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)


STYLE_ANALYSIS_PROMPT = """You are an expert content strategist and YouTube growth analyst.

Analyze the following YouTube video transcripts from a single channel and extract their complete CONTENT DNA.

TRANSCRIPTS:
{transcripts}

Return a detailed JSON analysis with exactly this structure:
{{
  "channel_voice": {{
    "tone": "string - e.g. 'energetic and hype', 'calm and educational', 'conversational and raw'",
    "personality_traits": ["list of 3-5 defining traits"],
    "speaking_style": "string - formal/casual/storytelling/instructional",
    "vocabulary_level": "string - simple/intermediate/technical",
    "signature_phrases": ["list of recurring phrases or expressions the creator uses"],
    "pov": "string - first person/second person/third person dominant"
  }},
  "hook_patterns": {{
    "hook_types": ["list of hook styles used - question/shock/story/promise/controversy"],
    "avg_hook_length": "string - short (under 15s) / medium (15-30s) / long (30s+)",
    "hook_examples": ["3 example openings extracted or derived from the transcripts"],
    "hook_formula": "string - describe the pattern used in 1-2 sentences"
  }},
  "content_structure": {{
    "format": "string - listicle/tutorial/story/interview/vlog/essay",
    "avg_sections": "number - typical number of main sections per video",
    "section_flow": ["ordered list of typical section types e.g. Hook > Problem > Story > Solution > CTA"],
    "transition_style": "string - how they move between topics",
    "pacing": "string - fast-cut/slow-burn/rhythmic/varied"
  }},
  "topic_clusters": {{
    "main_themes": ["list of 3-5 primary topic areas"],
    "sub_topics": ["list of 5-10 specific recurring sub-topics"],
    "content_pillars": ["list of 3 core content pillars that define the channel"],
    "trending_angles": ["2-3 angles that seem to get the most engagement based on context"]
  }},
  "cta_patterns": {{
    "cta_types": ["subscribe/like/comment/visit link/buy/follow"],
    "cta_placement": "string - early/middle/end/multiple",
    "cta_style": "string - hard sell/soft/embedded/none",
    "cta_examples": ["2-3 example CTAs from the content"]
  }},
  "storytelling": {{
    "uses_personal_stories": true,
    "story_structure": "string - e.g. 'hero journey', 'problem-agitation-solution', 'before-after'",
    "emotional_triggers": ["list of emotions frequently invoked"],
    "relatability_tactics": ["techniques used to connect with audience"]
  }},
  "title_patterns": {{
    "title_formulas": ["3-5 title structures used e.g. 'How I [Result] in [Timeframe]'"],
    "power_words": ["list of high-impact words frequently used in titles"],
    "number_usage": "string - frequent/occasional/rare",
    "curiosity_gap": true
  }},
  "audience": {{
    "target_demographic": "string - who this content is for",
    "pain_points_addressed": ["list of 3-5 problems the channel solves"],
    "aspiration_targets": ["list of 3-5 aspirations the audience has"]
  }},
  "uniqueness_score": {{
    "originality": 8,
    "production_value": 7,
    "consistency": 9,
    "notes": "string - what makes this channel stand out"
  }}
}}

Be specific, analytical, and extract real patterns from the actual transcripts. Do not be generic.
Return only valid JSON, no markdown.
"""


QUICK_ANALYSIS_PROMPT = """Analyze this single YouTube transcript and return key style insights as JSON:

TRANSCRIPT:
{transcript}

Return JSON with:
{{
  "hook": "string - first 2-3 sentences extracted",
  "tone": "string",
  "main_topics": ["list"],
  "cta": "string - any CTA found",
  "key_phrases": ["list of 5 signature phrases"]
}}
Return only valid JSON."""


class StyleAnalyzer:
    """
    Analyzes YouTube channel transcripts to extract style DNA.
    Uses Claude claude-sonnet-4-6 for deep content analysis.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_channel(self, transcripts: list[dict]) -> Optional[dict]:
        """
        Full channel DNA analysis from multiple video transcripts.

        Args:
            transcripts: list of {"title": str, "transcript": str, "video_id": str}

        Returns:
            dict with full style analysis, or None on failure
        """
        if not transcripts:
            return None

        # Build transcript block (cap at ~50k tokens to be safe)
        transcript_block = self._build_transcript_block(transcripts, max_chars=40000)

        prompt = STYLE_ANALYSIS_PROMPT.format(transcripts=transcript_block)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code blocks if present
            raw = self._strip_code_blocks(raw)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in analyze_channel: {e}")
            return None
        except Exception as e:
            logger.error(f"analyze_channel failed: {e}")
            return None

    def analyze_single_video(self, title: str, transcript: str) -> Optional[dict]:
        """Quick analysis of a single video transcript."""
        prompt = QUICK_ANALYSIS_PROMPT.format(transcript=transcript[:8000])
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = self._strip_code_blocks(response.content[0].text.strip())
            return json.loads(raw)
        except Exception as e:
            logger.error(f"analyze_single_video failed: {e}")
            return None

    def score_content(self, analysis: dict) -> dict:
        """
        Return a simple readability/virality score based on analysis.
        Mirrors the scoring pattern from DealScout's deal_scorer.
        """
        score = 50  # baseline
        reasons = []

        voice = analysis.get("channel_voice", {})
        hooks = analysis.get("hook_patterns", {})
        uniqueness = analysis.get("uniqueness_score", {})

        # Boost for strong hook formula
        if hooks.get("hook_formula"):
            score += 10
            reasons.append("Strong hook pattern detected")

        # Boost for signature phrases
        phrases = voice.get("signature_phrases", [])
        if len(phrases) >= 3:
            score += 10
            reasons.append(f"{len(phrases)} signature phrases identified")

        # Boost for high originality
        orig = uniqueness.get("originality", 5)
        if isinstance(orig, (int, float)) and orig >= 8:
            score += 15
            reasons.append("High originality score")

        # Boost for clear content pillars
        pillars = analysis.get("topic_clusters", {}).get("content_pillars", [])
        if len(pillars) >= 3:
            score += 10
            reasons.append("Clear content pillars defined")

        return {
            "score": min(score, 100),
            "grade": self._grade(score),
            "reasons": reasons,
        }

    # ------------------------------------------------------------------ #
    #  Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _build_transcript_block(self, transcripts: list[dict], max_chars: int) -> str:
        parts = []
        total = 0
        for i, t in enumerate(transcripts, 1):
            title = t.get("title", f"Video {i}")
            body = t.get("transcript", "")[:3000]  # cap per video
            chunk = f"--- VIDEO {i}: {title} ---\n{body}\n"
            if total + len(chunk) > max_chars:
                break
            parts.append(chunk)
            total += len(chunk)
        return "\n".join(parts)

    def _strip_code_blocks(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return text.strip()

    def _grade(self, score: int) -> str:
        if score >= 90: return "S"
        if score >= 80: return "A"
        if score >= 70: return "B"
        if score >= 60: return "C"
        return "D"
