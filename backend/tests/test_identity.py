
from canonical.models import Patient
from identity.matcher import match_patients, normalize_name


def test_same_patient_details():
    a = Patient(
        id="A100",
        name="Sara Ahmed",
        birth_date="1995-04-10"
    )
    b = Patient(
        id="B200",
        name="Sara Ahmed",
        birth_date="1995-04-10"
    )

    results = match_patients([a, b])

    assert len(results) == 1
    assert results[0].patient_a_id == "A100"
    assert results[0].patient_b_id == "B200"


def test_three_patients():
    patients = [
        Patient(id="1"),
        Patient(id="2"),
        Patient(id="3")
    ]

    assert len(match_patients(patients)) == 3


def test_single_patient():
    assert match_patients([Patient(id="1")]) == []


def test_name_normalization():
    assert normalize_name("  SARA   AHMED  ") == "sara ahmed"
