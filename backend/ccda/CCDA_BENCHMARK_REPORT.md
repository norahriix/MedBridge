# MedBridge - C-CDA Benchmark Report

## Test Dataset
- Format: Synthetic C-CDA XML
- XML files: 1,180
- XML parsing errors: 0

## Extracted Records
| Category | Records |
|---|---:|
| Observations | 393,389 |
| Medications | 14,102 |
| Allergies | 567 |
| Diagnoses | 8,766 |
| Encounters | 46,868 |
| Procedures | 36,451 |
| Immunizations | 15,013 |
| Total extracted items | 515,156 |

## Validation Results
- Observation date matching: 100%
- Medication name matching: 100%
- Medication dose matching: 100%
- Medication status matching: 100%
- Allergy matching: 100%
- Diagnosis matching: 100%
- Encounter matching: 100%
- Procedure matching: 100%
- Immunization matching: 100%
- Source record errors: 0
- Provenance coverage: 100%

## Limitations
- Matching tests used field-value comparisons and did not establish full clinical semantic equivalence.
- Total extracted items are not necessarily unique clinical events.
- Performance, scalability, security, and cross-format interoperability remain to be tested.
- Dataset contains synthetic data only.
