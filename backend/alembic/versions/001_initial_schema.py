"""Initial schema — all Phase 3 tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-09-24

Creates:
- pgvector extension
- patients table
- studies table
- series table
- images table
- analyses table
- embeddings table (with vector column)
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── patients ───────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("external_patient_id", sa.String(255), nullable=False, comment="External patient identifier from upstream clinical system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_patient_id"),
    )
    op.create_index("ix_patients_external_patient_id", "patients", ["external_patient_id"])

    # ── studies ────────────────────────────────────────────────────
    op.create_table(
        "studies",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("study_uid", sa.String(128), nullable=False, comment="DICOM Study Instance UID"),
        sa.Column("study_date", sa.Date(), nullable=True),
        sa.Column("modality", sa.String(16), nullable=True, comment="e.g. MR, CT, PT"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("study_uid"),
    )
    op.create_index("ix_studies_patient_id", "studies", ["patient_id"])
    op.create_index("ix_studies_study_uid", "studies", ["study_uid"])

    # ── series ─────────────────────────────────────────────────────
    op.create_table(
        "series",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("series_uid", sa.String(128), nullable=False, comment="DICOM Series Instance UID"),
        sa.Column("series_number", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("body_part", sa.String(64), nullable=True, comment="e.g. BRAIN, SPINE, KNEE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("series_uid"),
    )
    op.create_index("ix_series_study_id", "series", ["study_id"])
    op.create_index("ix_series_series_uid", "series", ["series_uid"])

    # ── images ─────────────────────────────────────────────────────
    op.create_table(
        "images",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("series_id", sa.UUID(), nullable=False),
        sa.Column("sop_instance_uid", sa.String(128), nullable=False, comment="DICOM SOP Instance UID"),
        sa.Column("file_path", sa.String(1024), nullable=False, comment="Path or object-storage key to the image file"),
        sa.Column("file_format", sa.String(32), nullable=True, comment="e.g. DICOM, NIfTI, PNG"),
        sa.Column("slice_index", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["series_id"], ["series.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("sop_instance_uid"),
    )
    op.create_index("ix_images_series_id", "images", ["series_id"])
    op.create_index("ix_images_sop_instance_uid", "images", ["sop_instance_uid"])

    # ── analyses ───────────────────────────────────────────────────
    op.create_table(
        "analyses",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("image_id", sa.UUID(), nullable=True),
        sa.Column("analysis_type", sa.String(64), nullable=False, comment="e.g. abnormality_detection, enhancement_quality"),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending", comment="pending | running | completed | failed"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_analyses_study_id", "analyses", ["study_id"])
    op.create_index("ix_analyses_image_id", "analyses", ["image_id"])
    op.create_index("ix_analyses_status", "analyses", ["status"])

    # ── embeddings ─────────────────────────────────────────────────
    op.create_table(
        "embeddings",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("study_id", sa.UUID(), nullable=False),
        sa.Column("image_id", sa.UUID(), nullable=True),
        sa.Column("embedding_type", sa.String(64), nullable=False, comment="e.g. image_feature, report_text"),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["study_id"], ["studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_embeddings_study_id", "embeddings", ["study_id"])
    op.create_index("ix_embeddings_image_id", "embeddings", ["image_id"])


def downgrade() -> None:
    op.drop_table("embeddings")
    op.drop_table("analyses")
    op.drop_table("images")
    op.drop_table("series")
    op.drop_table("studies")
    op.drop_table("patients")
    op.execute("DROP EXTENSION IF EXISTS vector")
