"""
download_enron.py
-----------------
Downloads the Enron email dataset and extracts a curated sample
of 25-30 clean threads suitable for behavioral profile extraction.

Run: python scripts/download_enron.py
Output: backend/data/enron_sample.json
"""

import os
import re
import json
import email
import tarfile
import urllib.request
from pathlib import Path
from collections import defaultdict

DATASET_URL = "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz"
RAW_PATH = Path("backend/data/enron_raw.tar.gz")
EXTRACT_PATH = Path("backend/data/enron_raw")
OUTPUT_PATH = Path("backend/data/enron_sample.json")

# These mailboxes have the richest back-and-forth threads
TARGET_USERS = [
    "kenneth.lay", "jeff.skilling", "andrew.fastow",
    "sherron.watkins", "louise.kitchen", "john.lavorato"
]

MIN_THREAD_EMAILS = 3   # minimum emails in a thread to be useful
MAX_THREADS = 30        # how many threads to extract


def download_dataset():
    if RAW_PATH.exists():
        print("✓ Dataset already downloaded")
        return
    print(f"Downloading Enron dataset (~420MB)...")
    print("This takes a few minutes. Do not interrupt.")
    urllib.request.urlretrieve(DATASET_URL, RAW_PATH, reporthook=progress_hook)
    print("\n✓ Download complete")


def progress_hook(block_num, block_size, total_size):
    downloaded = block_num * block_size
    pct = min(downloaded / total_size * 100, 100)
    print(f"\r  {pct:.1f}%", end="", flush=True)


def extract_dataset():
    if EXTRACT_PATH.exists():
        print("✓ Dataset already extracted")
        return
    print("Extracting archive...")
    with tarfile.open(RAW_PATH, "r:gz") as tar:
        tar.extractall(EXTRACT_PATH)
    print("✓ Extraction complete")


def parse_email_file(filepath: Path) -> dict | None:
    try:
        raw = filepath.read_bytes()
        msg = email.message_from_bytes(raw)

        subject = msg.get("Subject", "").strip()
        sender = msg.get("From", "").strip()
        recipient = msg.get("To", "").strip()
        date = msg.get("Date", "").strip()

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

        # Clean forwarded/reply chains — keep only the top reply
        body = re.split(r"-{5,}|_{5,}|Original Message", body)[0].strip()

        # Skip near-empty emails
        if len(body) < 50:
            return None

        return {
            "subject": subject,
            "from": sender,
            "to": recipient,
            "date": date,
            "body": body[:2000]  # cap to avoid token blowout
        }
    except Exception:
        return None


def group_into_threads(emails: list[dict]) -> dict[str, list[dict]]:
    """Group emails by normalized subject line (thread key)."""
    threads = defaultdict(list)
    for em in emails:
        subject = em["subject"]
        # Normalize: strip Re:, Fw:, whitespace
        key = re.sub(r"^(re:|fw:|fwd:)\s*", "", subject.lower()).strip()
        threads[key].append(em)
    return threads


def collect_emails_for_user(user_path: Path) -> list[dict]:
    emails = []
    for folder in ["sent", "sent_items", "inbox", "_sent_mail"]:
        folder_path = user_path / folder
        if not folder_path.exists():
            continue
        for f in folder_path.iterdir():
            if f.is_file():
                parsed = parse_email_file(f)
                if parsed:
                    emails.append(parsed)
    return emails


def extract_sample() -> list[dict]:
    enron_root = EXTRACT_PATH / "maildir"
    if not enron_root.exists():
        raise FileNotFoundError(f"Expected maildir at {enron_root}")

    all_threads = []

    for user_dir in enron_root.iterdir():
        if not user_dir.is_dir():
            continue

        # Prioritize target users, but accept any if we need more
        is_target = any(t in user_dir.name for t in TARGET_USERS)
        if not is_target and len(all_threads) >= MAX_THREADS // 2:
            continue

        emails = collect_emails_for_user(user_dir)
        if not emails:
            continue

        threads = group_into_threads(emails)

        for subject_key, thread_emails in threads.items():
            if len(thread_emails) < MIN_THREAD_EMAILS:
                continue
            if not subject_key:
                continue

            # Sort by date string (approximate — good enough for demo)
            thread_emails_sorted = sorted(thread_emails, key=lambda e: e["date"])

            # Extract the primary contact (most frequent non-enron sender, or just from field)
            participants = set()
            for em in thread_emails_sorted:
                participants.add(em["from"])
                participants.add(em["to"])

            all_threads.append({
                "thread_id": f"{user_dir.name}__{subject_key[:40]}",
                "owner_mailbox": user_dir.name,
                "subject": thread_emails_sorted[0]["subject"],
                "email_count": len(thread_emails_sorted),
                "participants": list(participants)[:5],
                "emails": thread_emails_sorted[:10]  # cap at 10 per thread
            })

            if len(all_threads) >= MAX_THREADS:
                break

        if len(all_threads) >= MAX_THREADS:
            break

    return all_threads


def main():
    Path("backend/data").mkdir(parents=True, exist_ok=True)

    download_dataset()
    extract_dataset()

    print("Extracting clean threads...")
    threads = extract_sample()
    print(f"✓ Extracted {len(threads)} threads")

    OUTPUT_PATH.write_text(json.dumps(threads, indent=2))
    print(f"✓ Saved to {OUTPUT_PATH}")
    print()
    print("Sample thread subjects:")
    for t in threads[:5]:
        print(f"  [{t['email_count']} emails] {t['subject'][:60]}")


if __name__ == "__main__":
    main()