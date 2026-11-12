from uuid import uuid5, NAMESPACE_URL


def normalize_gender(gender: str) -> str:

    value = gender.strip().lower()

    mapping = {
        "m": "male",
        "male": "male",
        "f": "female",
        "female": "female"
    }

    return mapping.get(value, "unknown")


# Convert Patient to FHIR
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
        "birthDate": patient["birth_date"]
    }


# Convert Observation to FHIR
def observation_to_fhir(
    observation,
    patient_fhir_id: str
) -> dict:

    observation_id = str(
        uuid5(
            NAMESPACE_URL,
            f"urn:medbridge:observation:{observation.id}"
        )
    )

    resource = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "unknown",
        "code": {
            "text": observation.type
        },
        "subject": {
            "reference": f"Patient/{patient_fhir_id}"
        },
        "effectiveDateTime": observation.date.isoformat(),
        "valueQuantity": {
            "value": observation.value,
            "unit": observation.unit
        },
        "identifier": [
            {
                "system": "urn:medbridge:observation",
                "value": observation.id
            }
        ]
    }

    if observation.type == "weight":

        resource["code"]["coding"] = [
            {
                "system": "http://loinc.org",
                "code": "29463-7",
                "display": "Body weight"
            }
        ]

        if observation.unit == "kg":

            resource["valueQuantity"]["system"] = (
                "http://unitsofmeasure.org"
            )

            resource["valueQuantity"]["code"] = "kg"

    return resource