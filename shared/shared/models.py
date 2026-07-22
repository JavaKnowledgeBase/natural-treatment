"""Pydantic models shared by every backend service.

These mirror the Redis-backed shapes in `shared.cache`, not SQL tables --
there is no database, so these models are the closest thing this project has
to a schema.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SessionStep(str, Enum):
    GREETING = "greeting"
    SYMPTOM_COLLECTION = "symptom_collection"
    CAUSE_COLLECTION = "cause_collection"
    ANALYSIS = "analysis"
    RESULTS = "results"
    EMAIL_SENT = "email_sent"
    PURGED = "purged"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: ChatRole
    text: str
    ts: float


class UserProfile(BaseModel):
    """Every field is optional and starts empty.

    Nothing in this system prompts the user for these fields. They are only
    ever populated if the user volunteers the information unprompted in free
    text (see agents/intake's extraction pass).
    """

    age_range: Optional[str] = None
    pregnancy_status: Optional[str] = None
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    chronic_conditions: list[str] = Field(default_factory=list)


class CachedItem(BaseModel):
    """Shared shape for both the symptom cache and the cause cache entries."""

    id: str
    label: str
    source: str = "user"
    category: Optional[str] = None
    confidence: float = 0.8
    ts: float


class CompoundRecord(BaseModel):
    id: str
    name: str
    canonical_name: Optional[str] = None
    formula: Optional[str] = None
    pubchem_id: Optional[str] = None
    chebi_id: Optional[str] = None
    mechanism_summary: Optional[str] = None
    curation_status: str = "starter_dataset_unreviewed"


class HerbCompoundLink(BaseModel):
    compound_id: str
    concentration_estimate: Optional[str] = None
    concentration_unit: Optional[str] = None


class HerbRecord(BaseModel):
    id: str
    name: str
    scientific_name: Optional[str] = None
    plant_part_used: Optional[str] = None
    common_use: Optional[str] = None
    compounds: list[HerbCompoundLink] = Field(default_factory=list)
    linked_symptoms: list[str] = Field(default_factory=list)
    evidence_level: str = "traditional_and_limited_clinical"
    contraindications: list[str] = Field(default_factory=list)
    curation_status: str = "starter_dataset_unreviewed"


class SymptomRecord(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    candidate_imbalances: list[str] = Field(default_factory=list)
    related_symptom_ids: list[str] = Field(default_factory=list)


class SafetyRule(BaseModel):
    id: str
    herb_id: str
    condition: str
    severity: str  # "low" | "moderate" | "high" | "disallowed"
    note: str


class SafetyVerdict(BaseModel):
    herb_id: str
    allowed: bool
    safety_factor: float
    rules_fired: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    herb_id: str
    herb_name: str
    score: float
    confidence_band: str
    reason: str
    evidence_level: str
    safety_note: Optional[str] = None
    curation_status: str = "starter_dataset_unreviewed"


class SessionMeta(BaseModel):
    session_id: str
    current_step: SessionStep = SessionStep.GREETING
    created_at: float
    last_active_at: float
