"""Add operational source-of-truth and generated-report review tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_02"
down_revision: str | None = "20260718_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operational_reports",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("classification", sa.String(64), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False),
        sa.Column("period_kind", sa.String(32), nullable=False),
        sa.Column("period_start", sa.String(10), nullable=False),
        sa.Column("period_end", sa.String(10), nullable=False),
        sa.Column("period_label", sa.String(255)),
        sa.Column("organization_id", sa.String(128), nullable=False),
        sa.Column("organization_name", sa.String(512), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("records", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_operational_reports_domain", "operational_reports", ["domain"])
    op.create_index(
        "ix_operational_reports_period", "operational_reports", ["period_start", "period_end"]
    )
    op.create_index("ix_operational_reports_checksum", "operational_reports", ["checksum_sha256"])
    op.create_table(
        "generated_reports",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "operational_report_id",
            sa.String(64),
            sa.ForeignKey("operational_reports.id"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("template_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("validation_result", sa.JSON(), nullable=False),
        sa.Column("reviewer_comment", sa.Text()),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_generated_reports_status", "generated_reports", ["status"])


def downgrade() -> None:
    op.drop_table("generated_reports")
    op.drop_table("operational_reports")
