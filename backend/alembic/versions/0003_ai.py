"""Tablas de generación, guías, progreso y corpus RAG."""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '0003_ai'
down_revision: str | None = '0002_core'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_key', sa.String(length=160), nullable=False),
        sa.Column('chunk_index', sa.SmallInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('category', sa.Enum('technique', 'product', 'beginner_guide', 'color_theory', 'faq', name='knowledge_category', native_enum=False, create_constraint=False, length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("knowledge_documents.category IN ('technique', 'product', 'beginner_guide', 'color_theory', 'faq')", name='knowledge_category'),
        sa.PrimaryKeyConstraint('id', name='pk_knowledge_documents'),
        sa.UniqueConstraint('document_key', 'chunk_index', name='uq_knowledge_documents_document_chunk'),
    )
    op.create_index('ix_knowledge_documents_category', 'knowledge_documents', ['category'])
    op.create_index('ix_knowledge_documents_embedding', 'knowledge_documents', ['embedding'], postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'}, postgresql_with={'m': 16, 'ef_construction': 64})
    op.create_table(
        "generations",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('source_image_id', sa.Uuid(), nullable=False),
        sa.Column('result_image_id', sa.Uuid(), nullable=True),
        sa.Column('provider', sa.String(length=40), nullable=False, server_default=sa.text("'qwen-local'")),
        sa.Column('model_name', sa.String(length=120), nullable=False),
        sa.Column('quality', sa.Enum('draft', 'final', name='quality_mode', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='draft'),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('status', sa.Enum('queued', 'running', 'succeeded', 'failed', 'cancelled', name='generation_status', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='queued'),
        sa.Column('progress_stage', sa.Enum('queued', 'loading', 'inference', 'postprocess', 'done', name='generation_stage', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='queued'),
        sa.Column('progress_percent', sa.SmallInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('job_id', sa.String(length=120), nullable=True),
        sa.Column('estimated_seconds', sa.Integer(), nullable=True),
        sa.Column('model_load_ms', sa.Integer(), nullable=True),
        sa.Column('inference_ms', sa.Integer(), nullable=True),
        sa.Column('vram_peak_mb', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(length=60), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("generations.quality IN ('draft', 'final')", name='quality_mode'),
        sa.CheckConstraint("generations.status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')", name='generation_status'),
        sa.CheckConstraint("generations.progress_stage IN ('queued', 'loading', 'inference', 'postprocess', 'done')", name='generation_stage'),
        sa.CheckConstraint('progress_percent BETWEEN 0 AND 100', name='progress_percent_range'),
        sa.ForeignKeyConstraint(['source_image_id'], ['project_images.id'], name='fk_generations_source_image_id_project_images', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_generations_project_id_projects', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['result_image_id'], ['project_images.id'], name='fk_generations_result_image_id_project_images', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_generations'),
        sa.UniqueConstraint('job_id', name='uq_generations_job_id'),
    )
    op.create_index('ix_generations_active', 'generations', ['status'], postgresql_where=sa.text("status IN ('queued', 'running')"))
    op.create_index('ix_generations_project_id_created_at', 'generations', ['project_id', 'created_at'])
    op.create_table(
        "generation_events",
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column('generation_id', sa.Uuid(), nullable=False),
        sa.Column('stage', sa.Enum('queued', 'loading', 'inference', 'postprocess', 'done', name='generation_stage', native_enum=False, create_constraint=False, length=32), nullable=False),
        sa.Column('message', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("generation_events.stage IN ('queued', 'loading', 'inference', 'postprocess', 'done')", name='generation_stage'),
        sa.ForeignKeyConstraint(['generation_id'], ['generations.id'], name='fk_generation_events_generation_id_generations', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_generation_events'),
    )
    op.create_index('ix_generation_events_generation_id_created_at', 'generation_events', ['generation_id', 'created_at'])
    op.create_table(
        "guides",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('generation_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'generating', 'ready', 'failed', name='guide_status', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='pending'),
        sa.Column('llm_model', sa.String(length=120), nullable=True),
        sa.Column('prompt_version', sa.String(length=20), nullable=False, server_default=sa.text("'v1'")),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('retrieved_chunks', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('total_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("guides.status IN ('pending', 'generating', 'ready', 'failed')", name='guide_status'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_guides_project_id_projects', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['generation_id'], ['generations.id'], name='fk_guides_generation_id_generations', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_guides'),
    )
    op.create_index('ix_guides_project_id_created_at', 'guides', ['project_id', 'created_at'])
    op.create_table(
        "guide_steps",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('guide_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.SmallInteger(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('technique', sa.Enum('base_coat', 'wash', 'layering', 'edge_highlight', 'drybrush', 'glazing', 'blending', 'varnish', 'basing', 'other', name='technique_type', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='other'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('time_minutes', sa.SmallInteger(), nullable=True),
        sa.Column('is_optional', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('image_id', sa.Uuid(), nullable=True),
        sa.CheckConstraint("guide_steps.technique IN ('base_coat', 'wash', 'layering', 'edge_highlight', 'drybrush', 'glazing', 'blending', 'varnish', 'basing', 'other')", name='technique_type'),
        sa.CheckConstraint('position > 0', name='position_positive'),
        sa.CheckConstraint('time_minutes IS NULL OR time_minutes >= 0', name='time_non_negative'),
        sa.ForeignKeyConstraint(['guide_id'], ['guides.id'], name='fk_guide_steps_guide_id_guides', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['image_id'], ['project_images.id'], name='fk_guide_steps_image_id_project_images', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_guide_steps'),
        sa.UniqueConstraint('guide_id', 'position', name='uq_guide_steps_guide_position'),
    )
    op.create_table(
        "guide_step_paints",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('step_id', sa.Uuid(), nullable=False),
        sa.Column('paint_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.Enum('primary', 'secondary', 'accent', 'skin', 'metal', 'wash', 'highlight', 'base_rim', 'other', name='scheme_role', native_enum=False, create_constraint=False, length=32), nullable=False, server_default='primary'),
        sa.Column('is_substitute', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('substitute_for_paint_id', sa.Uuid(), nullable=True),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.CheckConstraint("guide_step_paints.role IN ('primary', 'secondary', 'accent', 'skin', 'metal', 'wash', 'highlight', 'base_rim', 'other')", name='scheme_role'),
        sa.ForeignKeyConstraint(['substitute_for_paint_id'], ['paints.id'], name='fk_guide_step_paints_substitute_for_paint_id_paints', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['paint_id'], ['paints.id'], name='fk_guide_step_paints_paint_id_paints', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['step_id'], ['guide_steps.id'], name='fk_guide_step_paints_step_id_guide_steps', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_guide_step_paints'),
        sa.UniqueConstraint('step_id', 'paint_id', 'role', name='uq_guide_step_paints_step_paint'),
    )
    op.create_index('ix_guide_step_paints_step_id', 'guide_step_paints', ['step_id'])
    op.create_table(
        "progress_entries",
        sa.Column('id', sa.Uuid(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('guide_step_id', sa.Uuid(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('minutes_spent', sa.SmallInteger(), nullable=True),
        sa.Column('image_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('minutes_spent IS NULL OR minutes_spent >= 0', name='minutes_non_negative'),
        sa.ForeignKeyConstraint(['image_id'], ['project_images.id'], name='fk_progress_entries_image_id_project_images', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_progress_entries_project_id_projects', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guide_step_id'], ['guide_steps.id'], name='fk_progress_entries_guide_step_id_guide_steps', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_progress_entries'),
    )
    op.create_index('ix_progress_entries_project_id_created_at', 'progress_entries', ['project_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_progress_entries_project_id_created_at', table_name='progress_entries')
    op.drop_table("progress_entries")
    op.drop_index('ix_guide_step_paints_step_id', table_name='guide_step_paints')
    op.drop_table("guide_step_paints")
    op.drop_table("guide_steps")
    op.drop_index('ix_guides_project_id_created_at', table_name='guides')
    op.drop_table("guides")
    op.drop_index('ix_generation_events_generation_id_created_at', table_name='generation_events')
    op.drop_table("generation_events")
    op.drop_index('ix_generations_project_id_created_at', table_name='generations')
    op.drop_index('ix_generations_active', table_name='generations')
    op.drop_table("generations")
    op.drop_index('ix_knowledge_documents_embedding', table_name='knowledge_documents')
    op.drop_index('ix_knowledge_documents_category', table_name='knowledge_documents')
    op.drop_table("knowledge_documents")
