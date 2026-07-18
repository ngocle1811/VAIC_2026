# AGENTS.md

## 1. Project overview

This repository implements an Agentic AI Governance Report Assistant for Vietnamese ward-level People's Committees.

The system only supports three operational domains:

1. Population reporting: `population`
2. Complaints and denunciations: `complaints`
3. Task execution indicators: `tasks`

There is also a shared Knowledge Base domain:

```text
common_reporting
```

The Agent is the central orchestrator.

The Agent may call specialized tools:

* Data Query Tool
* KPI Tool
* Rule Engine Tool
* RAG Search Tool
* Report Export Tool

RAG is one tool available to the Agent. RAG is not the central controller of the system.

Before modifying or implementing the RAG module, read:

```text
docs/RAG_IMPLEMENTATION.md
```

---

## 2. Important data boundary

The system has two separate data flows.

### 2.1 Operational report data

Examples:

* Population reports
* Complaint statistics
* Task progress reports
* Monthly, weekly or quarterly operational figures

Operational data follows this pipeline:

```text
Upload
→ Parse
→ Extract
→ Standardize
→ Validate
→ Store in PostgreSQL / Unified Dataset
```

Operational data is the source of official numbers used in reports.

Operational report files must not be used as the primary RAG Knowledge Base for calculating official statistics.

### 2.2 Knowledge Base documents

Examples:

* Laws
* Decrees
* Circulars
* Decisions
* Local regulations
* Reporting instructions
* Report templates
* Business procedures
* Indicator definitions

Knowledge Base documents follow this pipeline:

```text
Upload
→ Classify
→ Parse or OCR
→ Clean
→ Analyze structure
→ Chunk
→ Attach metadata
→ Create embeddings
→ Store in Vector Database
```

RAG supplies regulations, templates, instructions and source evidence.

RAG must not calculate official statistics.

---

## 3. Required architecture

Place RAG implementation code under:

```text
backend/app/rag/
```

Recommended structure:

```text
backend/app/rag/
├── ingestion/
├── parsers/
├── cleaning/
├── structure/
├── chunking/
├── metadata/
├── embeddings/
├── vectorstores/
├── retrieval/
├── reranking/
├── context/
├── citations/
├── prompts/
└── types.py
```

Place the Agent-facing RAG tool under:

```text
backend/app/agent/tools/rag_search_tool.py
```

Do not place parsing, embedding, retrieval or vector database logic directly inside FastAPI route files.

---

## 4. Technology profile

Use existing project conventions when they already provide an equivalent component.

### Backend

```text
FastAPI
Pydantic
SQLAlchemy
PostgreSQL
```

### General document parsing

Primary parser:

```text
Docling
```

Specialized fallback parsers:

```text
PDF: PyMuPDF
DOCX: python-docx
XLSX: openpyxl
```

### OCR

Use PaddleOCR for scanned files.

OCR is not required in the first implementation phase unless the current task explicitly requests it.

### Chunking

Use structure-aware chunking.

Legal documents should be split according to:

```text
Chapter
→ Section
→ Article
→ Clause
→ Point
```

Reporting guidelines should be split according to headings and subheadings.

Report templates should preserve table headers, required fields and filling instructions.

Do not rely exclusively on fixed-length character splitting.

### Embedding

Default embedding model:

```text
Qwen/Qwen3-Embedding-0.6B
```

The embedding model must be isolated behind an `EmbeddingService`.

Initialize the model once and reuse it.

Do not load the embedding model for every request.

### Vector Database

Default Vector Database:

```text
Qdrant
```

The Qdrant implementation must be isolated behind a Vector Store interface.

Required retrieval capabilities:

* Dense vector search
* Metadata filtering
* Document deletion
* Document reindexing
* Idempotent ingestion

Hybrid dense and sparse retrieval may be added after basic dense retrieval is working.

### Reranker

Default reranking model:

```text
Qwen/Qwen3-Reranker-0.6B
```

The reranker must be isolated behind a `RerankerService`.

The reranker operates only on retrieved candidate chunks, not the full Knowledge Base.

### LLM provider

The application uses FPT AI Factory as its LLM provider through an OpenAI-compatible client.

Default generation model:

```text
Llama-3.3-70B-Instruct
```

The exact model identifier and base URL must come from environment variables.

Never hardcode the API key, base URL or model identifier.

Expected environment variables:

```env
FPT_API_KEY=
FPT_BASE_URL=
LLM_MODEL=Llama-3.3-70B-Instruct
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
PYTHONIOENCODING=utf-8
```

Use the exact base URL and model identifier issued by the user's FPT AI Factory account.

The FPT-hosted LLM is responsible for:

* Agent task analysis
* Tool selection
* Query rewriting when needed
* Reading retrieved RAG context
* Writing Vietnamese administrative reports
* Producing structured outputs
* Producing citations from retrieved source identifiers

The FPT-hosted LLM is not responsible for:

* OCR
* Embedding generation
* Vector search
* KPI calculation
* Official numeric validation
* Rule Engine validation

Implement an `LLMClient` abstraction so the provider or model can be replaced through configuration without changing Agent or RAG business logic.

---

## 5. Required RAG pipelines

### Pipeline 1: Knowledge Base ingestion

```text
Knowledge Base document
→ User-selected classification
→ Classification validation
→ Parser or OCR
→ Text cleaning
→ Document structure analysis
→ Structure-aware chunking
→ Metadata construction
→ Embedding generation
→ Vector Database storage
→ Index readiness verification
→ Knowledge Base ready
```

### Pipeline 2: Agent retrieval

```text
User request
→ Agent analyzes task
→ Agent decides whether RAG is needed
→ Build retrieval query
→ Apply metadata filters
→ Dense or hybrid search
→ Retrieve candidate chunks
→ Rerank candidates
→ Select final chunks
→ Build context
→ Send operational data and RAG context separately to LLM
→ Generate answer or report
→ Validate citations
→ Return structured result to Agent
```

---

## 6. Document classification rules

The administrator selects the document domain and document type.

Use this validation order:

```text
User-selected classification
→ Keyword and structural validation
→ LLM fallback only when classification remains uncertain
```

Do not use the LLM to classify every uploaded document.

Do not silently replace the administrator's selection.

When there is a mismatch, return:

* Selected category
* Suggested category
* Confidence
* Evidence
* Warning requiring user confirmation

Supported domains:

```text
common_reporting
population
complaints
tasks
```

Supported document types:

```text
legal_document
local_regulation
reporting_guideline
report_template
business_procedure
indicator_definition
```

Do not introduce new identifiers without updating schemas, tests and documentation.

---

## 7. Required chunk metadata

Every Vector Database chunk must contain:

```text
chunk_id
document_id
document_name
document_type
domain
document_status
chunk_index
content
```

Include these fields when available:

```text
source
document_number
issued_date
effective_date
expiry_date
chapter
section
article
clause
point
heading
page_number
sheet_name
table_name
parent_chunk_id
file_path
```

Metadata names must remain consistent across:

* Ingestion
* Vector Database storage
* Retrieval
* Context building
* Citation generation
* Document deletion

Validate metadata with Pydantic before indexing.

---

## 8. Sources of truth

PostgreSQL is the source of truth for:

* Document records
* Processing status
* Original file location
* Upload information
* Document lifecycle
* Operational report data
* Official numerical data

Object or local file storage is the source of truth for:

* Original PDF files
* Original DOCX files
* Original XLSX files
* Original scanned documents

Qdrant is the source of truth for:

* Searchable chunks
* Chunk embeddings
* Retrieval metadata

Do not discard the original uploaded file after indexing.

---

## 9. Coding rules

Follow the repository's existing patterns before creating new ones.

Required rules:

* Use Python type hints.
* Use Pydantic for validation.
* Keep API routes thin.
* Put business orchestration in services.
* Put PostgreSQL queries in repositories.
* Put RAG-specific processing under `app/rag`.
* Keep provider-specific LLM code behind `LLMClient`.
* Keep Qdrant-specific code behind a Vector Store interface.
* Keep model-specific reranking code behind `RerankerService`.
* Avoid hidden global mutable state.
* Avoid duplicate parsing, embedding or retrieval implementations.
* Do not load large models per request.
* Do not put all RAG logic in one file.
* Do not create generic dumping-ground files such as `utils.py` for unrelated responsibilities.
* Preserve page and structural source information whenever possible.
* Do not modify unrelated modules unless necessary.

Preferred component dependency direction:

```text
API Route
→ Service
→ RAG Pipeline
→ Parser / Embedding / Vector Store / Reranker
```

The lower-level RAG components must not import FastAPI route objects.

---

## 10. Error handling

The ingestion pipeline must handle:

* Unsupported file type
* File size violation
* Empty document
* Duplicate document
* Parser failure
* OCR failure
* Cleaning failure
* Structure analysis failure
* Missing required metadata
* Embedding failure
* Qdrant connection failure
* Partial indexing
* Reindexing failure

Document processing statuses:

```text
uploaded
processing
ready
failed
deleted
```

When ingestion fails:

1. Update the PostgreSQL document status to `failed`.
2. Save a useful error message and failed stage.
3. Remove partially indexed chunks for that document.
4. Log the document ID and pipeline stage.
5. Do not mark the document as `ready`.

Ingestion and reingestion must be idempotent.

---

## 11. Security rules

Never commit:

* API keys
* Real `.env` files
* Authentication tokens
* Sensitive citizen information
* Runtime uploaded documents
* Qdrant persisted runtime data

Use `.env.example` for placeholder configuration.

Before sending data to an external LLM:

* Separate operational data from RAG context.
* Mask personally identifiable information when required.
* Do not send unnecessary raw documents.
* Do not send file system paths.
* Do not send API credentials.
* Apply existing anonymization and redaction hooks.

---

## 12. Testing requirements

Add tests for:

* Parser selection
* PDF parsing
* DOCX parsing
* Text cleaning
* Vietnamese legal structure analysis
* Legal document chunking
* Guideline chunking
* Template chunking
* Metadata construction
* Ingestion idempotency
* Qdrant insertion
* Qdrant deletion by document ID
* Metadata filtering
* Retrieval relevance
* Reranking
* Context building
* Citation validation
* LLM client configuration
* Agent RAG Tool integration

Use the repository's current testing framework.

If none exists, use:

```text
pytest
```

Tests must not call the paid FPT API by default.

Use mocks or test doubles for:

* FPT LLM requests
* Embedding service when appropriate
* Qdrant network requests when appropriate

Integration tests that require external services must be explicitly marked.

---

## 13. Implementation phases

Implement incrementally.

### Phase 1 — Document processing

```text
Types
→ Parser interfaces
→ PDF parser
→ DOCX parser
→ Text cleaner
→ Structure analyzer
→ Chunkers
→ Metadata builder
→ Unit tests
```

### Phase 2 — Knowledge Base ingestion

```text
EmbeddingService
→ QdrantVectorStore
→ IngestionPipeline
→ PostgreSQL document model
→ Seed script
→ Integration tests
```

### Phase 3 — Retrieval

```text
Query builder
→ Metadata filters
→ Dense retrieval
→ Reranker
→ Context builder
→ Citation structures
→ RAG service
```

### Phase 4 — Agent integration

```text
FPT LLMClient
→ RAG Search Tool
→ Tool registration
→ Agent decision rules
→ Citation validation
→ Report-generation integration
```

### Phase 5 — Enhancements

```text
OCR
→ XLSX template parsing
→ Sparse/BM25 retrieval
→ Hybrid fusion
→ Background ingestion jobs
→ RAG evaluation
→ Administrative UI
```

Do not implement later phases until the required earlier phase tests pass.

---

## 14. Definition of done

A basic RAG implementation is complete only when:

1. A PDF or DOCX Knowledge Base document can be ingested.
2. The original file is preserved.
3. PostgreSQL stores the document record and status.
4. Content is parsed and cleaned.
5. Document structure is preserved where possible.
6. Meaningful chunks are created.
7. Required metadata is validated.
8. Embeddings are generated.
9. Qdrant stores chunks and vectors.
10. Reingestion does not create duplicate chunks.
11. Queries retrieve relevant chunks.
12. Retrieval supports domain and document-type filters.
13. Candidate chunks are reranked.
14. Context includes verifiable source information.
15. The Agent can call the RAG Search Tool.
16. The LLM provider can be changed through environment configuration.
17. FPT API credentials are never hardcoded.
18. Automated tests cover ingestion and retrieval.
