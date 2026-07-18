# System Architecture

## Authority and boundaries

- Backend: `backend/app/`
- Tests: `backend/tests/`
- Runtime originals: `backend/storage/`
- Synthetic automated-test data: `dataset/synthetic_tests/`
- Team-managed candidate official data: `ubnd_report_dataset/`

Operational values and RAG evidence are separate flows. PostgreSQL owns report lifecycle and
validated operational values. Qdrant owns searchable Knowledge Base chunks. The LLM is never a
source of official numbers, formulas, rules, or citations.

```text
API → Service → Repository / Domain Pipeline → Provider abstraction
```

The Agent coordinates tools. RAG supplies evidence only. Data Query and deterministic KPI/rule
services supply operational values. Report rendering requires numeric, citation, and human-review
validation.

## Current modules

- `app/rag`: document processing, ingestion, retrieval, context, citations.
- `app/llm`: fake and opt-in FPT-compatible clients.
- `app/agent`: bounded orchestration, tool registry, decision hints.
- `app/operational_data`: generic metadata, provenance, validation interfaces.
- `app/calculations`, `app/kpi`, `app/rules`: whitelisted deterministic operations.
- `app/reporting`: typed drafts, template registry, validation, synthetic DOCX renderer.
- `app/security`: external-transmission blocking and masking.

Domain-specific operational fields remain intentionally undefined until approved schemas arrive.
