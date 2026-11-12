from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class MedBridgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(MedBridgeModel):
    source: str
    original_field: str
    original_value: str
    transformations: list[str] = Field(default_factory=list)


class Observation(MedBridgeModel):
    id: str
    type: str
    value: float
    unit: str
    date: date
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


class Medication(MedBridgeModel):
    id: str
    name: str
    dose: str | None = None
    status: Literal["active", "stopped", "unknown"] = "unknown"
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


class Allergy(MedBridgeModel):
    id: str
    substance: str
    reaction: str | None = None
    status: Literal["confirmed", "unconfirmed", "unknown"] = "unknown"
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


class Diagnosis(MedBridgeModel):
    id: str
    code: str | None = None
    description: str
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


class Patient(MedBridgeModel):
    id: str
    name: str | None = None
    birth_date: date | None = None
    gender: Literal["male", "female", "unknown"] = "unknown"
    sources: list[str] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    allergies: list[Allergy] = Field(default_factory=list)
    diagnoses: list[Diagnosis] = Field(default_factory=list)


class IdentityMatch(MedBridgeModel):
    patient_a_id: str
    patient_b_id: str
    score: float = Field(ge=0, le=1)
    status: Literal["MATCH", "POSSIBLE_MATCH", "NO_MATCH"]


class Conflict(MedBridgeModel):
    id: str
    patient_id: str
    field: str
    conflict_type: str
    record_ids: list[str]
    values: list[str]
    sources: list[str]
    critical: bool
    status: Literal[
        "OPEN",
        "RESOLVED",
        "NEEDS_HUMAN_REVIEW"
    ] = "OPEN"


class ResolutionResult(MedBridgeModel):
    conflict_id: str
    status: Literal["RESOLVED", "NEEDS_HUMAN_REVIEW"]
    selected_value: str | None = None
    reason: str
    strategy: str


class ValidationResult(MedBridgeModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SourceRecord(MedBridgeModel):
    source: str
    original: dict
    mapped: dict
    normalized: dict
    provenance: list[Provenance] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PipelineResult(MedBridgeModel):
    run_id: str
    status: Literal["completed", "failed"]
    patients: list[Patient] = Field(default_factory=list)
    matches: list[IdentityMatch] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    resolutions: list[ResolutionResult] = Field(default_factory=list)
    source_records: list[SourceRecord] = Field(default_factory=list)
    fhir_resources: list[dict] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)