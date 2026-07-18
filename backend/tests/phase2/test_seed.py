from pathlib import Path

from app.config import Settings
from app.models.knowledge_document import ProcessingStatus
from app.schemas.knowledge_document import IngestionOutcome, IngestionResult
from scripts import seed_knowledge_base


def test_seed_discovery_and_explicit_mapping(tmp_path: Path) -> None:
    population = tmp_path / "population"
    population.mkdir()
    pdf = population / "law.pdf"
    pdf.write_bytes(b"pdf")
    (population / "ignored.txt").write_text("ignored")
    mapping = {"population/": {"domain": "population", "document_type": "legal"}}
    assert seed_knowledge_base.discover(tmp_path) == [pdf]
    classification = seed_knowledge_base.map_document(pdf, tmp_path, mapping)
    assert classification is not None
    assert tuple(item.value for item in classification) == ("population", "legal")


class _SessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, *args):
        return None


class _Factory:
    def __call__(self):
        return _SessionContext()


class _SeedService:
    def upload_and_ingest(self, request):
        if request.source_path.name.startswith("bad"):
            raise RuntimeError("failure")
        return IngestionResult(
            document_id=request.source_path.name,
            processing_status=ProcessingStatus.READY,
            outcome=IngestionOutcome.INDEXED,
            chunk_count=2,
            embedding_model="Vietnamese_Embedding",
            embedding_dimension=4,
        )


def test_seed_continues_after_failure(monkeypatch, tmp_path: Path) -> None:
    for name in ("good.pdf", "bad.pdf", "unmapped.pdf"):
        (tmp_path / name).write_bytes(b"pdf")
    mapping = {
        "good.pdf": {"domain": "common", "document_type": "legal"},
        "bad.pdf": {"domain": "common", "document_type": "legal"},
    }
    monkeypatch.setattr(seed_knowledge_base, "create_session_factory", lambda url: _Factory())
    monkeypatch.setattr(
        seed_knowledge_base,
        "create_knowledge_base_service",
        lambda session, settings: _SeedService(),
    )
    summary = seed_knowledge_base.run_seed(
        Settings(
            _env_file=None,
            knowledge_base_seed_dir=tmp_path,
            database_url="sqlite://",
        ),
        mapping,
    )
    assert summary.files_found == 3
    assert summary.indexed == 1
    assert summary.failed == 1
    assert summary.skipped == 1
    assert summary.total_chunks == 2
