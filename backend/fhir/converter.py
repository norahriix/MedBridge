def patient_to_fhir(patient: dict) -> dict:
    return {
        "resourceType": "Patient",
        "id": patient["source_patient_id"],
        "name": [
            {
                "text": patient["name"]
            }
        ],
        "gender": normalize_gender(patient["gender"]),
        "birthDate": patient["birth_date"],
    }


def normalize_gender(gender: str) -> str:
    value = gender.strip().lower()

    mapping = {
        "m": "male",
        "male": "male",
        "f": "female",
        "female": "female",
    }

    return mapping.get(value, "unknown")