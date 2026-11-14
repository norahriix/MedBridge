
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

from ccda.connector import (
    fetch_ccda_data,
    patient_from_document,
    find_section,
)

DATA_DIR = Path.home() / "Downloads" / "MedBridge_CCDA_Test" / "ccda"


def tag(element):
    return element.tag.split("}")[-1] if element is not None else ""


def child(element, name):
    if element is None:
        return None
    return next((x for x in list(element) if tag(x) == name), None)


def raw_date(observation):
    effective = child(observation, "effectiveTime")
    if effective is None:
        return None

    value = effective.attrib.get("value")

    if not value:
        low = child(effective, "low")
        value = low.attrib.get("value") if low is not None else None

    if not value:
        return None

    value = value.strip()

    try:
        if len(value) >= 8 and value[:8].isdigit():
            return datetime.strptime(value[:8], "%Y%m%d").date()

        if len(value) >= 10:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        pass

    return None


patients, records = fetch_ccda_data()
mapped = {p.id: p for p in patients}

checked = 0
correct = 0
wrong = 0
missing_source = 0
missing_mapped = 0
count_mismatch = 0

for file_path in sorted(DATA_DIR.glob("*.xml")):
    root = ET.parse(file_path).getroot()
    patient = patient_from_document(root, file_path.name)

    source_dates = []

    for section_name in ("Diagnostic Results", "Vital Signs"):
        section = find_section(root, section_name)

        if section is None:
            continue

        for obs in section.iter():
            if tag(obs) != "observation":
                continue

            value_node = child(obs, "value")
            if value_node is None:
                continue

            raw_value = value_node.attrib.get("value")

            try:
                float(raw_value)
            except (ValueError, TypeError):
                continue

            date = raw_date(obs)

            if date is None:
                missing_source += 1
            else:
                source_dates.append(date)

    mapped_patient = mapped.get(patient.id)

    mapped_dates = (
        [o.date for o in mapped_patient.observations]
        if mapped_patient else []
    )

    if len(source_dates) != len(mapped_dates):
        count_mismatch += 1

    for index, source_date in enumerate(source_dates):
        checked += 1

        if index >= len(mapped_dates):
            missing_mapped += 1
        elif mapped_dates[index] is None:
            missing_mapped += 1
        elif source_date == mapped_dates[index]:
            correct += 1
        else:
            wrong += 1
            if wrong <= 5:
                print("DATE MISMATCH:", file_path.name)
                print("XML:", source_date)
                print("MAPPED:", mapped_dates[index])
                print("--------------------")

print("\n===== DATE ACCURACY RESULTS =====")
print("SOURCE DATES CHECKED:", checked)
print("CORRECT DATES:", correct)
print("WRONG DATES:", wrong)
print("MISSING SOURCE DATES:", missing_source)
print("MISSING MAPPED DATES:", missing_mapped)
print("FILES WITH COUNT MISMATCH:", count_mismatch)

accuracy = (correct / checked * 100) if checked else 0
print("DATE ACCURACY: {:.2f}%".format(accuracy))
print("================================")
