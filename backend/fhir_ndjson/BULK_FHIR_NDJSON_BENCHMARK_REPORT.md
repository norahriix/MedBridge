# MedBridge - Bulk FHIR NDJSON Benchmark Report

## Test Dataset
- Format: Synthetic Bulk FHIR NDJSON
- Files: 8
- Patients: 1
- Source records mapped: 8
- Clinical records: 7
- Conversion errors: 0

## Extracted Records
| Category | Records |
|---|---:|
| Observations | 1 |
| Medications | 1 |
| Allergies | 1 |
| Diagnoses | 1 |
| Encounters | 1 |
| Procedures | 1 |
| Immunizations | 1 |
| Total | 7 |

## Accuracy Audit
- Patient fields: 4/4 (100%)
- Observation fields: 5/5 (100%)
- Medication fields: 2/2 (100%)
- Allergy fields: 2/2 (100%)
- Diagnosis fields: 2/2 (100%)
- Encounter fields: 2/2 (100%)
- Procedure fields: 3/3 (100%)
- Immunization fields: 3/3 (100%)
- Total field comparisons: 23/23 (100%)
- Source record errors: 0

## Limitations
- Validation used one synthetic resource per category.
- Results do not establish full FHIR specification compliance.
- Performance and scalability remain untested.
- MedicationRequest and additional resource types were not tested.
