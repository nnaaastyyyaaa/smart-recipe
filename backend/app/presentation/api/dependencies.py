from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth_service import AuthService
from app.core.config import SESSION_COOKIE_NAME
from app.domain.entities.user import User
from app.domain.repositories.session_repository import SessionRepository
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.database import get_db
from app.infrastructure.database.repositories.session_repository import (
    SqlAlchemySessionRepository,
)
from app.infrastructure.database.repositories.user_repository import (
    SqlAlchemyUserRepository,
)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(db)


def get_session_repository(db: AsyncSession = Depends(get_db)) -> SessionRepository:
    return SqlAlchemySessionRepository(db)


def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    sessions: SessionRepository = Depends(get_session_repository),
) -> AuthService:
    return AuthService(users, sessions)


async def get_current_user(
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if token:
        user = await service.get_user_by_session(token)
        if user is not None:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не авторизовано.",
    )