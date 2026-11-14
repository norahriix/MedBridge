
from datetime import datetime, timezone, date, timedelta

from fastapi import FastAPI, HTTPException, Query


app = FastAPI(
    title="MedBridge Mock Hospital",
    description="Synthetic FHIR R4 server for testing",
    version="1.0.0"
)


# ==================================================
# Synthetic data generation - 1000 patients
# ==================================================

FIRST_NAMES = [
    "Sara", "Omar", "Lina", "Khalid", "Nora",
    "Faisal", "Maha", "Yousef", "Huda", "Salem",
    "Reem", "Abdullah", "Amal", "Rayan", "Layla"
]

LAST_NAMES = [
    "Demo", "Sample", "Test", "Mock", "Example",
    "Fiction", "Synthetic", "Patient", "Record", "Data"
]

PATIENTS = {}
OBSERVATIONS = {}


def generate_patient(index):
    patient_id = f"HOSP-A-{index:04d}"

    first_name = FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]
    last_name = LAST_NAMES[((index - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]

    gender = "female" if index % 2 == 0 else "male"

    birth_date = (
        date(1945, 1, 1)
        + timedelta(days=(index * 37) % (80 * 365))
    )

    full_name = f"{first_name} {last_name} {index}"

    return {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "urn:mock-hospital:patient-id",
                "value": patient_id
            }
        ],
        "name": [
            {
                "use": "official",
                "family": last_name,
                "given": [first_name, str(index)],
                "text": full_name
            }
        ],
        "gender": gender,
        "birthDate": birth_date.isoformat(),
        "active": True
    }


def generate_weight_observation(index, patient_id):
    observation_id = f"OBS-W-{index:04d}"

    weight = round(50 + ((index * 17) % 500) / 10, 1)

    return {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "text": "Vital Signs"
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "29463-7",
                    "display": "Body weight"
                }
            ],
            "text": "Body weight"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": "2026-11-10T09:00:00Z",
        "valueQuantity": {
            "value": weight,
            "unit": "kg",
            "system": "http://unitsofmeasure.org",
            "code": "kg"
        }
    }


def generate_blood_pressure_observation(index, patient_id):
    observation_id = f"OBS-BP-{index:04d}"

    systolic = 105 + (index % 36)
    diastolic = 65 + (index % 21)

    return {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "text": "Vital Signs"
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "85354-9",
                    "display": "Blood pressure panel"
                }
            ],
            "text": "Blood pressure"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "effectiveDateTime": "2026-11-10T09:05:00Z",
        "component": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic blood pressure"
                        }
                    ],
                    "text": "Systolic blood pressure"
                },
                "valueQuantity": {
                    "value": systolic,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8462-4",
                            "display": "Diastolic blood pressure"
                        }
                    ],
                    "text": "Diastolic blood pressure"
                },
                "valueQuantity": {
                    "value": diastolic,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ]
    }


for index in range(1, 1001):
    patient = generate_patient(index)
    patient_id = patient["id"]

    PATIENTS[patient_id] = patient

    weight = generate_weight_observation(index, patient_id)
    blood_pressure = generate_blood_pressure_observation(
        index,
        patient_id
    )

    OBSERVATIONS[weight["id"]] = weight
    OBSERVATIONS[blood_pressure["id"]] = blood_pressure


# ==================================================
# FHIR Bundle
# ==================================================

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
                "search": {
                    "mode": "match"
                }
            }
            for resource in resources
        ]
    }


# ==================================================
# Health
# ==================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "server": "Mock Hospital",
        "mode": "synthetic-data-only",
        "patients": len(PATIENTS),
        "observations": len(OBSERVATIONS)
    }


# ==================================================
# FHIR Patient
# ==================================================

@app.get("/fhir/Patient")
def search_patients(
    patient_id: str | None = Query(default=None, alias="_id")
):
    resources = list(PATIENTS.values())

    if patient_id:
        resources = [
            patient
            for patient in resources
            if patient["id"] == patient_id
        ]

    return make_bundle(resources)


@app.get("/fhir/Patient/{patient_id}")
def get_patient(patient_id: str):
    patient = PATIENTS.get(patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    return patient


# ==================================================
# FHIR Observation
# ==================================================

@app.get("/fhir/Observation")
def search_observations(
    subject: str | None = Query(default=None)
):
    resources = list(OBSERVATIONS.values())

    if subject:
        normalized_subject = subject.replace("Patient/", "")

        resources = [
            observation
            for observation in resources
            if observation.get("subject", {}).get("reference", "")
            == f"Patient/{normalized_subject}"
        ]

    return make_bundle(resources)


@app.get("/fhir/Observation/{observation_id}")
def get_observation(observation_id: str):
    observation = OBSERVATIONS.get(observation_id)

    if observation is None:
        raise HTTPException(
            status_code=404,
            detail="Observation not found"
        )

    return observation


# ==================================================
# FHIR Capability Statement
# ==================================================

@app.get("/fhir/metadata")
def metadata():
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": datetime.now(timezone.utc).isoformat(),
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {
                        "type": "Patient",
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"}
                        ]
                    },
                    {
                        "type": "Observation",
                        "interaction": [
                            {"code": "read"},
                            {"code": "search-type"}
                        ]
                    }
                ]
            }
        ]
    }
