"""
backend/services/pipeline.py

IngestionPipeline: orchestrates EnronLoader + ProfilerService.
Called by both the CLI script and FastAPI endpoints.
"""

from dataclasses import dataclass

from backend.core.logging import get_logger
from backend.models.schemas import BehaviorProfile
from backend.services.enron import EnronLoader
from backend.services.profiler import ProfilerService

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    username: str
    name: str
    email: str
    profile: BehaviorProfile
    threads_used: int
    risk_score: float = 0.5
    trust_score: float = 0.5


class IngestionPipeline:
    def __init__(self) -> None:
        self._loader = EnronLoader()
        self._profiler = ProfilerService()

    def run_for_user(
        self,
        username: str,
        max_threads: int = 10,
    ) -> PipelineResult:
        """
        Full pipeline: identity → threads → profile.
        Raises on unrecoverable errors. Caller decides how to handle.
        """
        logger.info("Pipeline starting for %s", username)

        try:
            name, email = self._loader.get_user_identity(username)
        except Exception as e:
            logger.error("Identity extraction failed for %s: %s", username, e)
            raise

        try:
            threads = self._loader.load_threads_for_user(
                username, max_threads=max_threads
            )
        except Exception as e:
            logger.error("Thread loading failed for %s: %s", username, e)
            raise

        if not threads:
            raise ValueError(f"No usable threads found for {username}")

        thread_dicts = [t.to_dict() for t in threads]

        try:
            profile = self._profiler.extract_profile(
                name=name, email=email, threads=thread_dicts
            )
        except Exception as e:
            logger.error("Profile extraction failed for %s: %s", username, e)
            raise

        logger.info("Pipeline complete for %s — %d threads used", username, len(threads))

        # Compute aggregate scores from profile
        scores = [
            profile.follow_through_score,
            profile.pressure_score,
            profile.reply_speed_score,
        ]
        valid_scores = [s for s in scores if s is not None]
        trust_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.5

        risk_score = min(
            sum(s.severity for s in profile.risk_indicators) / 5.0,
            1.0
        ) if profile.risk_indicators else 0.2

        return PipelineResult(
            username=username,
            name=name,
            email=email,
            profile=profile,
            threads_used=len(threads),
            risk_score=round(risk_score, 2),
            trust_score=round(trust_score, 2),
        )
