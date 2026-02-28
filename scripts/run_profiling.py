"""
scripts/test_profiling.py

First real end-to-end test: Enron emails → Claude → validated BehaviorProfile.
Run: uv run python scripts/test_profiling.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.logging import get_logger, setup_logging
from backend.services.enron import INTERESTING_USERS, EnronLoader
from backend.services.profiler import ProfilerService

setup_logging()
logger = get_logger("test_profiling")


def run(username: str = "arnold-j", max_threads: int = 5) -> None:
    logger.info("=== Starting profile extraction test for %s ===", username)

    loader = EnronLoader()
    profiler = ProfilerService()

    name, email_addr = loader.get_user_identity(username)
    logger.info("Identity: %s <%s>", name, email_addr)

    threads = loader.load_threads_for_user(username, max_threads=max_threads)
    logger.info("Threads loaded: %d", len(threads))

    if not threads:
        logger.error("No threads found for %s — try a different user", username)
        return

    thread_dicts = [t.to_dict() for t in threads]

    profile = profiler.extract_profile(name=name, email=email_addr, threads=thread_dicts)

    # --- Print results ---
    print("\n" + "=" * 60)
    print(f"BEHAVIORAL PROFILE: {name} <{email_addr}>")
    print("=" * 60)
    print(f"\nSUMMARY:\n{profile.summary}")
    print(f"\nREPLY SPEED: {profile.reply_speed}")
    print(f"  score: {profile.reply_speed_score}")
    print(f"\nFOLLOW-THROUGH: {profile.follow_through_rate}")
    print(f"  score: {profile.follow_through_score}")
    print(f"\nCOMMUNICATION TONE: {profile.communication_tone}")
    print(f"  score: {profile.communication_tone_score}")
    print(f"\nPRESSURE RESPONSE: {profile.pressure_response}")
    print(f"  score: {profile.pressure_score}")
    print(f"\nNON-RESPONSE PATTERNS:\n{profile.non_response_patterns}")
    print(f"\nCHANNEL PREFERENCE:\n{profile.channel_preference}")

    print(f"\nTRUST INDICATORS ({len(profile.trust_indicators)}):")
    for s in profile.trust_indicators:
        print(f"  [{s.severity:.1f}] {s.signal} (source: {s.source})")

    print(f"\nRISK INDICATORS ({len(profile.risk_indicators)}):")
    for s in profile.risk_indicators:
        print(f"  [{s.severity:.1f}] {s.signal} (source: {s.source})")

    print(f"\nDATA QUALITY:\n{profile.data_quality_notes}")
    print(f"\nEXTRACTED AT: {profile.extracted_at}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="arnold-j", help="Enron username to profile")
    parser.add_argument("--threads", type=int, default=5, help="Max threads to use")
    args = parser.parse_args()

    run(username=args.user, max_threads=args.threads)