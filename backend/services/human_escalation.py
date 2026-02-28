"""
backend/services/human_escalation.py

When system escalates to human, Claude writes a full briefing
so the human agent has everything they need in one document.
"""

import json
import anthropic
from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are writing a briefing for a human collections agent who is taking over this case.
Be direct and specific. The agent is about to make contact — they need to know everything.
Write in plain professional prose. No bullet points. Under 200 words.
""".strip()


def generate_briefing(contact: dict, history: list[dict]) -> str:
    """
    Generate a human agent briefing based on contact profile and interaction history.
    """
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    profile = contact.get("behavior_profile", {})
    debt = profile.get("debt_amount", 0)

    prompt = f"""
Write a briefing for a human collections agent taking over this case.

CONTACT: {contact.get('name')}
EMAIL: {contact.get('email')}
DEBT: €{debt:,.0f}
TRUST SCORE: {contact.get('trust_score')}
RISK SCORE: {contact.get('risk_score')}

BEHAVIORAL PROFILE:
{profile.get('summary', 'No profile available')}

INTERACTION HISTORY:
{json.dumps([{{'type': i.get('type'), 'summary': i.get('summary')}} for i in history[-5:]], indent=2)}

Cover: who this person is, what has been tried, why it is being escalated,
and what approach the human agent should take.
""".strip()

    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text