from fastapi.testclient import TestClient

from app.api.routes.rag_search import get_rag_service
from app.config import Settings
from app.main import app
from app.rag.evaluation.metrics import hit_rate, mean_reciprocal_rank, ndcg, precision, recall
from app.rag.reranking.fake import FakeReranker
from app.rag.reranking.service import RerankerService
from app.rag.retrieval.dense_retriever import DenseRetriever
from app.rag.retrieval.lexical_retriever import BM25Retriever
from app.rag.retrieval.models import RetrievalRequest
from app.rag.retrieval.parent_expander import ParentContextExpander
from app.rag.retrieval.pipeline import RetrievalPipeline
from app.services.rag import RAGService
from tests.phase3.conftest import FakeVectorStore


def _service(searchable_chunks, corpus, embedding_service, **settings_overrides):
    settings = Settings(
        _env_file=None,
        rag_enable_parent_expansion=False,
        rag_enable_reranker=False,
        rag_final_top_k=2,
        **settings_overrides,
    )
    vector = FakeVectorStore(searchable_chunks)
    pipeline = RetrievalPipeline(
        settings=settings,
        dense_retriever=DenseRetriever(embedding_service, vector),
        lexical_retriever=BM25Retriever(corpus),
        reranker_service=RerankerService(FakeReranker()),
        parent_expander=ParentContextExpander(corpus),
    )
    return RAGService(pipeline), vector


def test_dense_lexical_hybrid_and_reranked_pipeline(
    searchable_chunks, corpus, embedding_service, fake_embedding
) -> None:
    service, vector = _service(searchable_chunks, corpus, embedding_service)
    dense = service.search(RetrievalRequest(query="unmatched", enable_hybrid=False))
    assert dense.success and fake_embedding.query_calls == 1
    assert vector.filters.document_status == "active"
    hybrid = service.search(RetrievalRequest(query="Điều 8 báo cáo", enable_hybrid=True))
    assert hybrid.sources[0].dense_score is not None
    assert hybrid.sources[0].lexical_score is not None
    reranked = service.search(
        RetrievalRequest(query="dân cư", enable_hybrid=True, enable_reranker=True)
    )
    assert reranked.sources[0].reranker_score is not None
    assert "vector" not in reranked.model_dump_json()


def test_lexical_only_and_empty_knowledge_base(corpus) -> None:
    settings = Settings(
        _env_file=None,
        rag_enable_dense_search=False,
        rag_enable_reranker=False,
        rag_enable_parent_expansion=False,
    )
    pipeline = RetrievalPipeline(
        settings=settings,
        dense_retriever=None,
        lexical_retriever=BM25Retriever(corpus),
        reranker_service=None,
        parent_expander=None,
    )
    assert pipeline.retrieve(RetrievalRequest(query="dân cư")).success
    corpus.replace([])
    assert not pipeline.retrieve(RetrievalRequest(query="dân cư")).success


def test_rag_api_returns_evidence_only(searchable_chunks, corpus, embedding_service) -> None:
    service, _ = _service(searchable_chunks, corpus, embedding_service)
    app.dependency_overrides[get_rag_service] = lambda: service
    try:
        response = TestClient(app).post("/rag/search", json={"query": "Điều 8 báo cáo"})
        assert response.status_code == 200
        body = response.json()
        assert body["sources"] and "answer" not in body and "vector" not in response.text
        lexical = TestClient(app).post(
            "/rag/search",
            json={"query": "09/2019/NĐ-CP", "retrieval_mode": "lexical"},
        )
        assert lexical.status_code == 200
        assert lexical.json()["sources"][0]["lexical_score"] is not None
        assert TestClient(app).post("/rag/search", json={"query": " "}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_evaluation_metrics() -> None:
    retrieved = ["a", "x", "b"]
    expected = {"a", "b"}
    assert hit_rate(retrieved, expected, 2) == 1
    assert recall(retrieved, expected, 3) == 1
    assert precision(retrieved, expected, 2) == 0.5
    assert mean_reciprocal_rank(retrieved, expected) == 1
    assert 0 < ndcg(retrieved, expected, 3) <= 1
    assert recall(retrieved, set(), 3) == 0


def test_explicit_retrieval_modes(searchable_chunks, corpus, embedding_service) -> None:
    service, _ = _service(searchable_chunks, corpus, embedding_service)
    query = "09/2019/NĐ-CP"
    dense = service.search(RetrievalRequest(query=query, retrieval_mode="dense"))
    lexical = service.search(RetrievalRequest(query=query, retrieval_mode="lexical"))
    hybrid = service.search(RetrievalRequest(query=query, retrieval_mode="hybrid"))
    assert dense.sources and dense.sources[0].dense_score is not None
    assert lexical.sources and lexical.sources[0].lexical_score is not None
    assert hybrid.sources and hybrid.sources[0].fused_score is not None
