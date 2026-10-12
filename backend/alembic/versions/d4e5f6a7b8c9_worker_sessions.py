"""Revoke old agent credentials when a worker reconnects.
Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("workers", sa.Column("session_id", postgresql.UUID(as_uuid=True)))

def downgrade():
    op.drop_column("workers", "session_id")
