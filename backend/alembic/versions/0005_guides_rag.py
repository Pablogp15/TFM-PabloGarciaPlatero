"""Contexto reproducible, cola y seguimiento de guías RAG."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0005_guides_rag"
down_revision = "0004_wishlist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("guides", sa.Column("target_image_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_guides_target_image_id_project_images",
        "guides",
        "project_images",
        ["target_image_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "guides", sa.Column("stage", sa.String(32), nullable=False, server_default="queued")
    )
    for name in ("context", "analysis", "metrics"):
        op.add_column(
            "guides",
            sa.Column(name, JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        )
    op.add_column(
        "guides",
        sa.Column("limitations", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("guides", sa.Column("error_message", sa.String(500)))
    for name in ("started_at", "finished_at"):
        op.add_column("guides", sa.Column(name, sa.DateTime(timezone=True)))
    op.add_column(
        "guides",
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    for name in ("objective", "continue_when"):
        op.add_column("guide_steps", sa.Column(name, sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "guide_steps", sa.Column("zone", sa.String(120), nullable=False, server_default="")
    )
    op.add_column(
        "guide_steps",
        sa.Column("source_ids", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "guide_steps",
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("guide_steps", sa.Column("progress_note", sa.Text()))
    op.add_column(
        "guide_steps",
        sa.Column("minutes_spent", sa.SmallInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    for name in (
        "minutes_spent",
        "progress_note",
        "completed",
        "source_ids",
        "zone",
        "continue_when",
        "objective",
    ):
        op.drop_column("guide_steps", name)
    for name in (
        "cancel_requested",
        "finished_at",
        "started_at",
        "error_message",
        "limitations",
        "metrics",
        "analysis",
        "context",
        "stage",
        "target_image_id",
    ):
        op.drop_column("guides", name)
