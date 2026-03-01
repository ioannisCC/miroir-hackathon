"""
scripts/seed_recruitment_contacts.py

Seeds the Supabase contacts table with 2 new recruitment contacts:
1. Maria Konstantinou — cold call / first contact (zero prior interaction)
2. Nikos Andreou — intermediate case (one brief exchange, then went silent)

Existing contact Alex Papadopoulos remains untouched (he's the "warm" end).

Run: uv run python scripts/seed_recruitment_contacts.py
Idempotent — upserts on email, safe to run multiple times.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import get_db
from backend.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("seed_recruitment")


# ---------------------------------------------------------------------------
# Contact 1: COLD CALL — Maria Konstantinou
# First contact ever. Zero interaction history. Profile inferred from public data.
# She is a junior-to-mid data engineer. We found her on LinkedIn.
# Low trust (no interaction yet), moderate risk (passive candidate, may ignore).
# ---------------------------------------------------------------------------
MARIA = {
    "name": "Maria Konstantinou",
    "email": "maria.konstantinou@dataworks.io",
    "use_case": "recruitment",
    "trust_score": 0.45,
    "risk_score": 0.65,
    "profile_version": 1,
    "previous_profiles": [],
    "behavior_profile": {
        "phone": "+306971234567",
        "summary": (
            "Maria Konstantinou is a data engineer with 3 years of experience, "
            "currently at a mid-sized fintech startup in Athens. Found via LinkedIn — "
            "no prior contact or interaction history exists. Her public profile indicates "
            "strong Python and Spark skills, a recent PySpark certification, and active "
            "contributions to open-source ETL tooling. She appears to be quietly exploring "
            "new opportunities (updated her LinkedIn headline recently) but has not "
            "applied anywhere. This is a purely cold outreach — we have no behavioral "
            "signals from direct interaction. Approach must be highly personalized to "
            "cut through recruiter noise."
        ),
        "timezone": "Europe/Athens",
        "debt_amount": 0,

        # Reply behavior — unknown, inferred from public signals only
        "reply_speed": "Unknown — no prior interaction. LinkedIn activity suggests she checks messages 1-2x per week.",
        "reply_speed_score": None,

        # Non-response
        "non_response_patterns": (
            "No direct data. Other recruiters report she ignores InMail — "
            "3 unanswered outreach attempts visible in market intelligence. "
            "Likely filters heavily and only engages with personalized, technically relevant messages."
        ),

        # Tone — inferred from her blog posts and GitHub comments
        "communication_tone": (
            "Inferred from public writing: concise, technically precise, slightly informal. "
            "Uses emojis sparingly in GitHub comments. Prefers substance over pleasantries."
        ),
        "communication_tone_score": None,

        # Follow-through — no data
        "follow_through_rate": "No data — zero prior commitments to measure against.",
        "follow_through_score": None,

        # Channel
        "channel_preference": (
            "Unknown. LinkedIn InMail has failed for other recruiters. "
            "Email may be more effective — she lists a personal domain on her GitHub."
        ),

        # Pressure
        "pressure_response": (
            "No direct data. Her open-source contributions suggest a calm, methodical "
            "personality — unlikely to respond well to artificial urgency."
        ),
        "pressure_score": None,

        # Signals
        "trust_indicators": [
            {
                "signal": "Active open-source contributor — 47 commits to apache/spark-etl in last 6 months",
                "source": "github_profile",
                "severity": 0.6,
            },
            {
                "signal": "Recently updated LinkedIn headline to include 'Open to opportunities'",
                "source": "linkedin_profile",
                "severity": 0.5,
            },
        ],
        "risk_indicators": [
            {
                "signal": "Zero response to 3 recruiter InMail attempts from other firms",
                "source": "market_intel",
                "severity": 0.7,
            },
            {
                "signal": "Currently employed — passive candidate, may not prioritize recruiter outreach",
                "source": "linkedin_profile",
                "severity": 0.5,
            },
            {
                "signal": "No prior relationship — cold outreach has historically low conversion rate",
                "source": "baseline_assumption",
                "severity": 0.6,
            },
        ],

        "data_quality_notes": (
            "Profile built entirely from public data (LinkedIn, GitHub, personal blog). "
            "No direct interaction data. Behavioral predictions are low-confidence. "
            "First interaction will dramatically update this profile."
        ),
    },
}


# ---------------------------------------------------------------------------
# Contact 2: INTERMEDIATE — Nikos Andreou
# Had one brief email exchange 2 weeks ago. Showed initial interest, then
# went quiet after we sent role details. We have SOME behavioral signals
# but not enough to be confident. Mid-range between cold Maria and warm Alex.
# ---------------------------------------------------------------------------
NIKOS = {
    "name": "Nikos Andreou",
    "email": "nikos.andreou@cloudstack.gr",
    "use_case": "recruitment",
    "trust_score": 0.58,
    "risk_score": 0.48,
    "profile_version": 1,
    "previous_profiles": [],
    "behavior_profile": {
        "phone": "+306945678901",
        "summary": (
            "Nikos Andreou is a backend developer with 5 years of experience, "
            "specializing in Go and Kubernetes. Currently a senior engineer at a "
            "cloud infrastructure company in Thessaloniki. We initiated contact 2 weeks "
            "ago — he replied within 4 hours expressing interest in the role, asked "
            "three specific questions about the tech stack (microservices architecture, "
            "deployment pipeline, team size). We sent detailed answers but he has not "
            "responded in 12 days. This silence could indicate: he's evaluating other "
            "offers, lost interest after seeing details, or simply got busy at work. "
            "His initial reply was notably enthusiastic and technically engaged — "
            "suggesting genuine interest rather than polite brushoff."
        ),
        "timezone": "Europe/Athens",
        "debt_amount": 0,

        # Reply behavior — one data point
        "reply_speed": (
            "First reply came within 4 hours — unusually fast for passive candidates. "
            "Second message has gone unanswered for 12 days. Possible pattern: fast "
            "when interested, complete silence when deliberating."
        ),
        "reply_speed_score": 0.5,

        # Non-response
        "non_response_patterns": (
            "Currently in a non-response phase after initial engagement. "
            "12 days without reply to a detailed role description. "
            "This is the critical juncture — one more unanswered follow-up and "
            "we risk losing him. The initial fast reply suggests this is deliberation, "
            "not disinterest."
        ),

        # Tone
        "communication_tone": (
            "Direct and technically curious based on initial email. Asked three "
            "specific technical questions unprompted (microservices, CI/CD, team size). "
            "No small talk. Used bullet points. Engineering mindset."
        ),
        "communication_tone_score": 0.8,

        # Follow-through
        "follow_through_rate": (
            "Insufficient data — only one interaction. He followed through on his "
            "initial interest by asking substantive questions, but has not yet "
            "followed through on the implicit next step."
        ),
        "follow_through_score": 0.5,

        # Channel
        "channel_preference": (
            "Responded to email (not LinkedIn). His initial reply suggests he "
            "prefers structured written communication for initial screening. "
            "A call might be the right escalation to break the silence."
        ),

        # Pressure
        "pressure_response": (
            "No direct data under pressure. His technical question style suggests "
            "he's methodical and analytical — likely responds better to specific "
            "value propositions than to deadline pressure."
        ),
        "pressure_score": 0.6,

        # Signals
        "trust_indicators": [
            {
                "signal": "Replied within 4 hours to initial outreach — shows genuine interest",
                "source": "email_interaction_1",
                "severity": 0.75,
            },
            {
                "signal": "Asked 3 specific technical questions — indicates serious evaluation not just browsing",
                "source": "email_interaction_1",
                "severity": 0.7,
            },
            {
                "signal": "5 years at current company — indicates loyalty and stability",
                "source": "linkedin_profile",
                "severity": 0.5,
            },
        ],
        "risk_indicators": [
            {
                "signal": "12 days non-responsive after initial engagement — may have lost interest or chosen competitor",
                "source": "email_interaction_2",
                "severity": 0.6,
            },
            {
                "signal": "Currently interviewing with at least one other company (mentioned in initial reply)",
                "source": "email_interaction_1",
                "severity": 0.5,
            },
            {
                "signal": "Based in Thessaloniki — role is Athens-based, relocation could be a blocker",
                "source": "linkedin_profile",
                "severity": 0.3,
            },
        ],

        "data_quality_notes": (
            "Profile based on one email exchange (2 messages total) plus public data. "
            "Behavioral predictions have moderate confidence — initial signals are strong "
            "but sample size is minimal. Next interaction will significantly sharpen profile."
        ),
    },
}


def seed() -> None:
    db = get_db()

    for contact in [MARIA, NIKOS]:
        try:
            result = (
                db.table("contacts")
                .upsert(contact, on_conflict="email")
                .execute()
            )
            logger.info(
                "✓ %s — trust: %.2f, risk: %.2f, use_case: %s",
                contact["name"],
                contact["trust_score"],
                contact["risk_score"],
                contact["use_case"],
            )
        except Exception as e:
            logger.error("✗ Failed to upsert %s: %s", contact["name"], e)

    # Verify
    result = (
        db.table("contacts")
        .select("name, email, trust_score, risk_score, use_case")
        .eq("use_case", "recruitment")
        .order("trust_score")
        .execute()
    )
    print(f"\n{'='*60}")
    print(f"RECRUITMENT CONTACTS ({len(result.data)} total)")
    print(f"{'='*60}")
    for c in result.data:
        print(f"  {c['name']:25s}  trust={c['trust_score']:.2f}  risk={c['risk_score']:.2f}  [{c['email']}]")
    print(f"{'='*60}")


if __name__ == "__main__":
    seed()
