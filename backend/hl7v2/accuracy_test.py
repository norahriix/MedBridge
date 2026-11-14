
from pathlib import Path
from collections import Counter

from hl7v2.connector import fetch_hl7_data

DATA_DIR = Path(__file__).parent / "data"

patients, records, errors = fetch_hl7_data()

source_segments = []

for file in DATA_DIR.glob("*.hl7"):
    content = file.read_text(encoding="utf-8", errors="replace")
    source_segments.extend(
        line.strip()
        for line in content.replace("\n", "\r").split("\r")
        if line.strip()
    )

def fields(segment):
    return segment.split("|")

def component(value, index=0):
    parts = value.split("^")
    return parts[index] if index < len(parts) else ""

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

    return unmatched == 0 and extra == 0

patient = patients[0] if patients else None

print("===== HL7 V2 ACCURACY AUDIT =====")

if patient:
    pid = next(s for s in source_segments if s.startswith("PID|"))
    pf = fields(pid)

    patient_checks = {
        "ID": (component(pf[3]), patient.id),
        "NAME": (
            " ".join(x for x in [
                component(pf[5], 1),
                component(pf[5], 0)
            ] if x),
            patient.name
        ),
        "GENDER": (
            {"M": "male", "F": "female"}.get(pf[8], "unknown"),
            patient.gender
        ),
    }

    for label, (source, mapped) in patient_checks.items():
        print(
            f"PATIENT {label}:",
            "MATCH" if source == mapped else "MISMATCH",
            "| SOURCE:", source,
            "| MAPPED:", mapped
        )

    report(
        "OBSERVATIONS",
        [
            (component(fields(s)[3], 1), float(fields(s)[5]),
             fields(s)[6])
            for s in source_segments if s.startswith("OBX|")
        ],
        [
            (o.type, o.value, o.unit)
            for o in patient.observations
        ]
    )

    report(
        "MEDICATIONS",
        [
            component(fields(s)[5], 1) or component(fields(s)[5])
            for s in source_segments if s.startswith("RXA|")
        ],
        [m.name for m in patient.medications]
    )

    report(
        "ALLERGIES",
        [
            component(fields(s)[3], 1) or component(fields(s)[3])
            for s in source_segments if s.startswith("AL1|")
        ],
        [a.substance for a in patient.allergies]
    )

    report(
        "DIAGNOSES",
        [
            (component(fields(s)[3]), component(fields(s)[3], 1))
            for s in source_segments if s.startswith("DG1|")
        ],
        [(d.code or "", d.description) for d in patient.diagnoses]
    )

    report(
        "ENCOUNTERS",
        [
            fields(s)[2]
            for s in source_segments if s.startswith("PV1|")
        ],
        [e.encounter_type for e in patient.encounters]
    )

    report(
        "PROCEDURES",
        [
            component(fields(s)[3], 1) or component(fields(s)[3])
            for s in source_segments if s.startswith("PR1|")
        ],
        [p.name for p in patient.procedures]
    )

else:
    print("ERROR: NO PATIENTS FOUND")

print("\nSOURCE RECORD ERRORS:", errors)
print("===== AUDIT COMPLETE =====")
