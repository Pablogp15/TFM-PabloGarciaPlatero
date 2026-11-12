"""Tablas de identidad, catálogo, inventario y proyectos."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0002_core'
down_revision: str | None = '0001_extensions'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paints",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('brand', sa.String(length=80), nullable=False),
        sa.Column('range_name', sa.String(length=80), nullable=False, server_default=sa.text("''")),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('code', sa.String(length=40), nullable=True),
        sa.Column('hex', sa.String(length=7), nullable=False),
        sa.Column('paint_type', sa.Enum('base', 'layer', 'wash', 'contrast', 'metallic', 'technical', 'ink', 'pigment', name='paint_type', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='base'),
        sa.Column('finish', sa.Enum('matte', 'satin', 'gloss', name='finish', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='matte'),
        sa.Column('lab_l', sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column('lab_a', sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column('lab_b', sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("paints.paint_type IN ('base', 'layer', 'wash', 'contrast', 'metallic', 'technical', 'ink', 'pigment')", name='paint_type'),
        sa.CheckConstraint("paints.finish IN ('matte', 'satin', 'gloss')", name='finish'),
        sa.CheckConstraint("hex ~ '^#[0-9A-Fa-f]{6}$'", name='hex_format'),
        sa.PrimaryKeyConstraint('id', name='pk_paints'),
        sa.UniqueConstraint('brand', 'range_name', 'name', name='uq_paints_brand_range_name'),
    )
    op.create_index('ix_paints_brand', 'paints', ['brand'])
    op.create_index('ix_paints_name', 'paints', ['name'])
    op.create_table(
        "users",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=80), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
    )
    op.create_index('uq_users_email_lower', 'users', [sa.text('lower(email)')], unique=True)
    op.create_table(
        "projects",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=120), nullable=True),
        sa.Column('scale_mm', sa.SmallInteger(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'generating', 'ready', 'painting', 'completed', 'archived', name='project_status', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("projects.status IN ('draft', 'generating', 'ready', 'painting', 'completed', 'archived')", name='project_status'),
        sa.CheckConstraint('scale_mm IS NULL OR scale_mm > 0', name='scale_positive'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_projects_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_projects'),
    )
    op.create_index('ix_projects_user_id_status', 'projects', ['user_id', 'status'])
    op.create_table(
        "refresh_tokens",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_refresh_tokens_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_refresh_tokens'),
        sa.UniqueConstraint('token_hash', name='uq_refresh_tokens_token_hash'),
    )
    op.create_index('ix_refresh_tokens_user_id_active', 'refresh_tokens', ['user_id'], postgresql_where=sa.text('revoked_at IS NULL'))
    op.create_table(
        "user_paints",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('paint_id', sa.Uuid(), nullable=False),
        sa.Column('quantity', sa.SmallInteger(), nullable=False, server_default=sa.text('1')),
        sa.Column('status', sa.Enum('owned', 'running_low', 'wishlist', name='inventory_status', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='owned'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("user_paints.status IN ('owned', 'running_low', 'wishlist')", name='inventory_status'),
        sa.CheckConstraint('quantity >= 0', name='quantity_non_negative'),
        sa.ForeignKeyConstraint(['paint_id'], ['paints.id'], name='fk_user_paints_paint_id_paints', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_paints_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_user_paints'),
        sa.UniqueConstraint('user_id', 'paint_id', name='uq_user_paints_user_paint'),
    )
    op.create_index('ix_user_paints_user_id_status', 'user_paints', ['user_id', 'status'])
    op.create_table(
        "project_images",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.Enum('source', 'generated', 'progress', name='image_kind', native_enum=False, create_constraint=False, length=32), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=80), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("project_images.kind IN ('source', 'generated', 'progress')", name='image_kind'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_project_images_project_id_projects', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_project_images'),
        sa.UniqueConstraint('storage_key', name='uq_project_images_storage_key'),
        sa.UniqueConstraint('project_id', 'checksum', name='uq_project_images_project_checksum'),
    )
    op.create_index('ix_project_images_project_id_kind', 'project_images', ['project_id', 'kind'])
    op.create_table(
        "project_scheme_colors",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.SmallInteger(), nullable=False),
        sa.Column('role', sa.Enum('primary', 'secondary', 'accent', 'skin', 'metal', 'wash', 'highlight', 'base_rim', 'other', name='scheme_role', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='other'),
        sa.Column('paint_id', sa.Uuid(), nullable=True),
        sa.Column('hex_override', sa.String(length=7), nullable=True),
        sa.Column('notes', sa.String(length=255), nullable=True),
        sa.CheckConstraint("project_scheme_colors.role IN ('primary', 'secondary', 'accent', 'skin', 'metal', 'wash', 'highlight', 'base_rim', 'other')", name='scheme_role'),
        sa.CheckConstraint("hex_override IS NULL OR hex_override ~ '^#[0-9A-Fa-f]{6}$'", name='hex_override_format'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_project_scheme_colors_project_id_projects', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['paint_id'], ['paints.id'], name='fk_project_scheme_colors_paint_id_paints', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_project_scheme_colors'),
        sa.UniqueConstraint('project_id', 'position', name='uq_project_scheme_colors_project_position'),
    )


def downgrade() -> None:
    op.drop_table("project_scheme_colors")
    op.drop_index('ix_project_images_project_id_kind', table_name='project_images')
    op.drop_table("project_images")
    op.drop_index('ix_user_paints_user_id_status', table_name='user_paints')
    op.drop_table("user_paints")
    op.drop_index('ix_refresh_tokens_user_id_active', table_name='refresh_tokens')
    op.drop_table("refresh_tokens")
    op.drop_index('ix_projects_user_id_status', table_name='projects')
    op.drop_table("projects")
    op.drop_index('uq_users_email_lower', table_name='users')
    op.drop_table("users")
    op.drop_index('ix_paints_name', table_name='paints')
    op.drop_index('ix_paints_brand', table_name='paints')
    op.drop_table("paints")
