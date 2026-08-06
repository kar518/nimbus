"""
Aggregates all v1 endpoint routers into a single APIRouter mounted by
`app.main`.

As resources are implemented, include them here, e.g.:

    from app.api.v1.endpoints import gpu_workers, queue, workloads
    api_router.include_router(workloads.router, prefix="/workloads", tags=["workloads"])
    api_router.include_router(gpu_workers.router, prefix="/gpu-workers", tags=["gpu-workers"])
    api_router.include_router(queue.router, prefix="/queue", tags=["queue"])
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router)
