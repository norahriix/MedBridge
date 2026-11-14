
import json
from pathlib import Path
from datetime import datetime

from canonical.models import (
    Patient, Observation, Medication, Allergy, Diagnosis,
    Encounter, Procedure, Immunization, Provenance, SourceRecord
)

DATA_DIR = Path(__file__).parent / "data"
SOURCE = "FHIR_STU3"


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None


def make_provenance(field, value):
    return Provenance(
        source=SOURCE,
        original_field=field,
        original_value=json.dumps(value, ensure_ascii=False)
        if isinstance(value, (dict, list)) else str(value),
        transformations=["FHIR STU3 resource extraction"]
    )


def make_sample():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    resources = [
        {
            "resourceType": "Patient",
            "id": "STU3-P001",
            "name": [{"family": "TEST", "given": ["PATIENT"]}],
            "birthDate": "1990-01-01",
            "gender": "male"
        },
        {
            "resourceType": "Observation",
            "id": "STU3-OBS001",
            "status": "final",
            "code": {"coding": [{"code": "GLU", "display": "Glucose"}]},
            "subject": {"reference": "Patient/STU3-P001"},
            "effectiveDateTime": "2026-11-14",
            "valueQuantity": {"value": 110, "unit": "mg/dL"}
        },
        {
            "resourceType": "MedicationStatement",
            "id": "STU3-MED001",
            "status": "active",
            "medicationCodeableConcept": {
                "coding": [{"display": "Metformin"}]
            },
            "subject": {"reference": "Patient/STU3-P001"},
            "dosage": [{"text": "500 mg"}]
        },
        {
            "resourceType": "AllergyIntolerance",
            "id": "STU3-ALL001",
            "patient": {"reference": "Patient/STU3-P001"},
            "code": {"coding": [{"display": "Penicillin"}]},
            "clinicalStatus": "active",
            "reaction": [{"manifestation": [{"text": "Rash"}]}]
        },
        {
            "resourceType": "Condition",
            "id": "STU3-DX001",
            "subject": {"reference": "Patient/STU3-P001"},
            "code": {"coding": [{"code": "E11.9", "display": "Diabetes mellitus"}]},
            "onsetDateTime": "2026-01-01"
        },
        {
            "resourceType": "Encounter",
            "id": "STU3-ENC001",
            "status": "finished",
            "class": {"code": "outpatient"},
            "subject": {"reference": "Patient/STU3-P001"},
            "period": {"start": "2026-11-14"}
        },
        {
            "resourceType": "Procedure",
            "id": "STU3-PR001",
            "status": "completed",
            "subject": {"reference": "Patient/STU3-P001"},
            "code": {"coding": [{"display": "Blood test"}]},
            "performedDateTime": "2026-11-14"
        },
        {
            "resourceType": "Immunization",
            "id": "STU3-IMM001",
            "status": "completed",
            "patient": {"reference": "Patient/STU3-P001"},
            "vaccineCode": {"coding": [{"display": "Influenza vaccine"}]},
            "date": "2026-11-14"
        }
    ]

    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": r} for r in resources]
    }

    (DATA_DIR / "synthetic_stu3.json").write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def fetch_fhir_stu3(directory=DATA_DIR):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    files = list(directory.glob("*.json"))
    if not files:
        make_sample()
        files = list(directory.glob("*.json"))

    patients = {}
    records = []
    errors = []

    for file_path in files:
        try:
            bundle = json.loads(file_path.read_text(encoding="utf-8"))
            entries = bundle.get("entry", [])

            for entry in entries:
                resource = entry.get("resource", {})
                kind = resource.get("resourceType")
                rid = resource.get("id", "unknown")

                if kind == "Patient":
                    names = resource.get("name", [{}])
                    name_data = names[0] if names else {}
                    full_name = " ".join(
                        name_data.get("given", []) +
                        ([name_data["family"]] if name_data.get("family") else [])
                    ) or None

                    gender = resource.get("gender", "unknown")
                    if gender not in ("male", "female"):
                        gender = "unknown"

                    patients[rid] = {
                        "id": rid,
                        "name": full_name,
                        "birth_date": parse_date(resource.get("birthDate")),
                        "gender": gender,
                        "sources": [SOURCE],
                        "observations": [],
                        "medications": [],
                        "allergies": [],
                        "diagnoses": [],
                        "encounters": [],
                        "procedures": [],
                        "immunizations": [],
                    }

            def patient_for(resource):
                ref = (
                    resource.get("subject", {}).get("reference")
                    or resource.get("patient", {}).get("reference")
                    or ""
                )
                return ref.split("/")[-1]

            for entry in entries:
                resource = entry.get("resource", {})
                kind = resource.get("resourceType")
                rid = resource.get("id", "unknown")
                pid = patient_for(resource)

                if kind == "Patient" or pid not in patients:
                    continue

                patient = patients[pid]
                mapped = None

                if kind == "Observation":
                    quantity = resource.get("valueQuantity", {})
                    value = quantity.get("value")
                    code = resource.get("code", {}).get("coding", [{}])[0]
                    if value is not None:
                        mapped = Observation(
                            id=rid,
                            type=code.get("display") or code.get("code") or "unknown",
                            value=float(value),
                            unit=quantity.get("unit", "unknown"),
                            date=parse_date(
                                resource.get("effectiveDateTime")
                                or resource.get("issued")
                            ) or parse_date("2026-01-01"),
                            source=SOURCE,
                            provenance=[
                                make_provenance("valueQuantity", quantity),
                                make_provenance("code", resource.get("code", {}))
                            ]
                        )
                        patient["observations"].append(mapped)

                elif kind == "MedicationStatement":
                    med = resource.get("medicationCodeableConcept", {})
                    coding = med.get("coding", [{}])
                    medication_name = (
                        coding[0].get("display")
                        if coding else med.get("text")
                    ) or "unknown"
                    dosage = resource.get("dosage", [{}])
                    mapped = Medication(
                        id=rid,
                        name=medication_name,
                        dose=dosage[0].get("text") if dosage else None,
                        status=resource.get("status", "unknown"),
                        source=SOURCE,
                        provenance=[make_provenance("medicationCodeableConcept", med)]
                    )
                    patient["medications"].append(mapped)

                elif kind == "AllergyIntolerance":
                    code = resource.get("code", {}).get("coding", [{}])
                    substance = (
                        code[0].get("display") if code else None
                    ) or resource.get("code", {}).get("text") or "unknown"
                    reactions = resource.get("reaction", [])
                    manifestation = (
                        reactions[0].get("manifestation", [{}])[0].get("text")
                        if reactions else None
                    )
                    clinical = resource.get("clinicalStatus", "unknown")
                    mapped = Allergy(
                        id=rid,
                        substance=substance,
                        reaction=manifestation,
                        status="confirmed" if clinical == "active" else "unknown",
                        source=SOURCE,
                        provenance=[make_provenance("code", resource.get("code", {}))]
                    )
                    patient["allergies"].append(mapped)

                elif kind == "Condition":
                    coding = resource.get("code", {}).get("coding", [{}])
                    code = coding[0] if coding else {}
                    mapped = Diagnosis(
                        id=rid,
                        code=code.get("code"),
                        description=code.get("display") or "unknown",
                        source=SOURCE,
                        provenance=[make_provenance("code", resource.get("code", {}))]
                    )
                    patient["diagnoses"].append(mapped)

                elif kind == "Encounter":
                    mapped = Encounter(
                        id=rid,
                        encounter_type=resource.get("class", {}).get("code", "unknown"),
                        date=parse_date(resource.get("period", {}).get("start")),
                        status=resource.get("status", "unknown"),
                        source=SOURCE,
                        provenance=[make_provenance("class", resource.get("class", {}))]
                    )
                    patient["encounters"].append(mapped)

                elif kind == "Procedure":
                    coding = resource.get("code", {}).get("coding", [{}])
                    procedure_name = (
                        coding[0].get("display") if coding else None
                    ) or "unknown"
                    mapped = Procedure(
                        id=rid,
                        name=procedure_name,
                        date=parse_date(resource.get("performedDateTime")),
                        status=resource.get("status", "unknown"),
                        source=SOURCE,
                        provenance=[make_provenance("code", resource.get("code", {}))]
                    )
                    patient["procedures"].append(mapped)

                elif kind == "Immunization":
                    coding = resource.get("vaccineCode", {}).get("coding", [{}])
                    vaccine = (
                        coding[0].get("display") if coding else None
                    ) or "unknown"
                    mapped = Immunization(
                        id=rid,
                        vaccine=vaccine,
                        date=parse_date(resource.get("date")),
                        status=resource.get("status", "unknown"),
                        source=SOURCE,
                        provenance=[make_provenance("vaccineCode", resource.get("vaccineCode", {}))]
                    )
                    patient["immunizations"].append(mapped)

                if mapped is not None:
                    records.append(
                        SourceRecord(
                            source=SOURCE,
                            original=resource,
                            mapped=mapped.model_dump(mode="json"),
                            normalized=mapped.model_dump(mode="json"),
                            provenance=mapped.provenance
                        )
                    )

        except Exception as error:
            errors.append(f"{file_path.name}: {error}")

    result = [Patient(**data) for data in patients.values()]
    return result, records, errors


if __name__ == "__main__":
    patients, records, errors = fetch_fhir_stu3()

    print("FHIR STU3 CONNECTOR TEST")
    print("FILES:", len(list(DATA_DIR.glob("*.json"))))
    print("PATIENTS:", len(patients))
    print("SOURCE RECORDS:", len(records))
    print("OBSERVATIONS:", sum(len(p.observations) for p in patients))
    print("MEDICATIONS:", sum(len(p.medications) for p in patients))
    print("ALLERGIES:", sum(len(p.allergies) for p in patients))
    print("DIAGNOSES:", sum(len(p.diagnoses) for p in patients))
    print("ENCOUNTERS:", sum(len(p.encounters) for p in patients))
    print("PROCEDURES:", sum(len(p.procedures) for p in patients))
    print("IMMUNIZATIONS:", sum(len(p.immunizations) for p in patients))
    print("ERRORS:", errors)
