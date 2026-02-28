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

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are a professional collections specialist drafting outreach emails.

RULES:
- Adapt tone entirely to the contact's behavioral profile
- Never threaten legal action
- Never use aggressive or demeaning language
- Never create false urgency or fabricate deadlines
- Never imply consequences you cannot deliver
- Be specific — reference the debt amount and any prior contact
- Keep it under 200 words
- End with a clear single call to action
- Sign as [Agent Name] — never impersonate a specific person

Return JSON only. No markdown. No preamble.
""".strip()


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

        prompt = f"""
Draft a collections email for: {contact.get('name')} <{contact.get('email')}>
Debt amount: €{debt:,.0f}

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
                system=SYSTEM_PROMPT,
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