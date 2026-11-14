
from datetime import date as Date
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
    date: Date
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


# العمليات الجراحية والإجراءات الطبية
class Procedure(MedBridgeModel):
    id: str
    name: str
    procedure_type: str | None = None
    date: Date | None = None
    status: str = "unknown"
    outcome: str | None = None
    notes: str | None = None
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


# التاريخ المرضي السابق والحالات المزمنة
class MedicalHistory(MedBridgeModel):
    id: str
    condition: str
    code: str | None = None
    onset_date: Date | None = None
    resolved_date: Date | None = None
    status: str = "unknown"
    notes: str | None = None
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


# الزيارات الطبية والتنويم
class Encounter(MedBridgeModel):
    id: str
    encounter_type: str
    date: Date | None = None
    reason: str | None = None
    diagnosis: str | None = None
    location: str | None = None
    status: str = "unknown"
    notes: str | None = None
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


# التطعيمات
class Immunization(MedBridgeModel):
    id: str
    vaccine: str
    date: Date | None = None
    dose: str | None = None
    status: str = "unknown"
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


# التاريخ العائلي المرضي
class FamilyHistory(MedBridgeModel):
    id: str
    condition: str
    relationship: str | None = None
    notes: str | None = None
    source: str
    provenance: list[Provenance] = Field(default_factory=list)


class Patient(MedBridgeModel):
    id: str
    national_id: str | None = None
    name: str | None = None
    birth_date: Date | None = None
    gender: Literal["male", "female", "unknown"] = "unknown"

    sources: list[str] = Field(default_factory=list)

    observations: list[Observation] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    allergies: list[Allergy] = Field(default_factory=list)
    diagnoses: list[Diagnosis] = Field(default_factory=list)

    procedures: list[Procedure] = Field(default_factory=list)
    medical_history: list[MedicalHistory] = Field(default_factory=list)
    encounters: list[Encounter] = Field(default_factory=list)
    immunizations: list[Immunization] = Field(default_factory=list)
    family_history: list[FamilyHistory] = Field(default_factory=list)


class IdentityMatch(MedBridgeModel):
    patient_a_id: str
    patient_b_id: str
    score: float = Field(ge=0, le=1)
    status: Literal["MATCH", "POSSIBLE_MATCH", "NO_MATCH"]


class Conflict(MedBridgeModel):
    id: str
    patient_id: str
    patient_name: str = ""
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
