from fhir.converter import patient_to_fhir


def test_patient_to_fhir():
    patient = {
        "source_patient_id": "A100",
        "name": "Sara Ahmed",
        "birth_date": "1995-04-10",
        "gender": "F",
    }

    result = patient_to_fhir(patient)

    assert result["resourceType"] == "Patient"
    assert result["id"] == "A100"
    assert result["name"][0]["text"] == "Sara Ahmed"
    assert result["birthDate"] == "1995-04-10"
    assert result["gender"] == "female"