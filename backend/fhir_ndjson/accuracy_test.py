
import json
from pathlib import Path

from fhir_ndjson.connector import fetch_bulk_fhir_data, DATA_DIR


def read_sources():
    records = []
    for path in DATA_DIR.glob("*.ndjson"):
        with path.open("r", encoding="utf-8-sig") as file:
            for line in file:
                if line.strip():
                    records.append(json.loads(line))
    return records


def text_value(resource):
    concept = (
        resource.get("code")
        or resource.get("medicationCodeableConcept")
        or resource.get("vaccineCode")
        or {}
    )
    if concept.get("text"):
        return concept["text"]
    coding = concept.get("coding", [])
    return coding[0].get("display") or coding[0].get("code") if coding else "Unknown"


def audit(label, source, mapped, checks):
    matched = sum(1 for a, b in checks if a == b)
    total = len(checks)
    rate = matched / total * 100 if total else 0
    print(
        f"{label}: SOURCE/MAPPED {source}/{mapped} | "
        f"FIELDS MATCHED {matched}/{total} | ACCURACY {rate:.2f}%"
    )


def main():
    result = fetch_bulk_fhir_data()
    sources = read_sources()

    mapped_records = {
        item.original.get("id"): item.mapped
        for item in result["source_records"]
    }

    print("===== BULK FHIR NDJSON ACCURACY AUDIT =====")

    patient_sources = [r for r in sources if r.get("resourceType") == "Patient"]
    for source in patient_sources:
        mapped = mapped_records.get(source.get("id"))
        if not mapped:
            print("PATIENT:", source.get("id"), "NOT MAPPED")
            continue

        names = source.get("name", [])
        expected_name = names[0].get("text") if names else None
        checks = [
            (source.get("id"), mapped.get("id")),
            (expected_name, mapped.get("name")),
            (source.get("gender", "unknown"), mapped.get("gender")),
            (source.get("birthDate"), mapped.get("birth_date")),
        ]
        audit("PATIENT", 1, 1, checks)

    categories = {
        "Observation": ("observations", [
            ("code", lambda r: text_value(r), "type"),
            ("value", lambda r: r.get("valueQuantity", {}).get("value"), "value"),
            ("unit", lambda r: r.get("valueQuantity", {}).get("unit", ""), "unit"),
            ("date", lambda r: (r.get("effectiveDateTime") or r.get("issued") or "")[:10], "date"),
        ]),
        "MedicationStatement": ("medications", [
            ("name", lambda r: text_value(r), "name"),
        ]),
        "AllergyIntolerance": ("allergies", [
            ("substance", lambda r: text_value(r), "substance"),
        ]),
        "Condition": ("diagnoses", [
            ("description", lambda r: text_value(r), "description"),
        ]),
        "Encounter": ("encounters", [
            ("date", lambda r: (r.get("period", {}).get("start") or "")[:10], "date"),
        ]),
        "Procedure": ("procedures", [
            ("name", lambda r: text_value(r), "name"),
            ("date", lambda r: (r.get("performedDateTime") or "")[:10], "date"),
        ]),
        "Immunization": ("immunizations", [
            ("vaccine", lambda r: text_value(r), "vaccine"),
            ("date", lambda r: (r.get("occurrenceDateTime") or "")[:10], "date"),
        ]),
    }

    for resource_type, (category, fields) in categories.items():
        source_items = [
            r for r in sources if r.get("resourceType") == resource_type
        ]
        mapped_items = result[category]
        checks = []

        for source in source_items:
            mapped = mapped_records.get(source.get("id"))
            if not mapped:
                continue
            checks.append((source.get("id"), mapped.get("id")))

            for _, getter, mapped_field in fields:
                expected = getter(source)
                actual = mapped.get(mapped_field)

                if mapped_field == "date" and actual:
                    actual = str(actual)[:10]

                checks.append((expected, actual))

        audit(resource_type, len(source_items), len(mapped_items), checks)

    print("SOURCE RECORD ERRORS:", result["errors"])


if __name__ == "__main__":
    main()
