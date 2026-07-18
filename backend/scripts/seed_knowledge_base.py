"""Manually ingest explicitly mapped PDF/DOCX seed documents."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.database import create_session_factory
from app.rag.models import DocumentDomain, DocumentType
from app.schemas.knowledge_document import IngestionOutcome, IngestionRequest
from app.services.factory import create_knowledge_base_service


@dataclass(slots=True)
class SeedSummary:
    files_found: int = 0
    indexed: int = 0
    reindexed: int = 0
    skipped: int = 0
    failed: int = 0
    total_chunks: int = 0


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Seed mapping must be a JSON object")
    return data


def map_document(
    path: Path, root: Path, mapping: dict[str, dict[str, str]]
) -> tuple[DocumentDomain, DocumentType] | None:
    relative = path.relative_to(root).as_posix()
    matches = [
        (prefix, values) for prefix, values in mapping.items() if relative.startswith(prefix)
    ]
    if not matches:
        return None
    _, values = max(matches, key=lambda item: len(item[0]))
    return DocumentDomain(values["domain"]), DocumentType(values["document_type"])


def discover(seed_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in seed_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".pdf", ".docx"}
    )


def run_seed(
    settings: Settings,
    mapping: dict[str, dict[str, str]],
    *,
    dry_run: bool = False,
) -> SeedSummary:
    if settings.knowledge_base_seed_dir is None:
        raise ValueError("KNOWLEDGE_BASE_SEED_DIR is required")
    seed_dir = settings.knowledge_base_seed_dir.resolve()
    files = discover(seed_dir)
    summary = SeedSummary(files_found=len(files))
    if dry_run:
        for path in files:
            print(f"DRY-RUN {path}: {map_document(path, seed_dir, mapping)}")
        return summary
    session_factory = create_session_factory(settings.database_url)
    with session_factory() as session:
        service = create_knowledge_base_service(session, settings)
        for path in files:
            classification = map_document(path, seed_dir, mapping)
            if classification is None:
                summary.skipped += 1
                continue
            domain, document_type = classification
            try:
                result = service.upload_and_ingest(
                    IngestionRequest(
                        source_path=path,
                        document_name=path.name,
                        document_type=document_type,
                        domain=domain,
                    )
                )
                if result.outcome == IngestionOutcome.INDEXED:
                    summary.indexed += 1
                elif result.outcome == IngestionOutcome.REINDEXED:
                    summary.reindexed += 1
                else:
                    summary.skipped += 1
                summary.total_chunks += result.chunk_count
            except Exception as exc:
                summary.failed += 1
                print(f"FAILED {path.name}: {type(exc).__name__}: {exc}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-dir", type=Path, help="Override KNOWLEDGE_BASE_SEED_DIR")
    parser.add_argument("--mapping", type=Path, help="Explicit JSON prefix mapping")
    parser.add_argument("--dry-run", action="store_true", help="Discover and map without ingestion")
    args = parser.parse_args()
    settings = Settings()
    if args.seed_dir:
        settings.knowledge_base_seed_dir = args.seed_dir
    mapping_path = args.mapping or settings.knowledge_base_seed_mapping
    if mapping_path is None:
        parser.error("--mapping or KNOWLEDGE_BASE_SEED_MAPPING is required")
    summary = run_seed(settings, load_mapping(mapping_path), dry_run=args.dry_run)
    print(
        "Files found={files_found} Indexed={indexed} Reindexed={reindexed} "
        "Skipped={skipped} Failed={failed} Total chunks={total_chunks}".format(**vars(summary))
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
