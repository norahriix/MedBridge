from collections import defaultdict
from uuid import uuid4

from canonical.models import Conflict, Patient


def detect_clinical_conflicts(patient: Patient):

    conflicts = []

    rules = [
        (
            patient.medications,
            "name",
            "dose",
            "medication_dose_mismatch"
        ),
        (
            patient.allergies,
            "substance",
            "status",
            "allergy_status_mismatch"
        ),
        (
            patient.diagnoses,
            "code",
            "description",
            "diagnosis_description_mismatch"
        )
    ]

    for records, group_field, value_field, conflict_type in rules:

        grouped = defaultdict(list)

        for record in records:

            key = getattr(record, group_field)

            if key:
                key = str(key).strip().casefold()
                grouped[key].append(record)

        for key, items in grouped.items():

            values = [
                str(getattr(item, value_field))
                for item in items
            ]

            unique_values = {
                value.strip().casefold()
                for value in values
            }

            if len(unique_values) > 1:

                conflict = Conflict(
                    id=str(uuid4()),
                    patient_id=patient.id,
                    field=f"{key}.{value_field}",
                    conflict_type=conflict_type,
                    record_ids=[
                        item.id for item in items
                    ],
                    values=values,
                    sources=[
                        item.source for item in items
                    ],
                    critical=True,
                    status="NEEDS_HUMAN_REVIEW"
                )

                conflicts.append(conflict)

    return conflicts