# Operational Data Pipeline

```text
Managed upload → domain extractor → generic schema mapping → standardization
→ deterministic validation → PostgreSQL → KPI/rule tools → human review
```

The current provider-independent contracts define report metadata, reporting period,
organization, processing status, provenance, and validation issues for `population`,
`complaints`, and `tasks`.

No domain-specific fields are final. Extractors must retain source evidence. Model-produced
extraction must be identified and reviewed. Validators and rules must not mutate source values.
Official domain schemas and mappings are blocked by the artifacts listed in
`DATASET_GAP_REPORT.md`.
