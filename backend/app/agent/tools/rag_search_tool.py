"""Agent-facing wrapper around RAGService; it returns evidence only."""

from app.agent.models import AgentExecutionContext, ToolResult
from app.rag.retrieval.models import RetrievalRequest
from app.services.rag import RAGService


class RAGSearchTool:
    name = "rag_search"
    description = "Retrieve legal, procedural, and template evidence from the Knowledge Base."
    input_model = RetrievalRequest

    def __init__(self, service: RAGService) -> None:
        self.service = service

    def execute(self, arguments: RetrievalRequest, context: AgentExecutionContext) -> ToolResult:
        result = self.service.search(arguments)
        return ToolResult(
            success=result.success,
            data={
                "context": result.context,
                "sources": [source.model_dump(mode="json") for source in result.sources],
                "warnings": result.warnings,
            },
            source_ids=[source.source_id for source in result.sources],
        )
