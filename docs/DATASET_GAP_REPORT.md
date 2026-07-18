# Dataset Gap Report

## Separation policy

- `ubnd_report_dataset/`: team-managed candidate official files; untouched by generated tests.
- `dataset/synthetic_tests/`: safe automated-test inputs marked `SYNTHETIC_TEST_DATA` and paired
  expected values marked `NOT_OFFICIAL`.

No candidate file is considered authoritative merely because it exists in the repository.

## Current gaps

| Area | Population | Complaints | Tasks | Status |
|---|---|---|---|---|
| Operational input report | Missing | Missing | Missing | `blocked_by_official_dataset` |
| Approved machine-readable input schema/mapping | Missing | Missing | Missing | `blocked_by_official_dataset` |
| Approved output template | Present candidates are unverified/legacy `.doc` | Mẫu 02 and six tables extracted from official DOCX; human review pending | Present candidates unverified | `blocked_by_official_dataset` |
| Approved indicator definitions and KPI formulas | Missing | Missing | Missing | `blocked_by_official_dataset` |
| Approved validation rules | Candidate JSON exists but authority/version unverified | Same | Same | `blocked_by_official_dataset` |
| Human-reviewed input/output ground truth | Missing | Missing | Missing | `blocked_by_official_dataset` |
| Knowledge Base coverage | Population candidates present, authority/effect unverified | TT06 DOCX/PDF preserved with hashes; remaining complaint coverage still requires review | Non-official technical drafts exist; official task documents remain missing | `blocked_by_official_dataset` |

## Exact artifacts still required from the team

For each of `population`, `complaints`, and `tasks`:

1. At least one de-identified official operational input report with its reporting period and
   issuing organization metadata.
2. The approved field dictionary/schema and source-to-standard-field mapping.
3. The approved output DOCX/XLSX template and written placeholder/filling rules.
4. Approved indicator definitions, units, rounding rules, and KPI formulas with authority/version.
5. Approved validation rules with severity and effective version.
6. A human-reviewed ground-truth package pairing input, standardized values, validation outcome,
   KPI result, and expected report content.

Knowledge Base artifacts still required:

- task-assignment/progress/status/evaluation regulations or guidance;
- complete complaint law/decree/guideline coverage used for reporting;
- confirmation of source, document number, issue/effective/expiry status for every candidate KB
  document;
- confirmation or replacement of common-reporting guidance and templates.

Complaint-template review still required:

- compare the extracted Mẫu số 02 and six XLSX workbooks with the signed source page by page;
- approve merged headers, units, formula-code rows, notes, print layout, and empty input rows;
- approve the canonical field mapping before changing complaint indicators to production status.

Non-official candidate master files now exist for indicators, report types, reporting periods,
task statuses, and field aliases. They remain development inputs rather than approved master data.

Master data still required:

- authority and field-level confirmation for `indicator_master`;
- approval or replacement of the draft `task_status_master`;
- approval of `report_type_master`, `reporting_period_master`, and `field_alias_master`;
- version/authority confirmation for organization and administrative-unit masters.

File names must be assigned by the team or derived only after document content is verified. This
report intentionally does not invent official filenames.

Ground Truth workflow scaffolding and the planned case registry now exist under
`ubnd_report_dataset/06_ground_truth/`. All cases remain `AWAITING_OFFICIAL_INPUT`; this structural
work does not change the missing status in the table above.
