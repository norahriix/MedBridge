from canonical.models import (
    Medication,
    Allergy,
    Diagnosis,
    SourceRecord
)

from ingestion.readers import read_source
from core.mapper import map_record
from provenance.tracker import track_provenance

import yaml


CLINICAL_MODELS = {
    "medications": Medication,
    "allergies": Allergy,
    "diagnoses": Diagnosis
}


def process_clinical_records(
    data_path,
    mapping_path,
    source,
    patients,
    record_type
):

    records = read_source(str(data_path))

    with open(mapping_path, encoding="utf-8") as file:
        mapping = yaml.safe_load(file)

    model = CLINICAL_MODELS[record_type]

    patient_index = {
        patient.id: patient
        for patient in patients
    }

    source_records = []

    for record in records:

        mapped = {}
        normalized = {}
        provenance = []
        errors = []

        try:

            mapped = map_record(record, mapping)
            normalized = mapped.copy()

            for field in ["name", "substance", "description", "dose", "reaction"]:

                if isinstance(normalized.get(field), str):
                    normalized[field] = normalized[field].strip()

            if isinstance(normalized.get("status"), str):
                normalized["status"] = (
                    normalized["status"].strip().lower()
                )

            for original_field, canonical_field in mapping["fields"].items():

                if original_field not in record:
                    continue

                original_value = record[original_field]
                transformations = []

                if original_field != canonical_field:
                    transformations.append(
                        f"{original_field} -> {canonical_field}"
                    )

                if canonical_field in normalized:

                    new_value = normalized[canonical_field]

                    if original_value != new_value:
                        transformations.append(
                            f"{original_value} -> {new_value}"
                        )

                provenance.append(
                    track_provenance(
                        source,
                        original_field,
                        original_value,
                        transformations
                    )
                )

            patient_id = (
                f"{source}:"
                f"{normalized['source_patient_id']}"
            )

            if patient_id not in patient_index:
                raise ValueError(
                    f"Patient not found: {patient_id}"
                )

            payload = normalized.copy()

            payload.pop("source_patient_id")

            payload["id"] = f"{source}:{payload['id']}"
            payload["source"] = source
            payload["provenance"] = provenance

            clinical_record = model(**payload)

            patient = patient_index[patient_id]

            collection = getattr(patient, record_type)

            if any(item.id == clinical_record.id for item in collection):
                raise ValueError(
                    f"Duplicate record ID: {clinical_record.id}"
                )

            collection.append(clinical_record)

        except Exception as error:

            errors.append(str(error))

        source_records.append(
            SourceRecord(
                source=source,
                original=record,
                mapped=mapped,
                normalized=normalized,
                provenance=provenance,
                errors=errors
            )
        )

    return source_records