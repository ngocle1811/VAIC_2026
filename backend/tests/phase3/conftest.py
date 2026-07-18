import hashlib

import pytest

from app.rag.embeddings.service import EmbeddingService
from app.rag.index_models import VectorSearchResult
from app.rag.retrieval.corpus import InMemoryChunkCorpusSource
from app.rag.retrieval.models import SearchableChunk


class FakeEmbedding:
    model_name = "fake"

    def __init__(self) -> None:
        self.query_calls = 0

    def embed_documents(self, texts):
        return [self._vector(text) for text in texts]

    def embed_query(self, query):
        self.query_calls += 1
        return self._vector(query)

    @staticmethod
    def _vector(text):
        digest = hashlib.sha256(text.encode()).digest()
        return [float(digest[index] + 1) for index in range(4)]


class FakeVectorStore:
    def __init__(self, chunks: list[SearchableChunk]) -> None:
        self.chunks = chunks
        self.filters = None

    def search(self, query_vector, filters, top_k):
        self.filters = filters
        return [
            VectorSearchResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                content=chunk.content,
                score=1.0 / (index + 1),
                metadata={
                    **chunk.metadata,
                    "document_type": chunk.document_type,
                    "domain": chunk.domain,
                    "document_status": chunk.document_status,
                    "chunk_index": chunk.chunk_index,
                },
            )
            for index, chunk in enumerate(self.chunks[:top_k])
        ]


@pytest.fixture
def searchable_chunks() -> list[SearchableChunk]:
    return [
        SearchableChunk(
            chunk_id="c1",
            document_id="d1",
            document_name="Nghị định 09/2019/NĐ-CP",
            document_type="legal",
            domain="common",
            document_status="active",
            chunk_index=0,
            content="Điều 8 quy định chế độ báo cáo định kỳ.",
            metadata={
                "document_number": "09/2019/NĐ-CP",
                "article": "8",
                "page_numbers": [6],
                "heading_hierarchy": ["CHƯƠNG II", "Điều 8"],
            },
        ),
        SearchableChunk(
            chunk_id="c2",
            document_id="d2",
            document_name="Hướng dẫn dân cư",
            document_type="guideline",
            domain="population",
            document_status="active",
            chunk_index=0,
            content="Hướng dẫn thống kê dân cư và nhân khẩu.",
            metadata={"effective_date": "2025-01-01"},
        ),
        SearchableChunk(
            chunk_id="parent",
            document_id="d1",
            document_name="Nghị định 09/2019/NĐ-CP",
            document_type="legal",
            domain="common",
            document_status="active",
            chunk_index=1,
            content="Toàn văn Điều 8 gồm các khoản báo cáo.",
            metadata={"article": "8"},
        ),
    ]


@pytest.fixture
def corpus(searchable_chunks) -> InMemoryChunkCorpusSource:
    return InMemoryChunkCorpusSource(searchable_chunks)


@pytest.fixture
def fake_embedding() -> FakeEmbedding:
    return FakeEmbedding()


@pytest.fixture
def embedding_service(fake_embedding) -> EmbeddingService:
    return EmbeddingService(fake_embedding, normalize=False)
