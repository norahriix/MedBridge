
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter

from ccda.connector import (
    fetch_ccda_data,
    patient_from_document,
    find_section,
    children,
    first_descendant,
    first_child,
    text_of,
    attr,
)

DATA_DIR = Path.home() / "Downloads" / "MedBridge_CCDA_Test" / "ccda"


def normalize(value):
    return " ".join(str(value or "").split()).strip().casefold()


patients, records = fetch_ccda_data()
mapped = {p.id: p for p in patients}

source_count = 0
mapped_count = 0
name_correct = 0
dose_correct = 0
status_correct = 0
name_missing = 0
dose_missing = 0
status_missing = 0
count_mismatch = 0
examples = []

for file_path in sorted(DATA_DIR.glob("*.xml")):
    root = ET.parse(file_path).getroot()
    source_patient = patient_from_document(root, file_path.name)

    section = find_section(root, "Medications")
    source_items = []

    if section is not None:
        for entry in children(section, "entry"):
            activity = first_descendant(entry, "substanceAdministration")
            if activity is None:
                continue

            material = first_descendant(activity, "manufacturedMaterial")
            name_node = first_child(material, "name")
            code_node = first_child(material, "code")

            name = (
                text_of(name_node)
                or attr(code_node, "displayName")
                or "Unknown medication"
            )

            status_node = first_child(activity, "statusCode")
            raw_status = attr(status_node, "code", "unknown").lower()

            status = (
                "active" if raw_status in ("active", "new")
                else "stopped" if raw_status in (
                    "completed", "aborted", "cancelled", "suspended"
                )
                else "unknown"
            )

            dose_node = first_child(activity, "doseQuantity")
            dose_value = attr(dose_node, "value")
            dose_unit = attr(dose_node, "unit")

            dose = (
                f"{dose_value} {dose_unit or ''}".strip()
                if dose_value else None
            )

            source_items.append((name, dose, status))

    mapped_patient = mapped.get(source_patient.id)
    mapped_items = mapped_patient.medications if mapped_patient else []

    source_count += len(source_items)
    mapped_count += len(mapped_items)

    if len(source_items) != len(mapped_items):
        count_mismatch += 1

    # مقارنة مجموعات القيم مع الحفاظ على التكرارات
    for field_index, counters in enumerate((
        (name_correct, name_missing),
        (dose_correct, dose_missing),
        (status_correct, status_missing),
    )):
        pass

    source_names = Counter(normalize(x[0]) for x in source_items)
    mapped_names = Counter(normalize(x.name) for x in mapped_items)

    source_doses = Counter(normalize(x[1]) for x in source_items)
    mapped_doses = Counter(normalize(x.dose) for x in mapped_items)

    source_statuses = Counter(normalize(x[2]) for x in source_items)
    mapped_statuses = Counter(normalize(x.status) for x in mapped_items)

    name_correct += sum((source_names & mapped_names).values())
    dose_correct += sum((source_doses & mapped_doses).values())
    status_correct += sum((source_statuses & mapped_statuses).values())

    name_missing += sum((source_names - mapped_names).values())
    dose_missing += sum((source_doses - mapped_doses).values())
    status_missing += sum((source_statuses - mapped_statuses).values())

    if len(examples) < 5 and source_items and mapped_items:
        examples.append((file_path.name, source_items[0], mapped_items[0]))

print("\n===== MEDICATION CONVERSION AUDIT =====")
print("SOURCE MEDICATIONS:", source_count)
print("MAPPED MEDICATIONS:", mapped_count)
print("FILES WITH COUNT MISMATCH:", count_mismatch)

def report(label, correct, missing):
    total = correct + missing
    accuracy = correct / total * 100 if total else 0
    print(f"\n{label}")
    print("MATCHED:", correct)
    print("UNMATCHED:", missing)
    print("MATCH RATE: {:.2f}%".format(accuracy))

report("MEDICATION NAME", name_correct, name_missing)
report("MEDICATION DOSE", dose_correct, dose_missing)
report("MEDICATION STATUS", status_correct, status_missing)

print("\n===== SAMPLE RECORDS =====")
for filename, source, mapped_item in examples:
    print("FILE:", filename)
    print("SOURCE:", source)
    print("MAPPED:", (
        mapped_item.name,
        mapped_item.dose,
        mapped_item.status,
    ))
    print("--------------------")

print("======================================")
