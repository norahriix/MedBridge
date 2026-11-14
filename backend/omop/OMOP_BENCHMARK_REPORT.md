# MedBridge - OMOP CDM Benchmark Report

## Test Dataset
- Format: Synthetic OMOP-style CSV
- Files: 7
- Patients: 1
- Source records mapped: 7
- Conversion errors: 0

## Extracted Records
| Category | Records |
|---|---:|
| Observations | 1 |
| Medications | 1 |
| Diagnoses | 1 |
| Encounters | 1 |
| Procedures | 1 |
| Immunizations | 1 |
| Allergies | 0 |
| Total mapped clinical records | 6 |

## Accuracy Audit
| Category | Matched Fields | Accuracy |
|---|---:|---:|
| Patients | 3/3 | 100% |
| Observations | 4/4 | 100% |
| Medications | 2/2 | 100% |
| Diagnoses | 1/1 | 100% |
| Encounters | 2/2 | 100% |
| Procedures | 2/2 | 100% |
| Immunizations | 2/2 | 100% |
| Total | 16/16 | 100% |

## Limitations
- Synthetic sample contains one patient and a small number of records.
- Allergy mapping was not tested.
- The sample uses simplified CSV tables and is not a complete OMOP CDM implementation.
- Immunization data uses a custom sample table.
- Performance, scalability, and full OMOP vocabulary validation remain untested.
