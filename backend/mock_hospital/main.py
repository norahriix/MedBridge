
from datetime import datetime, timezone, date, timedelta

from fastapi import FastAPI, HTTPException, Query


app = FastAPI(
    title="MedBridge Mock Hospital",
    description="Synthetic FHIR R4 server - 1000 fictional patients",
    version="2.0.0"
)

SOURCE = "mock_hospital_fhir"

FIRST_NAMES = [
    "Sara", "Omar", "Lina", "Khalid", "Nora",
    "Faisal", "Maha", "Yousef", "Huda", "Salem",
    "Reem", "Abdullah", "Amal", "Rayan", "Layla"
]

LAST_NAMES = [
    "Demo", "Sample", "Test", "Mock", "Example",
    "Fiction", "Synthetic", "Patient", "Record", "Data"
]

DIAGNOSES = [
    ("E11.9", "Type 2 diabetes mellitus"),
    ("I10", "Essential hypertension"),
    ("J45.909", "Asthma"),
    ("E78.5", "Hyperlipidemia"),
    ("M54.5", "Low back pain"),
    ("K21.9", "Gastro-esophageal reflux disease"),
    ("J30.9", "Allergic rhinitis"),
    ("G43.909", "Migraine"),
]

MEDICATIONS = [
    "Metformin 500 mg",
    "Amlodipine 5 mg",
    "Salbutamol inhaler",
    "Atorvastatin 20 mg",
    "Omeprazole 20 mg",
    "Cetirizine 10 mg",
]

ALLERGIES = [
    ("Penicillin", "Skin rash"),
    ("Peanuts", "Mild allergic reaction"),
    ("Latex", "Skin irritation"),
    ("No known allergy", None),
]

VACCINES = [
    "Influenza vaccine",
    "COVID-19 vaccine",
    "Hepatitis B vaccine",
]

PATIENTS = {}
RESOURCES = {
    "Observation": {},
    "Condition": {},
    "AllergyIntolerance": {},
    "MedicationStatement": {},
    "Encounter": {},
    "Procedure": {},
    "Immunization": {},
    "FamilyMemberHistory": {},
}


def reference(patient_id):
    return {"reference": f"Patient/{patient_id}"}


def generate_patient(index):
    patient_id = f"HOSP-A-{index:04d}"

    first = FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]
    last = LAST_NAMES[((index - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]

    gender = "female" if index % 2 == 0 else "male"

    birth_date = (
        date(1945, 1, 1)
        + timedelta(days=(index * 37) % (80 * 365))
    )

    return {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "urn:mock-hospital:patient-id",
                "value": patient_id
            },
            {
                "system": "urn:mock-hospital:national-id",
                "value": f"DEMO-{index:010d}"
            }
        ],
        "name": [{
            "use": "official",
            "family": last,
            "given": [first, str(index)],
            "text": f"{first} {last} {index}"
        }],
        "gender": gender,
        "birthDate": birth_date.isoformat(),
        "active": True
    }


def add_observation(index, patient_id, code, display, value, unit, suffix):
    resource_id = f"OBS-{suffix}-{index:04d}"

    resource = {
        "resourceType": "Observation",
        "id": resource_id,
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": code,
                "display": display
            }],
            "text": display
        },
        "subject": reference(patient_id),
        "effectiveDateTime": "2026-11-10T09:00:00Z",
        "valueQuantity": {
            "value": value,
            "unit": unit
        }
    }

    RESOURCES["Observation"][resource_id] = resource


def generate_patient_resources(index, patient_id):
    # Weight
    weight = round(50 + ((index * 17) % 500) / 10, 1)

    add_observation(
        index, patient_id,
        "29463-7", "Body weight",
        weight, "kg", "WEIGHT"
    )

    # Blood glucose
    glucose = 75 + (index % 70)

    add_observation(
        index, patient_id,
        "2345-7", "Glucose",
        glucose, "mg/dL", "GLUCOSE"
    )

    # Hemoglobin
    hemoglobin = round(11 + (index % 50) / 10, 1)

    add_observation(
        index, patient_id,
        "718-7", "Hemoglobin",
        hemoglobin, "g/dL", "HEMOGLOBIN"
    )

    # Blood pressure with two components
    bp_id = f"OBS-BP-{index:04d}"

    bp = {
        "resourceType": "Observation",
        "id": bp_id,
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel"
            }],
            "text": "Blood pressure"
        },
        "subject": reference(patient_id),
        "effectiveDateTime": "2026-11-10T09:05:00Z",
        "component": [
            {
                "code": {
                    "text": "Systolic blood pressure"
                },
                "valueQuantity": {
                    "value": 105 + (index % 36),
                    "unit": "mmHg"
                }
            },
            {
                "code": {
                    "text": "Diastolic blood pressure"
                },
                "valueQuantity": {
                    "value": 65 + (index % 21),
                    "unit": "mmHg"
                }
            }
        ]
    }

    RESOURCES["Observation"][bp_id] = bp

    # Diagnosis / medical history
    code, description = DIAGNOSES[index % len(DIAGNOSES)]

    condition_id = f"COND-{index:04d}"

    RESOURCES["Condition"][condition_id] = {
        "resourceType": "Condition",
        "id": condition_id,
        "clinicalStatus": {
            "text": "active"
        },
        "code": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": code,
                "display": description
            }],
            "text": description
        },
        "subject": reference(patient_id),
        "onsetDateTime": "2024-01-15"
    }

    # Allergy
    allergy_name, reaction = ALLERGIES[index % len(ALLERGIES)]

    allergy_id = f"ALLERGY-{index:04d}"

    RESOURCES["AllergyIntolerance"][allergy_id] = {
        "resourceType": "AllergyIntolerance",
        "id": allergy_id,
        "clinicalStatus": {
            "text": "active"
        },
        "code": {
            "text": allergy_name
        },
        "patient": reference(patient_id),
        "type": "allergy",
        "reaction": (
            [{
                "manifestation": [{
                    "text": reaction
                }]
            }]
            if reaction else []
        )
    }

    # Medication
    medication_id = f"MED-{index:04d}"

    RESOURCES["MedicationStatement"][medication_id] = {
        "resourceType": "MedicationStatement",
        "id": medication_id,
        "status": "active",
        "medicationCodeableConcept": {
            "text": MEDICATIONS[index % len(MEDICATIONS)]
        },
        "subject": reference(patient_id),
        "effectiveDateTime": "2026-01-01",
        "dosage": [{
            "text": "One dose daily - synthetic example"
        }]
    }

    # Medical visit
    encounter_id = f"ENC-{index:04d}"

    RESOURCES["Encounter"][encounter_id] = {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "class": {
            "code": "AMB",
            "display": "Outpatient"
        },
        "type": [{
            "text": "Outpatient visit"
        }],
        "subject": reference(patient_id),
        "period": {
            "start": "2026-10-15T09:00:00Z",
            "end": "2026-10-15T09:30:00Z"
        },
        "reasonCode": [{
            "text": description
        }],
        "serviceProvider": {
            "display": "Synthetic Mock Hospital"
        }
    }

    # Procedure
    procedure_id = f"PROC-{index:04d}"

    RESOURCES["Procedure"][procedure_id] = {
        "resourceType": "Procedure",
        "id": procedure_id,
        "status": "completed",
        "code": {
            "text": "Routine clinical examination"
        },
        "subject": reference(patient_id),
        "performedDateTime": "2026-10-15"
    }

    # Immunization
    vaccine_id = f"IMM-{index:04d}"

    RESOURCES["Immunization"][vaccine_id] = {
        "resourceType": "Immunization",
        "id": vaccine_id,
        "status": "completed",
        "vaccineCode": {
            "text": VACCINES[index % len(VACCINES)]
        },
        "patient": reference(patient_id),
        "occurrenceDateTime": "2025-06-01"
    }

    # Family history
    family_id = f"FAM-{index:04d}"

    RESOURCES["FamilyMemberHistory"][family_id] = {
        "resourceType": "FamilyMemberHistory",
        "id": family_id,
        "status": "completed",
        "patient": reference(patient_id),
        "relationship": {
            "text": "Mother"
        },
        "condition": [{
            "code": {
                "text": "Family history of hypertension"
            }
        }]
    }


# Generate 1000 fictional patients and their clinical records
for index in range(1, 1001):
    patient = generate_patient(index)
    patient_id = patient["id"]

    PATIENTS[patient_id] = patient
    generate_patient_resources(index, patient_id)


def make_bundle(resources):
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": [
            {
                "fullUrl": (
                    f"http://localhost:8001/fhir/"
                    f"{resource['resourceType']}/{resource['id']}"
                ),
                "resource": resource,
                "search": {"mode": "match"}
            }
            for resource in resources
        ]
    }


def filter_by_patient(resources, subject):
    if not subject:
        return resources

    patient_id = subject.replace("Patient/", "")

    result = []

    for resource in resources:
        patient_reference = (
            resource.get("subject", {}).get("reference")
            or resource.get("patient", {}).get("reference")
        )

        if patient_reference == f"Patient/{patient_id}":
            result.append(resource)

    return result


@app.get("/")
def root():
    return {
        "service": "MedBridge Mock Hospital",
        "status": "healthy",
        "mode": "synthetic-data-only"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "server": "Mock Hospital",
        "mode": "synthetic-data-only",
        "patients": len(PATIENTS),
        "resources": {
            resource_type: len(items)
            for resource_type, items in RESOURCES.items()
        },
        "total_fhir_resources": (
            len(PATIENTS)
            + sum(len(items) for items in RESOURCES.values())
        )
    }


@app.get("/fhir/Patient")
def search_patients(
    patient_id: str | None = Query(default=None, alias="_id")
):
    resources = list(PATIENTS.values())

    if patient_id:
        resources = [
            patient for patient in resources
            if patient["id"] == patient_id
        ]

    return make_bundle(resources)


@app.get("/fhir/Patient/{patient_id}")
def get_patient(patient_id: str):
    patient = PATIENTS.get(patient_id)

    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    return patient


def register_resource_routes(resource_type):
    @app.get(f"/fhir/{resource_type}")
    def search_resource(subject: str | None = Query(default=None)):
        resources = list(RESOURCES[resource_type].values())
        resources = filter_by_patient(resources, subject)
        return make_bundle(resources)

    @app.get(f"/fhir/{resource_type}/{{resource_id}}")
    def get_resource(resource_id: str):
        resource = RESOURCES[resource_type].get(resource_id)

        if resource is None:
            raise HTTPException(
                status_code=404,
                detail=f"{resource_type} not found"
            )

        return resource


for resource_type in RESOURCES:
    register_resource_routes(resource_type)


@app.get("/fhir/metadata")
def metadata():
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": datetime.now(timezone.utc).isoformat(),
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [
                {"type": "Patient", "interaction": [
                    {"code": "read"}, {"code": "search-type"}
                ]}
            ] + [
                {
                    "type": resource_type,
                    "interaction": [
                        {"code": "read"}, {"code": "search-type"}
                    ]
                }
                for resource_type in RESOURCES
            ]
        }]
    }
