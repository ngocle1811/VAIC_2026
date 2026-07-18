"""Provider-neutral validated models for Phase 2 indexing and search."""

import math
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from app.rag.models import DocumentChunk


class EmbeddedChunk(BaseModel):
    chunk: DocumentChunk
    vector: list[float] = Field(min_length=1)
    payload_metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, vector: list[float]) -> list[float]:
        if any(not math.isfinite(value) for value in vector):
            raise ValueError("embedding vector must contain only finite values")
        return vector


class VectorSearchFilters(BaseModel):
    domain: str | None = None
    document_type: str | None = None
    document_id: str | None = None
    document_status: str | None = "active"
    document_types: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    source: str | None = None
    document_number: str | None = None
    effective_on: date | None = None


class VectorSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    score: float
    metadata: dict[str, object] = Field(default_factory=dict)


class EmbeddingBatch(BaseModel):
    vectors: list[list[float]]
    dimension: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_dimensions(self) -> "EmbeddingBatch":
        if any(len(vector) != self.dimension for vector in self.vectors):
            raise ValueError("embedding vectors have inconsistent dimensions")
        return self
