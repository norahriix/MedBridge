from collections import Counter
from core.pipeline import run_pipeline


def test_pipeline_success():
    r = run_pipeline()
    assert r.status == "completed"
    assert r.errors == []


def test_patient_records():
    r = run_pipeline()
    assert len(r.patients) == 6
    assert len(r.source_records) == 14


def test_clinical_records():
    r = run_pipeline()
    assert sum(len(p.observations) for p in r.patients) == 2
    assert sum(len(p.medications) for p in r.patients) == 2
    assert sum(len(p.allergies) for p in r.patients) == 2
    assert sum(len(p.diagnoses) for p in r.patients) == 2


def test_identity_matching():
    r = run_pipeline()
    assert len(r.matches) == 15
    assert len(r.patients) == 6


def test_conflicts():
    r = run_pipeline()
    assert len(r.conflicts) == 4
    assert all(c.critical for c in r.conflicts)
    assert all(
        c.status == "NEEDS_HUMAN_REVIEW"
        for c in r.conflicts
    )


def test_resolution():
    r = run_pipeline()
    assert len(r.resolutions) == 4
    assert all(
        x.selected_value is None
        for x in r.resolutions
    )


def test_provenance():
    r = run_pipeline()
    assert all(s.original for s in r.source_records)
    assert all(s.provenance for s in r.source_records)


def test_fhir_resources():
    r = run_pipeline()
    counts = Counter(
        x["resourceType"] for x in r.fhir_resources
    )
    assert counts == {
        "Patient": 6,
        "Observation": 2,
        "MedicationStatement": 2,
        "AllergyIntolerance": 2,
        "Condition": 2
    }


def test_fhir_references():
    r = run_pipeline()
    patient_refs = {
        "Patient/" + x["id"]
        for x in r.fhir_resources
        if x["resourceType"] == "Patient"
    }

    for resource in r.fhir_resources:
        if resource["resourceType"] != "Patient":
            reference = resource.get(
                "subject", resource.get("patient")
            )
            assert reference["reference"] in patient_refs


def test_fhir_review_flags():
    r = run_pipeline()
    flagged = [
        x for x in r.fhir_resources
        if any(
            t.get("code") == "NEEDS_HUMAN_REVIEW"
            for t in x.get("meta", {}).get("tag", [])
        )
    ]
    assert len(flagged) == 8


def test_stable_fhir_ids():
    first = run_pipeline()
    second = run_pipeline()
    assert first.status == second.status == "completed"
    assert len(first.fhir_resources) == 14
    assert [x["id"] for x in first.fhir_resources] == [
        x["id"] for x in second.fhir_resources
    ]
