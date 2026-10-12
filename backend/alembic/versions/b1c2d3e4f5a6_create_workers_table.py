"""Create the workers table before adding heartbeat tracking.

Revision ID: b1c2d3e4f5a6
Revises: 7fe5fea5128e
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "7fe5fea5128e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Earlier development databases may already contain this table.
    if sa.inspect(op.get_bind()).has_table("workers"):
        return

    op.create_table(
        "workers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("IDLE", "BUSY", "OFFLINE", name="worker_status"),
            server_default="OFFLINE",
            nullable=False,
        ),
        sa.Column("gpu_memory", sa.Integer(), nullable=False),
        sa.Column("gpu_utilization", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_job", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workers")),
    )
    op.create_index(op.f("ix_workers_name"), "workers", ["name"], unique=True)
    op.create_index(op.f("ix_workers_status"), "workers", ["status"], unique=False)
    op.create_index(op.f("ix_workers_current_job"), "workers", ["current_job"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workers_current_job"), table_name="workers")
    op.drop_index(op.f("ix_workers_status"), table_name="workers")
    op.drop_index(op.f("ix_workers_name"), table_name="workers")
    op.drop_table("workers")
    sa.Enum(name="worker_status").drop(op.get_bind(), checkfirst=True)
