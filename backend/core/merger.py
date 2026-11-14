
from canonical.models import Patient, IdentityMatch


def merge_patients(
    patients: list[Patient],
    matches: list[IdentityMatch]
) -> list[Patient]:

    parent = list(range(len(patients)))

    def find(index):
        if parent[index] != index:
            parent[index] = find(parent[index])
        return parent[index]

    def union(a, b):
        root_a = find(a)
        root_b = find(b)

        if root_a != root_b:
            parent[root_b] = root_a

    patient_index = {
        patient.id: index
        for index, patient in enumerate(patients)
    }

    for match in matches:
        if match.status != "MATCH":
            continue

        if match.patient_a_id not in patient_index:
            continue

        if match.patient_b_id not in patient_index:
            continue

        a = patient_index[match.patient_a_id]
        b = patient_index[match.patient_b_id]

        union(a, b)

    groups = {}

    for index, patient in enumerate(patients):
        root = find(index)
        groups.setdefault(root, []).append(patient)

    merged_patients = []

    for group in groups.values():

        first = group[0]

        merged = Patient(
            id=first.id,
            national_id=first.national_id,
            name=first.name,
            birth_date=first.birth_date,
            gender=first.gender,
            sources=[],
            observations=[],
            medications=[],
            allergies=[],
            diagnoses=[],
            procedures=[],
            medical_history=[],
            encounters=[],
            immunizations=[],
            family_history=[]
        )

        for patient in group:

            for source in patient.sources:
                if source not in merged.sources:
                    merged.sources.append(source)

            merged.observations.extend(patient.observations)
            merged.medications.extend(patient.medications)
            merged.allergies.extend(patient.allergies)
            merged.diagnoses.extend(patient.diagnoses)

            merged.procedures.extend(patient.procedures)
            merged.medical_history.extend(patient.medical_history)
            merged.encounters.extend(patient.encounters)
            merged.immunizations.extend(patient.immunizations)
            merged.family_history.extend(patient.family_history)

        merged_patients.append(merged)

    return merged_patients
