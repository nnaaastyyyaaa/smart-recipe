from fastapi import APIRouter

from app.presentation.api import health
from app.presentation.api import auth
from app.presentation.api import recipes
from app.presentation.api import catalog
from app.presentation.api import users

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api")
api_router.include_router(auth.router, prefix="/api")
api_router.include_router(recipes.router, prefix="/api")
api_router.include_router(catalog.router, prefix="/api")
api_router.include_router(users.router, prefix="/api")