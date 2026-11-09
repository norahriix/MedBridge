from validation.validator import validate_patient


def test_valid_patient():
    patient = {
        "source_patient_id": "A100",
        "name": "Sara Ahmed",
        "birth_date": "1995-04-10",
        "gender": "F",
    }

    errors = validate_patient(patient)

    assert errors == []


def test_missing_name():
    patient = {
        "source_patient_id": "A100",
        "birth_date": "1995-04-10",
        "gender": "F",
    }

    errors = validate_patient(patient)

    assert "Missing required field: name" in errors


def test_invalid_birth_date():
    patient = {
        "source_patient_id": "A100",
        "name": "Sara Ahmed",
        "birth_date": "1995/04/10",
        "gender": "F",
    }

    errors = validate_patient(patient)

    assert "Invalid birth_date format" in errors