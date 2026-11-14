
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

from canonical.models import (
    Patient, Observation, Medication, Allergy, Diagnosis,
    Encounter, Procedure, Immunization, Provenance, SourceRecord
)

DATA_DIR = Path(__file__).parent / "data"
SOURCE = "HL7v2"


def get_field(segment, number):
    fields = segment.split("|")
    return fields[number] if number < len(fields) else ""


def component(value, number=0):
    parts = value.split("^")
    return parts[number] if number < len(parts) else ""


def parse_date(value):
    if not value:
        return None

    value = value.strip()

    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:len(datetime.now().strftime(fmt))], fmt).date()
        except ValueError:
            pass

    return None


def provenance(field, value):
    return Provenance(
        source=SOURCE,
        original_field=field,
        original_value=str(value),
        transformations=["HL7 v2 field extraction"]
    )


def create_synthetic_sample():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sample = (
        "MSH|^~\\&|SYNTHETIC_HOSPITAL|MEDBRIDGE|MEDBRIDGE|TEST|20261114120000||ORU^R01|MSG0001|P|2.5\r"
        "PID|1||SYNTH001^^^SYNTHETIC^MR||TEST^PATIENT||19900101|M\r"
        "PV1|1|O|||||||||||||||||ENC001||||||||||||||||||||||||20261114100000\r"
        "AL1|1|DA|PEN^PENICILLIN||RASH\r"
        "DG1|1||E11.9^DIABETES MELLITUS||20260101\r"
        "OBX|1|NM|GLU^GLUCOSE||110|mg/dL|||||F|||20261114110000\r"
        "RXA|0|1|20261114110000||MED001^METFORMIN||500 MG\r"
        "PR1|1||PROC001^BLOOD TEST||20261114110000\r"
        "RXA|0|1|20261114110000||VAC001^INFLUENZA VACCINE||1 DOSE\r"
    )

    (DATA_DIR / "synthetic_sample.hl7").write_text(
        sample, encoding="utf-8"
    )


def parse_message(content):
    segments = [
        line.strip()
        for line in content.replace("\n", "\r").split("\r")
        if line.strip()
    ]

    pid = next((s for s in segments if s.startswith("PID|")), None)
    if not pid:
        return None, []

    patient_id = component(get_field(pid, 3))
    if not patient_id:
        patient_id = "UNKNOWN-" + str(abs(hash(content)))

    family = component(get_field(pid, 5), 0)
    given = component(get_field(pid, 5), 1)
    name = " ".join(x for x in [given, family] if x) or None

    gender_value = get_field(pid, 8).upper()
    gender = (
        "male" if gender_value == "M"
        else "female" if gender_value == "F"
        else "unknown"
    )

    birth_date = parse_date(get_field(pid, 7))

    patient_data = {
        "id": patient_id,
        "name": name,
        "birth_date": birth_date,
        "gender": gender,
        "sources": [SOURCE],
        "observations": [],
        "medications": [],
        "allergies": [],
        "diagnoses": [],
        "encounters": [],
        "procedures": [],
        "immunizations": [],
    }

    records = []

    message_date = parse_date(
        get_field(next((s for s in segments if s.startswith("MSH|")), ""), 7)
    )

    for index, segment in enumerate(segments):
        fields = segment.split("|")
        kind = fields[0]
        mapped = None

        if kind == "OBX":
            code = component(get_field(segment, 3))
            description = component(get_field(segment, 3), 1) or code
            raw_value = get_field(segment, 5)
            unit = component(get_field(segment, 6)) or get_field(segment, 6)
            obs_date = parse_date(get_field(segment, 14)) or message_date

            try:
                value = float(raw_value)
                if obs_date:
                    mapped = Observation(
                        id=get_field(segment, 21) or f"{patient_id}-OBX-{index}",
                        type=description,
                        value=value,
                        unit=unit or "unknown",
                        date=obs_date,
                        source=SOURCE,
                        provenance=[
                            provenance("OBX-3", get_field(segment, 3)),
                            provenance("OBX-5", raw_value),
                            provenance("OBX-6", get_field(segment, 6)),
                            provenance("OBX-14", get_field(segment, 14)),
                        ],
                    )
                    patient_data["observations"].append(mapped)
            except (ValueError, TypeError):
                pass

        elif kind == "AL1":
            substance = component(get_field(segment, 3), 1) or component(get_field(segment, 3))
            if substance:
                mapped = Allergy(
                    id=f"{patient_id}-AL1-{index}",
                    substance=substance,
                    reaction=get_field(segment, 5) or None,
                    status="confirmed",
                    source=SOURCE,
                    provenance=[provenance("AL1-3", get_field(segment, 3))],
                )
                patient_data["allergies"].append(mapped)

        elif kind == "DG1":
            code = component(get_field(segment, 3))
            description = component(get_field(segment, 3), 1) or code
            if description:
                mapped = Diagnosis(
                    id=f"{patient_id}-DG1-{index}",
                    code=code or None,
                    description=description,
                    source=SOURCE,
                    provenance=[provenance("DG1-3", get_field(segment, 3))],
                )
                patient_data["diagnoses"].append(mapped)

        elif kind == "PV1":
            encounter_date = parse_date(get_field(segment, 44)) or message_date
            mapped = Encounter(
                id=get_field(segment, 19) or f"{patient_id}-PV1-{index}",
                encounter_type=get_field(segment, 2) or "unknown",
                date=encounter_date,
                location=get_field(segment, 3) or None,
                status="unknown",
                source=SOURCE,
                provenance=[provenance("PV1-2", get_field(segment, 2))],
            )
            patient_data["encounters"].append(mapped)

        elif kind == "RXA":
            medication = component(get_field(segment, 5), 1) or component(get_field(segment, 5))
            if medication:
                mapped = Medication(
                    id=f"{patient_id}-RXA-{index}",
                    name=medication,
                    dose=get_field(segment, 7) or None,
                    status="active",
                    source=SOURCE,
                    provenance=[
                        provenance("RXA-5", get_field(segment, 5)),
                        provenance("RXA-7", get_field(segment, 7)),
                    ],
                )
                patient_data["medications"].append(mapped)

        elif kind == "PR1":
            procedure = component(get_field(segment, 3), 1) or component(get_field(segment, 3))
            if procedure:
                mapped = Procedure(
                    id=f"{patient_id}-PR1-{index}",
                    name=procedure,
                    date=parse_date(get_field(segment, 5)),
                    source=SOURCE,
                    provenance=[provenance("PR1-3", get_field(segment, 3))],
                )
                patient_data["procedures"].append(mapped)

        if mapped is not None:
            records.append(
                SourceRecord(
                    source=SOURCE,
                    original={"segment": segment},
                    mapped=mapped.model_dump(mode="json"),
                    normalized=mapped.model_dump(mode="json"),
                    provenance=getattr(mapped, "provenance", []),
                )
            )

    return patient_data, records


def fetch_hl7_data(directory=DATA_DIR):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    files = list(directory.glob("*.hl7")) + list(directory.glob("*.txt"))

    if not files:
        create_synthetic_sample()
        files = list(directory.glob("*.hl7"))

    patients = {}
    all_records = []
    errors = []

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            patient_data, records = parse_message(content)

            if patient_data:
                patient_id = patient_data["id"]

                if patient_id not in patients:
                    patients[patient_id] = patient_data
                else:
                    for key in patient_data:
                        if isinstance(patient_data[key], list):
                            patients[patient_id][key].extend(patient_data[key])

                all_records.extend(records)

        except Exception as error:
            errors.append(f"{file_path.name}: {error}")

    result = [
        Patient(**patient_data)
        for patient_data in patients.values()
    ]

    return result, all_records, errors


if __name__ == "__main__":
    patients, records, errors = fetch_hl7_data()

    print("HL7 v2 CONNECTOR TEST")
    print("FILES:", len(list(DATA_DIR.glob("*.hl7"))))
    print("PATIENTS:", len(patients))
    print("SOURCE RECORDS:", len(records))
    print("OBSERVATIONS:", sum(len(p.observations) for p in patients))
    print("MEDICATIONS:", sum(len(p.medications) for p in patients))
    print("ALLERGIES:", sum(len(p.allergies) for p in patients))
    print("DIAGNOSES:", sum(len(p.diagnoses) for p in patients))
    print("ENCOUNTERS:", sum(len(p.encounters) for p in patients))
    print("PROCEDURES:", sum(len(p.procedures) for p in patients))
    print("ERRORS:", errors)
