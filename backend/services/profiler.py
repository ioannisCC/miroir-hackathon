"""
backend/services/profiler.py

ProfilerService: map-reduce profile extraction.
Phase 1 — one thread at a time, full fidelity, partial signals extracted.
Phase 2 — synthesis call merges all partials into final profile.

extracted_at injected server-side — Claude has no access to current time.
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.models.schemas import BehaviorProfile, ProfileSignal
from backend.prompts.profile_extraction import (
    SYSTEM_PROMPT,
    SYNTHESIS_PROMPT,
    build_synthesis_prompt,
    build_user_prompt,
)

logger = get_logger(__name__)

SLEEP_BETWEEN_CALLS = 10  # seconds — profiling is offline, time does not matter
CACHE_DIR = Path(__file__).parent.parent / "data" / "profile_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class ProfilerService:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    def extract_profile(
        self,
        name: str,
        email: str,
        threads: list[dict],
    ) -> BehaviorProfile:
        """
        Extract behavioral profile using map-reduce.
        Phase 1 — one thread at a time, full fidelity, partial signals extracted.
        Phase 2 — synthesis call merges all partials into final profile.
        Crash-safe — each partial is cached to disk immediately after extraction.
        """
        if not threads:
            raise ValueError(f"No threads provided for {email}")

        logger.info(
            "Starting map-reduce extraction for %s (%d threads)",
            email,
            len(threads),
        )

        # Phase 1 — Map: one thread at a time
        partial_profiles = []
        for idx, thread in enumerate(threads):
            logger.info(
                "Thread %d/%d for %s — subject: %s",
                idx + 1,
                len(threads),
                email,
                thread.get("subject", "no subject"),
            )

            partial_data = self._extract_partial(name, email, [thread], idx + 1)
            if partial_data is None:
                logger.warning("Skipping thread %d from synthesis", idx + 1)
                continue
            partial_profiles.append({
                "thread_index": idx + 1,
                "subject": thread.get("subject", ""),
                "profile": partial_data,
            })

            if idx < len(threads) - 1:
                logger.debug("Sleeping %ds before next thread", SLEEP_BETWEEN_CALLS)
                time.sleep(SLEEP_BETWEEN_CALLS)

        # Phase 2 — Reduce: synthesize into final profile
        if len(partial_profiles) == 1:
            logger.info("Single thread — skipping synthesis for %s", email)
            profile_data = partial_profiles[0]["profile"]
        else:
            logger.info(
                "Synthesizing %d partial profiles for %s",
                len(partial_profiles),
                email,
            )
            time.sleep(SLEEP_BETWEEN_CALLS)
            profile_data = self._synthesize(name, email, partial_profiles)

        profile_data["extracted_at"] = datetime.now(timezone.utc).isoformat()
        return self._validate_profile(profile_data, email)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_partial(
        self,
        name: str,
        email: str,
        threads: list[dict],
        thread_index: int,
    ) -> dict:
        """
        Extract partial profile from a single thread.
        Checks disk cache first — skips Claude call if already done.
        Writes to disk immediately after extraction for crash recovery.
        """
        cache_file = CACHE_DIR / f"{email}_thread_{thread_index}.json"

        if cache_file.exists():
            logger.info("Cache hit — thread %d for %s", thread_index, email)
            return json.loads(cache_file.read_text())

        try:
            user_prompt = build_user_prompt(name, email, threads)
            if len(user_prompt) // 4 > 29000:
                logger.warning("Thread %d too large (~%dk tokens) — skipping", thread_index, len(user_prompt) // 4000)
                return None
            response = self._call_claude(
                user_prompt,
                context=f"{email} thread {thread_index}",
                system_prompt=SYSTEM_PROMPT,
            )
            partial = self._parse_json(response.content[0].text)
            cache_file.write_text(json.dumps(partial, indent=2))
            logger.info("Cached partial — thread %d for %s", thread_index, email)
            return partial
        except Exception as e:
            logger.warning(
                "Thread %d failed for %s — skipping. Error: %s",
                thread_index, email, e
            )
            return None

    def _synthesize(
        self,
        name: str,
        email: str,
        partial_profiles: list[dict],  # ignored — we use disk instead
    ) -> dict:
        """
        Synthesize from ALL cached partials for this email on disk.
        Always recomputes — never uses a cached synthesis.
        """
        # Load all cached partials for this user from disk
        partial_files = sorted(CACHE_DIR.glob(f"{email}_thread_*.json"))

        if not partial_files:
            raise ValueError(f"No cached partials found for {email}")

        all_partials = []
        for f in partial_files:
            # Extract thread index from filename
            thread_index = int(f.stem.split("_thread_")[-1])
            data = json.loads(f.read_text())
            all_partials.append({
                "thread_index": thread_index,
                "subject": data.get("summary", "")[:50],  # best we have from partial
                "profile": data,
            })

        logger.info(
            "Synthesizing from %d cached partials on disk for %s",
            len(all_partials),
            email,
        )

        synthesis_prompt = build_synthesis_prompt(name, email, all_partials)
        response = self._call_claude(
            synthesis_prompt,
            context=f"{email} synthesis",
            system_prompt=SYNTHESIS_PROMPT,
        )
        result = self._parse_json(response.content[0].text)

        # Write for inspection — not read back as cache
        cache_file = CACHE_DIR / f"{email}_synthesis.json"
        cache_file.write_text(json.dumps(result, indent=2))
        logger.info("Synthesis written for %s (%d partials)", email, len(all_partials))

        return result

    def _call_claude(
        self,
        user_prompt: str,
        context: str = "",
        system_prompt: str = SYSTEM_PROMPT,
    ) -> anthropic.types.Message:
        """
        Call Claude with retry on rate limit.
        Non-rate-limit API errors propagate immediately — no point retrying a 401.
        """
        response = None
        for attempt in range(3):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                break
            except anthropic.RateLimitError:
                wait = 60 * (attempt + 1)
                logger.warning(
                    "Rate limited [%s] — waiting %ds (attempt %d/3)",
                    context,
                    wait,
                    attempt + 1,
                )
                time.sleep(wait)
            except anthropic.APIError as e:
                logger.error("Claude API error [%s]: %s", context, e)
                raise

        if response is None:
            raise RuntimeError(f"Rate limit exceeded after 3 attempts [{context}]")

        if not response.content:
            raise ValueError(f"Claude returned empty response [{context}]")

        logger.info(
            "Claude call complete [%s] — input: %d output: %d tokens",
            context,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return response

    def _parse_json(self, raw: str) -> dict:
        """Strip markdown fences and parse JSON."""
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Claude JSON: %s\nRaw: %s", e, raw[:500])
            raise ValueError(f"Claude returned invalid JSON: {e}") from e

    def _validate_profile(self, data: dict, email: str) -> BehaviorProfile:
        """Validate and coerce profile data into BehaviorProfile."""
        for key in ("trust_indicators", "risk_indicators"):
            raw_signals = data.get(key, [])
            coerced = []
            for s in raw_signals:
                if isinstance(s, dict):
                    try:
                        coerced.append(ProfileSignal(**s))
                    except Exception as e:
                        logger.warning("Skipping malformed signal in %s: %s", key, e)
                elif isinstance(s, ProfileSignal):
                    coerced.append(s)
            data[key] = coerced

        for score_field in (
            "reply_speed_score",
            "follow_through_score",
            "communication_tone_score",
            "pressure_score",
        ):
            if data.get(score_field) is None:
                logger.warning(
                    "Profile for %s missing %s — thin data or Claude skipped it",
                    email,
                    score_field,
                )

        try:
            return BehaviorProfile(**data)
        except Exception as e:
            logger.error("BehaviorProfile validation failed for %s: %s", email, e)
            raise ValueError(f"Profile validation failed: {e}") from e