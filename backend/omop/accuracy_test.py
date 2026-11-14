
from omop.connector import fetch_omop_data, DATA_DIR, read_csv_from
from datetime import date

def check(label, source_count, mapped_count, comparisons):
    matched = sum(a == b for a, b in comparisons)
    total = len(comparisons)
    accuracy = matched / total * 100 if total else 0
    print(
        f"{label}: SOURCE/MAPPED {source_count}/{mapped_count} | "
        f"MATCHED {matched}/{total} | ACCURACY {accuracy:.2f}%"
    )


def main():
    result = fetch_omop_data()

    print("===== OMOP CDM ACCURACY AUDIT =====")

    # Patient
    source = read_csv_from(DATA_DIR, "person.csv")
    mapped = {p.id: p.model_dump(mode="json") for p in result["patients"]}
    comparisons = []

    for row in source:
        item = mapped.get(row["person_id"])
        if not item:
            continue

        year = row.get("year_of_birth")
        birth = (
            f"{year}-{int(row.get('month_of_birth') or 1):02d}-{int(row.get('day_of_birth') or 1):02d}"
            if year else None
        )
        gender = (
            "male" if row.get("gender_concept_id") == "8507"
            else "female" if row.get("gender_concept_id") == "8532"
            else "unknown"
        )

        comparisons.extend([
            (row["person_id"], item["id"]),
            (birth, item["birth_date"]),
            (gender, item["gender"]),
        ])

    check("PATIENT", len(source), len(result["patients"]), comparisons)

    tests = [
        ("measurement.csv", "observations", "measurement_id", [
            ("measurement_concept_id", "type"),
            ("value_as_number", "value"),
            ("unit_source_value", "unit"),
            ("measurement_date", "date"),
        ]),
        ("drug_exposure.csv", "medications", "drug_exposure_id", [
            ("drug_source_value", "name"),
            ("quantity", "dose"),
        ]),
        ("condition_occurrence.csv", "diagnoses", "condition_occurrence_id", [
            ("condition_source_value", "description"),
        ]),
        ("visit_occurrence.csv", "encounters", "visit_occurrence_id", [
            ("visit_source_value", "encounter_type"),
            ("visit_start_date", "date"),
        ]),
        ("procedure_occurrence.csv", "procedures", "procedure_occurrence_id", [
            ("procedure_source_value", "name"),
            ("procedure_date", "date"),
        ]),
        ("drug_exposure_immunization.csv", "immunizations", "drug_exposure_id", [
            ("drug_source_value", "vaccine"),
            ("drug_exposure_start_date", "date"),
        ]),
    ]

    for filename, category, id_field, fields in tests:
        source = read_csv_from(DATA_DIR, filename)
        mapped_items = {
            item.id: item.model_dump(mode="json")
            for item in result[category]
        }
        comparisons = []

        for row in source:
            item = mapped_items.get(row[id_field])
            if not item:
                continue

            for source_field, mapped_field in fields:
                expected = row.get(source_field)
                actual = item.get(mapped_field)

                if mapped_field == "value" and actual is not None:
                    expected = float(expected)

                if mapped_field == "date" and actual:
                    actual = str(actual)[:10]

                comparisons.append((expected, actual))

        check(category.upper(), len(source), len(result[category]), comparisons)

    print("ALLERGIES: NOT TESTED - NO SYNTHETIC ALLERGY TABLE")
    print("SOURCE RECORD ERRORS:", result["errors"])


if __name__ == "__main__":
    main()
