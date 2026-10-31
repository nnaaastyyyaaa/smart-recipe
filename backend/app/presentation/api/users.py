from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.application.dto.catalog_dto import (
    DietaryRestrictionResponseSchema,
    RestrictionIdsUpdateSchema,
)
from app.application.exceptions import DietaryRestrictionsNotFoundError
from app.application.user_service import UserService
from app.core.config import SESSION_COOKIE_NAME, SESSION_COOKIE_SECURE
from app.domain.entities.user import User
from app.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCurrentPasswordError,
    InvalidUserNameError,
)
from app.presentation.api.dependencies import (
    get_current_user,
    get_user_service,
)
from app.presentation.schemas.auth import UserResponseSchema
from app.presentation.schemas.user import (
    ChangePasswordSchema,
    UserUpdateSchema,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserResponseSchema)
async def update_me(
    data: UserUpdateSchema,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> User:
    try:
        return await service.update_profile(
            current_user,
            name=data.name,
            email=data.email,
        )

    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except InvalidUserNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordSchema,
    request: Request,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await service.change_password(
            current_user,
            current_password=data.current_password,
            new_password=data.new_password,
            current_session_token=request.cookies.get(SESSION_COOKIE_NAME),
        )

    except InvalidCurrentPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    response: Response,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.delete_account(current_user)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
    )


@router.get(
    "/me/dietary-restrictions",
    response_model=list[DietaryRestrictionResponseSchema],
)
async def get_my_dietary_restrictions(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get_restrictions(current_user.id)


@router.patch(
    "/me/dietary-restrictions",
    response_model=list[DietaryRestrictionResponseSchema],
)
async def set_my_dietary_restrictions(
    data: RestrictionIdsUpdateSchema,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.set_restrictions(
            current_user.id,
            data.restriction_ids,
        )

    except DietaryRestrictionsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Одне або декілька дієтичних обмежень не знайдені.",
        )
