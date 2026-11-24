
from canonical.models import Patient, IdentityMatch


def normalize_id(national_id: str | None) -> str | None:
    if not national_id:
        return None
    return "".join(national_id.split())


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.casefold().strip().split())


def compare_patients(
    patient_a: Patient,
    patient_b: Patient
) -> IdentityMatch:

    id_a = normalize_id(patient_a.national_id)
    id_b = normalize_id(patient_b.national_id)

    name_a = normalize_name(patient_a.name)
    name_b = normalize_name(patient_b.name)

    dob_a = patient_a.birth_date
    dob_b = patient_b.birth_date

    if id_a and id_b:
        if id_a == id_b:
            score, status = 1.0, "MATCH"
        else:
            score, status = 0.0, "NO_MATCH"

    elif name_a and name_b and name_a == name_b:
        if dob_a and dob_b:
            if dob_a == dob_b:
                score, status = 0.85, "POSSIBLE_MATCH"
            else:
                score, status = 0.0, "NO_MATCH"
        else:
            score, status = 0.65, "POSSIBLE_MATCH"

    else:
        score, status = 0.0, "NO_MATCH"

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
            results.append(
                compare_patients(patients[i], patients[j])
            )

    return results
