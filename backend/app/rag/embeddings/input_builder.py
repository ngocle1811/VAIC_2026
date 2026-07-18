"""Deterministic semantic text construction for document chunk embeddings."""

from app.rag.models import DocumentChunk


def build_embedding_input(chunk: DocumentChunk) -> str:
    """Include retrieval-relevant labels without local or operational metadata."""
    lines = [
        f"Domain: {chunk.domain.value}",
        f"Document type: {chunk.document_type.value}",
        f"Document: {chunk.document_name}",
    ]
    locations: list[str] = []
    if chunk.metadata.heading_hierarchy:
        locations.extend(chunk.metadata.heading_hierarchy)
    for label, value in (
        ("Article", chunk.metadata.article),
        ("Clause", chunk.metadata.clause),
        ("Point", chunk.metadata.point),
        ("Table", chunk.metadata.table_name),
    ):
        if value and value not in locations:
            locations.append(f"{label}: {value}")
    if locations:
        lines.append(f"Location: {', '.join(locations)}")
    lines.extend(("Content:", chunk.content))
    return "\n".join(lines)
