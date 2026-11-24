
from datetime import date
from uuid import uuid5, NAMESPACE_URL

import httpx
from provenance.tracker import track_provenance

from canonical.models import (
    Patient,
    Observation,
    Medication,
    Allergy,
    Diagnosis,
    Procedure,
    MedicalHistory,
    Encounter,
    Immunization,
    FamilyHistory,
    SourceRecord,
)


SOURCE = "mock_hospital_fhir"

RESOURCE_TYPES = [
    "Patient",
    "Observation",
    "Condition",
    "AllergyIntolerance",
    "MedicationStatement",
    "Encounter",
    "Procedure",
    "Immunization",
    "FamilyMemberHistory",
]


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
    for name in resource.get("name", []):
        if name.get("text"):
            return name["text"]

        given = " ".join(name.get("given", []))
        family = name.get("family", "")
        full_name = f"{given} {family}".strip()

        if full_name:
            return full_name

    return None


def _get_code_text(code_data):
    if not isinstance(code_data, dict):
        return None

    if code_data.get("text"):
        return code_data["text"]

    for item in code_data.get("coding", []):
        if item.get("display"):
            return item["display"]

        if item.get("code"):
            return item["code"]

    return None


def _get_date(value):
    if not value:
        return None

    if isinstance(value, dict):
        value = value.get("start") or value.get("end")

    if not value:
        return None

    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _get_reference_id(resource):
    reference = resource.get("subject", {}).get("reference", "")

    if not reference:
        reference = resource.get("patient", {}).get("reference", "")

    if not reference:
        return None

    if "Patient/" not in reference:
        return None

    return reference.split("Patient/", 1)[1].split("/", 1)[0]


def _get_national_id(resource):
    for identifier in resource.get("identifier", []):
        if identifier.get("system") == "urn:mock-hospital:national-id":
            return identifier.get("value")

    return None


def _get_status(resource, default="unknown"):
    return resource.get("status") or default

def _build_fhir_provenance(resource):
    return [
        track_provenance(
            source=SOURCE,
            original_field=field,
            original_value=value,
            transformations=[]
        )
        for field, value in resource.items()
    ]
def _make_source_record(resource, mapped, normalized, errors=None):
    return SourceRecord(
        source=SOURCE,
        original=resource,
        mapped=mapped,
        normalized=normalized,
        provenance=_build_fhir_provenance(resource),
        errors=errors or [],
    )


def _resource_id(resource, resource_type):
    return resource.get("id") or str(
        uuid5(
            NAMESPACE_URL,
            f"{SOURCE}:{resource_type}:{resource}",
        )
    )


def fetch_fhir_data(base_url="http://127.0.0.1:8001"):
    base_url = base_url.rstrip("/")

    # جلب جميع أنواع موارد FHIR من المستشفى الوهمي
    resources_by_type = {}

    with httpx.Client(timeout=60.0) as client:
        for resource_type in RESOURCE_TYPES:
            response = client.get(
                f"{base_url}/fhir/{resource_type}"
            )
            response.raise_for_status()

            resources_by_type[resource_type] = _get_bundle_resources(
                response.json(),
                resource_type,
            )

    patients = []
    source_records = []
    patient_index = {}

    # ==================================================
    # 1. Patients
    # ==================================================

    for resource in resources_by_type["Patient"]:
        fhir_id = resource.get("id")

        if not fhir_id:
            continue

        name = _get_patient_name(resource)
        birth_date_value = resource.get("birthDate")
        birth_date = _get_date(birth_date_value)

        gender = resource.get("gender", "unknown")

        if gender not in ("male", "female"):
            gender = "unknown"

        national_id = _get_national_id(resource)

        patient = Patient(
            id=f"{SOURCE}:{fhir_id}",
            national_id=national_id,
            name=name,
            birth_date=birth_date,
            gender=gender,
            sources=[SOURCE],
        )

        patients.append(patient)
        patient_index[fhir_id] = patient

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "source_patient_id": fhir_id,
                    "national_id": national_id,
                    "name": name,
                    "birth_date": birth_date_value,
                    "gender": gender,
                },
                normalized={
                    "source_patient_id": fhir_id,
                    "national_id": national_id,
                    "name": name,
                    "birth_date": (
                        birth_date.isoformat() if birth_date else None
                    ),
                    "gender": gender,
                },
            )
        )

    # ==================================================
    # 2. Observations
    # ==================================================

    for resource in resources_by_type["Observation"]:
        errors = []
        patient_id = _get_reference_id(resource)
        patient = patient_index.get(patient_id)

        if patient is None:
            source_records.append(
                _make_source_record(
                    resource,
                    {},
                    {},
                    ["Referenced patient was not found"],
                )
            )
            continue

        observation_id = resource.get("id")
        effective_date = (
            resource.get("effectiveDateTime")
            or resource.get("effectiveInstant")
            or resource.get("effectivePeriod", {}).get("start")
        )
        observation_date = _get_date(effective_date)

        if not observation_date:
            source_records.append(
                _make_source_record(
                    resource,
                    {},
                    {},
                    ["Observation has no valid effective date"],
                )
            )
            continue

        readings = []
        components = resource.get("component", [])

        if components:
            for index, component in enumerate(components):
                quantity = component.get("valueQuantity", {})
                value = quantity.get("value")
                observation_type = _get_code_text(
                    component.get("code", {})
                )

                if value is None or not observation_type:
                    errors.append(
                        f"Invalid Observation component {index + 1}"
                    )
                    continue

                readings.append({
                    "id": str(uuid5(
                        NAMESPACE_URL,
                        f"{SOURCE}:{observation_id}:{index}:{observation_type}",
                    )),
                    "type": observation_type,
                    "value": float(value),
                    "unit": quantity.get("unit", "unknown"),
                })

        else:
            quantity = resource.get("valueQuantity", {})
            value = quantity.get("value")
            observation_type = _get_code_text(
                resource.get("code", {})
            )

            if value is not None and observation_type:
                readings.append({
                    "id": observation_id or _resource_id(
                        resource, "Observation"
                    ),
                    "type": observation_type,
                    "value": float(value),
                    "unit": quantity.get("unit", "unknown"),
                })
            else:
                errors.append(
                    "Observation has no numeric valueQuantity or components"
                )

        normalized_readings = []

        for reading in readings:
            patient.observations.append(
                Observation(
                    id=reading["id"],
                    type=reading["type"],
                    value=reading["value"],
                    unit=reading["unit"],
                    date=observation_date,
                    source=SOURCE,
                    provenance=_build_fhir_provenance(resource),
                )
            )

            normalized_readings.append({
                "type": reading["type"],
                "value": reading["value"],
                "unit": reading["unit"],
                "date": observation_date.isoformat(),
            })

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "patient_id": patient_id,
                    "readings": readings,
                },
                normalized={
                    "patient_id": patient_id,
                    "readings": normalized_readings,
                },
                errors=errors,
            )
        )

    # ==================================================
    # 3. Conditions: diagnoses and medical history
    # ==================================================

    for resource in resources_by_type["Condition"]:
        patient_id = _get_reference_id(resource)
        patient = patient_index.get(patient_id)

        code_data = resource.get("code", {})
        description = _get_code_text(code_data) or "Unknown condition"
        code = None

        for coding in code_data.get("coding", []):
            if coding.get("code"):
                code = coding["code"]
                break

        onset_date = _get_date(
            resource.get("onsetDateTime")
            or resource.get("onsetPeriod")
        )
        resolved_date = _get_date(
            resource.get("abatementDateTime")
            or resource.get("abatementPeriod")
        )
        status = _get_code_text(
            resource.get("clinicalStatus", {})
        ) or "unknown"

        if patient is None:
            source_records.append(
                _make_source_record(
                    resource, {}, {},
                    ["Referenced patient was not found"],
                )
            )
            continue

        condition_id = _resource_id(resource, "Condition")

        patient.diagnoses.append(
            Diagnosis(
                id=condition_id,
                code=code,
                description=description,
                source=SOURCE,
                provenance=_build_fhir_provenance(resource),
            )
        )

        patient.medical_history.append(
            MedicalHistory(
                id=condition_id,
                condition=description,
                code=code,
                onset_date=onset_date,
                resolved_date=resolved_date,
                status=status,
                notes=None,
                source=SOURCE,
                provenance=_build_fhir_provenance(resource),
            )
        )

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "patient_id": patient_id,
                    "diagnosis": description,
                    "code": code,
                    "status": status,
                },
                normalized={
                    "patient_id": patient_id,
                    "diagnosis": description,
                    "code": code,
                    "status": status,
                    "onset_date": (
                        onset_date.isoformat() if onset_date else None
                    ),
                },
            )
        )

    # ==================================================
    # 4. Allergies
    # ==================================================

    for resource in resources_by_type["AllergyIntolerance"]:
        patient_id = _get_reference_id(resource)
        patient = patient_index.get(patient_id)

        code_data = resource.get("code", {})
        substance = _get_code_text(code_data) or "Unknown allergy"

        reaction = None
        reactions = resource.get("reaction", [])

        if reactions:
            manifestations = reactions[0].get("manifestation", [])
            if manifestations:
                reaction = _get_code_text(manifestations[0])

        if patient is None:
            source_records.append(
                _make_source_record(
                    resource, {}, {},
                    ["Referenced patient was not found"],
                )
            )
            continue

        patient.allergies.append(
            Allergy(
                id=_resource_id(resource, "AllergyIntolerance"),
                substance=substance,
                reaction=reaction,
                status=_get_status(resource),
                source=SOURCE,
                provenance=_build_fhir_provenance(resource),
            )
        )

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "patient_id": patient_id,
                    "substance": substance,
                    "reaction": reaction,
                },
                normalized={
                    "patient_id": patient_id,
                    "substance": substance,
                    "reaction": reaction,
                    "status": _get_status(resource),
                },
            )
        )

    # ==================================================
    # 5. Medication Statements
    # ==================================================

    for resource in resources_by_type["MedicationStatement"]:
        patient_id = _get_reference_id(resource)
        patient = patient_index.get(patient_id)

        medication_data = resource.get(
            "medicationCodeableConcept", {}
        )
        medication_name = (
            _get_code_text(medication_data)
            or resource.get("medicationReference", {}).get("display")
            or "Unknown medication"
        )

        dose = None
        dosage = resource.get("dosage", [])

        if dosage:
            dose = dosage[0].get("text")

            if not dose:
                dose_quantity = dosage[0].get("doseAndRate", [])
                if dose_quantity:
                    quantity = dose_quantity[0].get(
                        "doseQuantity", {}
                    )
                    if quantity.get("value") is not None:
                        dose = (
                            f"{quantity['value']} "
                            f"{quantity.get('unit', '')}"
                        ).strip()

        if patient is None:
            source_records.append(
                _make_source_record(
                    resource, {}, {},
                    ["Referenced patient was not found"],
                )
            )
            continue

        patient.medications.append(
            Medication(
                id=_resource_id(resource, "MedicationStatement"),
                name=medication_name,
                dose=dose,
                status=_get_status(resource),
                source=SOURCE,
                provenance=_build_fhir_provenance(resource),
            )
        )

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "patient_id": patient_id,
                    "medication": medication_name,
                    "dose": dose,
                },
                normalized={
                    "patient_id": patient_id,
                    "medication": medication_name,
                    "dose": dose,
                    "status": _get_status(resource),
                },
            )
        )

    # ==================================================
    # 6. Encounters
    # ==================================================

    for resource in resources_by_type["Encounter"]:
        patient_id = _get_reference_id(resource)
        patient = patient_index.get(patient_id)

        encounter_type = "Unknown encounter"
        encounter_classes = resource.get("class", [])

        if isinstance(encounter_classes, dict):
            encounter_type = (
                encounter_classes.get("display")
                or encounter_classes.get("code")
                or encounter_type
            )
        elif encounter_classes:
            encounter_type = _get_code_text(
                encounter_classes[0].get("type", {})
            ) or encounter_type

        period = resource.get("period", {})
        encounter_date = _get_date(
            period.get("start")
            or resource.get("actualPeriod", {}).get("start")
        )

        reason = None
        reasons = resource.get("reasonCode", [])

        if reasons:
            reason = _get_code_text(reasons[0])

        if patient is None:
            source_records.append(
                _make_source_record(
                    resource, {}, {},
                    ["Referenced patient was not found"],
                )
            )
            continue

        patient.encounters.append(
            Encounter(
                id=_resource_id(resource, "Encounter"),
                encounter_type=encounter_type,
                date=encounter_date,
                reason=reason,
                diagnosis=None,
                location=None,
                status=_get_status(resource),
                notes=None,
                source=SOURCE,
                provenance=_build_fhir_provenance(resource),
            )
        )

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "patient_id": patient_id,
                    "encounter_type": encounter_type,
                    "reason": reason,
                },
                normalized={
                    "patient_id": patient_id,
                    "encounter_type": encounter_type,
                    "date": (
                        encounter_date.isoformat()
                        if encounter_date else None
                    ),
                    "reason": reason,
                    "status": _get_status(resource),
                },
            )
        )

    # ==================================================
    # 7. Procedures
    # ==================================================

    for resource in resources_by_type["Procedure"]:
        patient_id = _get_reference_id(resource)
        patient = patient_index.get(patient_id)

        code_data = resource.get("code", {})
        procedure_name = (
            _get_code_text(code_data) or "Unknown procedure"
        )

        performed_date = _get_date(
            resource.get("performedDateTime")
            or resource.get("performedPeriod")
        )

        if patient is None:
            source_records.append(
                _make_source_record(
                    resource, {}, {},
                    ["Referenced patient was not found"],
                )
            )
            continue

        patient.procedures.append(
            Procedure(
                id=_resource_id(resource, "Procedure"),
                name=procedure_name,
                procedure_type=None,
                date=performed_date,
                status=_get_status(resource),
                outcome=None,
                notes=None,
                source=SOURCE,
                provenance=_build_fhir_provenance(resource),
            )
        )

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "patient_id": patient_id,
                    "procedure": procedure_name,
                },
                normalized={
                    "patient_id": patient_id,
                    "procedure": procedure_name,
                    "date": (
                        performed_date.isoformat()
                        if performed_date else None
                    ),
                    "status": _get_status(resource),
                },
            )
        )

    # ==================================================
    # 8. Immunizations
    # ==================================================

    for resource in resources_by_type["Immunization"]:
        patient_id = _get_reference_id(resource)
        patient = patient_index.get(patient_id)

        vaccine = (
            _get_code_text(resource.get("vaccineCode", {}))
            or "Unknown vaccine"
        )

        immunization_date = _get_date(
            resource.get("occurrenceDateTime")
        )

        dose = resource.get("doseQuantity", {}).get("value")

        if patient is None:
            source_records.append(
                _make_source_record(
                    resource, {}, {},
                    ["Referenced patient was not found"],
                )
            )
            continue

        patient.immunizations.append(
            Immunization(
                id=_resource_id(resource, "Immunization"),
                vaccine=vaccine,
                date=immunization_date,
                dose=str(dose) if dose is not None else None,
                status=_get_status(resource),
                source=SOURCE,
                provenance=_build_fhir_provenance(resource),
            )
        )

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "patient_id": patient_id,
                    "vaccine": vaccine,
                    "dose": dose,
                },
                normalized={
                    "patient_id": patient_id,
                    "vaccine": vaccine,
                    "date": (
                        immunization_date.isoformat()
                        if immunization_date else None
                    ),
                    "dose": dose,
                    "status": _get_status(resource),
                },
            )
        )

    # ==================================================
    # 9. Family Member History
    # ==================================================

    for resource in resources_by_type["FamilyMemberHistory"]:
        patient_id = _get_reference_id(resource)
        patient = patient_index.get(patient_id)

        relationship = _get_code_text(
            resource.get("relationship", {})
        )

        conditions = resource.get("condition", [])
        family_condition = "Unknown family condition"

        if conditions:
            family_condition = (
                _get_code_text(conditions[0].get("code", {}))
                or family_condition
            )

        notes = None

        if conditions:
            notes = conditions[0].get("note", [{}])[0].get("text")

        if patient is None:
            source_records.append(
                _make_source_record(
                    resource, {}, {},
                    ["Referenced patient was not found"],
                )
            )
            continue

        patient.family_history.append(
            FamilyHistory(
                id=_resource_id(resource, "FamilyMemberHistory"),
                condition=family_condition,
                relationship=relationship,
                notes=notes,
                source=SOURCE,
                provenance=_build_fhir_provenance(resource),
            )
        )

        source_records.append(
            _make_source_record(
                resource,
                mapped={
                    "patient_id": patient_id,
                    "condition": family_condition,
                    "relationship": relationship,
                },
                normalized={
                    "patient_id": patient_id,
                    "condition": family_condition,
                    "relationship": relationship,
                },
            )
        )

    return patients, source_records
