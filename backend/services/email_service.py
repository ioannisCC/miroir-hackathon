"""
backend/services/email_service.py

EmailService: drafts behavioral-profile-adapted collection emails via Claude.
Does not send — returns draft for operator approval or logs directly.
"""

import json

import anthropic

import re


from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.services.guidelines import get_guidelines

logger = get_logger(__name__)

def _build_email_system_prompt() -> str:
    """Build email system prompt from live guidelines."""
    gl = get_guidelines()
    email_rules = gl["email_rules"]
    agent_role = gl.get("agent_role", "professional collections specialist")
    rules_block = "\n".join(f"- {line.strip()}" for line in email_rules.split("\n") if line.strip())
    return f"""You are a {agent_role} drafting outreach emails.

RULES:
{rules_block}

Return JSON only. No markdown. No preamble."""


class EmailService:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    def draft_email(
        self,
        contact: dict,
        interaction_history: list[dict],
        debt_amount: float | None = None,
    ) -> dict:
        """
        Draft a behavioral-profile-adapted collections email.
        Returns subject, body, tone_notes.
        """
        profile = contact.get("behavior_profile", {})
        debt = debt_amount or profile.get("debt_amount", 0)
        prior_emails = [
            i for i in interaction_history[-5:]
            if i.get("type") == "email"
        ]

        prior_emails_block = json.dumps(
            [
                {
                    "summary": str(i.get("summary") or ""),
                    "transcript": str(i.get("transcript") or "")[:200],
                }
                for i in prior_emails
            ],
            indent=2,
        )

        # Contact's local time for time-appropriate greetings
        contact_tz = profile.get("timezone") or "UTC"
        try:
            from zoneinfo import ZoneInfo
            from datetime import datetime
            local_now = datetime.now(ZoneInfo(contact_tz))
            local_time_str = local_now.strftime("%A %H:%M") + f" ({contact_tz})"
        except Exception:
            local_time_str = "unknown"

        # Dynamic context from guidelines (debt vs recruitment)
        gl = get_guidelines()
        context_label = gl.get("context_label", "OUTSTANDING DEBT")
        context_value_prefix = gl.get("context_value_prefix", "€")
        agent_role = gl.get("agent_role", "professional collections specialist")

        if context_value_prefix:
            context_value = f"{context_value_prefix}{debt:,.0f}"
        else:
            context_value = f"{debt:,.0f}" if debt else "Not specified"

        prompt = f"""
Draft a professional email for: {contact.get('name')} <{contact.get('email')}>
You are writing as a {agent_role}.
Contact's current local time: {local_time_str}
{context_label}: {context_value}

Emails sent so far: {len(prior_emails)}
Prior email summaries:
{prior_emails_block}

Escalate tone appropriately based on prior contact and lack of response.

BEHAVIORAL PROFILE:
Summary: {profile.get('summary', 'No summary')}
Communication tone: {profile.get('communication_tone', 'Unknown')}
Follow-through score: {profile.get('follow_through_score')} (1.0 = always follows through)
Pressure response: {profile.get('pressure_response', 'Unknown')}
Trust score: {contact.get('trust_score')}
Risk score: {contact.get('risk_score')}

PRIOR INTERACTIONS:
{json.dumps([{'type': str(i.get('type') or ''), 'summary': str(i.get('summary') or '')} for i in interaction_history[-5:]], indent=2)}

Draft the email. Return:
{{
  "subject": "<email subject>",
  "body": "<full email body>",
  "tone": "<one word: warm/professional/firm/urgent>",
  "tone_notes": "<why this tone was chosen based on the profile>"
}}
""".strip()

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=_build_email_system_prompt(),
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as e:
            logger.error("Claude API error drafting email for %s: %s", contact.get("email"), e)
            raise

        if not response.content:
            raise ValueError("Claude returned empty response for email draft")

        logger.info(
            "Email drafted for %s — input: %d output: %d tokens",
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
            logger.error("Failed to parse email draft JSON: %s", e)
            raise ValueError(f"Invalid JSON from email draft: {e}") from e