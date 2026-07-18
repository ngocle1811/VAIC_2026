"""Single deterministic orchestration pipeline for complete Phase 3 retrieval."""

from app.config import Settings
from app.rag.context.builder import ContextBuilder
from app.rag.reranking.service import RerankerService
from app.rag.retrieval.dense_retriever import DenseRetriever
from app.rag.retrieval.filter_builder import MetadataFilterBuilder
from app.rag.retrieval.fusion import reciprocal_rank_fusion
from app.rag.retrieval.lexical_retriever import BM25Retriever
from app.rag.retrieval.models import (
    FusedSearchResult,
    RAGSearchResult,
    RetrievalCandidate,
    RetrievalQueryPlan,
    RetrievalRequest,
)
from app.rag.retrieval.parent_expander import ParentContextExpander
from app.rag.retrieval.query_builder import DeterministicQueryBuilder


class RetrievalPipeline:
    def __init__(
        self,
        *,
        settings: Settings,
        dense_retriever: DenseRetriever | None,
        lexical_retriever: BM25Retriever | None,
        reranker_service: RerankerService | None,
        parent_expander: ParentContextExpander | None,
    ) -> None:
        self.settings = settings
        self.query_builder = DeterministicQueryBuilder()
        self.filter_builder = MetadataFilterBuilder(settings.rag_default_document_status)
        self.dense_retriever = dense_retriever
        self.lexical_retriever = lexical_retriever
        self.reranker_service = reranker_service
        self.parent_expander = parent_expander

    def retrieve(self, request: RetrievalRequest) -> RAGSearchResult:
        normalized, identifiers = self.query_builder.build(request)
        filters = self.filter_builder.build(request)
        plan = self._plan(request, normalized, identifiers, filters)
        warnings: list[str] = []
        dense = (
            self.dense_retriever.search(normalized, filters, plan.candidate_top_k)
            if plan.use_dense and self.dense_retriever
            else []
        )
        lexical = (
            self.lexical_retriever.search(normalized, filters, plan.candidate_top_k)
            if plan.use_lexical and self.lexical_retriever
            else []
        )
        candidates = self._combine(dense, lexical, plan)
        if plan.use_reranker:
            if self.reranker_service:
                candidates, rerank_warnings = self.reranker_service.rerank(
                    normalized, candidates, plan.final_top_k
                )
                warnings.extend(rerank_warnings)
            else:
                warnings.append("Reranker unavailable; retrieval ordering preserved.")
                candidates = candidates[: plan.final_top_k]
        else:
            candidates = candidates[: plan.final_top_k]
        if plan.expand_parent_context and self.parent_expander:
            candidates, expansion_warnings = self.parent_expander.expand(
                candidates, self.settings.rag_max_context_tokens
            )
            if request.debug:
                warnings.extend(expansion_warnings)
        built = ContextBuilder(self.settings.rag_max_context_tokens).build(candidates)
        warnings.extend(built.warnings)
        debug = None
        if request.debug:
            debug = {
                "plan": plan.model_dump(mode="json"),
                "dense_candidates": len(dense),
                "lexical_candidates": len(lexical),
                "final_sources": len(built.sources),
            }
        return RAGSearchResult(
            success=bool(built.sources),
            original_query=request.query,
            normalized_query=normalized,
            context=built.text,
            sources=built.sources,
            warnings=list(dict.fromkeys(warnings)),
            retrieval_debug=debug,
        )

    def _plan(self, request, normalized, identifiers, filters) -> RetrievalQueryPlan:
        requested_mode = request.retrieval_mode
        use_dense = (
            requested_mode != "lexical"
            and self.settings.rag_enable_dense_search
            and self.dense_retriever is not None
        )
        use_lexical = (
            requested_mode != "dense"
            and self.settings.rag_enable_lexical_search
            and self.lexical_retriever is not None
        )
        use_hybrid = (
            (
                requested_mode == "hybrid"
                or (
                    requested_mode == "auto"
                    and (
                        request.enable_hybrid
                        if request.enable_hybrid is not None
                        else self.settings.rag_enable_hybrid_search
                    )
                )
            )
            and use_dense
            and use_lexical
        )
        if requested_mode == "dense" and not use_dense:
            raise ValueError("Dense retrieval is unavailable")
        if requested_mode == "lexical" and not use_lexical:
            raise ValueError("Lexical retrieval is unavailable")
        if requested_mode == "hybrid" and not use_hybrid:
            raise ValueError("Hybrid retrieval requires dense and lexical retrievers")
        return RetrievalQueryPlan(
            original_query=request.query,
            normalized_query=normalized,
            exact_identifiers=identifiers,
            filters=filters,
            candidate_top_k=request.candidate_top_k or self.settings.rag_candidate_top_k,
            final_top_k=request.final_top_k or self.settings.rag_final_top_k,
            use_dense=use_dense,
            use_lexical=use_lexical,
            use_hybrid=use_hybrid,
            use_reranker=(
                request.enable_reranker
                if request.enable_reranker is not None
                else self.settings.rag_enable_reranker
            ),
            expand_parent_context=(
                request.expand_parent_context
                if request.expand_parent_context is not None
                else self.settings.rag_enable_parent_expansion
            ),
        )

    def _combine(self, dense, lexical, plan) -> list[RetrievalCandidate]:
        if plan.use_hybrid:
            return reciprocal_rank_fusion(
                dense,
                lexical,
                rrf_k=self.settings.rag_rrf_k,
                dense_weight=self.settings.rag_dense_weight,
                lexical_weight=self.settings.rag_lexical_weight,
            )[: plan.candidate_top_k]
        selected = dense or lexical
        return [FusedSearchResult(**candidate.model_dump()) for candidate in selected]
