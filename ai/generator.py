"""
YouTube Clone AI — Script Generator
DHD Data | Clients First. Perfection Always.

Generates new video scripts cloned from a channel's style DNA.
"""
import os
import json
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)


SCRIPT_GEN_PROMPT = """You are a master YouTube scriptwriter who can perfectly replicate any creator's style.

CHANNEL STYLE DNA:
{style_dna}

TASK: Write a complete YouTube video script about the following topic:
TOPIC: {topic}
VIDEO LENGTH TARGET: {length} minutes
ADDITIONAL INSTRUCTIONS: {instructions}

Match the channel's style EXACTLY:
- Use their exact tone: {tone}
- Apply their hook formula: {hook_formula}
- Follow their content structure: {structure}
- Use their signature phrases naturally
- Match their pacing and energy
- Include CTAs in their style

OUTPUT FORMAT:
Return a JSON object with:
{{
  "title": "string - video title using their title formula",
  "title_alternatives": ["2 alternative title options"],
  "hook": "string - opening hook (first 30 seconds)",
  "script": "string - full script with [SECTION] markers",
  "description": "string - YouTube description in their style",
  "tags": ["list of 10-15 tags"],
  "thumbnail_idea": "string - thumbnail concept description",
  "cta": "string - call to action",
  "estimated_duration": "string - e.g. '8-10 minutes'"
}}

Return only valid JSON, no markdown fences."""


HOOK_GEN_PROMPT = """Generate 5 different video hooks in this creator's exact style.

CHANNEL STYLE DNA:
{style_dna}

TOPIC: {topic}

The hooks must:
- Match tone: {tone}
- Follow hook formula: {hook_formula}
- Be 2-4 sentences each
- Create immediate curiosity or urgency

Return JSON:
{{
  "hooks": [
    {{"type": "string", "hook": "string"}},
    ...
  ]
}}
Return only valid JSON."""


TITLE_GEN_PROMPT = """Generate 10 YouTube video titles for this topic using the channel's exact title formula.

CHANNEL STYLE DNA:
Title formulas: {title_formulas}
Power words: {power_words}

TOPIC: {topic}

Return JSON:
{{
  "titles": ["list of 10 titles"]
}}
Return only valid JSON."""


class ScriptGenerator:
    """
    Generates YouTube scripts cloned from a channel's style DNA.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_script(
        self,
        style_dna: dict,
        topic: str,
        length_minutes: int = 10,
        instructions: str = "",
    ) -> Optional[dict]:
        """
        Generate a full video script cloned from the channel's style.

        Args:
            style_dna: output from StyleAnalyzer.analyze_channel()
            topic: what the video should be about
            length_minutes: target video duration
            instructions: any extra creative direction

        Returns:
            dict with title, script, description, tags, etc.
        """
        voice = style_dna.get("channel_voice", {})
        hooks = style_dna.get("hook_patterns", {})
        structure = style_dna.get("content_structure", {})

        prompt = SCRIPT_GEN_PROMPT.format(
            style_dna=json.dumps(style_dna, indent=2)[:6000],
            topic=topic,
            length=length_minutes,
            instructions=instructions or "None",
            tone=voice.get("tone", "engaging"),
            hook_formula=hooks.get("hook_formula", "grab attention immediately"),
            structure=" > ".join(structure.get("section_flow", ["Hook", "Body", "CTA"])),
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = self._strip_code_blocks(response.content[0].text.strip())
            result = json.loads(raw)
            result["topic"] = topic
            result["style_source"] = style_dna.get("channel_voice", {}).get("tone", "")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in generate_script: {e}")
            return None
        except Exception as e:
            logger.error(f"generate_script failed: {e}")
            return None

    def generate_hooks(self, style_dna: dict, topic: str) -> list[dict]:
        """Generate 5 hook variations for a topic."""
        voice = style_dna.get("channel_voice", {})
        hooks = style_dna.get("hook_patterns", {})

        prompt = HOOK_GEN_PROMPT.format(
            style_dna=json.dumps(style_dna, indent=2)[:4000],
            topic=topic,
            tone=voice.get("tone", "engaging"),
            hook_formula=hooks.get("hook_formula", ""),
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = self._strip_code_blocks(response.content[0].text.strip())
            data = json.loads(raw)
            return data.get("hooks", [])
        except Exception as e:
            logger.error(f"generate_hooks failed: {e}")
            return []

    def generate_titles(self, style_dna: dict, topic: str) -> list[str]:
        """Generate 10 title variations for a topic."""
        title_patterns = style_dna.get("title_patterns", {})

        prompt = TITLE_GEN_PROMPT.format(
            title_formulas=json.dumps(title_patterns.get("title_formulas", [])),
            power_words=json.dumps(title_patterns.get("power_words", [])),
            topic=topic,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = self._strip_code_blocks(response.content[0].text.strip())
            data = json.loads(raw)
            return data.get("titles", [])
        except Exception as e:
            logger.error(f"generate_titles failed: {e}")
            return []

    def batch_generate(
        self,
        style_dna: dict,
        topics: list[str],
        length_minutes: int = 10,
    ) -> list[dict]:
        """Generate scripts for multiple topics (autonomous batch mode)."""
        results = []
        for topic in topics:
            logger.info(f"Generating script for: {topic}")
            script = self.generate_script(style_dna, topic, length_minutes)
            if script:
                results.append(script)
        return results

    # ------------------------------------------------------------------ #
    #  Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _strip_code_blocks(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return text.strip()
