
# MedBridge - Team Contracts v1

Status: APPROVED FOR PROTOTYPE
Contract version: 1.0
Owner: Person 1

## 1. Project Rules

- Use Python for the backend.
- Use Pydantic for shared models.
- Use JSON for API requests and responses.
- Use YAML for hospital mappings and configuration.
- Use synthetic patient data only.
- Preserve original values and source information.
- Never silently discard conflicting medical records.
- High-risk conflicts require human review.
- No real hospital integration is included in v1.

## 2. Canonical Models

Source file: backend/canonical/models.py

Models:
- Provenance
- Patient
- Observation
- Medication
- Allergy
- Diagnosis
- IdentityMatch
- Conflict
- ResolutionResult
- ValidationResult
- PipelineResult

Dates use YYYY-MM-DD.
Unknown values must not be invented.
Patient.id is a MedBridge internal identifier.

## 3. Person 1 - Core Engine

Owned folders:
- backend/core/
- backend/ingestion/
- backend/canonical/
- mappings/
- data/

Functions:

read_source(path: str) -> list[dict]
Reads JSON or CSV synthetic source data.

map_record(
    record: dict,
    mapping: dict
) -> dict
Maps source field names to canonical field names.

run(sources: list[str]) -> PipelineResult
Coordinates ingestion, mapping, normalization,
identity matching, conflict detection,
validation and final result assembly.

## 4. Person 2 - Normalization and Identity

Owned folders:
- backend/normalization/
- backend/identity/

Functions:

normalize(record: dict) -> dict
Standardizes mapped values.

normalize_date(value: str, fmt: str) -> str
Returns YYYY-MM-DD.

match_patients(
    patients: list[Patient]
) -> list[IdentityMatch]
Returns candidate identity match results.

Match statuses:
- MATCH
- POSSIBLE_MATCH
- NO_MATCH

Scores are prototype heuristics, not clinical proof.

## 5. Person 3 - Conflicts and Provenance

Owned folders:
- backend/conflicts/
- backend/resolution/
- backend/provenance/

Functions:

detect_conflicts(
    patients: list[Patient]
) -> list[Conflict]

resolve(conflict: Conflict) -> ResolutionResult

Critical conflicts must return
NEEDS_HUMAN_REVIEW.

Every transformation must retain provenance.
Unresolved values must not be represented
as confirmed medical truth.

## 6. Person 4 - Validation and FHIR

Owned folders:
- backend/validation/
- backend/fhir/
- backend/tests/

Functions:

validate_patient(
    patient: Patient
) -> ValidationResult

build_bundle(patient: Patient) -> dict

FHIR target:
- FHIR R4 for the prototype
- Patient
- Observation
- MedicationStatement or agreed equivalent
- AllergyIntolerance
- Condition
- Bundle

FHIR resource mapping must be tested.
Missing or unresolved data must not be
fabricated to satisfy a resource schema.

## 7. Person 5 - API and Frontend

Owned folders:
- backend/api/
- frontend/

Framework: FastAPI
Frontend: HTML, CSS, JavaScript

Endpoints:

GET /api/health
Response:
{"status": "ok"}

GET /api/sources
Returns configured synthetic sources.

POST /api/run
Runs the pipeline and returns PipelineResult.

GET /api/dashboard
Returns summary counts.

GET /api/matches
Returns list[IdentityMatch].

GET /api/conflicts
Returns list[Conflict].

GET /api/patients/{id}
Returns Patient.

GET /api/patients/{id}/provenance
Returns provenance for patient records.

GET /api/patients/{id}/fhir
Returns a FHIR Bundle.

POST /api/conflicts/{id}/review
Accepts an explicit reviewer decision.
No automatic approval of critical conflicts.

API errors use:
{
  "detail": "Error description"
}

## 8. Integration Order

1. Person 1 defines shared models.
2. Person 1 creates source data and mappings.
3. Person 2 implements normalization and matching.
4. Person 3 implements conflicts and resolution.
5. Person 4 implements validation and FHIR.
6. Person 1 connects the pipeline.
7. Person 5 connects API and frontend.
8. All modules are tested together.

## 9. Change Rules

- Do not rename shared fields without updating
  this contract and dependent tests.
- Do not change function signatures silently.
- Use separate Git branches for development.
- Review changes before merging into main.
- Update the contract version for breaking changes.

## 10. Prototype Scope

MedBridge demonstrates interoperability using
synthetic data. It does not establish clinical
identity, authorize real patient access, or make
medical decisions.
