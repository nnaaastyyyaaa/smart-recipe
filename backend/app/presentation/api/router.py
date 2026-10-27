from fastapi import APIRouter

from app.presentation.api import health
from app.presentation.api import auth

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api")
api_router.include_router(auth.router, prefix="/api")