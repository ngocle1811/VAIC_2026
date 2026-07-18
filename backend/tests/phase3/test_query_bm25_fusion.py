from datetime import date

import pytest

from app.rag.models import DocumentDomain, DocumentType
from app.rag.retrieval.filter_builder import MetadataFilterBuilder
from app.rag.retrieval.fusion import reciprocal_rank_fusion
from app.rag.retrieval.lexical_retriever import BM25Retriever, tokenize_vietnamese
from app.rag.retrieval.models import (
    DenseSearchResult,
    LexicalSearchResult,
    RetrievalFilters,
    RetrievalRequest,
)
from app.rag.retrieval.query_builder import DeterministicQueryBuilder


def test_query_normalization_preserves_vietnamese_and_identifiers() -> None:
    builder = DeterministicQueryBuilder()
    query = "  Điều  8   Khoản 2 của 09/2019/NĐ-CP  "
    normalized, identifiers = builder.build(RetrievalRequest(query=query))
    assert normalized == "Điều 8 Khoản 2 của 09/2019/NĐ-CP"
    assert identifiers == ["Điều 8", "Khoản 2", "09/2019/NĐ-CP"]
    assert builder.build(RetrievalRequest(query=query)) == (normalized, identifiers)
    with pytest.raises(ValueError):
        builder.normalize("   ")


def test_filter_builder_defaults_and_explicit_constraints() -> None:
    filters = MetadataFilterBuilder().build(
        RetrievalRequest(
            query="test",
            domain=DocumentDomain.POPULATION,
            document_types=[DocumentType.LEGAL],
            document_ids=["d1"],
            effective_on=date(2026, 1, 1),
        )
    )
    assert filters.domain == "population"
    assert filters.document_types == ["legal"]
    assert filters.document_ids == ["d1"]
    assert filters.document_status == "active"
    assert "deleted" in filters.exclude_processing_statuses


def test_bm25_exact_identifier_filter_cache_and_invalidation(corpus) -> None:
    retriever = BM25Retriever(corpus)
    common = RetrievalFilters(domain="common")
    result = retriever.search("09/2019/NĐ-CP Điều 8", common, 5)
    assert result[0].chunk_id == "c1"
    assert retriever.build_count == 1
    retriever.search("báo cáo", common, 5)
    assert retriever.build_count == 1
    assert not retriever.search("dân cư", common, 5)
    retriever.invalidate()
    retriever.search("Điều", common, 5)
    assert retriever.build_count == 2
    assert tokenize_vietnamese("Điều 8 09/2019/NĐ-CP") == ["điều", "8", "09/2019/nđ-cp"]


def _result(model, chunk_id, score):
    return model(
        chunk_id=chunk_id,
        document_id="d",
        document_name="doc",
        document_type="legal",
        domain="common",
        document_status="active",
        content=chunk_id,
        retrieval_score=score,
        dense_score=score if model is DenseSearchResult else None,
        lexical_score=score if model is LexicalSearchResult else None,
    )


def test_rrf_merges_duplicates_weights_and_ties() -> None:
    fused = reciprocal_rank_fusion(
        [_result(DenseSearchResult, "c1", 0.9), _result(DenseSearchResult, "c2", 0.8)],
        [_result(LexicalSearchResult, "c2", 5), _result(LexicalSearchResult, "c3", 4)],
        rrf_k=10,
        dense_weight=1,
        lexical_weight=2,
    )
    assert fused[0].chunk_id == "c2"
    assert fused[0].dense_score == 0.8 and fused[0].lexical_score == 5
    assert len({item.chunk_id for item in fused}) == 3
    assert reciprocal_rank_fusion([_result(DenseSearchResult, "c1", 1)], [])[0].chunk_id == "c1"
