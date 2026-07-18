# Project Completion Plan

Status values are evidence-based and do not merge mocked and real integration results.

| Ordered item | Status | Evidence / remaining gate |
|---|---|---|
| 1. PostgreSQL local infrastructure | `unverified_real_integration` | Compose healthcheck and opt-in empty-DB migration test exist; local server credentials not verified |
| 2. Qdrant local infrastructure | `unverified_real_integration` | Compose persistence/healthcheck and opt-in lifecycle test exist; service not running during implementation |
| 3. Phase 3 retrieval | `complete` | Dense/lexical/hybrid modes, RRF, effective-date filters, reranker factory/fallback, context and citations covered offline |
| 4. Phase 4 fake Agent/LLM scaffold | `complete` | Bounded orchestration, explicit registry/factory, fake LLM/tools, overwrite and citation protections tested |
| 5. Synthetic paired fixtures | `complete` | Three isolated domain pairs carry mandatory synthetic/non-official labels and explicit values |
| 6. Operational-data interfaces | `partially_complete` | Common typed metadata/provenance/validation contracts exist; domain fields/extractors blocked by official schemas |
| 7. KPI and Rule Engine frameworks | `partially_complete` | Whitelisted deterministic engines exist; official formulas/rules are `blocked_by_official_dataset` |
| 8. Report models and DOCX mechanics | `partially_complete` | Typed models/validators and synthetic rendering tests exist; official template compatibility is blocked |
| 9. Unit/integration/API/security tests | `partially_complete` | Offline and opt-in service tests exist; production auth/rate-limit/E2E tests remain |
| 10. Documentation | `complete` | Architecture, setup, testing, data gaps, security, evaluation, Agent and report docs exist |

## Verification snapshot

Verified on 2026-07-19:

- Code quality: `python -m ruff check app tests alembic` passed.
- Formatting: `python -m ruff format --check app tests alembic` passed for 153 files.
- Offline/default suite: 95 passed, 4 skipped, 0 failed. The skipped tests are the explicitly
  opt-in PostgreSQL, Qdrant, FPT Embedding, and FPT LLM service checks.
- Compose structure: `docker compose config --quiet` passed and exposes `postgres` and `qdrant`.
- Alembic: revision head `20260718_01`; offline PostgreSQL upgrade SQL generation passed.
- Real PostgreSQL: not verified because Docker Desktop's Linux daemon was unavailable and the
  unrelated listener on port 5432 did not accept the configured development credentials.
- Real Qdrant: not verified because Docker Desktop's Linux daemon was unavailable and no service
  was listening on port 6333.
- FPT services: no paid or external request was made.

## External integrations

| Integration | Status |
|---|---|
| PostgreSQL migration on empty real database | `unverified_real_integration` |
| Qdrant service persistence | `unverified_real_integration` |
| FPT Embedding | `blocked_by_credentials` |
| FPT Reranker | `blocked_by_credentials` and exact endpoint contract |
| FPT Llama | `blocked_by_credentials` |
| Full end-to-end workflow | `blocked_by_official_dataset` |

The next safe gate after official artifacts arrive is schema inventory and approval: record hashes,
authority/version, classification, expected mappings, and reviewed outputs before adding any
domain-specific parser, KPI, rule, or template logic.
