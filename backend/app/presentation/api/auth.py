from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.application.auth_service import AuthService
from app.core.config import SESSION_COOKIE_NAME, SESSION_COOKIE_SECURE
from app.domain.entities.user import User
from app.domain.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from app.presentation.api.dependencies import get_auth_service, get_current_user
from app.presentation.schemas.auth import (
    UserLoginSchema,
    UserRegisterSchema,
    UserResponseSchema,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _delete_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserRegisterSchema,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> User:
    try:
        user = await service.register(data.name, data.email, data.password)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    _set_session_cookie(response, await service.create_session(user))
    return user


@router.post("/login", response_model=UserResponseSchema)
async def login(
    data: UserLoginSchema,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> User:
    try:
        user = await service.authenticate(data.email, data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    old_token = request.cookies.get(SESSION_COOKIE_NAME)
    if old_token:
        await service.logout(old_token)

    _set_session_cookie(response, await service.create_session(user))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        await service.logout(token)

    _delete_session_cookie(response)


@router.get("/me", response_model=UserResponseSchema)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user