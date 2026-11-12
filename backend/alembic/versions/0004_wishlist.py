"""Separa deseados del inventario y conserva las marcas existentes."""

import sqlalchemy as sa

from alembic import op

revision = "0004_wishlist"
down_revision = "0003_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wishlist_items",
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "paint_id", sa.Uuid(), sa.ForeignKey("paints.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        "INSERT INTO wishlist_items (user_id, paint_id, created_at) SELECT user_id, paint_id, created_at FROM user_paints WHERE status = 'wishlist'"
    )
    op.execute("DELETE FROM user_paints WHERE status = 'wishlist'")
    op.add_column(
        "user_paints",
        sa.Column("running_low", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE user_paints SET running_low = (status = 'running_low')")
    op.drop_index("ix_user_paints_user_id_status", table_name="user_paints")
    op.drop_constraint(op.f("ck_user_paints_inventory_status"), "user_paints", type_="check")
    op.drop_column("user_paints", "status")
    op.create_index("ix_user_paints_user_id_running_low", "user_paints", ["user_id", "running_low"])


def downgrade() -> None:
    # El esquema anterior no puede representar posesión y deseo a la vez;
    # se conserva la posesión cuando ambas coinciden.
    op.add_column(
        "user_paints", sa.Column("status", sa.String(32), nullable=False, server_default="owned")
    )
    op.execute("UPDATE user_paints SET status = 'running_low' WHERE running_low")
    op.execute(
        "INSERT INTO user_paints (user_id, paint_id, status, quantity, created_at) SELECT user_id, paint_id, 'wishlist', 0, created_at FROM wishlist_items ON CONFLICT (user_id, paint_id) DO NOTHING"
    )
    op.drop_index("ix_user_paints_user_id_running_low", table_name="user_paints")
    op.drop_column("user_paints", "running_low")
    op.create_check_constraint(
        "inventory_status", "user_paints", "status IN ('owned', 'running_low', 'wishlist')"
    )
    op.create_index("ix_user_paints_user_id_status", "user_paints", ["user_id", "status"])
    op.drop_table("wishlist_items")
