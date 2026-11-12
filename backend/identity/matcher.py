
from canonical.models import Patient, IdentityMatch


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None

    return " ".join(name.casefold().split())


def compare_patients(
    patient_a: Patient,
    patient_b: Patient
) -> IdentityMatch:

    name_a = normalize_name(patient_a.name)
    name_b = normalize_name(patient_b.name)

    name_match = (
        name_a is not None
        and name_b is not None
        and name_a == name_b
    )

    dob_match = (
        patient_a.birth_date is not None
        and patient_b.birth_date is not None
        and patient_a.birth_date == patient_b.birth_date
    )

    both_names_available = name_a is not None and name_b is not None

    both_dates_available = (
        patient_a.birth_date is not None
        and patient_b.birth_date is not None
    )

    if name_match and dob_match:
        score = 0.9
        status = "POSSIBLE_MATCH"

    elif name_match or dob_match:
        score = 0.5
        status = "POSSIBLE_MATCH"

    elif both_names_available and both_dates_available:
        score = 0.0
        status = "NO_MATCH"

    else:
        score = 0.0
        status = "POSSIBLE_MATCH"

    return IdentityMatch(
        patient_a_id=patient_a.id,
        patient_b_id=patient_b.id,
        score=score,
        status=status
    )

def match_patients(patients: list[Patient]) -> list[IdentityMatch]:
    results = []

    for i in range(len(patients)):
        for j in range(i + 1, len(patients)):
            result = compare_patients(patients[i], patients[j])
            results.append(result)

    return results
