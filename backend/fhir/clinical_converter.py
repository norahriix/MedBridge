from uuid import uuid5, NAMESPACE_URL


def build_fhir_id(resource_type, record_id):

    return str(
        uuid5(
            NAMESPACE_URL,
            f"urn:medbridge:{resource_type}:{record_id}"
        )
    )


def mark_for_review(resource):

    resource["meta"] = {
        "tag": [
            {
                "system": "urn:medbridge:review-status",
                "code": "NEEDS_HUMAN_REVIEW",
                "display": "Needs human review"
            }
        ]
    }

    resource["note"] = [
        {
            "text": "Conflicting synthetic record. Human review required."
        }
    ]

    return resource


# 1. MedicationStatement
def medication_to_fhir(medication, patient_id, needs_review=False):

    resource = {
        "resourceType": "MedicationStatement",
        "id": build_fhir_id(
            "medication", medication.id
        ),
        "status": (
            "unknown" if needs_review
            else medication.status
        ),
        "medicationCodeableConcept": {
            "text": medication.name
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "identifier": [
            {
                "system": "urn:medbridge:medication",
                "value": medication.id
            }
        ]
    }

    if medication.dose:

        resource["dosage"] = [
            {
                "text": medication.dose
            }
        ]

    if needs_review:
        mark_for_review(resource)

    return resource


# 2. AllergyIntolerance
def allergy_to_fhir(allergy, patient_id, needs_review=False):

    resource = {
        "resourceType": "AllergyIntolerance",
        "id": build_fhir_id(
            "allergy", allergy.id
        ),
        "code": {
            "text": allergy.substance
        },
        "patient": {
            "reference": f"Patient/{patient_id}"
        },
        "identifier": [
            {
                "system": "urn:medbridge:allergy",
                "value": allergy.id
            }
        ]
    }

    if allergy.status != "unknown" and not needs_review:

        resource["verificationStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": allergy.status
                }
            ]
        }

    if allergy.reaction:

        resource["reaction"] = [
            {
                "manifestation": [
                    {
                        "text": allergy.reaction
                    }
                ]
            }
        ]

    if needs_review:
        mark_for_review(resource)

    return resource


# 3. Condition
def diagnosis_to_fhir(diagnosis, patient_id, needs_review=False):

    resource = {
        "resourceType": "Condition",
        "id": build_fhir_id(
            "diagnosis", diagnosis.id
        ),
        "code": {
            "text": diagnosis.description
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "identifier": [
            {
                "system": "urn:medbridge:diagnosis",
                "value": diagnosis.id
            }
        ]
    }

    if diagnosis.code and not needs_review:

        resource["code"]["coding"] = [
            {
                "code": diagnosis.code
            }
        ]

    if needs_review:
        mark_for_review(resource)

    return resource