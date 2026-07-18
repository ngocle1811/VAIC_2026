# RAG Implementation Specification

## 1. Purpose

This document defines the detailed implementation requirements for the RAG module of the AI Governance Report Assistant.

The system follows an Agentic AI architecture.

The Agent can call RAG when it needs:

* Legal regulations
* Reporting requirements
* Report templates
* Reporting instructions
* Business procedures
* Indicator definitions
* Supporting evidence
* Source citations

RAG does not own or calculate official operational figures.

Official figures must come from PostgreSQL, the Unified Dataset, the Data Query Tool or the KPI Tool.

---

# 2. System architecture

## 2.1 Main components

```text
Knowledge Base Management API
        ↓
KnowledgeBaseService
        ↓
IngestionPipeline
        ├── DocumentClassifier
        ├── ParserFactory
        ├── TextCleaner
        ├── StructureAnalyzer
        ├── ChunkerFactory
        ├── MetadataBuilder
        ├── EmbeddingService
        └── QdrantVectorStore
```

Retrieval flow:

```text
Agent
  ↓
RAGSearchTool
  ↓
RAGService
  ↓
RetrievalPipeline
  ├── QueryBuilder
  ├── MetadataFilterBuilder
  ├── QdrantVectorStore
  ├── RerankerService
  ├── ContextBuilder
  └── CitationValidator
```

Generation flow:

```text
Agent
  ↓
Operational Data
+
RAG Context
  ↓
FPTLLMClient
  ↓
Llama-3.3-70B-Instruct
  ↓
Answer or Administrative Report
```

---

# 3. Technology decisions

## 3.1 Backend

```text
FastAPI
Pydantic
SQLAlchemy
PostgreSQL
```

## 3.2 Document parsing

Primary general parser:

```text
Docling
```

Specialized fallback parsers:

```text
PDF: PyMuPDF
DOCX: python-docx
XLSX: openpyxl
```

The first implementation phase must support:

```text
.pdf
.docx
```

XLSX and OCR may be implemented in later phases unless currently required.

## 3.3 OCR

Use:

```text
PaddleOCR
```

OCR should only run when:

* The PDF contains no meaningful text layer.
* The document is an image.
* Text extraction quality is below the configured threshold.

Do not run OCR on every PDF.

## 3.4 Embedding

Default model:

```text
Qwen/Qwen3-Embedding-0.6B
```

The embedding model is independent from the FPT-hosted generation LLM.

Required interface:

```python
class EmbeddingService:
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        ...

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        ...
```

The model must be initialized once and reused.

## 3.5 Vector Database

Use:

```text
Qdrant
```

Qdrant stores:

* Chunk IDs
* Chunk text
* Dense embeddings
* Retrieval metadata

Required Vector Store interface:

```python
class VectorStore:
    def add_chunks(self, chunks: list[EmbeddedChunk]) -> None:
        ...

    def search(
        self,
        query_vector: list[float],
        filters: RetrievalFilters,
        top_k: int,
    ) -> list[RetrievedChunk]:
        ...

    def delete_by_document_id(self, document_id: str) -> None:
        ...

    def count_by_document_id(self, document_id: str) -> int:
        ...
```

## 3.6 Reranking

Default model:

```text
Qwen/Qwen3-Reranker-0.6B
```

The reranker accepts only a limited candidate list.

Recommended defaults:

```text
retrieval_candidate_top_k = 20
reranker_final_top_k = 5
```

Both values must be configurable.

## 3.7 Generation LLM

Provider:

```text
FPT AI Factory
```

Default model:

```text
Llama-3.3-70B-Instruct
```

The exact model name and base URL are runtime configuration values.

Expected environment variables:

```env
FPT_API_KEY=your_fpt_ai_factory_api_key_here
FPT_BASE_URL=copy_the_exact_endpoint_from_fpt_ai_factory
LLM_MODEL=Llama-3.3-70B-Instruct
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
LLM_TIMEOUT_SECONDS=120
PYTHONIOENCODING=utf-8
```

Never assume that a manually written endpoint or model identifier is correct.

Use exactly the endpoint and model identifier displayed in the user's FPT AI Factory account.

Required abstraction:

```python
class LLMClient:
    def generate(
        self,
        messages: list[LLMMessage],
        response_schema: type | None = None,
    ) -> LLMResponse:
        ...
```

FPT-specific implementation:

```python
class FPTLLMClient(LLMClient):
    ...
```

The rest of the application must depend on `LLMClient`, not directly on the OpenAI-compatible SDK.

---

# 4. Supported domains and document types

## 4.1 Domains

```text
common_reporting
population
complaints
tasks
```

## 4.2 Document types

```text
legal_document
local_regulation
reporting_guideline
report_template
business_procedure
indicator_definition
```

## 4.3 Knowledge Base examples

### Common reporting

* General reporting regulations
* Reporting deadlines
* Administrative reporting procedures
* General report templates

### Population

* Population reporting instructions
* Residence-statistics definitions
* Population report templates
* Local population-reporting guidelines

### Complaints

* Citizen reception guidelines
* Complaint and denunciation reporting instructions
* Complaint report templates
* Complaint indicator definitions

### Tasks

* Task assignment procedures
* Progress reporting instructions
* Task status definitions
* Task progress report templates

---

# 5. Pipeline 1 — Building the Knowledge Base

## 5.1 Pipeline overview

```text
Knowledge Base Document
        │
        ▼
User-Selected Classification
        │
        ▼
Classification Validation
        │
        ▼
Parser or OCR
        │
        ▼
Text Cleaning
        │
        ▼
Document Structure Analysis
        │
        ▼
Structure-Aware Chunking
        │
        ▼
Metadata Construction
        │
        ▼
Embedding Generation
        │
        ▼
Qdrant Storage
        │
        ▼
Index Readiness Verification
        │
        ▼
Knowledge Base Ready
```

---

## 5.2 Step 1 — Receive and store document

### Input

Required:

```text
file
domain
document_type
```

Optional:

```text
document_name
document_number
source
issued_date
effective_date
expiry_date
document_status
notes
```

### Processing

1. Validate extension.
2. Validate MIME type.
3. Validate file size.
4. Calculate SHA-256 checksum.
5. Check duplicate documents.
6. Create a unique `document_id`.
7. Save the original file.
8. Create a PostgreSQL record.
9. Set processing status to `uploaded`.

### Output

```text
document_id
original_file_path
checksum
PostgreSQL document record
```

The runtime upload must be stored under `storage`, not copied into the developer seed dataset.

---

## 5.3 Step 2 — Classification validation

The administrator is the primary classifier.

The system validates the selection using:

* File name
* Document title
* Keywords
* Detected headings
* Expected structure
* Document-number patterns

Example domain terms:

### Population

```text
dân cư
nhân khẩu
hộ
thường trú
tạm trú
tạm vắng
biến động dân cư
cư trú
```

### Complaints

```text
khiếu nại
tố cáo
tiếp công dân
đơn thư
giải quyết đơn
thuộc thẩm quyền
tồn đọng
```

### Tasks

```text
nhiệm vụ
đơn vị chủ trì
đơn vị phối hợp
thời hạn
tiến độ
hoàn thành
quá hạn
```

Output:

```json
{
  "selected_domain": "complaints",
  "suggested_domain": "complaints",
  "confidence": 0.94,
  "evidence": [
    "Detected phrase: tiếp công dân",
    "Detected phrase: giải quyết khiếu nại"
  ],
  "requires_confirmation": false,
  "warning": null
}
```

Do not call the LLM unless rule-based confidence is below the configured threshold.

Do not automatically overwrite the administrator's selection.

---

## 5.4 Step 3 — Parser selection

Use `ParserFactory`.

```text
PDF with text layer
→ Docling or PyMuPDF parser

DOCX
→ Docling or python-docx parser

XLSX
→ openpyxl parser

Scanned PDF or image
→ PaddleOCR parser
```

Required parser interface:

```python
class BaseParser:
    def supports(self, file_path: str) -> bool:
        ...

    def parse(self, file_path: str) -> ParsedDocument:
        ...
```

Parsed output must preserve where available:

* Page number
* Paragraph order
* Heading hierarchy
* Tables
* Sheet names
* Cell ranges
* Source offsets
* Parser warnings

Example:

```json
{
  "document_id": "doc_001",
  "plain_text": "...",
  "blocks": [],
  "tables": [],
  "page_count": 15,
  "parser_name": "docling",
  "warnings": []
}
```

---

## 5.5 Step 4 — OCR decision

Before OCR, evaluate extracted text.

OCR should run when:

```text
Text length is below threshold
OR
Most pages have no text
OR
Extraction confidence is low
OR
The file is an image
```

OCR output must preserve page references.

Do not overwrite good native PDF text with lower-quality OCR output.

---

## 5.6 Step 5 — Text cleaning

The cleaner handles:

* Duplicate headers
* Duplicate footers
* Isolated page numbers
* Broken line endings
* Excessive whitespace
* Invalid Unicode
* Repeated blank lines
* Common OCR artifacts
* Hyphenation caused by page breaks

The cleaner must not:

* Rewrite legal meaning
* Summarize text
* Remove document numbers
* Remove article numbers
* Remove clause numbers
* Remove point labels
* Remove report field names
* Alter official values

Output:

```text
cleaned blocks
cleaned plain text
cleaning warnings
```

---

## 5.7 Step 6 — Structure analysis

Detect Vietnamese administrative structures.

### Legal documents

```text
Phần
Chương
Mục
Điều
Khoản
Điểm
Phụ lục
```

Example patterns:

```text
PHẦN I
CHƯƠNG II
Mục 1
Điều 8.
1.
a)
```

### Guidelines and procedures

```text
I.
II.
1.
1.1.
1.2.
Bước 1
Bước 2
```

### Report templates

Preserve:

* Template name
* Section names
* Table headers
* Required fields
* Placeholder fields
* Filling instructions
* Notes
* Signatory sections

Output:

```python
list[DocumentBlock]
```

Each block should contain:

```text
block_id
block_type
title
content
page_number
hierarchy
source_position
```

---

## 5.8 Step 7 — Structure-aware chunking

Choose the chunker based on document type.

### Legal document chunker

Priority:

```text
Chapter
→ Section
→ Article
→ Clause
→ Point
```

Prefer keeping a complete article together.

Split an article only when it exceeds the configured maximum.

### Guideline chunker

Priority:

```text
Heading
→ Subheading
→ Related paragraph group
```

### Template chunker

Keep related items together:

```text
Template title
+ Section name
+ Table headers
+ Required fields
+ Filling instructions
```

### Parent-child strategy

Use smaller child chunks for retrieval and larger parent blocks for context expansion.

Example:

```text
Child chunk
→ Khoản 2, Điều 8

Parent chunk
→ Full Điều 8
```

Initial configurable values:

```text
target_chunk_tokens = 700
maximum_chunk_tokens = 1200
overlap_tokens = 100
```

Structure boundaries take priority over token limits.

Required chunk fields:

```text
chunk_id
document_id
parent_chunk_id
content
chunk_index
token_count
metadata
```

---

## 5.9 Step 8 — Metadata construction

Required metadata:

```json
{
  "document_id": "doc_001",
  "document_name": "Nghị định 09/2019/NĐ-CP",
  "document_type": "legal_document",
  "domain": "common_reporting",
  "document_status": "active",
  "chunk_index": 12
}
```

Optional metadata:

```json
{
  "source": "Chính phủ",
  "document_number": "09/2019/NĐ-CP",
  "issued_date": "2019-01-24",
  "effective_date": "2019-03-12",
  "expiry_date": null,
  "chapter": "Chương II",
  "section": null,
  "article": "Điều 8",
  "clause": "Khoản 2",
  "point": null,
  "heading": null,
  "page_number": 6,
  "sheet_name": null,
  "parent_chunk_id": "doc_001_article_8",
  "file_path": "..."
}
```

Pydantic validation must run before embedding or indexing.

Missing required metadata stops ingestion.

---

## 5.10 Step 9 — Embedding generation

Embedding input should contain useful retrieval information:

```text
Domain: common_reporting
Document type: legal_document
Document: Nghị định 09/2019/NĐ-CP
Location: Điều 8, Khoản 2
Content:
...
```

Do not include:

* API keys
* Local absolute storage paths
* Internal error messages
* Unrelated operational metadata

Batch embedding requests.

Store embedding model version with the document ingestion record.

If the embedding model changes, documents must be reindexed.

---

## 5.11 Step 10 — Qdrant storage

For each chunk, store:

```text
point_id
dense_vector
chunk text
metadata payload
```

Required operations:

```text
create_collection
upsert_chunks
search
delete_by_document_id
count_by_document_id
collection_exists
```

Reingestion strategy:

```text
Mark document as processing
→ Delete previous points for document_id
→ Create new chunks and embeddings
→ Upsert new points
→ Verify inserted count
→ Mark document ready
```

If insertion or verification fails:

```text
Delete partially inserted points
→ Mark document failed
→ Save error stage and message
```

---

## 5.12 Step 11 — Readiness verification

Verify:

1. Qdrant collection exists.
2. Inserted chunk count matches expected chunk count.
3. Required metadata is present.
4. A smoke-test query can be executed.
5. PostgreSQL record contains embedding-model information.
6. No old duplicate points remain.

Success:

```text
document.processing_status = ready
```

Failure:

```text
document.processing_status = failed
document.failed_stage = ...
document.error_message = ...
```

---

# 6. Pipeline 2 — Agent uses the RAG Tool

## 6.1 Pipeline overview

```text
User Request
        │
        ▼
Agent Analyzes Task
        │
        ▼
Agent Decides Whether RAG Is Needed
        │
        ▼
Build RAG Query
        │
        ▼
Apply Metadata Filters
        │
        ▼
Dense or Hybrid Search
        │
        ▼
Retrieve Candidate Chunks
        │
        ▼
Rerank Candidates
        │
        ▼
Select Final Chunks
        │
        ▼
Expand Parent Context When Needed
        │
        ▼
Build Structured Context
        │
        ▼
Send Operational Data and RAG Context Separately to LLM
        │
        ▼
Generate Answer or Report
        │
        ▼
Validate Sources and Citations
        │
        ▼
Return Result to Agent
```

---

## 6.2 Agent decision rules

Call RAG for:

* Regulations
* Legal grounds
* Reporting requirements
* Report structure
* Report templates
* Business instructions
* Indicator definitions
* Source-based explanations
* Citation support

Do not call RAG merely for:

* Current operational totals
* Number of complaints
* Current population
* Current task status
* KPI calculations
* Overdue task lists
* Numerical validation

These require:

```text
Data Query Tool
KPI Tool
Rule Engine Tool
```

A report-generation request usually requires multiple tools:

```text
Data Query Tool
+
KPI Tool
+
Rule Engine Tool
+
RAG Search Tool
+
Report Export Tool
```

---

## 6.3 Query building

Input:

```text
original_user_request
agent_task
domain
requested_document_types
report_period when relevant
```

Output:

```json
{
  "search_query": "Nội dung bắt buộc và biểu mẫu báo cáo khiếu nại định kỳ tháng",
  "filters": {
    "domain": "complaints",
    "document_types": [
      "reporting_guideline",
      "report_template"
    ],
    "document_status": "active"
  }
}
```

Use deterministic query templates first.

Use the FPT-hosted LLM for query rewriting only when:

* The original request is ambiguous.
* Multiple regulations may apply.
* The Agent needs multiple specialized retrieval queries.

---

## 6.4 Metadata filtering

Supported filters:

```text
domain
document_type
document_status
document_id
source
document_number
effective_date
expiry_date
```

Default behavior:

```text
document_status = active
```

When date information is available, prefer documents effective for the requested reporting period.

Do not retrieve deleted documents.

---

## 6.5 Dense retrieval

First implementation:

```text
Query
→ Qwen3 query embedding
→ Qdrant similarity search
→ Top candidate chunks
```

Default:

```text
candidate_top_k = 20
```

All values must be configurable.

---

## 6.6 Hybrid retrieval enhancement

Later enhancement:

```text
Dense semantic search
+
Sparse or BM25 keyword search
        ↓
Rank fusion
        ↓
Candidate chunks
```

Hybrid search is useful for exact administrative identifiers such as:

```text
09/2019/NĐ-CP
Điều 8
Khoản 2
Mẫu số 03
QĐ-UBND
```

Dense retrieval must work before hybrid retrieval is introduced.

---

## 6.7 Reranking

Input:

```text
query
candidate chunks
```

Output:

```text
reranked chunks with scores
```

Default:

```text
candidate_top_k = 20
final_top_k = 5
```

Reranking may combine:

* Qwen3 reranker score
* Exact document-number match
* Domain match
* Document-type match
* Effective-date validity
* Document status

Do not rerank the entire Knowledge Base.

---

## 6.8 Context building

The context builder must:

1. Remove duplicate chunks.
2. Preserve document source metadata.
3. Expand parent blocks only when useful.
4. Sort related chunks logically.
5. Respect maximum context size.
6. Assign stable source labels.
7. Avoid including irrelevant chunks merely to fill context.

Example:

```text
[SOURCE_1]
Document ID: doc_001
Document: Nghị định 09/2019/NĐ-CP
Document number: 09/2019/NĐ-CP
Location: Điều 8, Khoản 2
Page: 6
Chunk ID: doc_001_chunk_12
Content:
...

[SOURCE_2]
Document ID: doc_015
Document: Hướng dẫn lập báo cáo khiếu nại
Location: Mục II
Page: 3
Chunk ID: doc_015_chunk_04
Content:
...
```

---

## 6.9 LLM request construction

Send separate sections:

```text
SYSTEM RULES
TASK
OPERATIONAL DATA
RAG CONTEXT
OUTPUT REQUIREMENTS
```

Example system requirements:

```text
You are an assistant supporting Vietnamese ward-level administrative reporting.

Official numbers may only come from OPERATIONAL_DATA.

Regulations, templates and instructions may only come from RAG_CONTEXT.

Do not invent numbers, document names, document numbers, articles, clauses or citations.

Every legal or procedural citation must reference one of the provided SOURCE identifiers.

When evidence is insufficient, explicitly state that the Knowledge Base does not contain enough information.

Use formal and concise Vietnamese administrative writing.
```

Recommended generation configuration:

```text
temperature = 0.1
max_tokens = configurable
timeout = configurable
```

Do not hardcode model parameters inside business services.

---

## 6.10 Structured LLM output

Where possible, request a validated structure:

```json
{
  "content": "...",
  "used_source_ids": [
    "SOURCE_1",
    "SOURCE_2"
  ],
  "warnings": []
}
```

For report generation, keep factual values separately identifiable so they can be validated against operational data.

Example:

```json
{
  "title": "...",
  "sections": [
    {
      "heading": "...",
      "content": "...",
      "used_source_ids": [
        "SOURCE_1"
      ]
    }
  ],
  "used_operational_fields": [
    "received_complaints",
    "resolved_complaints"
  ]
}
```

Validate structured output with Pydantic.

---

## 6.11 Citation validation

Every returned citation must map to a retrieved chunk.

Required citation fields:

```text
source_id
chunk_id
document_id
document_name
document_number
article or section
page_number
```

Validation:

```text
LLM used source ID
→ Source ID exists in context
→ Chunk exists in retrieval result
→ Document metadata matches
→ Citation accepted
```

When validation fails:

```text
Remove unsupported citation
OR
Regenerate once with explicit correction
OR
Mark output for human review
```

Never construct a legal citation from model memory alone.

---

## 6.12 RAG Search Tool output

The Agent-facing tool returns structured data:

```json
{
  "success": true,
  "query": "Các mục bắt buộc của báo cáo khiếu nại tháng",
  "context": "...",
  "sources": [
    {
      "source_id": "SOURCE_1",
      "chunk_id": "doc_001_chunk_12",
      "document_id": "doc_001",
      "document_name": "Hướng dẫn lập báo cáo khiếu nại",
      "document_number": null,
      "section": "Mục II",
      "article": null,
      "page_number": 3,
      "retrieval_score": 0.87,
      "reranker_score": 0.94
    }
  ],
  "warnings": []
}
```

The RAG Tool returns evidence to the Agent.

It does not calculate official operational statistics.

---

# 7. Storage responsibilities

```text
dataset/
→ Developer-maintained seed documents and evaluation data

storage/
→ Runtime original uploads and optional processed artifacts

PostgreSQL
→ Document lifecycle, metadata records and operational data

Qdrant
→ Searchable chunks, embeddings and retrieval payloads
```

Recommended runtime structure:

```text
backend/storage/knowledge_base/
├── originals/
├── processed/
└── failed/
```

Recommended seed structure:

```text
dataset/03_knowledge_base/
├── common_reporting_regulations/
├── population_reporting_guides/
├── complaint_reporting_guides/
├── task_reporting_guides/
├── report_templates/
└── local_guidelines/
```

Do not place runtime uploads into `dataset`.

---

# 8. Configuration

Suggested `.env.example` values:

```env
APP_ENV=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/ubnd_reports

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=ubnd_knowledge_base

EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
RERANKER_MODEL=Qwen/Qwen3-Reranker-0.6B

FPT_API_KEY=your_fpt_ai_factory_api_key_here
FPT_BASE_URL=copy_the_exact_endpoint_from_fpt_ai_factory
LLM_MODEL=Llama-3.3-70B-Instruct
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
LLM_TIMEOUT_SECONDS=120

PYTHONIOENCODING=utf-8
```

Do not commit the real `.env`.

---

# 9. Suggested module structure

```text
backend/app/
├── api/
│   └── routes/
│       ├── knowledge_base.py
│       └── rag_search.py
│
├── models/
│   └── knowledge_document.py
│
├── schemas/
│   ├── knowledge_document.py
│   └── rag.py
│
├── repositories/
│   └── knowledge_document_repository.py
│
├── services/
│   ├── knowledge_base_service.py
│   └── rag_service.py
│
├── llm/
│   ├── base.py
│   ├── fpt_client.py
│   └── factory.py
│
├── rag/
│   ├── types.py
│   │
│   ├── ingestion/
│   │   ├── pipeline.py
│   │   └── classifier.py
│   │
│   ├── parsers/
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── docling_parser.py
│   │   ├── pdf_parser.py
│   │   ├── docx_parser.py
│   │   ├── xlsx_parser.py
│   │   └── ocr_parser.py
│   │
│   ├── cleaning/
│   │   └── text_cleaner.py
│   │
│   ├── structure/
│   │   └── analyzer.py
│   │
│   ├── chunking/
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── legal.py
│   │   ├── guideline.py
│   │   └── template.py
│   │
│   ├── metadata/
│   │   └── builder.py
│   │
│   ├── embeddings/
│   │   └── service.py
│   │
│   ├── vectorstores/
│   │   ├── base.py
│   │   └── qdrant_store.py
│   │
│   ├── retrieval/
│   │   ├── pipeline.py
│   │   ├── query_builder.py
│   │   └── filter_builder.py
│   │
│   ├── reranking/
│   │   └── service.py
│   │
│   ├── context/
│   │   └── builder.py
│   │
│   ├── citations/
│   │   └── validator.py
│   │
│   └── prompts/
│       ├── query_rewrite.txt
│       └── report_generation.txt
│
└── agent/
    ├── tool_registry.py
    └── tools/
        └── rag_search_tool.py
```

Adapt this tree to the repository's existing conventions. Do not create duplicate `core`, `services`, `models` or database layers when equivalent folders already exist.

---

# 10. Implementation phases and acceptance criteria

## Phase 1 — Document processing

Implement:

```text
Shared RAG types
BaseParser
DoclingParser
PDFParser
DOCXParser
ParserFactory
TextCleaner
StructureAnalyzer
LegalDocumentChunker
GuidelineChunker
TemplateChunker
MetadataBuilder
Unit tests
```

Accepted when one PDF or DOCX can become validated chunks with preserved source metadata.

## Phase 2 — Ingestion

Implement:

```text
EmbeddingService
QdrantVectorStore
KnowledgeDocument model
KnowledgeDocument repository
IngestionPipeline
Seed script
Integration tests
```

Accepted when a document can be indexed, reindexed without duplicates and deleted by document ID.

## Phase 3 — Retrieval

Implement:

```text
QueryBuilder
FilterBuilder
Dense retrieval
RerankerService
ContextBuilder
Citation structures
RAGService
```

Accepted when test queries return relevant chunks with source metadata and filters.

## Phase 4 — Agent and FPT LLM integration

Implement:

```text
LLMClient interface
FPTLLMClient
RAGSearchTool
Tool registration
Agent RAG decision rules
CitationValidator
Report-generation prompt
Mocked tests
```

Accepted when the Agent can call RAG and the generated response only cites retrieved sources.

## Phase 5 — Enhancements

Implement later:

```text
OCR
XLSX template processing
Sparse/BM25 search
Hybrid rank fusion
Background jobs
Evaluation dashboard
Administrative Knowledge Base UI
```
