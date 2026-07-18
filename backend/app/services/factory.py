"""Runtime service graph composition at dependency boundaries."""

from sqlalchemy.orm import Session

from app.config import Settings
from app.rag.embeddings.factory import create_embedding_service
from app.rag.ingestion.pipeline import KnowledgeBaseIngestionPipeline
from app.rag.parsers.factory import ParserFactory
from app.rag.pipeline import RAGPhase1Pipeline
from app.rag.vectorstores.factory import create_vector_store
from app.repositories.knowledge_document_repository import KnowledgeDocumentRepository
from app.services.knowledge_base import KnowledgeBaseService
from app.services.knowledge_base_storage import KnowledgeBaseStorage


def create_knowledge_base_service(session: Session, settings: Settings) -> KnowledgeBaseService:
    repository = KnowledgeDocumentRepository(session)
    storage = KnowledgeBaseStorage(
        settings.knowledge_base_original_dir, settings.max_document_size_mb
    )
    embedding_service = create_embedding_service(settings)
    vector_store = create_vector_store(settings)
    ingestion = KnowledgeBaseIngestionPipeline(
        repository=repository,
        storage=storage,
        phase1_pipeline=RAGPhase1Pipeline(parser_factory=ParserFactory(prefer_docling=True)),
        embedding_service=embedding_service,
        vector_store=vector_store,
        embedding_provider_name=settings.embedding_provider,
    )
    return KnowledgeBaseService(repository, ingestion, vector_store)
