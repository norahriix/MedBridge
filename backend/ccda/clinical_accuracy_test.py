
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET

from ccda.connector import (
    fetch_ccda_data, patient_from_document, find_section,
    children, first_descendant, first_child, text_of, attr,
)

DATA = Path.home() / "Downloads" / "MedBridge_CCDA_Test" / "ccda"

def norm(v):
    return " ".join(str(v or "").split()).casefold()

patients, _ = fetch_ccda_data()
mapped = {p.id: p for p in patients}

categories = {
    "allergies": [0, 0],
    "diagnoses": [0, 0],
    "encounters": [0, 0],
    "procedures": [0, 0],
    "immunizations": [0, 0],
}

def add_source(category, values):
    source[category].extend(values)

source = {k: [] for k in categories}
target = {k: [] for k in categories}
file_mismatch = {k: 0 for k in categories}

for path in sorted(DATA.glob("*.xml")):
    root = ET.parse(path).getroot()
    patient = patient_from_document(root, path.name)
    mp = mapped.get(patient.id)

    sections = {
        "allergies": "Allergies and Adverse Reactions",
        "diagnoses": "Problems",
        "encounters": "Encounters",
        "procedures": "Surgeries",
        "immunizations": "Immunizations",
    }

    source_file = {k: [] for k in categories}

    for category, section_name in sections.items():
        section = find_section(root, section_name)
        if section is None:
            continue

        for entry in children(section, "entry"):

            if category == "allergies":
                act = first_descendant(entry, "act")
                entity = first_descendant(act, "playingEntity")
                name = text_of(first_child(entity, "name"))
                code = first_child(entity, "code")
                name = name or attr(code, "displayName")
                if name:
                    source_file[category].append(norm(name))

            elif category == "diagnoses":
                act = first_descendant(entry, "act")
                obs = first_descendant(act, "observation")
                val = first_child(obs, "value")
                if val is not None:
                    name = attr(val, "displayName") or text_of(val)
                    code = attr(val, "code")
                    if name:
                        source_file[category].append(
                            (norm(code), norm(name))
                        )

            elif category == "encounters":
                obj = first_descendant(entry, "encounter")
                if obj is not None:
                    code = first_child(obj, "code")
                    name = attr(code, "displayName") or text_of(code)
                    source_file[category].append(norm(name or "Unknown encounter"))

            elif category == "procedures":
                obj = first_descendant(entry, "procedure")
                if obj is not None:
                    code = first_child(obj, "code")
                    name = attr(code, "displayName") or text_of(code)
                    if name:
                        source_file[category].append(
                            (norm(attr(code, "code")), norm(name))
                        )

            elif category == "immunizations":
                obj = first_descendant(entry, "substanceAdministration")
                if obj is not None:
                    code = first_descendant(obj, "code")
                    if attr(code, "code") == "IMMUNIZ":
                        material = first_descendant(obj, "manufacturedMaterial")
                        name = text_of(first_child(material, "name"))
                        vaccine_code = first_child(material, "code")
                        name = name or attr(vaccine_code, "displayName") or "Unknown vaccine"
                        source_file[category].append(norm(name))

    for category in categories:
        source[category].extend(source_file[category])

    if mp:
        target["allergies"].extend(norm(x.substance) for x in mp.allergies)
        target["diagnoses"].extend(
            (norm(x.code), norm(x.description)) for x in mp.diagnoses
        )
        target["encounters"].extend(
            norm(x.encounter_type) for x in mp.encounters
        )
        target["procedures"].extend(
            (norm(x.procedure_type), norm(x.name)) for x in mp.procedures
        )
        target["immunizations"].extend(
            norm(x.vaccine) for x in mp.immunizations
        )

print("\n===== CLINICAL CONVERSION AUDIT =====")

for category in categories:
    s = Counter(source[category])
    t = Counter(target[category])
    matched = sum((s & t).values())
    unmatched = sum((s - t).values())
    extra = sum((t - s).values())
    total = sum(s.values())
    accuracy = matched / total * 100 if total else 0

    print(f"\n{category.upper()}")
    print("SOURCE:", total)
    print("MAPPED:", sum(t.values()))
    print("MATCHED:", matched)
    print("UNMATCHED:", unmatched)
    print("EXTRA:", extra)
    print("MATCH RATE: {:.2f}%".format(accuracy))

print("\n===== END OF AUDIT =====")
