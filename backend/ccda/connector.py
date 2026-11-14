from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL
import xml.etree.ElementTree as ET

from canonical.models import (
    Patient,
    Observation,
    Medication,
    Allergy,
    Diagnosis,
    Procedure,
    Encounter,
    Immunization,
    Provenance,
    SourceRecord,
)


SOURCE = "synthea_ccda"
DEFAULT_DIRECTORY = (
    Path.home() / "Downloads" / "MedBridge_CCDA_Test" / "ccda"
)


def tag_name(element):
    return element.tag.split("}")[-1] if element is not None else ""


def children(element, name):
    if element is None:
        return []
    return [x for x in list(element) if tag_name(x) == name]


def first_child(element, name):
    items = children(element, name)
    return items[0] if items else None


def descendants(element, name):
    if element is None:
        return []
    return [x for x in element.iter() if tag_name(x) == name]


def first_descendant(element, name):
    items = descendants(element, name)
    return items[0] if items else None


def attr(element, name, default=None):
    if element is None:
        return default
    return element.attrib.get(name, default)


def text_of(element):
    if element is None:
        return None
    value = "".join(element.itertext()).strip()
    return value or None


def code_info(element):
    code = first_descendant(element, "code")
    if code is None:
        return None, None

    display = attr(code, "displayName") or text_of(
        first_child(code, "originalText")
    )
    return attr(code, "code"), display


def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    try:
        if len(value) >= 8 and value[:8].isdigit():
            return datetime.strptime(value[:8], "%Y%m%d").date()

        if len(value) >= 10:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None

    return None


def element_date(element):
    if element is None:
        return None

    effective = first_child(element, "effectiveTime")

    if effective is not None:
        value = attr(effective, "value")
        if value:
            return parse_date(value)

        low = first_child(effective, "low")
        if low is not None:
            result = parse_date(attr(low, "value"))
            if result:
                return result

    return None


def record_id(element, fallback):
    identifier = first_descendant(element, "id")
    value = (
        attr(identifier, "extension")
        or attr(identifier, "root")
        if identifier is not None
        else None
    )
    return value or fallback


def stable_id(value):
    return str(uuid5(NAMESPACE_URL, f"{SOURCE}:{value}"))


def make_provenance(field, value):
    return Provenance(
        source=SOURCE,
        original_field=field,
        original_value=str(value),
        transformations=["C-CDA XML parsing", "Canonical mapping"],
    )


def find_section(root, title):
    for section in descendants(root, "section"):
        section_title = first_child(section, "title")
        if title.lower() in (text_of(section_title) or "").lower():
            return section
    return None


def patient_from_document(root, filename):
    role = first_descendant(root, "patientRole")
    patient_node = first_descendant(role, "patient")

    if patient_node is None:
        raise ValueError("Patient information not found")

    name_node = first_child(patient_node, "name")
    given = text_of(first_child(name_node, "given"))
    family = text_of(first_child(name_node, "family"))
    full_name = " ".join(x for x in [given, family] if x) or None

    gender_node = first_child(patient_node, "administrativeGenderCode")
    gender_code = attr(gender_node, "code", "").upper()

    gender = {
        "M": "male",
        "F": "female",
    }.get(gender_code, "unknown")

    birth_node = first_child(patient_node, "birthTime")
    birth_date = parse_date(attr(birth_node, "value"))

    patient_identifier = first_child(role, "id")
    patient_id = (
        attr(patient_identifier, "extension")
        or attr(patient_identifier, "root")
        if patient_identifier is not None
        else None
    )

    patient_id = patient_id or stable_id(filename)

    patient = Patient(
        id=f"synthea_ccda:{patient_id}",
        name=full_name,
        birth_date=birth_date,
        gender=gender,
        sources=[SOURCE],
    )

    return patient


def extract_observations(section, patient_id, filename, errors):
    results = []

    if section is None:
        return results

    for observation in descendants(section, "observation"):
        value_node = first_child(observation, "value")

        if value_node is None:
            continue

        raw_value = attr(value_node, "value")
        unit = attr(value_node, "unit")
        value_type = attr(value_node, "{http://www.w3.org/2001/XMLSchema-instance}type", "")

        if raw_value is None:
            continue

        try:
            numeric_value = float(raw_value)
        except (ValueError, TypeError):
            errors.append(f"Non-numeric observation skipped: {raw_value}")
            continue

        code_node = first_child(observation, "code")
        code = attr(code_node, "code")
        display = attr(code_node, "displayName") or text_of(code_node)

        observation_date = element_date(observation)

        if observation_date is None:
            errors.append(
                f"Observation without date skipped: {display or code or filename}"
            )
            continue

        source_id = record_id(
            observation,
            f"{patient_id}:{code}:{observation_date}:{raw_value}",
        )

        results.append(
            Observation(
                id=stable_id(source_id),
                type=display or code or "Unknown observation",
                value=numeric_value,
                unit=unit or "unknown",
                date=observation_date,
                source=SOURCE,
                provenance=[
                    make_provenance("code", code or ""),
                    make_provenance("displayName", display or ""),
                    make_provenance("value", raw_value),
                    make_provenance("unit", unit or ""),
                ],
            )
        )

    return results


def extract_medications(section, patient_id):
    results = []

    if section is None:
        return results

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

        dose = None
        if dose_value:
            dose = f"{dose_value} {dose_unit or ''}".strip()

        identifier = record_id(
            activity,
            f"{patient_id}:medication:{name}",
        )

        results.append(
            Medication(
                id=stable_id(identifier),
                name=name,
                dose=dose,
                status=status,
                source=SOURCE,
                provenance=[
                    make_provenance("medication_name", name),
                    make_provenance("medication_code", attr(code_node, "code", "")),
                    make_provenance("status", raw_status),
                ],
            )
        )

    return results


def extract_allergies(section, patient_id):
    results = []

    if section is None:
        return results

    for entry in children(section, "entry"):
        act = first_descendant(entry, "act")
        if act is None:
            continue

        playing_entity = first_descendant(act, "playingEntity")
        name_node = first_child(playing_entity, "name")
        code_node = first_child(playing_entity, "code")

        substance = (
            text_of(name_node)
            or attr(code_node, "displayName")
        )

        if not substance:
            continue

        identifier = record_id(
            act,
            f"{patient_id}:allergy:{substance}",
        )

        results.append(
            Allergy(
                id=stable_id(identifier),
                substance=substance,
                status="confirmed",
                source=SOURCE,
                provenance=[
                    make_provenance("substance", substance),
                    make_provenance(
                        "allergy_code",
                        attr(code_node, "code", ""),
                    ),
                    make_provenance(
                        "status",
                        attr(first_child(act, "statusCode"), "code", "unknown"),
                    ),
                ],
            )
        )

    return results


def extract_diagnoses(section, patient_id):
    results = []

    if section is None:
        return results

    for entry in children(section, "entry"):
        act = first_descendant(entry, "act")
        if act is None:
            continue

        observation = first_descendant(act, "observation")
        value_node = first_child(observation, "value")

        if value_node is None:
            continue

        description = attr(value_node, "displayName") or text_of(value_node)
        code = attr(value_node, "code")

        if not description:
            continue

        identifier = record_id(
            act,
            f"{patient_id}:diagnosis:{code}:{description}",
        )

        results.append(
            Diagnosis(
                id=stable_id(identifier),
                code=code,
                description=description,
                source=SOURCE,
                provenance=[
                    make_provenance("diagnosis_code", code or ""),
                    make_provenance("description", description),
                    make_provenance(
                        "status",
                        attr(first_child(act, "statusCode"), "code", "unknown"),
                    ),
                ],
            )
        )

    return results


def extract_encounters(section, patient_id):
    results = []

    if section is None:
        return results

    for entry in children(section, "entry"):
        encounter = first_descendant(entry, "encounter")
        if encounter is None:
            continue

        code_node = first_child(encounter, "code")
        code = attr(code_node, "code")
        name = attr(code_node, "displayName") or text_of(code_node)

        identifier = record_id(
            encounter,
            f"{patient_id}:encounter:{code}:{element_date(encounter)}",
        )

        results.append(
            Encounter(
                id=stable_id(identifier),
                encounter_type=name or "Unknown encounter",
                date=element_date(encounter),
                status=attr(
                    first_child(encounter, "statusCode"),
                    "code",
                    "unknown",
                ),
                source=SOURCE,
                provenance=[
                    make_provenance("encounter_code", code or ""),
                    make_provenance("encounter_type", name or ""),
                ],
            )
        )

    return results


def extract_procedures(section, patient_id):
    results = []

    if section is None:
        return results

    for entry in children(section, "entry"):
        procedure = first_descendant(entry, "procedure")
        if procedure is None:
            continue

        code_node = first_child(procedure, "code")
        code = attr(code_node, "code")
        name = attr(code_node, "displayName") or text_of(code_node)

        if not name:
            continue

        identifier = record_id(
            procedure,
            f"{patient_id}:procedure:{code}:{name}",
        )

        results.append(
            Procedure(
                id=stable_id(identifier),
                name=name,
                procedure_type=code,
                date=element_date(procedure),
                status=attr(
                    first_child(procedure, "statusCode"),
                    "code",
                    "unknown",
                ),
                source=SOURCE,
                provenance=[
                    make_provenance("procedure_code", code or ""),
                    make_provenance("procedure_name", name),
                ],
            )
        )

    return results


def extract_immunizations(section, patient_id):
    results = []

    if section is None:
        return results

    for entry in children(section, "entry"):
        activity = first_descendant(entry, "substanceAdministration")
        if activity is None:
            continue

        code_node = first_descendant(activity, "code")
        if attr(code_node, "code") != "IMMUNIZ":
            continue

        material = first_descendant(activity, "manufacturedMaterial")
        vaccine_code = first_child(material, "code")
        name_node = first_child(material, "name")

        vaccine = (
            text_of(name_node)
            or attr(vaccine_code, "displayName")
            or "Unknown vaccine"
        )

        identifier = record_id(
            activity,
            f"{patient_id}:immunization:{vaccine}:{element_date(activity)}",
        )

        results.append(
            Immunization(
                id=stable_id(identifier),
                vaccine=vaccine,
                date=element_date(activity),
                status=attr(
                    first_child(activity, "statusCode"),
                    "code",
                    "unknown",
                ),
                source=SOURCE,
                provenance=[
                    make_provenance("vaccine", vaccine),
                    make_provenance(
                        "vaccine_code",
                        attr(vaccine_code, "code", ""),
                    ),
                ],
            )
        )

    return results


def fetch_ccda_data(directory=DEFAULT_DIRECTORY):
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(
            f"C-CDA directory does not exist: {directory}"
        )

    files = sorted(directory.glob("*.xml"))

    patients = []
    source_records = []

    for file_path in files:
        errors = []

        try:
            root = ET.parse(file_path).getroot()
            patient = patient_from_document(root, file_path.name)

            patient_id = patient.id
            sections = {
                "diagnostic": find_section(root, "Diagnostic Results"),
                "vitals": find_section(root, "Vital Signs"),
                "medications": find_section(root, "Medications"),
                "allergies": find_section(root, "Allergies and Adverse Reactions"),
                "problems": find_section(root, "Problems"),
                "encounters": find_section(root, "Encounters"),
                "procedures": find_section(root, "Surgeries"),
                "immunizations": find_section(root, "Immunizations"),
            }

            patient.observations.extend(
                extract_observations(
                    sections["diagnostic"], patient_id, file_path.name, errors
                )
            )
            patient.observations.extend(
                extract_observations(
                    sections["vitals"], patient_id, file_path.name, errors
                )
            )
            patient.medications.extend(
                extract_medications(sections["medications"], patient_id)
            )
            patient.allergies.extend(
                extract_allergies(sections["allergies"], patient_id)
            )
            patient.diagnoses.extend(
                extract_diagnoses(sections["problems"], patient_id)
            )
            patient.encounters.extend(
                extract_encounters(sections["encounters"], patient_id)
            )
            patient.procedures.extend(
                extract_procedures(sections["procedures"], patient_id)
            )
            patient.immunizations.extend(
                extract_immunizations(sections["immunizations"], patient_id)
            )

            patients.append(patient)

            source_records.append(
                SourceRecord(
                    source=SOURCE,
                    original={
                        "filename": file_path.name,
                        "patient_id": patient_id,
                    },
                    mapped={
                        "patient": patient.id,
                        "observations": len(patient.observations),
                        "medications": len(patient.medications),
                        "allergies": len(patient.allergies),
                        "diagnoses": len(patient.diagnoses),
                        "encounters": len(patient.encounters),
                        "procedures": len(patient.procedures),
                        "immunizations": len(patient.immunizations),
                    },
                    normalized={
                        "format": "C-CDA XML",
                        "source": SOURCE,
                        "patient_name": patient.name,
                    },
                    provenance=[
                        make_provenance("filename", file_path.name),
                    ],
                    errors=errors,
                )
            )

        except Exception as exc:
            source_records.append(
                SourceRecord(
                    source=SOURCE,
                    original={"filename": file_path.name},
                    mapped={},
                    normalized={},
                    provenance=[],
                    errors=[f"{type(exc).__name__}: {exc}"],
                )
            )

    return patients, source_records


if __name__ == "__main__":
    patients, records = fetch_ccda_data()

    print("C-CDA CONNECTOR TEST")
    print("FILES:", len(records))
    print("PATIENTS:", len(patients))
    print("OBSERVATIONS:", sum(len(p.observations) for p in patients))
    print("MEDICATIONS:", sum(len(p.medications) for p in patients))
    print("ALLERGIES:", sum(len(p.allergies) for p in patients))
    print("DIAGNOSES:", sum(len(p.diagnoses) for p in patients))
    print("ENCOUNTERS:", sum(len(p.encounters) for p in patients))
    print("PROCEDURES:", sum(len(p.procedures) for p in patients))
    print("IMMUNIZATIONS:", sum(len(p.immunizations) for p in patients))
    print("ERRORS:", sum(bool(r.errors) for r in records))