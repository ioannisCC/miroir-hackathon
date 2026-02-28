"""
backend/services/enron.py

EnronLoader: reads the Enron maildir dataset from disk, selects clean threads,
and returns them in the format ProfilerService expects.

Confirmed dataset structure: backend/data/maildir/username/folder/files
Files are raw RFC 2822 email format.
"""

import email
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from backend.core.logging import get_logger

logger = get_logger(__name__)

# Confirmed path from dataset inspection
DATA_DIR = Path(__file__).parent.parent / "data" / "maildir"

# Demo contacts — 5 confirmed high-signal users, ordered by archetype diversity.
# Each represents a distinct behavioral profile for the collections demo.
DEMO_USERS = [
    "dasovich-j",   # External affairs — richest signal, California energy crisis context
    "kaminski-v",   # Chief risk officer — analytical, pushes back, principled archetype
    "kean-s",       # VP Government Affairs — diplomatic, careful, selective engagement
    "skilling-j",   # CEO — aggressive, time-pressured, difficult contact archetype
    "arnold-j",     # Trader — direct, baseline control, identity confirmed clean
]
# Curated list — users with rich, varied, high-signal threads
INTERESTING_USERS = DEMO_USERS


@dataclass
class EmailMessage:
    from_addr: str      # X-From
    to_addr: str        # X-To
    cc_addr: str        # X-cc
    folder: str         # X-Folder — context about stakes
    date: str
    subject: str
    body: str


@dataclass
class EmailThread:
    subject: str
    participants: list[str] = field(default_factory=list)
    messages: list[EmailMessage] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "participants": self.participants,
            "messages": [
                {
                    "from": m.from_addr,
                    "to": m.to_addr,
                    "cc": m.cc_addr,
                    "folder": m.folder,
                    "date": m.date,
                    "body": m.body,
                }
                for m in self.messages
            ],
        }


class EnronLoader:
    def __init__(self) -> None:
        if not DATA_DIR.exists():
            raise FileNotFoundError(
                f"Enron dataset not found at {DATA_DIR}. "
                "Run: uv run python scripts/download_enron.py"
            )

    def list_users(self) -> list[str]:
        """Return all available user directories in the dataset."""
        return sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])

    def load_threads_for_user(
        self,
        username: str,
        max_threads: int = 10,
        min_messages: int = 3,
        min_participants: int = 2,
    ) -> list[EmailThread]:
        """
        Load clean email threads for a given Enron username.
        Filters for threads with genuine back-and-forth.
        Returns up to max_threads threads.
        """
        user_dir = DATA_DIR / username
        if not user_dir.exists():
            raise FileNotFoundError(f"User directory not found: {user_dir}")

        raw_messages = self._load_messages(user_dir)
        logger.info("Loaded %d raw messages for %s", len(raw_messages), username)

        threads = self._group_into_threads(raw_messages)
        logger.info("Grouped into %d threads for %s", len(threads), username)

        clean = [
            t for t in threads
            if len(t.messages) >= min_messages
            and len(t.participants) >= min_participants
        ]
        logger.info(
            "%d threads pass filters (min_messages=%d, min_participants=%d) for %s",
            len(clean),
            min_messages,
            min_participants,
            username,
        )

        selected = clean[:max_threads]
        logger.info("Selected %d threads for %s", len(selected), username)
        return selected

    # Hardcoded for users whose assistants managed their sent folders
    KNOWN_IDENTITIES: dict[str, tuple[str, str]] = {
        "lay-k": ("Ken Lay", "ken.lay@enron.com"),
        "skilling-j": ("Jeff Skilling", "jeff.skilling@enron.com"),
        "fastow-a": ("Andy Fastow", "andrew.fastow@enron.com"),
    }

    def get_user_identity(self, username: str) -> tuple[str, str]:
        """
        Extract identity from sent/sent_items folders only.
        X-From in sent mail belongs to the user, not incoming senders.
        Falls back to KNOWN_IDENTITIES for executives whose assistants
        managed their sent folders.
        Returns (name, email).
        """
        if username in self.KNOWN_IDENTITIES:
            return self.KNOWN_IDENTITIES[username]

        user_dir = DATA_DIR / username
        for folder_name in ("sent", "sent_items", "_sent_mail"):
            folder_path = user_dir / folder_name
            if not folder_path.exists():
                continue
            for fpath in sorted(folder_path.iterdir())[:20]:
                if not fpath.is_file():
                    continue
                try:
                    raw = fpath.read_bytes()
                    msg = email.message_from_bytes(raw)
                    x_from = msg.get("X-From", "").strip()
                    from_header = msg.get("From", "").strip()
                    for header in (x_from, from_header):
                        if not header or "@" not in header:
                            continue
                        if "<" in header:
                            name = header.split("<")[0].strip().strip('"')
                            addr = header.split("<")[1].strip().rstrip(">")
                        else:
                            name = username.replace("-", " ").title()
                            addr = header.strip()
                        if name and addr:
                            return name, addr
                except Exception:
                    continue

        name = username.replace("-", " ").title()
        return name, f"{username}@enron.com"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_messages(self, user_dir: Path) -> list[EmailMessage]:
        """Walk all subdirectories and parse every email file."""
        messages = []
        for root, _, files in os.walk(user_dir):
            for fname in sorted(files):
                fpath = Path(root) / fname
                try:
                    raw = fpath.read_bytes()
                    msg = email.message_from_bytes(raw)
                    parsed = self._parse_message(msg)
                    if parsed:
                        messages.append(parsed)
                except Exception as e:
                    logger.debug("Skipping %s: %s", fpath, e)
        return messages

    def _parse_message(self, msg: email.message.Message) -> EmailMessage | None:
        """Extract fields from a parsed email. Returns None if malformed."""
        from_addr = (
            msg.get("X-From", "").strip()
            or msg.get("From", "").strip()
        )
        date = msg.get("Date", "").strip()
        subject = msg.get("Subject", "").strip()

        if not from_addr or not subject:
            return None

        body = self._extract_body(msg)
        if not body or len(body.strip()) < 10:
            return None

        return EmailMessage(
            from_addr=from_addr,
            to_addr=msg.get("X-To", msg.get("To", "")).strip(),
            cc_addr=msg.get("X-cc", msg.get("Cc", "")).strip(),
            folder=msg.get("X-Folder", "").strip(),
            date=date,
            subject=subject,
            body=body,
        )

    def _extract_body(self, msg: email.message.Message) -> str:
        """
        Extract plain text body from email, handling multipart.
        Enron dataset uses ANSI_X3.4-1968 — latin-1 fallback handles
        encoding artifacts better than utf-8 replace.
        """
        def decode_payload(part: email.message.Message) -> str:
            raw_bytes = part.get_payload(decode=True)
            if not raw_bytes:
                return ""
            charset = part.get_content_charset() or "latin-1"
            try:
                return raw_bytes.decode(charset)
            except (LookupError, UnicodeDecodeError):
                return raw_bytes.decode("latin-1", errors="replace")

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    text = decode_payload(part)
                    if text:
                        return text
            return ""
        else:
            return decode_payload(msg)

    def _group_into_threads(self, messages: list[EmailMessage]) -> list[EmailThread]:
        """
        Group messages into threads by normalized subject.
        Strips Re:/Fwd: prefixes for grouping.
        Deduplicates messages by body hash within each thread.
        """
        buckets: dict[str, list[EmailMessage]] = defaultdict(list)

        for msg in messages:
            key = self._normalize_subject(msg.subject)
            if key:
                buckets[key].append(msg)

        threads = []
        for subject, msgs in buckets.items():
            msgs_sorted = sorted(msgs, key=lambda m: m.date)

            # Deduplicate by first 200 chars of body
            seen = set()
            unique_msgs = []
            for msg in msgs_sorted:
                key = hash(msg.body[:200].strip())
                if key not in seen:
                    seen.add(key)
                    unique_msgs.append(msg)

            participants = list({m.from_addr for m in unique_msgs})
            threads.append(
                EmailThread(
                    subject=subject,
                    participants=participants,
                    messages=unique_msgs,
                )
            )

        return threads

    def _normalize_subject(self, subject: str) -> str:
        """Strip Re:/Fwd: variants for thread grouping."""
        normalized = re.sub(
            r"^(re|fwd?|fw):\s*", "", subject.strip(), flags=re.IGNORECASE
        )
        return normalized.strip().lower()