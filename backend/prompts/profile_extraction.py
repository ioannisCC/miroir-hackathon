"""
backend/prompts/profile_extraction.py

Claude prompt for extracting behavioral profiles from email threads.
Used for both contacts (debtors) and operators (Miroir users).
"""

import json

SYSTEM_PROMPT = """
You are a behavioral analyst. Your job is to extract observable communication patterns from email data.

RULES:
- Only claim what the data actually shows. No speculation beyond the evidence.
- Every signal must be traceable to a specific source (thread, email index).
- Scores must reflect the evidence strength, not assumptions.
- If data is thin, say so explicitly in data_quality_notes.
- Never infer intent, personality, or psychology. Only observable behavior.
- When the subject appears as both sender and recipient, analyze their behavior in each role separately and note the difference if relevant.

OUTPUT FORMAT:
You must return a single valid JSON object. No markdown, no explanation, no preamble. Just JSON.
""".strip()


def clean_body(body: str) -> str:
    """
    Strip noise before sending to Claude:
    - Quoted reply chains (lines starting with >)
    - Forwarded message headers
    - Signature blocks
    No arbitrary character truncation — keep full actual content.
    """
    lines = body.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Drop quoted reply lines
        if stripped.startswith(">"):
            continue
        # Stop at forwarded message headers
        if stripped.startswith("-----Original Message") or stripped.startswith("-----Forwarded"):
            break
        # Stop at signature blocks
        if stripped in ("--", "___", "****"):
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def build_user_prompt(name: str, email: str, threads: list[dict]) -> str:
    threads_text = ""
    for i, thread in enumerate(threads, 1):
        threads_text += f"\n--- THREAD {i} ---\n"
        threads_text += f"Subject: {thread.get('subject', 'No subject')}\n"
        threads_text += f"Participants: {', '.join(thread.get('participants', []))}\n"
        threads_text += f"Message count: {len(thread.get('messages', []))}\n\n"
        for j, msg in enumerate(thread.get('messages', []), 1):
            threads_text += f"[{j}] From: {msg.get('from', '')} | To: {msg.get('to', '')} | CC: {msg.get('cc', '')} | Folder: {msg.get('folder', '')} | {msg.get('date', '')}\n"
            threads_text += f"{clean_body(msg.get('body', ''))}\n\n"

    return f"""
Analyze the email communication history for: {name} <{email}>

EMAIL THREADS:
{threads_text}

Extract a behavioral profile. Return this exact JSON structure:

{{
  "reply_speed": "<narrative: how fast do they respond, to whom, in what situations>",
  "reply_speed_score": <0.0-1.0 where 1.0 = very fast responder, null if insufficient data>,
  "non_response_patterns": "<narrative: when do they go silent, what triggers non-response>",
  "communication_tone": "<narrative: formal vs casual, direct vs indirect, how it shifts>",
  "communication_tone_score": <0.0-1.0 where 1.0 = very direct and clear, null if insufficient data>,
  "follow_through_rate": "<narrative: do stated commitments result in action, examples>",
  "follow_through_score": <0.0-1.0 where 1.0 = always follows through, null if insufficient data>,
  "channel_preference": "<narrative: which medium gets responses, how fast>",
  "pressure_response": "<narrative: how do they behave when pushed, deadlines, conflict>",
  "pressure_score": <0.0-1.0 where 1.0 = calm and cooperative under pressure, null if insufficient data>,
  "trust_indicators": [
    {{"signal": "<specific observable behavior>", "severity": <0.0-1.0>, "source": "thread_<N>_msg_<M>"}}
  ],
  "risk_indicators": [
    {{"signal": "<specific observable behavior>", "severity": <0.0-1.0>, "source": "thread_<N>_msg_<M>"}}
  ],
  "timezone": "<IANA timezone inferred from email timestamps, headers, or location clues e.g. America/Chicago, Europe/London. Use UTC if uncertain>",
  "summary": "<2-3 sentences: what matters most about how this person communicates>",
  "data_quality_notes": "<honest assessment: how many threads, what is missing, confidence level>"
}}

Trust indicators = behaviors that suggest reliability, honesty, cooperation.
Risk indicators = behaviors that suggest evasion, inconsistency, broken commitments.
Both lists can be empty if not evidenced. Do not fabricate signals.
""".strip()


SYNTHESIS_PROMPT = """
You are a behavioral analyst synthesizing partial profiles into a final assessment.

RULES:
- Merge all signals keeping source references intact
- Resolve contradictions by noting both and explaining the difference
- Final scores reflect ALL evidence across all threads
- Identify patterns that only emerge across multiple conversations
- Be honest about confidence — more consistent evidence = higher score
- Never infer intent or psychology. Only observable behavior.

OUTPUT FORMAT:
Return a single valid JSON object matching the exact same schema as the partial profiles.
No markdown, no explanation, no preamble. Just JSON.
""".strip()

def build_synthesis_prompt(
    name: str,
    email: str,
    partial_profiles: list[dict],
) -> str:
    profiles_text = ""
    for p in partial_profiles:
        profiles_text += f"\n--- THREAD {p['thread_index']}: \"{p['subject']}\" ---\n"
        profiles_text += json.dumps(p["profile"], indent=2)
        profiles_text += "\n"

    return f"""
Synthesize these {len(partial_profiles)} partial behavioral profiles for: {name} <{email}>

Each partial was extracted from one email conversation. 
Merge them into one final profile using the same JSON schema.
Where partials contradict each other, include both observations in the narrative.
For timezone: pick the most evidenced one. If conflicting, use the one from the most recent emails.

{profiles_text}
""".strip()