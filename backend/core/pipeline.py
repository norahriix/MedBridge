from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL
import yaml

from canonical.models import (
    Patient,
    PipelineResult,
    Conflict,
    SourceRecord,
    Observation
)

from ingestion.readers import read_source
from core.mapper import map_record
from core.clinical import process_clinical_records
from normalization.normalizer import normalize
from normalization.units import normalize_weight
from validation.validator import validate_patient
from identity.matcher import match_patients
from provenance.tracker import track_provenance
from conflicts.detector import detect_conflicts
from conflicts.clinical_detector import detect_clinical_conflicts
from resolution.rules import resolve_conflict

from fhir.converter import (
    patient_to_fhir,
    observation_to_fhir
)

from fhir.clinical_converter import (
    medication_to_fhir,
    allergy_to_fhir,
    diagnosis_to_fhir,
    mark_for_review
)


ROOT = Path(__file__).resolve().parents[2]


# 1. Load Configuration
def load_yaml(path):

    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


# 2. Provenance Tracking
def build_provenance(result, mapping, source):

    provenance_records = []

    original = result["original"]
    normalized = result["normalized"]

    for original_field, canonical_field in mapping["fields"].items():

        if original_field not in original:
            continue

        original_value = original[original_field]
        transformations = []

        if canonical_field in result["mapped"]:

            if original_field != canonical_field:
                transformations.append(
                    f"{original_field} -> {canonical_field}"
                )

        if canonical_field in normalized:

            normalized_value = normalized[canonical_field]

            if original_value != normalized_value:
                transformations.append(
                    f"{original_value} -> {normalized_value}"
                )

        provenance_records.append(
            track_provenance(
                source,
                original_field,
                original_value,
                transformations
            )
        )

    return provenance_records


# 3. Process Patient Source
def process_source(data_path: str, mapping_path: str):

    records = read_source(data_path)
    mapping = load_yaml(mapping_path)

    source = Path(mapping_path).parent.name
    results = []

    for record in records:

        mapped = {}
        normalized = {}
        errors = []

        try:

            mapped = map_record(record, mapping)
            normalized = normalize(mapped)
            errors = validate_patient(normalized)

        except Exception as error:

            errors.append(str(error))

        result = {
            "source": source,
            "original": record,
            "mapped": mapped,
            "normalized": normalized,
            "errors": errors
        }

        result["provenance"] = build_provenance(
            result, mapping, source
        )

        results.append(result)

    return results


# 4. Build Canonical Patients
def build_patients(results: list[dict], source: str):

    patients = []

    for result in results:

        if result["errors"]:
            continue

        record = result["normalized"]

        patient = Patient(
            id=f"{source}:{record['source_patient_id']}",
            name=record["name"],
            birth_date=record["birth_date"],
            gender=record["gender"],
            sources=[source]
        )

        patients.append(patient)

    return patients


# 5. Process Clinical Observations
def process_observations(
    data_path,
    mapping_path,
    source,
    patients
):

    records = read_source(str(data_path))
    mapping = load_yaml(mapping_path)

    source_records = []

    patient_index = {
        patient.id: patient
        for patient in patients
    }

    for record in records:

        mapped = {}
        normalized = {}
        errors = []

        try:

            mapped = map_record(record, mapping)
            normalized = mapped.copy()

            normalized["value"] = float(
                normalized["value"]
            )

            if normalized["type"] == "weight":

                value, unit = normalize_weight(
                    normalized["value"],
                    normalized["unit"]
                )

                normalized["value"] = value
                normalized["unit"] = unit

            patient_id = (
                f"{source}:"
                f"{normalized['source_patient_id']}"
            )

            if patient_id not in patient_index:
                raise ValueError(
                    f"Patient not found: {patient_id}"
                )

            observation = Observation(
                id=f"{source}:{normalized['id']}",
                type=normalized["type"],
                value=normalized["value"],
                unit=normalized["unit"],
                date=normalized["date"],
                source=source
            )

            result = {
                "original": record,
                "mapped": mapped,
                "normalized": normalized
            }

            observation.provenance = build_provenance(
                result, mapping, source
            )

            patient_index[patient_id].observations.append(
                observation
            )

        except Exception as error:

            errors.append(str(error))

        result = {
            "source": source,
            "original": record,
            "mapped": mapped,
            "normalized": normalized,
            "errors": errors
        }

        result["provenance"] = build_provenance(
            result, mapping, source
        )

        source_records.append(
            SourceRecord(**result)
        )

    return source_records


# 6. Collect Source Records
def collect_source_records():

    configuration = load_yaml(
        ROOT / "config" / "sources.yaml"
    )

    all_patients = []
    all_source_records = []

    clinical_types = {
        "medications": "medication_mapping",
        "allergies": "allergy_mapping",
        "diagnoses": "diagnosis_mapping"
    }

    for settings in configuration["sources"]:

        source = settings["name"]

        results = process_source(
            str(ROOT / settings["patients"]),
            str(ROOT / settings["patient_mapping"])
        )

        patients = build_patients(results, source)

        all_patients.extend(patients)

        for result in results:

            all_source_records.append(
                SourceRecord(**result)
            )

        if "observations" in settings:

            observation_records = process_observations(
                ROOT / settings["observations"],
                ROOT / settings["observation_mapping"],
                source,
                patients
            )

            all_source_records.extend(
                observation_records
            )

        # Process medications, allergies and diagnoses
        for record_type, mapping_key in clinical_types.items():

            if record_type in settings:

                clinical_records = process_clinical_records(
                    ROOT / settings[record_type],
                    ROOT / settings[mapping_key],
                    source,
                    patients,
                    record_type
                )

                all_source_records.extend(
                    clinical_records
                )

    return all_patients, all_source_records


# 7. Identity Matching
def run_identity_matching():

    patients, source_records = collect_source_records()

    matches = match_patients(patients)

    return patients, matches

# 8. Conflict Detection and Resolution
def process_conflicts(patients: list[Patient]):

    conflicts = []
    resolutions = []

    for patient in patients:

        # Observation conflicts
        detected = detect_conflicts(
            patient.observations
        )

        for item in detected:

            conflict = Conflict(
                id=str(uuid4()),
                patient_id=patient.id,
                field=item["type"],
                conflict_type="observation_mismatch",
                record_ids=[
                    obs.id
                    for obs in patient.observations
                    if obs.type == item["type"]
                    and obs.date == item["date"]
                    and obs.unit == item["unit"]
                ],
                values=[
                    str(v["value"])
                    for v in item["values"]
                ],
                sources=[
                    v["source"]
                    for v in item["values"]
                ],
                critical=True,
                status="NEEDS_HUMAN_REVIEW"
            )

            conflicts.append(conflict)

        # Medication, allergy and diagnosis conflicts
        clinical_conflicts = detect_clinical_conflicts(
            patient
        )

        conflicts.extend(clinical_conflicts)

    # Resolve all detected conflicts
    for conflict in conflicts:

        resolution = resolve_conflict(conflict)

        resolutions.append(resolution)

    return conflicts, resolutions

# 9. FHIR Export
def export_fhir(patients: list[Patient], conflicts):

    resources = []

    review_ids = {
        record_id
        for conflict in conflicts
        if conflict.status == "NEEDS_HUMAN_REVIEW"
        for record_id in conflict.record_ids
    }

    for patient in patients:

        fhir_id = str(
            uuid5(
                NAMESPACE_URL,
                f"urn:medbridge:patient:{patient.id}"
            )
        )

        record = {
            "source_patient_id": fhir_id,
            "name": patient.name,
            "gender": patient.gender,
            "birth_date": patient.birth_date.isoformat()
        }

        resource = patient_to_fhir(record)

        resource["identifier"] = [
            {
                "system": "urn:medbridge:patient",
                "value": patient.id
            }
        ]

        resources.append(resource)

        # Observations
        for observation in patient.observations:

            observation_resource = observation_to_fhir(
                observation,
                fhir_id
            )

            if observation.id in review_ids:
                mark_for_review(observation_resource)

            resources.append(observation_resource)

        # Medications
        for medication in patient.medications:

            resources.append(
                medication_to_fhir(
                    medication,
                    fhir_id,
                    medication.id in review_ids
                )
            )

        # Allergies
        for allergy in patient.allergies:

            resources.append(
                allergy_to_fhir(
                    allergy,
                    fhir_id,
                    allergy.id in review_ids
                )
            )

        # Diagnoses
        for diagnosis in patient.diagnoses:

            resources.append(
                diagnosis_to_fhir(
                    diagnosis,
                    fhir_id,
                    diagnosis.id in review_ids
                )
            )

    return resources


# 10. Main Pipeline
def run_pipeline() -> PipelineResult:

    run_id = str(uuid4())

    try:

        patients, source_records = collect_source_records()

        matches = match_patients(patients)

        conflicts, resolutions = process_conflicts(
            patients
        )

        fhir_resources = export_fhir(patients, conflicts)

        errors = [
            f"{record.source}: {error}"
            for record in source_records
            for error in record.errors
        ]

        return PipelineResult(
            run_id=run_id,
            status="completed",
            patients=patients,
            matches=matches,
            conflicts=conflicts,
            resolutions=resolutions,
            source_records=source_records,
            fhir_resources=fhir_resources,
            errors=errors
        )

    except Exception as error:

        return PipelineResult(
            run_id=run_id,
            status="failed",
            errors=[str(error)]
        )