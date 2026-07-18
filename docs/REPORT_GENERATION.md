# Report Generation Framework

The framework defines typed requests, drafts, sections, tables, citations, numeric source
references, validation results, and lifecycle statuses. Numeric references must equal values from
the supplied operational report. Citations must use allowed retrieved source IDs. Human review is
mandatory before publication.

`SyntheticDOCXRenderer` only accepts templates marked `synthetic_test_only` and containing the
literal marker `SYNTHETIC_TEST_DATA`. This tests mechanics only and is not a claim of compatibility
with any government template. Official formatting support is blocked until approved templates are
provided.
