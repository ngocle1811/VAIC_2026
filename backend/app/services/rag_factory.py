"""Runtime composition for Phase 3 retrieval without provider leakage."""

from app.config import Settings
from app.rag.embeddings.factory import create_embedding_service
from app.rag.reranking.factory import create_reranker_service
from app.rag.retrieval.dense_retriever import DenseRetriever
from app.rag.retrieval.lexical_retriever import BM25Retriever
from app.rag.retrieval.parent_expander import ParentContextExpander
from app.rag.retrieval.pipeline import RetrievalPipeline
from app.rag.vectorstores.factory import create_vector_store
from app.services.rag import RAGService


def create_rag_service(settings: Settings) -> RAGService:
    vector_store = create_vector_store(settings)
    dense = None
    if settings.rag_enable_dense_search:
        dense = DenseRetriever(create_embedding_service(settings), vector_store)
    lexical = (
        BM25Retriever(vector_store, k1=settings.bm25_k1, b=settings.bm25_b)
        if settings.rag_enable_lexical_search
        else None
    )
    pipeline = RetrievalPipeline(
        settings=settings,
        dense_retriever=dense,
        lexical_retriever=lexical,
        reranker_service=create_reranker_service(settings),
        parent_expander=ParentContextExpander(vector_store),
    )
    return RAGService(pipeline)
