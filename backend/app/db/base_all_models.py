"""
Import every ORM model here so `Base.metadata` is fully populated before
Alembic's `--autogenerate` inspects it.
"""

from app.db.base import Base  # noqa: F401
from app.models.job import Job  # noqa: F401