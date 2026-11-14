
from datetime import date
from uuid import uuid5, NAMESPACE_URL

import httpx

from canonical.models import Patient, Observation, SourceRecord


SOURCE = "mock_hospital_fhir"


def _get_bundle_resources(response_data, expected_type):
    if response_data.get("resourceType") != "Bundle":
        raise ValueError("Hospital response is not a FHIR Bundle")

    resources = []

    for entry in response_data.get("entry", []):
        resource = entry.get("resource", {})

        if resource.get("resourceType") == expected_type:
            resources.append(resource)

    return resources


def _get_patient_name(resource):
    names = resource.get("name", [])

    for name in names:
        if name.get("text"):
            return name["text"]

        given = " ".join(name.get("given", []))
        family = name.get("family", "")
        full_name = f"{given} {family}".strip()

        if full_name:
            return full_name

    return None


def _get_code_text(code_data):
    if code_data.get("text"):
        return code_data["text"]

    coding = code_data.get("coding", [])

    for item in coding:
        if item.get("display"):
            return item["display"]

    return None


def fetch_fhir_data(base_url="http://127.0.0.1:8001"):
    base_url = base_url.rstrip("/")

    with httpx.Client(timeout=15.0) as client:
        patient_response = client.get(
            f"{base_url}/fhir/Patient"
        )
        patient_response.raise_for_status()

        observation_response = client.get(
            f"{base_url}/fhir/Observation"
        )
        observation_response.raise_for_status()

    patient_resources = _get_bundle_resources(
        patient_response.json(),
        "Patient"
    )

    observation_resources = _get_bundle_resources(
        observation_response.json(),
        "Observation"
    )

    patients = []
    source_records = []
    patient_index = {}

    # قراءة المرضى
    for resource in patient_resources:
        fhir_id = resource.get("id")

        if not fhir_id:
            continue

        name = _get_patient_name(resource)

        birth_date_value = resource.get("birthDate")
        birth_date = (
            date.fromisoformat(birth_date_value)
            if birth_date_value
            else None
        )

        gender = resource.get("gender", "unknown")

        if gender not in ("male", "female"):
            gender = "unknown"

        patient = Patient(
            id=f"{SOURCE}:{fhir_id}",
            national_id=None,
            name=name,
            birth_date=birth_date,
            gender=gender,
            sources=[SOURCE]
        )

        patients.append(patient)
        patient_index[fhir_id] = patient

        source_records.append(
            SourceRecord(
                source=SOURCE,
                original=resource,
                mapped={
                    "source_patient_id": fhir_id,
                    "name": name,
                    "birth_date": birth_date_value,
                    "gender": gender
                },
                normalized={
                    "source_patient_id": fhir_id,
                    "name": name,
                    "birth_date": birth_date_value,
                    "gender": gender
                },
                provenance=[],
                errors=[]
            )
        )

    # قراءة القياسات الطبية
    for resource in observation_resources:
        observation_errors = []

        observation_id = resource.get("id")

        subject_reference = (
            resource.get("subject", {}).get("reference", "")
        )

        if not subject_reference.startswith("Patient/"):
            source_records.append(
                SourceRecord(
                    source=SOURCE,
                    original=resource,
                    mapped={},
                    normalized={},
                    provenance=[],
                    errors=[
                        "Observation has no valid Patient reference"
                    ]
                )
            )
            continue

        fhir_patient_id = subject_reference.split("/", 1)[1]
        patient = patient_index.get(fhir_patient_id)

        if patient is None:
            source_records.append(
                SourceRecord(
                    source=SOURCE,
                    original=resource,
                    mapped={},
                    normalized={},
                    provenance=[],
                    errors=["Referenced patient was not found"]
                )
            )
            continue

        effective_date = resource.get("effectiveDateTime")

        if not effective_date:
            source_records.append(
                SourceRecord(
                    source=SOURCE,
                    original=resource,
                    mapped={},
                    normalized={},
                    provenance=[],
                    errors=["Observation has no effectiveDateTime"]
                )
            )
            continue

        observation_date = date.fromisoformat(
            effective_date[:10]
        )

        # تجهيز القياسات سواء كانت valueQuantity أو component
        readings = []

        components = resource.get("component", [])

        if components:
            for index, component in enumerate(components):
                quantity = component.get("valueQuantity", {})
                value = quantity.get("value")

                code_data = component.get("code", {})
                observation_type = _get_code_text(code_data)

                if value is None:
                    observation_errors.append(
                        f"Component {index + 1} has no numeric valueQuantity"
                    )
                    continue

                if not observation_type:
                    observation_errors.append(
                        f"Component {index + 1} has no readable code"
                    )
                    continue

                readings.append({
                    "type": observation_type,
                    "value": float(value),
                    "unit": quantity.get("unit", "unknown"),
                    "id": str(uuid5(
                        NAMESPACE_URL,
                        f"{SOURCE}:{observation_id}:{index}:{observation_type}"
                    ))
                })

        else:
            quantity = resource.get("valueQuantity", {})
            value = quantity.get("value")

            code_data = resource.get("code", {})
            observation_type = _get_code_text(code_data)

            if value is not None and observation_type:
                readings.append({
                    "type": observation_type,
                    "value": float(value),
                    "unit": quantity.get("unit", "unknown"),
                    "id": observation_id or str(uuid5(
                        NAMESPACE_URL,
                        f"{SOURCE}:{fhir_patient_id}:{observation_type}:{effective_date}"
                    ))
                })
            else:
                observation_errors.append(
                    "Observation has no numeric valueQuantity or valid components"
                )

        # إضافة كل قراءة إلى سجل المريض
        normalized_readings = []

        for reading in readings:
            observation = Observation(
                id=reading["id"],
                type=reading["type"],
                value=reading["value"],
                unit=reading["unit"],
                date=observation_date,
                source=SOURCE,
                provenance=[]
            )

            patient.observations.append(observation)

            normalized_readings.append({
                "patient_id": fhir_patient_id,
                "type": reading["type"],
                "value": reading["value"],
                "unit": reading["unit"],
                "date": observation_date.isoformat()
            })

        source_records.append(
            SourceRecord(
                source=SOURCE,
                original=resource,
                mapped={
                    "patient_id": fhir_patient_id,
                    "readings": [
                        {
                            "type": reading["type"],
                            "value": reading["value"],
                            "unit": reading["unit"]
                        }
                        for reading in readings
                    ]
                },
                normalized={
                    "patient_id": fhir_patient_id,
                    "readings": normalized_readings
                },
                provenance=[],
                errors=observation_errors
            )
        )

    return patients, source_records
