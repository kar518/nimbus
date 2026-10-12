"""add worker heartbeat

Revision ID: a2c3d4e5f6a7
Revises: b1c2d3e4f5a6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a2c3d4e5f6a7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workers",
        sa.Column("last_heartbeat", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_workers_last_heartbeat"),
        "workers",
        ["last_heartbeat"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_workers_last_heartbeat"),
        table_name="workers",
    )
    op.drop_column("workers", "last_heartbeat")
