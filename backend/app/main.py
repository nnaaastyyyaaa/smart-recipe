import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.persistence.database import wait_for_database
from app.presentation.api.router import api_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_database()

    yield


app = FastAPI(
    title="SmartRecipe API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)