"""X-SENTINEL V3 Jev AI audit and feedback schema.

Revision ID: 0002_v3_jev_ai_audit
Revises: 0001_v2_multiuser
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_v3_jev_ai_audit"
down_revision = "0001_v2_multiuser"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON()


def upgrade() -> None:
    op.create_table(
        "jev_ai_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_job_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("endpoint_label", sa.String(120), server_default="lm_studio_local", nullable=False),
        sa.Column("prompt_version", sa.String(120), nullable=False),
        sa.Column("input_digest_sha256", sa.String(64), nullable=False),
        sa.Column("output_digest_sha256", sa.String(64), nullable=True),
        sa.Column("context_summary", JSON_TYPE, server_default=sa.text("N'{}'"), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("mode IN ('explain','triage','compare','report','docs')", name="ck_jev_ai_runs_jev_ai_mode_allowed"),
        sa.CheckConstraint("status IN ('queued','running','completed','failed','blocked')", name="ck_jev_ai_runs_jev_ai_status_allowed"),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jev_ai_runs_analysis_job_id", "jev_ai_runs", ["analysis_job_id"])
    op.create_index("ix_jev_ai_runs_requested_by_user_id", "jev_ai_runs", ["requested_by_user_id"])
    op.create_index("ix_jev_ai_runs_mode", "jev_ai_runs", ["mode"])
    op.create_index("ix_jev_ai_runs_status", "jev_ai_runs", ["status"])
    op.create_index("ix_jev_ai_runs_input_digest_sha256", "jev_ai_runs", ["input_digest_sha256"])
    op.create_index("ix_jev_ai_runs_output_digest_sha256", "jev_ai_runs", ["output_digest_sha256"])
    op.create_index("ix_jev_ai_runs_created_at", "jev_ai_runs", ["created_at"])
    op.create_index("ix_jev_ai_runs_analysis_created", "jev_ai_runs", ["analysis_job_id", "created_at"])

    op.create_table(
        "jev_ai_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("jev_ai_run_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(32), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_jev_ai_feedback_jev_ai_feedback_rating_allowed"),
        sa.CheckConstraint("label IS NULL OR label IN ('helpful','not_helpful','incorrect','unsafe','unclear')", name="ck_jev_ai_feedback_jev_ai_feedback_label_allowed"),
        sa.ForeignKeyConstraint(["jev_ai_run_id"], ["jev_ai_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jev_ai_feedback_jev_ai_run_id", "jev_ai_feedback", ["jev_ai_run_id"])
    op.create_index("ix_jev_ai_feedback_user_id", "jev_ai_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_table("jev_ai_feedback")
    op.drop_table("jev_ai_runs")
