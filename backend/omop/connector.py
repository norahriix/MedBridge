
import csv
from pathlib import Path
from datetime import date

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


def read_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def create_sample():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    tables = {
        "person.csv": [
            {
                "person_id": "OMOP-P001",
                "gender_concept_id": "8507",
                "year_of_birth": "1985",
                "month_of_birth": "4",
                "day_of_birth": "12",
            }
        ],
        "measurement.csv": [
            {
                "measurement_id": "OMOP-O001",
                "person_id": "OMOP-P001",
                "measurement_concept_id": "Heart Rate",
                "measurement_date": "2026-11-14",
                "value_as_number": "75",
                "unit_source_value": "bpm",
            }
        ],
        "drug_exposure.csv": [
            {
                "drug_exposure_id": "OMOP-M001",
                "person_id": "OMOP-P001",
                "drug_source_value": "Sample Medication",
                "drug_exposure_start_date": "2026-11-14",
                "quantity": "10 mg daily",
            }
        ],
        "condition_occurrence.csv": [
            {
                "condition_occurrence_id": "OMOP-C001",
                "person_id": "OMOP-P001",
                "condition_source_value": "Hypertension",
                "condition_start_date": "2020-01-10",
            }
        ],
        "visit_occurrence.csv": [
            {
                "visit_occurrence_id": "OMOP-E001",
                "person_id": "OMOP-P001",
                "visit_source_value": "Outpatient",
                "visit_start_date": "2026-11-14",
            }
        ],
        "procedure_occurrence.csv": [
            {
                "procedure_occurrence_id": "OMOP-PR001",
                "person_id": "OMOP-P001",
                "procedure_source_value": "Sample Procedure",
                "procedure_date": "2026-11-14",
            }
        ],
        "drug_exposure_immunization.csv": [
            {
                "drug_exposure_id": "OMOP-I001",
                "person_id": "OMOP-P001",
                "drug_source_value": "Sample Vaccine",
                "drug_exposure_start_date": "2026-11-14",
                "quantity": "1 dose",
            }
        ],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for filename, rows in tables.items():
        path = DATA_DIR / filename
        if not path.exists():
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)


def fetch_omop_data(directory=DATA_DIR):
    global DATA_DIR
    directory = Path(directory)

    if not directory.exists() or not list(directory.glob("*.csv")):
        DATA_DIR = directory
        create_sample()

    tables = {
        "person": read_csv_from(directory, "person.csv"),
        "measurement": read_csv_from(directory, "measurement.csv"),
        "drug": read_csv_from(directory, "drug_exposure.csv"),
        "condition": read_csv_from(directory, "condition_occurrence.csv"),
        "visit": read_csv_from(directory, "visit_occurrence.csv"),
        "procedure": read_csv_from(directory, "procedure_occurrence.csv"),
        "immunization": read_csv_from(directory, "drug_exposure_immunization.csv"),
    }

    result = {
        "patients": [],
        "observations": [],
        "medications": [],
        "allergies": [],
        "diagnoses": [],
        "encounters": [],
        "procedures": [],
        "immunizations": [],
        "source_records": [],
        "errors": [],
    }

    for row in tables["person"]:
        try:
            year = row.get("year_of_birth")
            birth = f"{year}-{int(row.get('month_of_birth') or 1):02d}-{int(row.get('day_of_birth') or 1):02d}" if year else None
            gender_id = row.get("gender_concept_id")
            gender = "male" if gender_id == "8507" else "female" if gender_id == "8532" else "unknown"

            item = Patient(
                id=row["person_id"],
                birth_date=parse_date(birth),
                gender=gender,
                sources=["OMOP CDM"],
            )
            result["patients"].append(item)
            add_source(result, "person", row, item)
        except Exception as exc:
            result["errors"].append(f"person: {exc}")

    mappings = [
        ("measurement", "observations"),
        ("drug", "medications"),
        ("condition", "diagnoses"),
        ("visit", "encounters"),
        ("procedure", "procedures"),
        ("immunization", "immunizations"),
    ]

    for table, category in mappings:
        for row in tables[table]:
            try:
                rid = next((v for k, v in row.items() if k.endswith("_id") and k != "person_id"), None)
                if category == "observations":
                    item = Observation(
                        id=rid,
                        type=row.get("measurement_concept_id") or "Unknown",
                        value=float(row["value_as_number"]),
                        unit=row.get("unit_source_value") or "",
                        date=parse_date(row.get("measurement_date")) or date.today(),
                        source="OMOP CDM",
                    )
                elif category == "medications":
                    item = Medication(
                        id=rid,
                        name=row.get("drug_source_value") or "Unknown",
                        dose=row.get("quantity"),
                        status="unknown",
                        source="OMOP CDM",
                    )
                elif category == "diagnoses":
                    item = Diagnosis(
                        id=rid,
                        code=row.get("condition_source_value"),
                        description=row.get("condition_source_value") or "Unknown",
                        source="OMOP CDM",
                    )
                elif category == "encounters":
                    item = Encounter(
                        id=rid,
                        encounter_type=row.get("visit_source_value") or "Unknown",
                        date=parse_date(row.get("visit_start_date")),
                        source="OMOP CDM",
                    )
                elif category == "procedures":
                    item = Procedure(
                        id=rid,
                        name=row.get("procedure_source_value") or "Unknown",
                        date=parse_date(row.get("procedure_date")),
                        source="OMOP CDM",
                    )
                else:
                    item = Immunization(
                        id=rid,
                        vaccine=row.get("drug_source_value") or "Unknown",
                        date=parse_date(row.get("drug_exposure_start_date")),
                        source="OMOP CDM",
                    )

                result[category].append(item)
                add_source(result, table, row, item)

            except Exception as exc:
                result["errors"].append(f"{table}: {exc}")

    return result


def read_csv_from(directory, filename):
    path = directory / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def add_source(result, table, original, item):
    mapped = item.model_dump(mode="json")
    result["source_records"].append(
        SourceRecord(
            source="OMOP CDM",
            original=original,
            mapped=mapped,
            normalized=mapped,
            provenance=[
                Provenance(
                    source="OMOP CDM",
                    original_field="table",
                    original_value=table,
                    transformations=["CSV row parsed", "Mapped to canonical model"],
                )
            ],
        )
    )


def main():
    result = fetch_omop_data()

    print("OMOP CDM CONNECTOR TEST")
    print("FILES:", len(list(DATA_DIR.glob("*.csv"))))
    print("PATIENTS:", len(result["patients"]))
    print("SOURCE RECORDS:", len(result["source_records"]))

    for key in (
        "observations", "medications", "allergies",
        "diagnoses", "encounters", "procedures", "immunizations"
    ):
        print(f"{key.upper()}: {len(result[key])}")

    print("ERRORS:", result["errors"])


if __name__ == "__main__":
    main()
