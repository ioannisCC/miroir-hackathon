"""
backend/services/evaluation.py

EvaluationPipeline: two-pass LLM judge that decides the next action for a contact.

Pass 1 — Claude without company guidelines. Pure behavioral reasoning.
Pass 2 — Claude with company guidelines. Final approved decision.

Company guidelines always win on conflicts.
Both judgments preserved in the decision log for transparency.
"""

import json
import re
import anthropic

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.services.actions import Action, HARD_RULES, check_hard_rules

logger = get_logger(__name__)

PASS1_SYSTEM = """
You are a behavioral collections strategist. You have no company guidelines — only the data.

Given a contact's behavioral profile and interaction history, decide what should happen next.
Be honest and specific. Explain your reasoning based on observable patterns only.

Return JSON only. No markdown. No preamble.
""".strip()

PASS2_SYSTEM = """
You are a compliance-aware collections strategist. You follow company guidelines strictly.

You will receive:
1. A contact's behavioral profile and interaction history
2. A raw behavioral recommendation (Pass 1)
3. Company hard rules that cannot be violated

Your job: produce the final approved next action, respecting all hard rules.
If the Pass 1 recommendation violates a hard rule, override it and explain why.

Return JSON only. No markdown. No preamble.
""".strip()


def _build_context(contact: dict, history: list[dict]) -> str:
    profile = contact.get("behavior_profile", {})
    emails_sent = sum(1 for i in history if i.get("type") == "email")
    calls_made = sum(1 for i in history if i.get("type") == "call")

    # Compute days since first contact
    from datetime import datetime, timezone
    timestamps = [
        i.get("timestamp") for i in history if i.get("timestamp")
    ]
    if timestamps:
        try:
            first_ts = min(
                datetime.fromisoformat(str(t)) if isinstance(t, str) else t
                for t in timestamps
            )
            if first_ts.tzinfo is None:
                first_ts = first_ts.replace(tzinfo=timezone.utc)
            days_since_first_contact = (datetime.now(timezone.utc) - first_ts).days
        except Exception:
            days_since_first_contact = "unknown"
    else:
        days_since_first_contact = 0

    last_interaction_summary = history[-1].get("summary") if history else "None — first contact"

    # Contact's local time for timing-aware reasoning
    contact_tz = profile.get("timezone") or "UTC"
    try:
        from zoneinfo import ZoneInfo
        local_now = datetime.now(ZoneInfo(contact_tz))
        local_time_str = local_now.strftime("%A %H:%M") + f" ({contact_tz})"
    except Exception:
        local_time_str = "unknown"

    return f"""
CONTACT: {contact.get('name')} <{contact.get('email')}>
Risk score: {contact.get('risk_score')}
Trust score: {contact.get('trust_score')}
Contact local time: {local_time_str}

BEHAVIORAL PROFILE SUMMARY:
{profile.get('summary', 'No summary available')}

Follow-through score: {profile.get('follow_through_score')}
Reply speed score: {profile.get('reply_speed_score')}
Pressure score: {profile.get('pressure_score')}

Risk indicators: {json.dumps([r.get('signal') if isinstance(r, dict) else r for r in profile.get('risk_indicators', [])])}

COLLECTIONS LADDER POSITION:
Emails sent: {emails_sent}
Calls made: {calls_made}
Days since first contact: {days_since_first_contact}
Last interaction: {last_interaction_summary}

INTERACTION HISTORY ({len(history)} interactions):
{json.dumps([{'type': i.get('type'), 'summary': i.get('summary'), 'timestamp': str(i.get('timestamp'))} for i in history[-10:]], indent=2)}
""".strip()


def _build_pass1_prompt(context: str) -> str:
    actions = [a.value for a in Action]
    return f"""
{context}

Available actions: {actions}

Based purely on this contact's behavioral profile and history, what should happen next?

Return:
{{
  "recommended_action": "<one of the available actions>",
  "reasoning": "<specific behavioral reasoning>",
  "confidence": <0.0-1.0>,
  "confidence_notes": "<why this confidence level>"
}}
""".strip()


def _build_pass2_prompt(context: str, pass1: dict) -> str:
    actions = [a.value for a in Action]

    # Build a checklist that forces Claude to explicitly check each rule
    rules_checklist = "\n".join(
        f"[ ] {r['id']}: {r['description']}" for r in HARD_RULES
    )

    return f"""
{context}

PASS 1 RECOMMENDATION (behavioral, no guidelines):
{json.dumps(pass1, indent=2)}

HARD RULES CHECKLIST — check each one before finalizing:
{rules_checklist}

Available actions: {actions}

Step 1: For each rule above, write PASS or FAIL and why.
Step 2: If any rule FAILs, override the Pass 1 recommendation.
Step 3: Output the final approved action.

Return:
{{
  "rule_checks": {{"<rule_id>": "PASS/FAIL — reason"}},
  "recommended_action": "<one of the available actions>",
  "reasoning": "<final reasoning including any rule overrides>",
  "confidence": <0.0-1.0>,
  "confidence_notes": "<why this confidence level>",
  "overrode_pass1": <true/false>,
  "override_reason": "<why pass1 was overridden, or null>"
}}
""".strip()


class EvaluationPipeline:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    def evaluate(
        self,
        contact: dict,
        interaction_history: list[dict],
    ) -> dict:
        """
        Run two-pass evaluation and return next action with full reasoning.
        Both pass judgments preserved for audit trail.
        """
        context = _build_context(contact, interaction_history)

        logger.info("Pass 1 evaluation for %s", contact.get("email"))
        pass1 = self._call_claude(PASS1_SYSTEM, _build_pass1_prompt(context))

        logger.info("Pass 2 evaluation for %s", contact.get("email"))
        pass2 = self._call_claude(PASS2_SYSTEM, _build_pass2_prompt(context, pass1))

        # Validate action
        try:
            action = Action(pass2.get("recommended_action"))
        except ValueError:
            logger.warning("Invalid action from Pass 2: %s — defaulting to send_email", pass2.get("recommended_action"))
            action = Action.send_email

        confidence = float(pass2.get("confidence", 0.5))

        # Hard rules check
        allowed, block_reason = check_hard_rules(
            action, contact, interaction_history, confidence
        )

        if not allowed:
            logger.warning(
                "Hard rule blocked %s for %s: %s",
                action.value,
                contact.get("email"),
                block_reason,
            )
            action = Action.escalate_to_human
            pass2["reasoning"] += f" [BLOCKED BY HARD RULE: {block_reason}]"
            pass2["overrode_pass1"] = True
            pass2["override_reason"] = block_reason

        return {
            "action": action.value,
            "reasoning": pass2.get("reasoning"),
            "confidence": confidence,
            "confidence_notes": pass2.get("confidence_notes", ""),
            "escalate": action == Action.escalate_to_human,
            "overrode_pass1": pass2.get("overrode_pass1", False),
            "override_reason": pass2.get("override_reason"),
            "pass1_recommendation": pass1,
            "pass2_recommendation": pass2,
        }

    def _call_claude(self, system: str, prompt: str) -> dict:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as e:
            logger.error("Claude API error in evaluation: %s", e)
            raise

        if not response.content:
            raise ValueError("Claude returned empty response in evaluation")

        logger.info(
            "Evaluation call — input: %d output: %d tokens",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        raw = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse evaluation JSON: %s\nRaw: %s", e, raw[:300])
            raise ValueError(f"Invalid JSON from evaluation: {e}") from e