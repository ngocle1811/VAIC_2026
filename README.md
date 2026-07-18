# AI Governance Report Assistant

The authoritative backend is `backend/`. The current implementation provides document
processing, Knowledge Base ingestion abstractions, retrieval, a disabled-by-default Agent
scaffold, and provider-independent operational/KPI/rule/report frameworks.

The project is **not end-to-end complete**. Official operational schemas, KPI definitions,
validation rules, report templates, and reviewed ground truth are still being collected.

## Local setup

```powershell
cd backend
Copy-Item .env.example .env
docker compose up -d postgres qdrant
python -m alembic upgrade head
python -m pytest
```

Default tests do not call paid APIs. See `docs/TESTING.md` and
`docs/PROJECT_COMPLETION_PLAN.md` for integration gates and current status.

Synthetic fixtures live under `dataset/synthetic_tests/` and are explicitly marked
`SYNTHETIC_TEST_DATA` / `NOT_OFFICIAL`. Team-managed candidate official files remain under
`ubnd_report_dataset/` and are not modified by synthetic tests.
