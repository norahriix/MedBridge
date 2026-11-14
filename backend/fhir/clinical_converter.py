
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
        "id": build_fhir_id("medication", medication.id),
        "status": "unknown" if needs_review else medication.status,
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
            {"text": medication.dose}
        ]

    if needs_review:
        mark_for_review(resource)

    return resource


# 2. AllergyIntolerance
def allergy_to_fhir(allergy, patient_id, needs_review=False):
    resource = {
        "resourceType": "AllergyIntolerance",
        "id": build_fhir_id("allergy", allergy.id),
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
                    {"text": allergy.reaction}
                ]
            }
        ]

    if needs_review:
        mark_for_review(resource)

    return resource


# 3. Condition - Diagnosis
def diagnosis_to_fhir(diagnosis, patient_id, needs_review=False):
    resource = {
        "resourceType": "Condition",
        "id": build_fhir_id("diagnosis", diagnosis.id),
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
            {"code": diagnosis.code}
        ]

    if needs_review:
        mark_for_review(resource)

    return resource


# 4. Procedure
def procedure_to_fhir(procedure, patient_id):
    resource = {
        "resourceType": "Procedure",
        "id": build_fhir_id("procedure", procedure.id),
        "status": (
            procedure.status
            if procedure.status in [
                "preparation",
                "in-progress",
                "not-done",
                "on-hold",
                "stopped",
                "completed",
                "entered-in-error",
                "unknown"
            ]
            else "unknown"
        ),
        "code": {
            "text": procedure.name
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "identifier": [
            {
                "system": "urn:medbridge:procedure",
                "value": procedure.id
            }
        ]
    }

    if procedure.date:
        resource["performedDateTime"] = procedure.date.isoformat()

    if procedure.outcome:
        resource["outcome"] = {
            "text": procedure.outcome
        }

    if procedure.notes:
        resource["note"] = [
            {"text": procedure.notes}
        ]

    return resource


# 5. Condition - Medical History
def medical_history_to_fhir(history, patient_id):
    resource = {
        "resourceType": "Condition",
        "id": build_fhir_id("medical-history", history.id),
        "code": {
            "text": history.condition
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "identifier": [
            {
                "system": "urn:medbridge:medical-history",
                "value": history.id
            }
        ]
    }

    if history.code:
        resource["code"]["coding"] = [
            {"code": history.code}
        ]

    if history.status == "active":
        resource["clinicalStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }
            ]
        }
    elif history.status == "resolved":
        resource["clinicalStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "resolved"
                }
            ]
        }

    if history.onset_date:
        resource["onsetDateTime"] = history.onset_date.isoformat()

    if history.resolved_date:
        resource["abatementDateTime"] = history.resolved_date.isoformat()

    if history.notes:
        resource["note"] = [
            {"text": history.notes}
        ]

    return resource


# 6. Encounter
def encounter_to_fhir(encounter, patient_id):
    resource = {
        "resourceType": "Encounter",
        "id": build_fhir_id("encounter", encounter.id),
        "status": (
            encounter.status
            if encounter.status in [
                "planned",
                "in-progress",
                "on-hold",
                "discharged",
                "completed",
                "cancelled",
                "discontinued",
                "entered-in-error",
                "unknown"
            ]
            else "unknown"
        ),
        "class": {
            "system": "urn:medbridge:encounter-type",
            "code": encounter.encounter_type,
            "display": encounter.encounter_type
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "identifier": [
            {
                "system": "urn:medbridge:encounter",
                "value": encounter.id
            }
        ]
    }

    if encounter.date:
        resource["period"] = {
            "start": encounter.date.isoformat()
        }

    if encounter.reason:
        resource["reasonCode"] = [
            {"text": encounter.reason}
        ]

    if encounter.diagnosis:
        resource["diagnosis"] = [
            {
                "condition": {
                    "display": encounter.diagnosis
                }
            }
        ]

    if encounter.location:
        resource["location"] = [
            {
                "location": {
                    "display": encounter.location
                }
            }
        ]

    if encounter.notes:
        resource["text"] = {
            "status": "generated",
            "div": f"<div>{encounter.notes}</div>"
        }

    return resource


# 7. Immunization
def immunization_to_fhir(immunization, patient_id):
    resource = {
        "resourceType": "Immunization",
        "id": build_fhir_id("immunization", immunization.id),
        "status": (
            immunization.status
            if immunization.status in [
                "completed",
                "entered-in-error",
                "not-done"
            ]
            else "not-done"
            if immunization.status == "not_done"
            else "completed"
            if immunization.status == "unknown"
            else "completed"
        ),
        "vaccineCode": {
            "text": immunization.vaccine
        },
        "patient": {
            "reference": f"Patient/{patient_id}"
        },
        "identifier": [
            {
                "system": "urn:medbridge:immunization",
                "value": immunization.id
            }
        ]
    }

    if immunization.date:
        resource["occurrenceDateTime"] = immunization.date.isoformat()

    if immunization.dose:
        resource["protocolApplied"] = [
            {
                "doseNumberString": immunization.dose
            }
        ]

    return resource


# 8. Family History
def family_history_to_fhir(history, patient_id):
    resource = {
        "resourceType": "FamilyMemberHistory",
        "id": build_fhir_id("family-history", history.id),
        "status": "completed",
        "patient": {
            "reference": f"Patient/{patient_id}"
        },
        "identifier": [
            {
                "system": "urn:medbridge:family-history",
                "value": history.id
            }
        ],
        "condition": [
            {
                "code": {
                    "text": history.condition
                }
            }
        ]
    }

    if history.relationship:
        resource["relationship"] = {
            "text": history.relationship
        }

    if history.notes:
        resource["note"] = [
            {"text": history.notes}
        ]

    return resource
