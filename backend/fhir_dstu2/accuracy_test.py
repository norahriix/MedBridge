
import json
from pathlib import Path
from collections import Counter

from fhir_dstu2.connector import fetch_fhir_dstu2

DATA_DIR = Path(__file__).parent / "data"
patients, records, errors = fetch_fhir_dstu2()

bundle = json.loads(
    (DATA_DIR / "synthetic_dstu2.json").read_text(encoding="utf-8")
)
resources = [
    entry["resource"]
    for entry in bundle.get("entry", [])
    if "resource" in entry
]

patient = patients[0] if patients else None

def report(name, source, mapped):
    source = Counter(source)
    mapped = Counter(mapped)
    matched = sum((source & mapped).values())
    unmatched = sum((source - mapped).values())
    extra = sum((mapped - source).values())
    total = sum(source.values())
    rate = matched / total * 100 if total else 100

    print(f"\n{name}")
    print("SOURCE:", total)
    print("MAPPED:", sum(mapped.values()))
    print("MATCHED:", matched)
    print("UNMATCHED:", unmatched)
    print("EXTRA:", extra)
    print(f"MATCH RATE: {rate:.2f}%")

def source_resources(kind):
    return [r for r in resources if r["resourceType"] == kind]

def display(r, field):
    coding = r.get(field, {}).get("coding", [])
    return (
        coding[0].get("display") or coding[0].get("code")
        if coding else r.get(field, {}).get("text", "")
    )

print("===== FHIR DSTU2 ACCURACY AUDIT =====")

if patient:
    source_patient = next(r for r in resources if r["resourceType"] == "Patient")
    name = source_patient["name"][0]

    checks = [
        ("ID", source_patient["id"], patient.id),
        ("NAME", " ".join(
            name.get("given", []) + [name.get("family", "")]
        ).strip(), patient.name),
        ("GENDER", source_patient["gender"], patient.gender),
        ("BIRTH DATE", source_patient["birthDate"], str(patient.birth_date)),
    ]

    for label, source, mapped in checks:
        print(
            f"PATIENT {label}:",
            "MATCH" if source == mapped else "MISMATCH",
            "| SOURCE:", source,
            "| MAPPED:", mapped
        )

    report(
        "OBSERVATIONS",
        [
            (display(r, "code"), float(r["valueQuantity"]["value"]),
             r["valueQuantity"].get("unit", "unknown"))
            for r in source_resources("Observation")
        ],
        [(o.type, o.value, o.unit) for o in patient.observations]
    )

    report(
        "MEDICATIONS",
        [display(r, "medicationCodeableConcept")
         for r in source_resources("MedicationStatement")],
        [m.name for m in patient.medications]
    )

    report(
        "ALLERGIES",
        [display(r, "substance") for r in source_resources("AllergyIntolerance")],
        [a.substance for a in patient.allergies]
    )

    report(
        "DIAGNOSES",
        [
            (r.get("code", {}).get("coding", [{}])[0].get("code", ""),
             display(r, "code"))
            for r in source_resources("Condition")
        ],
        [(d.code or "", d.description) for d in patient.diagnoses]
    )

    report(
        "ENCOUNTERS",
        [r.get("class", {}).get("code", "")
         for r in source_resources("Encounter")],
        [e.encounter_type for e in patient.encounters]
    )

    report(
        "PROCEDURES",
        [display(r, "code") for r in source_resources("Procedure")],
        [p.name for p in patient.procedures]
    )

    report(
        "IMMUNIZATIONS",
        [display(r, "vaccineCode")
         for r in source_resources("Immunization")],
        [i.vaccine for i in patient.immunizations]
    )
else:
    print("ERROR: NO PATIENT FOUND")

print("\nSOURCE RECORD ERRORS:", errors)
print("===== AUDIT COMPLETE =====")
