# Testing and Integration

## Default offline suite

```powershell
cd backend
python -m compileall -q app tests scripts
python -m ruff check --no-cache .
python -m ruff format --check .
python -m pytest -p no:cacheprovider
```

The default suite uses fake FPT providers, SQLite or repository doubles, and Qdrant local memory.
It must not consume paid APIs.

## Local PostgreSQL and Qdrant

Use a disposable PostgreSQL database whose name ends with `_test` because the migration test
downgrades it to an empty schema before upgrading to head.

```env
RUN_LOCAL_INTEGRATION_TESTS=true
POSTGRES_TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/ubnd_reports_test
QDRANT_TEST_URL=http://localhost:6333
```

```powershell
docker compose up -d postgres qdrant
python -m pytest -m postgres
python -m pytest -m qdrant
```

## Paid/external services

External tests are opt-in and require `RUN_EXTERNAL_INTEGRATION_TESTS=true`. Exact URLs, model IDs,
and credentials must come from the FPT account. No external test is evidence until it actually
runs against that service.
