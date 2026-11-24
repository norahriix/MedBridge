# MedBridge - Master Benchmark Report

## 1. Tested Data Formats

All test datasets are synthetic. No real patient data was used.

| Format | Files | Patients | Clinical Records | Accuracy Audit |
|---|---:|---:|---:|---:|
| C-CDA XML | 1,180 | 1,180 | 515,156 | 100% on tested fields |
| HL7 v2 | 1 | 1 | 7 | 100% |
| FHIR STU3 | 1 | 1 | 7 | 100% |
| FHIR DSTU2 | 1 | 1 | 7 | 100% |
| Bulk FHIR NDJSON | 8 | 1 | 7 | 23/23 (100%) |
| OMOP CDM | 7 | 1 | 6 | 16/16 (100%) |
| CPCDS-style CSV | 4 | 1 | 4 | 11/11 (100%) |
| DICOM | 1 | 1 | 1 | 7/7 (100%) |
| BFD RIF-style CSV | 4 | 1 | 3 | 9/9 (100%) |

## 2. C-CDA Validation

- XML files parsed: 1,180
- Parse errors: 0
- Clinical items extracted: 515,156
- Provenance coverage: 100%
- Observation date accuracy: 100%
- Duplicate observation IDs: 0
- Source record errors: 0
- Tested clinical category comparisons: 100%

## 3. Connector Validation

- All nine standalone connector tests completed.
- All reported zero source record errors.
- Tested sample fields matched their source values.
- OMOP allergy mapping was not tested.
- DICOM validation covered metadata only.

## 4. Existing FHIR Integration Baseline

Separate existing Mock Hospital integration test:
- Synthetic patients: 1,000
- Canonical observations: 3,000
- Pipeline status: completed
- Total pipeline patients: 1,006
- Pipeline errors: 0

This integration test is separate from the small standalone format samples above.

### Updated Pipeline Results After Bug Fixes

- Patient records before merging: 1,004
- Patient records after merging: 1,002
- Identity comparisons: 6
- Confirmed matching pairs: 3
- Detected conflicts: 4
- Within-source conflicts: 1
- Cross-source conflicts: 3
- Conflicts flagged for human review: 4
- Exported FHIR resources: 9,010
- Pipeline errors: 0
- Source records with missing provenance: 0

These results describe the current local synthetic-data pipeline test.
They do not establish clinical accuracy or production readiness.

## 5. Important Limitations

- All datasets used for testing are synthetic.
- Most standalone connectors were tested using one synthetic patient.
- CPCDS and BFD RIF samples are simplified format-inspired datasets.
- Accuracy results apply only to the tested samples and fields.
- Full healthcare standards compliance has not been established.
- Full OMOP vocabulary validation remains untested.
- DICOM validation covers metadata only.
- Identity matching was evaluated using a small synthetic fixture.
- Previous FHIR conversion benchmarks covered 1,000, 5,000 and 10,000 patients.
- Previous local concurrent API tests covered 5, 10 and 20 requests.
- The historical performance results have not been revalidated after the latest bug fixes.
- Production-scale performance, full security validation and long-duration stability remain untested.

## 6. Conclusion

MedBridge processed synthetic healthcare data across multiple formats.

Field-level accuracy results apply only to the tested samples.

Historical benchmarks demonstrate preliminary technical feasibility, not production readiness.

Further testing is required to establish full standards compliance, real-world identity matching accuracy, security and production scalability.

## FHIR PERFORMANCE BENCHMARK

| Patients | Source Records | Mapped Observations | Conversion Time | Throughput | Peak Memory | Errors |
|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 3,000 | 3,000 | 0.482 sec | 2,073.65 patients/sec | 12.30 MB | 0 |
| 5,000 | 15,000 | 15,000 | 2.190 sec | 2,283.10 patients/sec | 61.43 MB | 0 |
| 10,000 | 30,000 | 30,000 | 4.674 sec | 2,139.30 patients/sec | 122.85 MB | 0 |

RESULT: All three synthetic-data test sizes completed successfully.

LIMITATIONS:
- Measures FHIR connector conversion, not the complete pipeline.
- Network latency and concurrent requests were not tested.
- Memory reports Python tracemalloc peak during conversion.
- Production-scale database and load testing remain pending.


## Pipeline Repeated Execution Stability Test

- Total Runs: 4
- Successful Runs: 4
- Failed Runs: 0
- Errors: 0
- Execution Times: 2.952, 2.922, 3.066, 2.651 seconds
- Average Execution Time: 2.898 seconds
- Minimum Execution Time: 2.651 seconds
- Maximum Execution Time: 3.066 seconds
- Result: All 4 sequential pipeline executions completed successfully.

Note: This is a sequential repeated-run test, not a concurrent pipeline load test.


## Concurrent Pipeline Load Test - 5 Requests

- Concurrent Requests: 5
- Successful Requests: 5
- Failed Requests: 0
- Errors: 0
- Individual Response Times: 3.314, 3.663, 4.049, 4.505, 4.655 seconds
- Average Response Time: 4.037 seconds
- Result: 5 out of 5 concurrent pipeline requests completed successfully.
- Scope: Initial local concurrent API test; larger loads and production scalability remain untested.


## Concurrent Pipeline Load Test - 10 Requests

- Concurrent Requests: 10
- Successful Requests: 10
- Failed Requests: 0
- Errors: 0
- Individual Response Times: 2.469, 2.567, 3.116, 3.764, 3.973, 4.272, 4.442, 3.007, 3.855, 3.094 seconds
- Average Response Time: 3.456 seconds
- Minimum Response Time: 2.469 seconds
- Maximum Response Time: 4.442 seconds
- Result: All 10 concurrent pipeline requests completed successfully.
- Scope: Local concurrent API test; larger loads and production scalability remain untested.


## Concurrent Pipeline Load Test - 20 Requests

- Concurrent Requests: 20
- Successful Requests: 20
- Failed Requests: 0
- Errors: 0
- Average Response Time: 5.767 seconds
- Minimum Response Time: 3.455 seconds
- Maximum Response Time: 8.421 seconds
- Result: All 20 concurrent pipeline requests completed successfully.
- Scope: Local concurrent API test; production scalability and resource utilization remain untested.
