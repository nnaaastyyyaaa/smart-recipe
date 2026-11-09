from math import ceil
from uuid import UUID

from app.application.dto.catalog_dto import DietaryRestrictionResponseSchema
from app.application.dto.generation_dto import (
    GenerationStateSchema,
    SuggestionItemSchema,
    SuggestionsPageSchema,
)
from app.application.dto.recipe_dto import (
    RecipeGenerationSchema,
    RecipeSuggestionSchema,
)
from app.application.exceptions import (
    CategoryNotFoundError,
    DietaryRestrictionsNotFoundError,
    GenerationNotFoundError,
    GenerationRestrictionsNotSelectedError,
    GenerationStateChangedError,
    GenerationSuggestionsNotReadyError,
    NoSuitableRecipesError,
    ProductsNotFoundError,
    ProductsViolateRestrictionsError,
    SuggestionNotFoundError,
    SuggestionsPageNotFoundError,
)
from app.application.interfaces.recipe_generator import RecipeGenerator
from app.core.config import (
    GENERATION_SESSION_TTL_MINUTES,
    MAX_RECIPE_SUGGESTIONS,
    SUGGESTIONS_PAGE_SIZE,
)
from app.domain.entities.category import Category
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.generation_session import (
    GenerationSession,
    GenerationStatus,
    GenerationSuggestion,
)
from app.domain.entities.product import Product
from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.dietary_restriction_repository import (
    DietaryRestrictionRepository,
)
from app.domain.repositories.generation_session_repository import (
    GenerationSessionRepository,
)
from app.domain.repositories.product_repository import ProductRepository


class GenerationService:
    """Покроковий процес створення рецепта.

    1. start                -> нова сесія ("Почати генерацію")
    2. set_restrictions     -> дієтичні обмеження (або "немає")
    3. get_available_categories / get_available_products
                            -> лише категорії й продукти, що підходять під обмеження
    4. suggest_recipes      -> до 16 варіантів, повертається перша сторінка
    5. get_suggestions_page -> інші сторінки варіантів (по 8)
    6. generate_full_recipe -> детальний рецепт для обраного варіанта
    """

    def __init__(
        self,
        sessions: GenerationSessionRepository,
        categories: CategoryRepository,
        products: ProductRepository,
        restrictions: DietaryRestrictionRepository,
        recipe_generator: RecipeGenerator,
    ) -> None:
        self.sessions = sessions
        self.categories = categories
        self.products = products
        self.restrictions = restrictions
        self.recipe_generator = recipe_generator

    # ------------------------------------------------------------------
    # Публічні методи
    # ------------------------------------------------------------------

    async def start(self, user_id: UUID) -> GenerationStateSchema:
        session = GenerationSession.start(
            user_id=user_id,
            ttl_minutes=GENERATION_SESSION_TTL_MINUTES,
        )

        await self.sessions.save(session)

        return await self._to_state(session)

    async def get_state(
        self,
        user_id: UUID,
        generation_id: UUID,
    ) -> GenerationStateSchema:
        session = await self._get_session(user_id, generation_id)

        return await self._to_state(session)

    async def set_restrictions(
        self,
        user_id: UUID,
        generation_id: UUID,
        restriction_ids: list[int],
    ) -> GenerationStateSchema:
        restrictions = await self._load_restrictions(restriction_ids)

        session = await self._get_session(user_id, generation_id)
        session.select_restrictions(restriction_ids)

        await self.sessions.save(session)

        return await self._to_state(session, restrictions)

    async def get_available_categories(
        self,
        user_id: UUID,
        generation_id: UUID,
    ) -> list[Category]:
        session = await self._get_session(user_id, generation_id)
        self._ensure_restrictions_selected(session)

        allowed_ids = set(
            await self.products.get_category_ids(session.restriction_ids)
        )

        return [
            category
            for category in await self.categories.get_all()
            if category.id in allowed_ids
        ]

    async def get_available_products(
        self,
        user_id: UUID,
        generation_id: UUID,
        category_id: int | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[Product]:
        session = await self._get_session(user_id, generation_id)
        self._ensure_restrictions_selected(session)

        if category_id is not None:
            category = await self.categories.get_by_id(category_id)

            if category is None:
                raise CategoryNotFoundError()

        return await self.products.get_all(
            category_id=category_id,
            limit=limit,
            offset=offset,
            search=search,
            exclude_restriction_ids=session.restriction_ids,
        )

    async def suggest_recipes(
        self,
        user_id: UUID,
        generation_id: UUID,
        product_ids: list[int],
    ) -> SuggestionsPageSchema:
        session = await self._get_session(user_id, generation_id)
        self._ensure_restrictions_selected(session)

        restriction_ids = list(session.restriction_ids)
        revision = session.revision

        products = await self.products.get_by_ids(product_ids)

        if len(products) != len(product_ids):
            raise ProductsNotFoundError()

        restrictions = await self._load_restrictions(restriction_ids)

        await self._ensure_products_allowed(products, restriction_ids)

        response = await self.recipe_generator.suggest_recipes(
            products,
            restrictions,
        )

        valid_recipes = self._filter_suggestions(
            response.recipes,
            selected_ids=set(product_ids),
        )

        if not valid_recipes:
            raise NoSuitableRecipesError()

        session = await self._get_session(user_id, generation_id)

        if session.revision != revision:
            raise GenerationStateChangedError()

        session.set_suggestions(
            product_ids=product_ids,
            suggestions=[
                GenerationSuggestion(
                    title=recipe.title,
                    description=recipe.description,
                    cooking_time=recipe.cooking_time,
                    used_product_ids=list(recipe.used_product_ids),
                )
                for recipe in valid_recipes
            ],
        )

        await self.sessions.save(session)

        return self._build_page(session, page=1)

    async def get_suggestions_page(
        self,
        user_id: UUID,
        generation_id: UUID,
        page: int,
    ) -> SuggestionsPageSchema:
        session = await self._get_session(user_id, generation_id)

        if session.status != GenerationStatus.SUGGESTIONS_READY:
            raise GenerationSuggestionsNotReadyError()

        return self._build_page(session, page)

    async def generate_full_recipe(
        self,
        user_id: UUID,
        generation_id: UUID,
        suggestion_id: int,
    ) -> RecipeGenerationSchema:
        session = await self._get_session(user_id, generation_id)

        if session.status != GenerationStatus.SUGGESTIONS_READY:
            raise GenerationSuggestionsNotReadyError()

        if not 0 <= suggestion_id < len(session.suggestions):
            raise SuggestionNotFoundError()

        suggestion = session.suggestions[suggestion_id]
        restriction_ids = list(session.restriction_ids)

        products = await self.products.get_by_ids(
            suggestion.used_product_ids
        )

        if len(products) != len(suggestion.used_product_ids):
            raise ProductsNotFoundError()

        restrictions = await self._load_restrictions(restriction_ids)

        await self._ensure_products_allowed(products, restriction_ids)

        return await self.recipe_generator.generate_full_recipe(
            suggestion=RecipeSuggestionSchema(
                title=suggestion.title,
                description=suggestion.description,
                cooking_time=suggestion.cooking_time,
                used_product_ids=suggestion.used_product_ids,
            ),
            products=products,
            restrictions=restrictions,
        )

    # ------------------------------------------------------------------
    # Внутрішні методи
    # ------------------------------------------------------------------

    async def _get_session(
        self,
        user_id: UUID,
        generation_id: UUID,
    ) -> GenerationSession:
        session = await self.sessions.get(generation_id)

        if session is None or session.user_id != user_id:
            raise GenerationNotFoundError()

        session.touch(GENERATION_SESSION_TTL_MINUTES)

        return session

    @staticmethod
    def _ensure_restrictions_selected(session: GenerationSession) -> None:
        if not session.restrictions_selected:
            raise GenerationRestrictionsNotSelectedError()

    async def _load_restrictions(
        self,
        restriction_ids: list[int],
    ) -> list[DietaryRestriction]:

        if not restriction_ids:
            return []

        restrictions = await self.restrictions.get_by_ids(restriction_ids)

        if len(restrictions) != len(set(restriction_ids)):
            raise DietaryRestrictionsNotFoundError()

        return restrictions

    async def _ensure_products_allowed(
        self,
        products: list[Product],
        restriction_ids: list[int],
    ) -> None:

        if not restriction_ids:
            return

        allowed = await self.products.get_by_ids(
            [product.id for product in products],
            exclude_restriction_ids=restriction_ids,
        )

        if len(allowed) != len(products):
            raise ProductsViolateRestrictionsError()

    @staticmethod
    def _filter_suggestions(
        recipes: list[RecipeSuggestionSchema],
        selected_ids: set[int],
    ) -> list[RecipeSuggestionSchema]:

        valid_recipes: list[RecipeSuggestionSchema] = []
        seen_titles: set[str] = set()

        for recipe in recipes:
            used_ids = set(recipe.used_product_ids)

            if len(used_ids) < 2:
                continue

            if not used_ids.issubset(selected_ids):
                continue

            normalized_title = recipe.title.casefold()

            if normalized_title in seen_titles:
                continue

            seen_titles.add(normalized_title)
            valid_recipes.append(recipe)

        valid_recipes.sort(
            key=lambda recipe: len(recipe.used_product_ids),
            reverse=True,
        )

        return valid_recipes[:MAX_RECIPE_SUGGESTIONS]

    @staticmethod
    def _build_page(
        session: GenerationSession,
        page: int,
    ) -> SuggestionsPageSchema:

        total = len(session.suggestions)
        total_pages = max(1, ceil(total / SUGGESTIONS_PAGE_SIZE))

        if page < 1 or page > total_pages:
            raise SuggestionsPageNotFoundError()

        start = (page - 1) * SUGGESTIONS_PAGE_SIZE
        chunk = session.suggestions[start:start + SUGGESTIONS_PAGE_SIZE]

        return SuggestionsPageSchema(
            items=[
                SuggestionItemSchema(
                    id=start + index,
                    title=suggestion.title,
                    description=suggestion.description,
                    cooking_time=suggestion.cooking_time,
                    used_product_ids=suggestion.used_product_ids,
                )
                for index, suggestion in enumerate(chunk)
            ],
            page=page,
            page_size=SUGGESTIONS_PAGE_SIZE,
            total=total,
            total_pages=total_pages,
        )

    async def _to_state(
        self,
        session: GenerationSession,
        restrictions: list[DietaryRestriction] | None = None,
    ) -> GenerationStateSchema:

        if restrictions is None:
            restrictions = await self._load_restrictions(
                session.restriction_ids
            )

        return GenerationStateSchema(
            id=session.id,
            status=session.status,
            restrictions=[
                DietaryRestrictionResponseSchema.model_validate(restriction)
                for restriction in restrictions
            ],
            product_ids=list(session.product_ids),
            suggestions_total=len(session.suggestions),
            expires_at=session.expires_at,
        )
