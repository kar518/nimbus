"""
Aggregates all v1 endpoint routers into a single APIRouter mounted by
`app.main`.

As resources are implemented, include them here, e.g.:

    from app.api.v1.endpoints import gpu_workers, queue
    api_router.include_router(gpu_workers.router, prefix="/gpu-workers", tags=["gpu-workers"])
    api_router.include_router(queue.router, prefix="/queue", tags=["queue"])
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, jobs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(jobs.router, prefix="/jobs")
