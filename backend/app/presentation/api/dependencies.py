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

from app.application.catalog_service import CatalogService
from app.application.user_service import UserService
from app.application.recipe_service import RecipeService
from app.application.interfaces.recipe_generator import RecipeGenerator

from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.dietary_restriction_repository import (
    DietaryRestrictionRepository,
)
from app.domain.repositories.user_dietary_restriction_repository import (
    UserDietaryRestrictionRepository,
)
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.recipe_repository import RecipeRepository
from app.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.infrastructure.database.repositories.user_dietary_restriction_repository import (
    SQLAlchemyUserDietaryRestrictionRepository,
)
from app.infrastructure.database.repositories.dietary_restriction_repository import (
    SQLAlchemyDietaryRestrictionRepository,
)
from app.infrastructure.database.repositories.category_repository import (
    SQLAlchemyCategoryRepository,
)
from app.infrastructure.database.repositories.product_repository import (
    SQLAlchemyProductRepository,
)
from app.infrastructure.database.repositories.recipe_repository import (
    SQLAlchemyRecipeRepository,
)
from app.infrastructure.database.repositories.saved_recipe_repository import (
    SQLAlchemySavedRecipeRepository,
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

def get_recipe_generator(request: Request) -> RecipeGenerator:
    return request.app.state.recipe_generator


def get_product_repository(
    db: AsyncSession = Depends(get_db),
) -> ProductRepository:
    return SQLAlchemyProductRepository(db)


def get_recipe_repository(
    db: AsyncSession = Depends(get_db),
) -> RecipeRepository:
    return SQLAlchemyRecipeRepository(db)


def get_saved_recipe_repository(
    db: AsyncSession = Depends(get_db),
) -> SavedRecipeRepository:
    return SQLAlchemySavedRecipeRepository(db)


def get_user_dietary_restriction_repository(
    db: AsyncSession = Depends(get_db),
) -> UserDietaryRestrictionRepository:
    return SQLAlchemyUserDietaryRestrictionRepository(db)


def get_dietary_restriction_repository(
    db: AsyncSession = Depends(get_db),
) -> DietaryRestrictionRepository:
    return SQLAlchemyDietaryRestrictionRepository(db)


def get_recipe_service(
    products: ProductRepository = Depends(get_product_repository),
    recipes: RecipeRepository = Depends(get_recipe_repository),
    saved_recipes: SavedRecipeRepository = Depends(get_saved_recipe_repository),
    restrictions: DietaryRestrictionRepository = Depends(
        get_dietary_restriction_repository
    ),
    user_restrictions: UserDietaryRestrictionRepository = Depends(
        get_user_dietary_restriction_repository
    ),
    recipe_generator: RecipeGenerator = Depends(get_recipe_generator),
) -> RecipeService:
    return RecipeService(
        products=products,
        recipes=recipes,
        saved_recipes=saved_recipes,
        restrictions=restrictions,
        user_restrictions=user_restrictions,
        recipe_generator=recipe_generator,
    )


def get_category_repository(
    db: AsyncSession = Depends(get_db),
) -> CategoryRepository:
    return SQLAlchemyCategoryRepository(db)

def get_catalog_service(
    categories: CategoryRepository = Depends(get_category_repository),
    products: ProductRepository = Depends(get_product_repository),
    restrictions: DietaryRestrictionRepository = Depends(
        get_dietary_restriction_repository
    ),
) -> CatalogService:
    return CatalogService(
        categories=categories,
        products=products,
        restrictions=restrictions,
    )


def get_user_service(
    users: UserRepository = Depends(get_user_repository),
    sessions: SessionRepository = Depends(get_session_repository),
    saved_recipes: SavedRecipeRepository = Depends(get_saved_recipe_repository),
    user_restrictions: UserDietaryRestrictionRepository = Depends(
        get_user_dietary_restriction_repository
    ),
    restrictions: DietaryRestrictionRepository = Depends(
        get_dietary_restriction_repository
    ),
) -> UserService:
    return UserService(
        users=users,
        sessions=sessions,
        saved_recipes=saved_recipes,
        user_restrictions=user_restrictions,
        restrictions=restrictions,
    )
