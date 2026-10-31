import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import (
    CORS_ORIGINS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_APP_RPM_LIMIT,
)
from app.infrastructure.database.database import wait_for_database
from app.infrastructure.ai.rate_limiter import InMemoryGeminiRateLimiter
from app.infrastructure.ai.gemini_recipe_generator import GeminiRecipeGenerator
from app.presentation.api.router import api_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_database()

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    if not GEMINI_MODEL:
        raise RuntimeError("GEMINI_MODEL is not set.")

    rate_limiter = InMemoryGeminiRateLimiter(
        requests_per_minute=GEMINI_APP_RPM_LIMIT,
    )

    recipe_generator = GeminiRecipeGenerator(
        api_key=GEMINI_API_KEY,
        model=GEMINI_MODEL,
        rate_limiter=rate_limiter,
    )

    app.state.recipe_generator = recipe_generator

    try:
        yield
    finally:
        await recipe_generator.close()


app = FastAPI(
    title="SmartRecipe API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)