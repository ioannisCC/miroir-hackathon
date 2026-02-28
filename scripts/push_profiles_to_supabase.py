"""
scripts/push_profiles_to_supabase.py

Reads all synthesis JSON files from profile_cache and pushes to Supabase contacts table.
Run: uv run python scripts/push_profiles_to_supabase.py

Idempotent — upserts on email, safe to run multiple times.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import get_db
from backend.core.logging import get_logger, setup_logging
from backend.models.schemas import BehaviorProfile, ProfileSignal

setup_logging()
logger = get_logger("push_profiles")

CACHE_DIR = Path(__file__).parent.parent / "backend" / "data" / "profile_cache"

# Demo contacts — name mapped from email for display
EMAIL_TO_NAME = {
    "jeff.dasovich@enron.com": "Jeff Dasovich",
    "vince.kaminski@enron.com": "Vince Kaminski",
    "steven.kean@enron.com": "Steven Kean",
    "jeff.skilling@enron.com": "Jeff Skilling",
    "john.arnold@enron.com": "John Arnold",
}

# Demo debt amounts — for dashboard display
EMAIL_TO_DEBT = {
    "jeff.dasovich@enron.com": 8000,
    "vince.kaminski@enron.com": 12000,
    "steven.kean@enron.com": 5000,
    "jeff.skilling@enron.com": 22000,
    "john.arnold@enron.com": 9500,
}


def compute_scores(profile_data: dict) -> tuple[float, float]:
    """
    Compute trust_score and risk_score from raw profile dict.
    Same logic as PipelineResult in pipeline.py.
    """
    scores = [
        profile_data.get("follow_through_score"),
        profile_data.get("pressure_score"),
        profile_data.get("reply_speed_score"),
    ]
    valid = [s for s in scores if s is not None]
    trust_score = round(sum(valid) / len(valid), 2) if valid else 0.5

    risk_indicators = profile_data.get("risk_indicators", [])
    if risk_indicators:
        total_severity = sum(
            s.get("severity", 0) if isinstance(s, dict) else s.severity
            for s in risk_indicators
        )
        risk_score = round(min(total_severity / 5.0, 1.0), 2)
    else:
        risk_score = 0.2

    return trust_score, risk_score


def push_synthesis(synthesis_path: Path) -> bool:
    """Push one synthesis file to Supabase. Returns True on success."""
    # Extract email from filename: jeff.dasovich@enron.com_synthesis.json
    filename = synthesis_path.stem  # jeff.dasovich@enron.com_synthesis
    email = filename.replace("_synthesis", "")

    logger.info("Processing %s", email)

    try:
        raw = json.loads(synthesis_path.read_text())
    except Exception as e:
        logger.error("Failed to read %s: %s", synthesis_path, e)
        return False

    trust_score, risk_score = compute_scores(raw)
    name = EMAIL_TO_NAME.get(email, email.split("@")[0].replace(".", " ").title())
    debt_amount = EMAIL_TO_DEBT.get(email, 0)

    # Add debt_amount to profile for dashboard display
    raw["debt_amount"] = debt_amount

    contact = {
        "name": name,
        "email": email,
        "behavior_profile": raw,
        "trust_score": trust_score,
        "risk_score": risk_score,
    }

    try:
        db = get_db()
        result = (
            db.table("contacts")
            .upsert(contact, on_conflict="email")
            .execute()
        )
        logger.info(
            "✓ %s — trust: %.2f, risk: %.2f",
            name,
            trust_score,
            risk_score,
        )
        return True
    except Exception as e:
        logger.error("Failed to push %s: %s", email, e)
        return False


def main() -> None:
    if not CACHE_DIR.exists():
        logger.error("Cache directory not found: %s", CACHE_DIR)
        sys.exit(1)

    synthesis_files = sorted(CACHE_DIR.glob("*_synthesis.json"))

    if not synthesis_files:
        logger.error("No synthesis files found in %s", CACHE_DIR)
        sys.exit(1)

    logger.info("Found %d synthesis files", len(synthesis_files))

    success = 0
    failed = 0

    for path in synthesis_files:
        if push_synthesis(path):
            success += 1
        else:
            failed += 1

    logger.info("Done — %d pushed, %d failed", success, failed)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()