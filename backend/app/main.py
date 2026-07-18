"""FastAPI application for Knowledge Base and operational-report workflows."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent import router as agent_router
from app.api.routes.knowledge_base import router as knowledge_base_router
from app.api.routes.operational_reports import router as operational_reports_router
from app.api.routes.rag_search import router as rag_search_router
from app.api.routes.reports import router as reports_router
from app.config import get_settings

app = FastAPI(title="UBND Report Backend", version="0.1.0")
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Accept", "Content-Type"],
)
app.include_router(knowledge_base_router)
app.include_router(rag_search_router)
app.include_router(operational_reports_router)
app.include_router(reports_router)
app.include_router(agent_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
