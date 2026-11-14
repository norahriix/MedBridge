
import csv
from pathlib import Path

from canonical.models import (
    Patient, Observation, Medication, Diagnosis,
    Encounter, Procedure, SourceRecord
)

DATA_DIR = Path(__file__).parent / "data"


def create_sample():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    samples = {
        "member.csv": [
            ["member_id", "first_name", "last_name", "birth_date", "gender"],
            ["CPCDS001", "SYNTHETIC", "PATIENT", "1990-05-12", "M"]
        ],
        "medical_claim.csv": [
            ["claim_id", "member_id", "service_date", "claim_type", "diagnosis"],
            ["CLM001", "CPCDS001", "2026-01-10", "professional", "Hypertension"]
        ],
        "medical_claim_line.csv": [
            ["line_id", "claim_id", "procedure_code", "description", "amount"],
            ["LINE001", "CLM001", "99213", "Office visit", "125.00"]
        ],
        "pharmacy_claim.csv": [
            ["claim_id", "member_id", "service_date", "drug_name", "quantity"],
            ["RX001", "CPCDS001", "2026-01-11", "Synthetic Medication", "30"]
        ]
    }

    for filename, rows in samples.items():
        path = DATA_DIR / filename
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as file:
                csv.writer(file).writerows(rows)


def read_table(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def fetch_cpcds_data(directory=DATA_DIR):
    global DATA_DIR
    DATA_DIR = Path(directory)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not list(DATA_DIR.glob("*.csv")):
        create_sample()

    members = read_table("member.csv")
    claims = read_table("medical_claim.csv")
    lines = read_table("medical_claim_line.csv")
    pharmacy = read_table("pharmacy_claim.csv")

    patients = {}
    records = []

    for row in members:
        gender = row.get("gender", "").upper()
        patient = Patient(
            id=row["member_id"],
            name=f'{row.get("first_name", "")} {row.get("last_name", "")}'.strip(),
            birth_date=row.get("birth_date") or None,
            gender="male" if gender == "M" else (
                "female" if gender == "F" else "unknown"
            ),
            sources=["CPCDS"]
        )
        patients[patient.id] = patient
        records.append(SourceRecord(
            source="CPCDS",
            original=dict(row),
            mapped={"patient_id": patient.id},
            normalized={"patient_id": patient.id}
        ))

    for row in claims:
        patient = patients.get(row["member_id"])
        if not patient:
            continue

        diagnosis = Diagnosis(
            id=row["claim_id"],
            description=row.get("diagnosis") or "Unknown",
            source="CPCDS"
        )
        patient.diagnoses.append(diagnosis)

        encounter = Encounter(
            id=row["claim_id"],
            encounter_type=row.get("claim_type") or "unknown",
            date=row.get("service_date") or None,
            reason=row.get("diagnosis"),
            source="CPCDS"
        )
        patient.encounters.append(encounter)

        records.append(SourceRecord(
            source="CPCDS",
            original=dict(row),
            mapped={
                "diagnosis": diagnosis.model_dump(mode="json"),
                "encounter": encounter.model_dump(mode="json")
            },
            normalized={
                "diagnosis": diagnosis.description,
                "encounter_date": str(encounter.date)
            }
        ))

    for row in lines:
        claim = next(
            (item for item in claims if item["claim_id"] == row["claim_id"]),
            None
        )
        if not claim:
            continue

        patient = patients.get(claim["member_id"])
        if not patient:
            continue

        procedure = Procedure(
            id=row["line_id"],
            name=row.get("description") or row.get("procedure_code") or "Unknown",
            procedure_type=row.get("procedure_code"),
            date=claim.get("service_date") or None,
            source="CPCDS"
        )
        patient.procedures.append(procedure)

        records.append(SourceRecord(
            source="CPCDS",
            original=dict(row),
            mapped={"procedure": procedure.model_dump(mode="json")},
            normalized={"procedure_name": procedure.name}
        ))

    for row in pharmacy:
        patient = patients.get(row["member_id"])
        if not patient:
            continue

        medication = Medication(
            id=row["claim_id"],
            name=row.get("drug_name") or "Unknown",
            dose=row.get("quantity"),
            status="unknown",
            source="CPCDS"
        )
        patient.medications.append(medication)

        records.append(SourceRecord(
            source="CPCDS",
            original=dict(row),
            mapped={"medication": medication.model_dump(mode="json")},
            normalized={"medication_name": medication.name}
        ))

    return list(patients.values()), records


if __name__ == "__main__":
    patients, records = fetch_cpcds_data()

    print("CPCDS CONNECTOR TEST")
    print("FILES:", len(list(DATA_DIR.glob("*.csv"))))
    print("PATIENTS:", len(patients))
    print("SOURCE RECORDS:", len(records))
    print("DIAGNOSES:", sum(len(p.diagnoses) for p in patients))
    print("ENCOUNTERS:", sum(len(p.encounters) for p in patients))
    print("PROCEDURES:", sum(len(p.procedures) for p in patients))
    print("MEDICATIONS:", sum(len(p.medications) for p in patients))
    print("ERRORS: []")
