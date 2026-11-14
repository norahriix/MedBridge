
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter

from ccda.connector import fetch_ccda_data

DIRECTORY = Path.home() / "Downloads" / "MedBridge_CCDA_Test" / "ccda"

def local_name(tag):
    return tag.split("}")[-1] if "}" in tag else tag

def original_codes(root):
    codes = Counter()
    for element in root.iter():
        if local_name(element.tag) == "code":
            code = element.attrib.get("code")
            if code:
                codes[code] += 1
    return codes

def original_dates(root):
    dates = Counter()
    for element in root.iter():
        if local_name(element.tag) in ("effectiveTime", "birthTime"):
            for key in ("value",):
                value = element.attrib.get(key)
                if value:
                    dates[value[:8]] += 1
            for child in element.iter():
                value = child.attrib.get("value")
                if value:
                    dates[value[:8]] += 1
    return dates

def original_numeric_values(root):
    values = Counter()
    for element in root.iter():
        if local_name(element.tag) == "value":
            value = element.attrib.get("value")
            if value:
                try:
                    values[float(value)] += 1
                except ValueError:
                    pass
    return values

patients, records = fetch_ccda_data()

source_codes = Counter()
source_dates = Counter()
source_values = Counter()
xml_files = list(DIRECTORY.glob("*.xml"))
parse_errors = 0

for file in xml_files:
    try:
        root = ET.parse(file).getroot()
        source_codes.update(original_codes(root))
        source_dates.update(original_dates(root))
        source_values.update(original_numeric_values(root))
    except Exception:
        parse_errors += 1

mapped_codes = Counter()
mapped_dates = Counter()
mapped_values = Counter()

for patient in patients:
    for category in (
        "observations", "medications", "allergies",
        "diagnoses", "encounters", "procedures",
        "immunizations"
    ):
        for item in getattr(patient, category, []):
            for provenance in getattr(item, "provenance", []):
                original = provenance.original_value
                field = provenance.original_field.lower()

                if "code" in field and original:
                    mapped_codes.update([original])

                if "date" in field or "time" in field:
                    if original:
                        mapped_dates.update([original[:8]])

            if category == "observations":
                try:
                    mapped_values.update([float(item.value)])
                except (ValueError, TypeError):
                    pass

common_codes = sum((source_codes & mapped_codes).values())
common_dates = sum((source_dates & mapped_dates).values())
common_values = sum((source_values & mapped_values).values())

print("\n===== CCDA CONVERSION ACCURACY AUDIT =====")
print("XML FILES:", len(xml_files))
print("PARSE ERRORS:", parse_errors)
print("PATIENTS:", len(patients))
print("SOURCE UNIQUE CODES:", len(source_codes))
print("MAPPED UNIQUE CODES:", len(mapped_codes))
print("COMMON CODE OCCURRENCES:", common_codes)
print("SOURCE DATE VALUES:", sum(source_dates.values()))
print("MAPPED DATE VALUES:", sum(mapped_dates.values()))
print("COMMON DATE OCCURRENCES:", common_dates)
print("SOURCE NUMERIC VALUES:", sum(source_values.values()))
print("MAPPED OBSERVATION VALUES:", sum(mapped_values.values()))
print("COMMON NUMERIC OCCURRENCES:", common_values)
print("==========================================")
