from fastapi import APIRouter

from app.presentation.api import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api")