from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.catalog_service import CatalogService
from app.application.dto.catalog_dto import (
    CategoryResponseSchema,
    DietaryRestrictionResponseSchema,
    ProductResponseSchema,
    RestrictionIdsUpdateSchema,
)
from app.application.exceptions import (
    CategoryNotFoundError,
    DietaryRestrictionsNotFoundError,
    ProductNotFoundError,
)
from app.domain.entities.user import User
from app.presentation.api.dependencies import (
    get_catalog_service,
    get_current_user,
)


router = APIRouter(tags=["catalog"])


@router.get(
    "/categories",
    response_model=list[CategoryResponseSchema],
)
async def get_categories(
    service: CatalogService = Depends(get_catalog_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get_categories()


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponseSchema,
)
async def get_category(
    category_id: int,
    service: CatalogService = Depends(get_catalog_service),
    current_user: User = Depends(get_current_user),
):
    category = await service.get_category(category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категорія не знайдена.",
        )

    return category


@router.get(
    "/dietary-restrictions",
    response_model=list[DietaryRestrictionResponseSchema],
)
async def get_dietary_restrictions(
    service: CatalogService = Depends(get_catalog_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get_dietary_restrictions()


@router.get(
    "/products",
    response_model=list[ProductResponseSchema],
)
async def get_products(
    category_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, min_length=1, max_length=60),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    restriction_ids: list[int] | None = Query(default=None),
    service: CatalogService = Depends(get_catalog_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.get_products(
            category_id=category_id,
            search=search,
            limit=limit,
            offset=offset,
            restriction_ids=restriction_ids,
        )

    except DietaryRestrictionsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Одне або декілька дієтичних обмежень не знайдені.",
        )

    except CategoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категорія не знайдена.",
        )


@router.get(
    "/products/{product_id}",
    response_model=ProductResponseSchema,
)
async def get_product(
    product_id: int,
    service: CatalogService = Depends(get_catalog_service),
    current_user: User = Depends(get_current_user),
):
    product = await service.get_product(product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продукт не знайдено.",
        )

    return product


@router.get(
    "/dietary-restrictions/{restriction_id}",
    response_model=DietaryRestrictionResponseSchema,
)
async def get_dietary_restriction(
    restriction_id: int,
    service: CatalogService = Depends(get_catalog_service),
    current_user: User = Depends(get_current_user),
):
    restriction = await service.get_dietary_restriction(restriction_id)

    if restriction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Дієтичне обмеження не знайдено.",
        )

    return restriction


@router.get(
    "/products/{product_id}/restrictions",
    response_model=list[DietaryRestrictionResponseSchema],
)
async def get_product_restrictions(
    product_id: int,
    service: CatalogService = Depends(get_catalog_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.get_product_restrictions(product_id)

    except ProductNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продукт не знайдено.",
        )
