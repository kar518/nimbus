from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, jobs, websocket, workers

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(jobs.router, prefix="/jobs")
api_router.include_router(workers.router, prefix="/workers")
api_router.include_router(websocket.router)
