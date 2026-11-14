import json
from pathlib import Path
from datetime import date, datetime

from canonical.models import (
    Patient,
    Observation,
    Medication,
    Allergy,
    Diagnosis,
    Encounter,
    Procedure,
    Immunization,
    Provenance,
    SourceRecord,
)

DATA_DIR = Path(__file__).parent / "data"


def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def reference_id(resource, *fields):
    for field in fields:
        ref = resource.get(field, {})
        if isinstance(ref, dict):
            value = ref.get("reference", "")
            if value:
                return value.split("/")[-1]
    return None


def coding_text(resource):
    concept = (
        resource.get("code")
        or resource.get("medicationCodeableConcept")
        or resource.get("vaccineCode")
        or {}
    )
    if concept.get("text"):
        return concept["text"]
    codings = concept.get("coding", [])
    if codings:
        return codings[0].get("display") or codings[0].get("code") or "Unknown"
    return "Unknown"


def create_sample():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    samples = {
        "patients.ndjson": [
            {
                "resourceType": "Patient",
                "id": "NDJSON-P001",
                "name": [{"text": "NDJSON TEST PATIENT"}],
                "gender": "male",
                "birthDate": "1985-04-12",
            }
        ],
        "observations.ndjson": [
            {
                "resourceType": "Observation",
                "id": "NDJSON-O001",
                "subject": {"reference": "Patient/NDJSON-P001"},
                "status": "final",
                "code": {"text": "Heart Rate"},
                "valueQuantity": {"value": 75, "unit": "bpm"},
                "effectiveDateTime": "2026-11-14",
            }
        ],
        "medications.ndjson": [
            {
                "resourceType": "MedicationStatement",
                "id": "NDJSON-M001",
                "subject": {"reference": "Patient/NDJSON-P001"},
                "status": "active",
                "medicationCodeableConcept": {"text": "Sample Medication"},
                "dosage": [{"text": "10 mg daily"}],
            }
        ],
        "allergies.ndjson": [
            {
                "resourceType": "AllergyIntolerance",
                "id": "NDJSON-A001",
                "patient": {"reference": "Patient/NDJSON-P001"},
                "code": {"text": "Penicillin"},
                "clinicalStatus": "active",
            }
        ],
        "conditions.ndjson": [
            {
                "resourceType": "Condition",
                "id": "NDJSON-C001",
                "subject": {"reference": "Patient/NDJSON-P001"},
                "code": {"text": "Hypertension"},
                "onsetDateTime": "2020-01-10",
            }
        ],
        "encounters.ndjson": [
            {
                "resourceType": "Encounter",
                "id": "NDJSON-E001",
                "subject": {"reference": "Patient/NDJSON-P001"},
                "status": "finished",
                "class": {"code": "AMB"},
                "period": {"start": "2026-11-14"},
            }
        ],
        "procedures.ndjson": [
            {
                "resourceType": "Procedure",
                "id": "NDJSON-PR001",
                "subject": {"reference": "Patient/NDJSON-P001"},
                "status": "completed",
                "code": {"text": "Sample Procedure"},
                "performedDateTime": "2026-11-14",
            }
        ],
        "immunizations.ndjson": [
            {
                "resourceType": "Immunization",
                "id": "NDJSON-I001",
                "patient": {"reference": "Patient/NDJSON-P001"},
                "status": "completed",
                "vaccineCode": {"text": "Sample Vaccine"},
                "occurrenceDateTime": "2026-11-14",
            }
        ],
    }

    for filename, records in samples.items():
        path = DATA_DIR / filename
        if not path.exists():
            with path.open("w", encoding="utf-8") as file:
                for record in records:
                    file.write(json.dumps(record) + "\n")


def fetch_bulk_fhir_data(directory=DATA_DIR):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    if not list(directory.glob("*.ndjson")) and not list(directory.glob("*.jsonl")):
        create_sample()

    resources = []
    errors = []

    for path in sorted(list(directory.glob("*.ndjson")) + list(directory.glob("*.jsonl"))):
        with path.open("r", encoding="utf-8-sig") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue
                try:
                    resource = json.loads(line)
                    if not isinstance(resource, dict) or not resource.get("resourceType"):
                        raise ValueError("Missing resourceType")
                    resources.append(resource)
                except Exception as exc:
                    errors.append(f"{path.name}:{line_number}: {exc}")

    patients = []
    patient_ids = set()
    observations = []
    medications = []
    allergies = []
    diagnoses = []
    encounters = []
    procedures = []
    immunizations = []
    source_records = []

    for resource in resources:
        kind = resource.get("resourceType")
        rid = str(resource.get("id") or f"generated-{len(source_records) + 1}")
        original = dict(resource)
        mapped = None

        try:
            if kind == "Patient":
                if rid in patient_ids:
                    continue
                names = resource.get("name", [])
                name = (
                    names[0].get("text")
                    if names and names[0].get("text")
                    else " ".join(names[0].get("given", []) + [names[0].get("family", "")]).strip()
                    if names else None
                )
                gender = resource.get("gender", "unknown")
                if gender not in ("male", "female"):
                    gender = "unknown"

                patient = Patient(
                    id=rid,
                    name=name,
                    birth_date=parse_date(resource.get("birthDate")),
                    gender=gender,
                    sources=["FHIR NDJSON"],
                )
                patients.append(patient)
                patient_ids.add(rid)
                mapped = patient.model_dump(mode="json")

            elif kind == "Observation":
                quantity = resource.get("valueQuantity", {})
                value = quantity.get("value")
                if value is None:
                    continue
                item = Observation(
                    id=rid,
                    type=coding_text(resource),
                    value=float(value),
                    unit=quantity.get("unit", ""),
                    date=parse_date(
                        resource.get("effectiveDateTime")
                        or resource.get("issued")
                    ) or date.today(),
                    source="FHIR NDJSON",
                )
                observations.append(item)
                mapped = item.model_dump(mode="json")

            elif kind in ("MedicationStatement", "MedicationRequest"):
                med_name = coding_text(resource)
                dosage = resource.get("dosage", [])
                dose = dosage[0].get("text") if dosage else None
                status = resource.get("status", "unknown")
                status = "active" if status in ("active", "intended", "on-hold") else (
                    "stopped" if status in ("stopped", "completed", "cancelled", "not-taken") else "unknown"
                )
                item = Medication(
                    id=rid,
                    name=med_name,
                    dose=dose,
                    status=status,
                    source="FHIR NDJSON",
                )
                medications.append(item)
                mapped = item.model_dump(mode="json")

            elif kind == "AllergyIntolerance":
                status = resource.get("clinicalStatus", "unknown")
                if isinstance(status, dict):
                    status = coding_text({"code": status})
                status = "confirmed" if status in ("active", "confirmed") else (
                    "unconfirmed" if status in ("unconfirmed", "inactive") else "unknown"
                )
                item = Allergy(
                    id=rid,
                    substance=coding_text(resource),
                    status=status,
                    source="FHIR NDJSON",
                )
                allergies.append(item)
                mapped = item.model_dump(mode="json")

            elif kind == "Condition":
                item = Diagnosis(
                    id=rid,
                    code=(resource.get("code", {}).get("coding") or [{}])[0].get("code"),
                    description=coding_text(resource),
                    source="FHIR NDJSON",
                )
                diagnoses.append(item)
                mapped = item.model_dump(mode="json")

            elif kind == "Encounter":
                period = resource.get("period", {})
                item = Encounter(
                    id=rid,
                    encounter_type=coding_text({"code": resource.get("class", {})}),
                    date=parse_date(period.get("start")),
                    status=resource.get("status", "unknown"),
                    source="FHIR NDJSON",
                )
                encounters.append(item)
                mapped = item.model_dump(mode="json")

            elif kind == "Procedure":
                item = Procedure(
                    id=rid,
                    name=coding_text(resource),
                    date=parse_date(resource.get("performedDateTime")),
                    status=resource.get("status", "unknown"),
                    source="FHIR NDJSON",
                )
                procedures.append(item)
                mapped = item.model_dump(mode="json")

            elif kind == "Immunization":
                item = Immunization(
                    id=rid,
                    vaccine=coding_text(resource),
                    date=parse_date(resource.get("occurrenceDateTime")),
                    status=resource.get("status", "unknown"),
                    source="FHIR NDJSON",
                )
                immunizations.append(item)
                mapped = item.model_dump(mode="json")

            if mapped is not None:
                source_records.append(
                    SourceRecord(
                        source="FHIR NDJSON",
                        original=original,
                        mapped=mapped,
                        normalized=mapped,
                        provenance=[
                            Provenance(
                                source="FHIR NDJSON",
                                original_field="resourceType",
                                original_value=kind,
                                transformations=["NDJSON line parsed", "Mapped to canonical model"],
                            )
                        ],
                    )
                )

        except Exception as exc:
            errors.append(f"{kind}/{rid}: {exc}")

    return {
        "patients": patients,
        "observations": observations,
        "medications": medications,
        "allergies": allergies,
        "diagnoses": diagnoses,
        "encounters": encounters,
        "procedures": procedures,
        "immunizations": immunizations,
        "source_records": source_records,
        "errors": errors,
    }


def main():
    result = fetch_bulk_fhir_data()

    print("BULK FHIR NDJSON CONNECTOR TEST")
    print("FILES:", len(list(DATA_DIR.glob("*.ndjson"))))
    print("PATIENTS:", len(result["patients"]))
    print("SOURCE RECORDS:", len(result["source_records"]))

    for key in (
        "observations",
        "medications",
        "allergies",
        "diagnoses",
        "encounters",
        "procedures",
        "immunizations",
    ):
        print(f"{key.upper()}: {len(result[key])}")

    print("ERRORS:", result["errors"])


if __name__ == "__main__":
    main()