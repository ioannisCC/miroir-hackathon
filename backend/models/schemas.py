"""
backend/models/schemas.py

Pydantic models for all domain objects.
Used by routers, services, and database layer.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums — only where code branches on the value
# ---------------------------------------------------------------------------

class InteractionType(str, Enum):
    call = "call"
    email = "email"


class OutcomeType(str, Enum):
    paid_now = "paid_now"
    promise_to_pay = "promise_to_pay"
    payment_plan_agreed = "payment_plan_agreed"
    refused_engagement = "refused_engagement"
    no_answer = "no_answer"
    escalated_human = "escalated_human"
    callback_scheduled = "callback_scheduled"
    other = "other"


class FollowUpStatus(str, Enum):
    pending = "pending"
    done = "done"
    cancelled = "cancelled"


class FailedActionStatus(str, Enum):
    pending = "pending"
    retried = "retried"
    dead = "dead"


# ---------------------------------------------------------------------------
# Profile Signals — weighted and traceable to source
# ---------------------------------------------------------------------------

class ProfileSignal(BaseModel):
    signal: str
    severity: float = Field(ge=0.0, le=1.0)  # 0.0 = minor, 1.0 = critical
    source: str = ""  # e.g. "email_thread_3", "call_2024_01_15"


# ---------------------------------------------------------------------------
# Behavior Profile — shared structure for contacts AND operators
#
# Each key behavioral dimension has:
#   - free-form narrative (Claude writes depth here)
#   - optional score 0.0-1.0 (queryable across profiles)
#
# Scores are optional — nothing breaks if Claude omits them.
# ---------------------------------------------------------------------------

class BehaviorProfile(BaseModel):
    # Reply behavior
    reply_speed: str = ""
    reply_speed_score: float | None = Field(default=None, ge=0.0, le=1.0)  # 1.0 = very fast

    # Non-response
    non_response_patterns: str = ""

    # Tone
    communication_tone: str = ""
    communication_tone_score: float | None = Field(default=None, ge=0.0, le=1.0)  # 1.0 = very direct/clear

    # Follow-through
    follow_through_rate: str = ""
    follow_through_score: float | None = Field(default=None, ge=0.0, le=1.0)  # 1.0 = always follows through

    # Channel
    channel_preference: str = ""

    # Pressure
    pressure_response: str = ""
    pressure_score: float | None = Field(default=None, ge=0.0, le=1.0)  # 1.0 = stays calm under pressure

    # Weighted, traceable signals
    trust_indicators: list[ProfileSignal] = Field(default_factory=list)
    risk_indicators: list[ProfileSignal] = Field(default_factory=list)

    # Timing
    timezone: str = "Europe/Athens"  # IANA timezone — default for demo contacts

    # Meta
    summary: str = ""
    data_quality_notes: str = ""
    extracted_at: str = ""


# ---------------------------------------------------------------------------
# Contacts (debtors being negotiated with)
# ---------------------------------------------------------------------------

class ContactCreate(BaseModel):
    name: str
    email: str
    behavior_profile: BehaviorProfile = Field(default_factory=BehaviorProfile)
    risk_score: float = Field(default=0.5, ge=0.0, le=1.0)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    # Profile versioning — history preserved across updates
    profile_version: int = 1
    previous_profiles: list[dict[str, Any]] = Field(default_factory=list)


class Contact(ContactCreate):
    id: UUID
    updated_at: datetime


# ---------------------------------------------------------------------------
# Operator Profiles (the person USING Miroir — profiled from their own data)
# Same BehaviorProfile structure. Same pipeline. Different subject.
# ---------------------------------------------------------------------------

class OperatorProfileCreate(BaseModel):
    operator_id: str
    call_count: int = 0
    behavior_profile: BehaviorProfile = Field(default_factory=BehaviorProfile)
    pattern_notes: str = ""  # Claude's free-form summary of operator tendencies
    # Profile versioning — same as contacts
    profile_version: int = 1
    previous_profiles: list[dict[str, Any]] = Field(default_factory=list)


class OperatorProfile(OperatorProfileCreate):
    id: UUID
    updated_at: datetime


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------

class InteractionCreate(BaseModel):
    contact_id: UUID
    type: InteractionType
    transcript: str = ""
    summary: str = ""


class Interaction(InteractionCreate):
    id: UUID
    timestamp: datetime


# ---------------------------------------------------------------------------
# Decisions
#
# approach_chosen  → free-form, Claude writes natural language strategy
# reasoning        → free-form, full explanation, no constraints
# confidence_score → 0.0-1.0, used for escalation threshold
# confidence_notes → why confidence is high or low (judges will ask)
# escalate         → hard boolean, code routes call to human on True
# outcome          → enum, score math branches on this
# outcome_notes    → free-form nuance, required when outcome=other
# ---------------------------------------------------------------------------

class DecisionCreate(BaseModel):
    contact_id: UUID
    interaction_id: UUID | None = None
    approach_chosen: str
    reasoning: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_notes: str = ""
    escalate: bool = False
    outcome: OutcomeType | None = None
    outcome_notes: str = ""


class Decision(DecisionCreate):
    id: UUID


# ---------------------------------------------------------------------------
# Follow-ups
# ---------------------------------------------------------------------------

class FollowUpCreate(BaseModel):
    contact_id: UUID
    scheduled_at: datetime
    action_type: str
    status: FollowUpStatus = FollowUpStatus.pending


class FollowUp(FollowUpCreate):
    id: UUID


# ---------------------------------------------------------------------------
# Failed Actions (dead letter queue)
# ---------------------------------------------------------------------------

class FailedActionCreate(BaseModel):
    contact_id: UUID
    action_type: str
    payload: dict[str, Any]
    error_message: str
    retry_count: int = 0
    status: FailedActionStatus = FailedActionStatus.pending


class FailedAction(FailedActionCreate):
    id: UUID
    created_at: datetime