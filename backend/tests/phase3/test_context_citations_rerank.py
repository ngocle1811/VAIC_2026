import pytest

from app.rag.citations.validator import CitationValidationError, CitationValidator
from app.rag.context.builder import ContextBuilder
from app.rag.reranking.factory import create_reranker_service
from app.rag.reranking.fake import FakeReranker
from app.rag.reranking.fpt import (
    ConfiguredFPTReranker,
    RerankerError,
    RerankerTransportError,
)
from app.rag.reranking.service import RerankerService
from app.rag.retrieval.models import CitationReference, RetrievalCandidate
from app.rag.retrieval.parent_expander import ParentContextExpander


def _candidate(chunk, score=1.0, parent=None):
    metadata = dict(chunk.metadata)
    if parent:
        metadata["parent_chunk_id"] = parent
    return RetrievalCandidate(
        **chunk.model_dump(exclude={"metadata"}), metadata=metadata, retrieval_score=score
    )


def test_fake_reranker_changes_order_and_enforces_top_k(searchable_chunks) -> None:
    candidates = [_candidate(searchable_chunks[1]), _candidate(searchable_chunks[0])]
    result = FakeReranker().rerank("Điều 8 báo cáo", candidates, 1)
    assert [item.chunk_id for item in result] == ["c1"]
    assert result[0].reranker_score is not None


class Transport:
    def __init__(self, response):
        self.response = response

    def rerank(self, **kwargs):
        return self.response


@pytest.mark.parametrize(
    "response",
    [[], [{"index": 0}], [{"index": 0, "score": float("nan")}]],
)
def test_configured_reranker_rejects_malformed_response(searchable_chunks, response) -> None:
    reranker = ConfiguredFPTReranker(Transport(response), model_name="configured")
    with pytest.raises(RerankerError):
        reranker.rerank("query", [_candidate(searchable_chunks[0])], 1)


def test_configured_reranker_retries_only_retryable_failures(searchable_chunks) -> None:
    class FlakyTransport:
        calls = 0

        def rerank(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RerankerTransportError("temporary", retryable=True)
            return [{"index": 0, "score": 0.75}]

    transport = FlakyTransport()
    reranker = ConfiguredFPTReranker(
        transport, model_name="configured", max_retries=1, sleep=lambda _: None
    )
    result = reranker.rerank("query", [_candidate(searchable_chunks[0])], 1)
    assert transport.calls == 2
    assert result[0].reranker_score == 0.75

    class PermanentFailure:
        def rerank(self, **kwargs):
            raise RerankerTransportError("invalid request", retryable=False)

    with pytest.raises(RerankerTransportError, match="invalid request"):
        ConfiguredFPTReranker(
            PermanentFailure(), model_name="configured", max_retries=3, sleep=lambda _: None
        ).rerank("query", [_candidate(searchable_chunks[0])], 1)


def test_reranker_failure_fallback_and_strict_mode(searchable_chunks) -> None:
    candidate = _candidate(searchable_chunks[0])

    class Failure:
        model_name = "failure"

        def rerank(self, query, candidates, top_k):
            raise RuntimeError("failure")

    fallback, warnings = RerankerService(Failure()).rerank("q", [candidate], 1)
    assert fallback[0].chunk_id == "c1" and warnings
    with pytest.raises(RuntimeError):
        RerankerService(Failure(), strict=True).rerank("q", [candidate], 1)


def test_reranker_factory_uses_fake_only_when_explicit(searchable_chunks) -> None:
    from app.config import Settings

    candidate = _candidate(searchable_chunks[0])
    unavailable = create_reranker_service(Settings(_env_file=None, reranker_provider="fpt"))
    _, warnings = unavailable.rerank("query", [candidate], 1)
    assert warnings
    fake = create_reranker_service(Settings(_env_file=None, reranker_provider="fake"))
    result, warnings = fake.rerank("query", [candidate], 1)
    assert result[0].reranker_score is not None and not warnings


def test_parent_expansion_found_missing_duplicate_and_budget(corpus, searchable_chunks) -> None:
    expander = ParentContextExpander(corpus)
    expanded, warnings = expander.expand([_candidate(searchable_chunks[0], parent="parent")], 1000)
    assert [item.chunk_id for item in expanded] == ["c1", "parent"]
    missing, warnings = expander.expand([_candidate(searchable_chunks[0], parent="missing")], 1000)
    assert [item.chunk_id for item in missing] == ["c1"] and warnings
    budget, warnings = expander.expand([_candidate(searchable_chunks[0], parent="parent")], 1)
    assert [item.chunk_id for item in budget] == ["c1"] and warnings


def test_context_stable_sources_budget_dedup_and_citations(searchable_chunks) -> None:
    candidates = [_candidate(searchable_chunks[0]), _candidate(searchable_chunks[0])]
    built = ContextBuilder(max_tokens=1000).build(candidates)
    assert len(built.sources) == 1
    assert built.sources[0].source_id == "SOURCE_1"
    assert "CHƯƠNG II" in built.text and "Điều 8" in built.text
    validator = CitationValidator()
    valid = validator.validate(
        [CitationReference(source_id="SOURCE_1", chunk_id="c1", document_id="d1")], built
    )
    assert valid.valid
    invalid = validator.validate(
        [CitationReference(source_id="UNKNOWN"), CitationReference(source_id="UNKNOWN")], built
    )
    assert not invalid.valid and len(invalid.rejected) == 1
    with pytest.raises(CitationValidationError):
        validator.validate([CitationReference(source_id="UNKNOWN")], built, strict=True)
    truncated = ContextBuilder(max_tokens=1).build(candidates)
    assert truncated.truncated and truncated.warnings
