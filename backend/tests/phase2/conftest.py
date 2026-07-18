import hashlib
from pathlib import Path

import pytest
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.rag.embeddings.service import EmbeddingService
from app.rag.vectorstores.qdrant import QdrantVectorStore


class FakeEmbeddingProvider:
    model_name = "Vietnamese_Embedding"

    def __init__(self, dimension: int = 4) -> None:
        self.dimension = dimension
        self.document_calls = 0
        self.query_calls = 0

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [float(digest[index] + 1) for index in range(self.dimension)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls += 1
        return [self._vector(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        self.query_calls += 1
        return self._vector(query)


@pytest.fixture
def db_session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def fake_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def embedding_service(fake_provider) -> EmbeddingService:
    return EmbeddingService(fake_provider, batch_size=2, normalize=False)


@pytest.fixture
def vector_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        QdrantClient(":memory:"), collection_name="test_kb", upsert_batch_size=2
    )
