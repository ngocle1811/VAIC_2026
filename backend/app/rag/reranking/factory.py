"""Provider-neutral reranker composition with an honest unavailable fallback."""

from app.config import Settings
from app.rag.reranking.fake import FakeReranker
from app.rag.reranking.fpt import ConfiguredFPTReranker, RerankerTransport
from app.rag.reranking.service import RerankerService


def create_reranker_service(
    settings: Settings,
    *,
    transport: RerankerTransport | None = None,
    strict: bool = False,
) -> RerankerService:
    if settings.reranker_provider == "fake":
        return RerankerService(FakeReranker(), strict=strict)
    if settings.reranker_provider == "fpt" and transport is not None:
        return RerankerService(
            ConfiguredFPTReranker(
                transport,
                model_name=settings.reranker_model,
                timeout=settings.reranker_timeout_seconds,
                batch_size=settings.reranker_batch_size,
                max_retries=settings.reranker_max_retries,
            ),
            strict=strict,
        )
    return RerankerService(None, strict=strict)
