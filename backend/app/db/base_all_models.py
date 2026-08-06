"""
Import every ORM model here so `Base.metadata` is fully populated before
Alembic's `--autogenerate` inspects it.

No models exist yet — this file is the designated hook point for when
they're added, e.g.:

    from app.models.user import User          # noqa: F401
    from app.models.workload import Workload   # noqa: F401
    from app.models.gpu_worker import GPUWorker  # noqa: F401
"""

from app.db.base import Base  # noqa: F401
