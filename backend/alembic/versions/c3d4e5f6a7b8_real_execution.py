"""Add executable workloads, worker capacities, accounts, and output files.

Revision ID: c3d4e5f6a7b8
Revises: a2c3d4e5f6a7
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b8"
down_revision = "a2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'ASSIGNED'")
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'CANCELLED'")
    for column in [
        sa.Column("image", sa.String(255), server_default="python:3.12-slim", nullable=False),
        sa.Column("command", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("memory_limit_mb", sa.Integer(), server_default="512", nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), server_default="300", nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("execution_token", postgresql.UUID(as_uuid=True)),
        sa.Column("exit_code", sa.Integer()),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("log_text", sa.Text(), server_default="", nullable=False),
        sa.Column("retry_of", postgresql.UUID(as_uuid=True)),
        sa.Column("assigned_at", sa.DateTime()),
    ]:
        op.add_column("jobs", column)
    for column in [
        sa.Column("cpu_capacity", sa.Numeric(6, 2), server_default="1", nullable=False),
        sa.Column("memory_capacity_mb", sa.Integer(), server_default="512", nullable=False),
        sa.Column("executor", sa.String(32), server_default="legacy", nullable=False),
        sa.Column("draining", sa.Boolean(), server_default="false", nullable=False),
    ]:
        op.add_column("workers", column)
    op.create_table("users", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("username", sa.String(64), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("is_admin", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("artifacts", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("size", sa.Integer(), nullable=False), sa.Column("content", sa.LargeBinary(), nullable=False))
    op.create_index("ix_artifacts_job_id", "artifacts", ["job_id"])
    op.execute("UPDATE jobs SET status='FAILED', failure_reason='Legacy execution was interrupted before upgrade.', completed_at=now() WHERE status='RUNNING'")
    op.execute("UPDATE workers SET status='OFFLINE', current_job=NULL")


def downgrade():
    op.drop_table("artifacts")
    op.drop_table("users")
    for name in ["draining", "executor", "memory_capacity_mb", "cpu_capacity"]:
        op.drop_column("workers", name)
    for name in ["assigned_at", "retry_of", "log_text", "failure_reason", "exit_code", "execution_token", "cancel_requested", "timeout_seconds", "memory_limit_mb", "command", "image"]:
        op.drop_column("jobs", name)
    # PostgreSQL enum additions are retained; existing historical states remain valid.
