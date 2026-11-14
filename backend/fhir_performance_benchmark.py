
import csv
import gc
import time
import tracemalloc
from unittest.mock import patch

import fhir.connector as connector
import mock_hospital.main as hospital


SIZES = [1000, 5000, 10000]
CURRENT_BUNDLES = {}


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, url):
        if url.endswith("/Patient"):
            return FakeResponse(CURRENT_BUNDLES["Patient"])
        if url.endswith("/Observation"):
            return FakeResponse(CURRENT_BUNDLES["Observation"])
        raise ValueError(f"Unexpected URL: {url}")


def make_bundle(resources):
    return {
        "resourceType": "Bundle",
        "entry": [{"resource": item} for item in resources]
    }


def build_data(count):
    patients = []
    observations = []

    for index in range(1, count + 1):
        patient = hospital.generate_patient(index)
        patient_id = patient["id"]
        patients.append(patient)

        observations.append(
            hospital.generate_weight_observation(index, patient_id)
        )
        observations.append(
            hospital.generate_blood_pressure_observation(
                index, patient_id
            )
        )

    return {
        "Patient": make_bundle(patients),
        "Observation": make_bundle(observations)
    }


def run_benchmark():
    results = []

    print("\n===== MEDBRIDGE FHIR PERFORMANCE BENCHMARK =====")

    for size in SIZES:
        gc.collect()

        generation_start = time.perf_counter()
        CURRENT_BUNDLES.clear()
        CURRENT_BUNDLES.update(build_data(size))
        generation_time = time.perf_counter() - generation_start

        tracemalloc.start()
        start = time.perf_counter()

        try:
            with patch.object(connector.httpx, "Client", FakeClient):
                patients, records = connector.fetch_fhir_data()

            elapsed = time.perf_counter() - start
            current_memory, peak_memory = tracemalloc.get_traced_memory()

        finally:
            tracemalloc.stop()

        mapped_observations = sum(
            len(patient.observations) for patient in patients
        )

        errors = sum(
            len(record.errors) for record in records
        )

        throughput = (
            len(patients) / elapsed if elapsed > 0 else 0
        )

        result = {
            "patients_requested": size,
            "patients_mapped": len(patients),
            "source_records": len(records),
            "observations_mapped": mapped_observations,
            "generation_seconds": round(generation_time, 3),
            "conversion_seconds": round(elapsed, 3),
            "patients_per_second": round(throughput, 2),
            "peak_memory_mb": round(peak_memory / (1024 * 1024), 2),
            "errors": errors
        }

        results.append(result)

        print("\n--------------------------------")
        for key, value in result.items():
            print(f"{key}: {value}")

        del patients, records
        gc.collect()

    with open(
        "FHIR_PERFORMANCE_BENCHMARK.csv",
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n===== BENCHMARK COMPLETED =====")
    print("REPORT: FHIR_PERFORMANCE_BENCHMARK.csv")


if __name__ == "__main__":
    run_benchmark()
