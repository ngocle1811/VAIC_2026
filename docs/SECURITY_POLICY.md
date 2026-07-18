# Security Policy

- Credentials are server-side environment values and must never enter source control.
- Restricted/classified documents are blocked from external transmission, not partially scrubbed.
- Phone/identifier-shaped values, API credentials, and local paths are masked before FPT LLM or
  embedding calls.
- Restoration maps are excluded from serialization and must not be logged.
- Managed upload storage enforces extension, MIME, size, safe names, and resolved-path boundaries.
- Default tests use synthetic data without real citizen information.

Authentication, authorization, rate limiting, malware scanning, and organization-specific data
classification policy remain incomplete and must precede production deployment.
