
from canonical.models import (
    Patient,
    Observation,
    Provenance,
    Conflict,
    ResolutionResult,
)


def test_patient_model():
    patient = Patient(
        id="p-001",
        name="Sara Ahmed",
        birth_date="1995-04-10",
        gender="female",
        sources=["hospital_a"],
        observations=[
            Observation(
                id="obs-001",
                type="HbA1c",
                value=7.2,
                unit="%",
                date="2026-11-01",
                source="hospital_a",
                provenance=[
                    Provenance(
                        source="hospital_a",
                        original_field="hba1c_result",
                        original_value="7.2%",
                        transformations=["removed %"]
                    )
                ]
            )
        ]
    )

    assert patient.name == "Sara Ahmed"
    assert patient.observations[0].value == 7.2
    assert patient.observations[0].source == "hospital_a"


def test_critical_conflict():
    conflict = Conflict(
        id="conflict-001",
        patient_id="p-001",
        field="allergy",
        conflict_type="ALLERGY_DRUG",
        record_ids=["allergy-001", "med-001"],
        values=["penicillin", "amoxicillin"],
        sources=["hospital_a", "hospital_b"],
        critical=True,
        status="NEEDS_HUMAN_REVIEW"
    )

    result = ResolutionResult(
        conflict_id=conflict.id,
        status="NEEDS_HUMAN_REVIEW",
        reason="Potential allergy-medication safety conflict",
        strategy="human_review"
    )

    assert conflict.critical is True
    assert result.status == "NEEDS_HUMAN_REVIEW"
    assert result.selected_value is None
