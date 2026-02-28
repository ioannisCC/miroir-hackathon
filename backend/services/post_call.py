"""
backend/services/post_call.py

PostCallAnalyzer: reads a call transcript, extracts new behavioral signals,
updates the contact's profile in Supabase, returns a before/after delta.

This is the "profile updating live" moment on screen 2.
"""

import json
import re

import anthropic

from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are a behavioral analyst reviewing a completed collections call.

Extract new behavioral signals observed during this call.
Update scores only if the call provides clear evidence.
Be conservative — do not change scores without direct evidence.

Return JSON only. No markdown. No preamble.
""".strip()


class PostCallAnalyzer:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    def analyze(self, contact: dict, transcript: str) -> dict:
        """
        Analyze transcript against existing profile.
        Returns delta: what changed and why.
        """
        profile = contact.get("behavior_profile", {})

        prompt = f"""
CONTACT: {contact.get('name')}
EXISTING PROFILE SUMMARY: {profile.get('summary', 'None')}

CURRENT SCORES:
- follow_through_score: {profile.get('follow_through_score')}
- reply_speed_score: {profile.get('reply_speed_score')}
- pressure_score: {profile.get('pressure_score')}

CALL TRANSCRIPT:
{transcript}

Based on this call, extract new behavioral signals and determine if scores should update.

Return:
{{
  "outcome": "<paid_now|promise_to_pay|payment_plan_agreed|refused_engagement|no_answer|escalated_human|callback_scheduled|other>",
  "outcome_notes": "<what specifically happened>",
  "new_signals": [
    {{"signal": "<observation>", "severity": <0.0-1.0>, "source": "call_transcript"}}
  ],
  "score_updates": {{
    "follow_through_score": <new value 0.0-1.0 or null if no evidence>,
    "pressure_score": <new value or null>,
    "reply_speed_score": <new value or null>
  }},
  "score_reasoning": {{
    "follow_through_score": "<why this changed or null>",
    "pressure_score": "<why this changed or null>",
    "reply_speed_score": "<why this changed or null>"
  }},
  "summary_update": "<one sentence to append to profile summary based on this call, or null>"
}}
""".strip()

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as e:
            logger.error("Claude API error in post-call analysis: %s", e)
            raise

        if not response.content:
            raise ValueError("Claude returned empty response in post-call analysis")

        logger.info(
            "Post-call analysis — contact: %s input: %d output: %d tokens",
            contact.get("email"),
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        raw = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse post-call JSON: %s", e)
            raise ValueError(f"Invalid JSON from post-call analysis: {e}") from e

    def apply_delta(self, contact: dict, analysis: dict) -> dict:
        """
        Apply analysis results to the contact's profile.
        Returns the delta: before/after scores for dashboard display.
        """
        profile = contact.get("behavior_profile", {})

        # Capture before state
        before = {
            "follow_through_score": profile.get("follow_through_score"),
            "pressure_score": profile.get("pressure_score"),
            "reply_speed_score": profile.get("reply_speed_score"),
            "risk_indicator_count": len(profile.get("risk_indicators", [])),
        }

        # Apply score updates
        score_updates = analysis.get("score_updates", {})
        for field, value in score_updates.items():
            if value is not None:
                profile[field] = round(float(value), 2)

        # Merge new signals into risk_indicators
        new_signals = analysis.get("new_signals", [])
        existing = profile.get("risk_indicators", [])
        profile["risk_indicators"] = existing + new_signals

        # Append summary update
        summary_update = analysis.get("summary_update")
        if summary_update:
            existing_summary = profile.get("summary", "")
            profile["summary"] = f"{existing_summary} {summary_update}".strip()

        # Recompute trust and risk scores
        score_fields = [
            profile.get("follow_through_score"),
            profile.get("pressure_score"),
            profile.get("reply_speed_score"),
        ]
        valid = [s for s in score_fields if s is not None]
        trust_score = round(sum(valid) / len(valid), 2) if valid else contact.get("trust_score", 0.5)

        all_risks = profile.get("risk_indicators", [])
        if all_risks:
            total_sev = sum(
                r.get("severity", 0.5) if isinstance(r, dict) else 0.5
                for r in all_risks
            )
            risk_score = round(min(total_sev / 5.0, 1.0), 2)
        else:
            risk_score = contact.get("risk_score", 0.2)

        # Capture after state
        after = {
            "follow_through_score": profile.get("follow_through_score"),
            "pressure_score": profile.get("pressure_score"),
            "reply_speed_score": profile.get("reply_speed_score"),
            "risk_indicator_count": len(profile.get("risk_indicators", [])),
            "trust_score": trust_score,
            "risk_score": risk_score,
        }

        return {
            "updated_profile": profile,
            "trust_score": trust_score,
            "risk_score": risk_score,
            "delta": {
                "before": before,
                "after": after,
                "changed_fields": [
                    k for k in before
                    if before[k] != after.get(k)
                ],
            },
        }