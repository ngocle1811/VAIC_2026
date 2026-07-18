"""Create Knowledge Base document lifecycle table."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("stored_filename", sa.String(512), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("document_name", sa.String(512), nullable=False),
        sa.Column("document_number", sa.String(255)),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("domain", sa.String(64), nullable=False),
        sa.Column("document_status", sa.String(32), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False),
        sa.Column("embedding_provider", sa.String(64)),
        sa.Column("embedding_model", sa.String(255)),
        sa.Column("embedding_dimension", sa.Integer()),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processing_started_at", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("failed_stage", sa.String(64)),
        sa.Column("error_message", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for name, column in (
        ("checksum", "checksum_sha256"),
        ("processing_status", "processing_status"),
        ("domain", "domain"),
        ("document_type", "document_type"),
    ):
        op.create_index(f"ix_knowledge_documents_{name}", "knowledge_documents", [column])


def downgrade() -> None:
    op.drop_table("knowledge_documents")
