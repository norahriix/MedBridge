
import csv
from pathlib import Path

from canonical.models import (
    Patient, Diagnosis, Medication, Encounter, SourceRecord
)

DATA_DIR = Path(__file__).parent / "data"


def create_sample():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    samples = {
        "beneficiary.csv": [
            ["BENE_ID", "BENE_BIRTH_DT", "BENE_SEX_IDENT_CD"],
            ["BFD001", "19500115", "1"]
        ],
        "inpatient_claim.csv": [
            ["DESYNPUF_ID", "CLM_ID", "CLM_FROM_DT", "CLM_ADMSN_DT"],
            ["BFD001", "CLAIM001", "20260110", "20260110"]
        ],
        "diagnosis.csv": [
            ["DESYNPUF_ID", "CLM_ID", "ICD9_DGNS_CD"],
            ["BFD001", "CLAIM001", "4019"]
        ],
        "prescription.csv": [
            ["DESYNPUF_ID", "PDE_ID", "SRVC_DT", "PROD_SRVC_ID"],
            ["BFD001", "RX001", "20260111", "SYNTH-MED-001"]
        ]
    }

    for filename, rows in samples.items():
        path = DATA_DIR / filename
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)


def read_table(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    try:
        from datetime import datetime
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def fetch_bfd_data(directory=DATA_DIR):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    if not list(directory.glob("*.csv")):
        create_sample()

    beneficiaries = read_table("beneficiary.csv")
    claims = read_table("inpatient_claim.csv")
    diagnoses = read_table("diagnosis.csv")
    prescriptions = read_table("prescription.csv")

    patients = {}
    records = []

    for row in beneficiaries:
        sex = row.get("BENE_SEX_IDENT_CD", "")
        patient = Patient(
            id=row["BENE_ID"],
            birth_date=parse_date(row.get("BENE_BIRTH_DT")),
            gender="male" if sex == "1" else (
                "female" if sex == "2" else "unknown"
            ),
            sources=["BFD RIF"]
        )
        patients[patient.id] = patient

        records.append(SourceRecord(
            source="BFD RIF",
            original=dict(row),
            mapped={"patient_id": patient.id},
            normalized={"patient_id": patient.id}
        ))

    for row in claims:
        patient = patients.get(row["DESYNPUF_ID"])
        if not patient:
            continue

        encounter = Encounter(
            id=row["CLM_ID"],
            encounter_type="inpatient",
            date=parse_date(row.get("CLM_ADMSN_DT")),
            reason="Inpatient claim",
            source="BFD RIF"
        )
        patient.encounters.append(encounter)

        records.append(SourceRecord(
            source="BFD RIF",
            original=dict(row),
            mapped={"encounter": encounter.model_dump(mode="json")},
            normalized={"encounter_date": str(encounter.date)}
        ))

    for row in diagnoses:
        patient = patients.get(row["DESYNPUF_ID"])
        if not patient:
            continue

        diagnosis = Diagnosis(
            id=f'{row["CLM_ID"]}-{row["ICD9_DGNS_CD"]}',
            code=row["ICD9_DGNS_CD"],
            description=row["ICD9_DGNS_CD"],
            source="BFD RIF"
        )
        patient.diagnoses.append(diagnosis)

        records.append(SourceRecord(
            source="BFD RIF",
            original=dict(row),
            mapped={"diagnosis": diagnosis.model_dump(mode="json")},
            normalized={"diagnosis_code": diagnosis.code}
        ))

    for row in prescriptions:
        patient = patients.get(row["DESYNPUF_ID"])
        if not patient:
            continue

        medication = Medication(
            id=row["PDE_ID"],
            name=row["PROD_SRVC_ID"],
            status="unknown",
            source="BFD RIF"
        )
        patient.medications.append(medication)

        records.append(SourceRecord(
            source="BFD RIF",
            original=dict(row),
            mapped={"medication": medication.model_dump(mode="json")},
            normalized={"medication_name": medication.name}
        ))

    return list(patients.values()), records


if __name__ == "__main__":
    patients, records = fetch_bfd_data()

    print("BFD RIF CONNECTOR TEST")
    print("FILES:", len(list(DATA_DIR.glob("*.csv"))))
    print("PATIENTS:", len(patients))
    print("SOURCE RECORDS:", len(records))
    print("DIAGNOSES:", sum(len(p.diagnoses) for p in patients))
    print("ENCOUNTERS:", sum(len(p.encounters) for p in patients))
    print("MEDICATIONS:", sum(len(p.medications) for p in patients))
    print("ERRORS:", sum(len(r.errors) for r in records))
