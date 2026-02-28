"""
scripts/generate_short_summaries.py

Reads each synthesis JSON, asks Claude for a 3-line summary,
updates the contact in Supabase with short_summary field.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("short_summaries")

CACHE_DIR = Path(__file__).parent.parent / "backend" / "data" / "profile_cache"

PROMPT = """
Given this behavioral profile JSON, write exactly 3 lines that summarize this person for a collections agent about to contact them.

Line 1: Who they are and how they communicate
Line 2: Their biggest risk signal
Line 3: The recommended approach

Maximum 20 words per line. No bullet points. No labels. Just 3 plain lines.

Profile:
{profile}
"""

def generate_summary(profile: dict, client: anthropic.Anthropic) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": PROMPT.format(profile=json.dumps(profile, indent=2))
        }]
    )
    return response.content[0].text.strip()

def main():
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    db = get_db()

    synthesis_files = sorted(CACHE_DIR.glob("*_synthesis.json"))
    logger.info("Found %d synthesis files", len(synthesis_files))

    for path in synthesis_files:
        email = path.stem.replace("_synthesis", "")
        profile = json.loads(path.read_text())

        logger.info("Generating summary for %s", email)
        summary = generate_summary(profile, client)
        logger.info("\n%s\n%s", email, summary)

        # Update Supabase — add short_summary to behavior_profile
        try:
            contact = db.table("contacts").select("id, behavior_profile").eq("email", email).single().execute().data
            updated_profile = contact["behavior_profile"]
            updated_profile["short_summary"] = summary

            db.table("contacts").update({
                "behavior_profile": updated_profile
            }).eq("email", email).execute()

            logger.info("✓ Updated %s", email)
        except Exception as e:
            logger.error("Failed to update %s: %s", email, e)

if __name__ == "__main__":
    main()