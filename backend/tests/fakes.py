from __future__ import annotations

from uuid import UUID

from app.application.dto.recipe_dto import (
    RecipeGenerationSchema,
    RecipeSuggestionSchema,
    RecipeSuggestionsResponse,
)
from app.application.interfaces.recipe_generator import RecipeGenerator
from app.domain.entities.category import Category
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.product import Product
from app.domain.entities.recipe import Recipe
from app.domain.entities.session import Session
from app.domain.entities.user import User
from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.dietary_restriction_repository import (
    DietaryRestrictionRepository,
)
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.recipe_repository import RecipeRepository
from app.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.domain.repositories.session_repository import SessionRepository
from app.domain.repositories.user_repository import UserRepository


class FakeRecipeGenerator(RecipeGenerator):
    def __init__(self, recipe_count: int = 10) -> None:
        self.recipe_count = recipe_count
        self.custom_suggestions: list[RecipeSuggestionSchema] | None = None
        self.suggest_error: Exception | None = None
        self.full_error: Exception | None = None
        self.suggest_calls: list[tuple[list[Product], list[DietaryRestriction]]] = []
        self.full_calls: list[tuple[RecipeSuggestionSchema, list[Product], list[DietaryRestriction]]] = []
        self.closed = False

    async def suggest_recipes(self, products, restrictions):
        self.suggest_calls.append((list(products), list(restrictions)))

        if self.suggest_error is not None:
            raise self.suggest_error

        if self.custom_suggestions is not None:
            recipes = self.custom_suggestions
        else:
            ids = [product.id for product in products]
            recipes = [
                RecipeSuggestionSchema(
                    title=f"Страва {index + 1}",
                    description=f"Опис страви {index + 1}",
                    cooking_time=10 + index,
                    used_product_ids=ids[: max(2, len(ids) - index % 3)],
                )
                for index in range(self.recipe_count)
            ]

        return RecipeSuggestionsResponse.model_construct(recipes=recipes)

    async def generate_full_recipe(self, suggestion, products, restrictions):
        self.full_calls.append((suggestion, list(products), list(restrictions)))

        if self.full_error is not None:
            raise self.full_error

        ingredients = "\n".join(f"- {product.name} — 100 г" for product in products)

        return RecipeGenerationSchema(
            title=suggestion.title,
            description=suggestion.description,
            ingredients=ingredients,
            instructions="1. Підготуйте продукти.\n2. Приготуйте страву.",
            cooking_time=suggestion.cooking_time,
        )

    async def close(self) -> None:
        self.closed = True


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}

    async def get_by_email(self, email):
        return next((u for u in self.users.values() if u.email == email), None)

    async def get_by_id(self, user_id):
        return self.users.get(user_id)

    async def save(self, user):
        self.users[user.id] = user

    async def delete(self, user_id):
        self.users.pop(user_id, None)


class FakeSessionRepository(SessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    async def get_by_token_hash(self, token_hash):
        return self.sessions.get(token_hash)

    async def save(self, session):
        self.sessions[session.token_hash] = session

    async def delete_by_token_hash(self, token_hash):
        self.sessions.pop(token_hash, None)

    async def delete_all_by_user_id(self, user_id, except_token_hash=None):
        self.sessions = {
            key: value
            for key, value in self.sessions.items()
            if value.user_id != user_id or key == except_token_hash
        }


    async def delete_expired(self):
        self.sessions = {k: v for k, v in self.sessions.items() if not v.is_expired()}


class FakeCategoryRepository(CategoryRepository):
    def __init__(self, categories: list[Category] | None = None) -> None:
        self.categories = {c.id: c for c in (categories or [])}

    async def get_by_id(self, category_id):
        return self.categories.get(category_id)

    async def get_by_name(self, name):
        return next((c for c in self.categories.values() if c.name == name), None)

    async def get_all(self):
        return sorted(self.categories.values(), key=lambda c: c.name)


class FakeRestrictionRepository(DietaryRestrictionRepository):
    def __init__(self, restrictions: list[DietaryRestriction] | None = None) -> None:
        self.restrictions = {r.id: r for r in (restrictions or [])}

    async def get_by_id(self, restriction_id):
        return self.restrictions.get(restriction_id)

    async def get_by_name(self, name):
        return next((r for r in self.restrictions.values() if r.name == name), None)

    async def get_by_ids(self, restriction_ids):
        found = [self.restrictions[i] for i in dict.fromkeys(restriction_ids) if i in self.restrictions]
        return sorted(found, key=lambda r: r.name)

    async def get_all(self):
        return sorted(self.restrictions.values(), key=lambda r: r.name)


class FakeProductRepository(ProductRepository):
    def __init__(
        self,
        products: list[Product],
        forbidden: dict[int, set[int]] | None = None,
        restrictions: dict[int, DietaryRestriction] | None = None,
    ) -> None:
        self.products = {p.id: p for p in products}
        self.forbidden = forbidden or {}
        self.restrictions = restrictions or {}

    def _allowed(self, product: Product, exclude: list[int] | None) -> bool:
        if not exclude:
            return True
        return not (self.forbidden.get(product.id, set()) & set(exclude))

    async def get_by_id(self, product_id):
        return self.products.get(product_id)

    async def get_by_ids(self, product_ids, exclude_restriction_ids=None):
        return [
            self.products[i]
            for i in dict.fromkeys(product_ids)
            if i in self.products
            and self._allowed(self.products[i], exclude_restriction_ids)
        ]

    async def get_all(self, category_id=None, limit=12, offset=0, search=None,
                      exclude_restriction_ids=None):
        items = [
            p for p in self.products.values()
            if (category_id is None or p.category_id == category_id)
            and (not search or search.casefold() in p.name.casefold())
            and self._allowed(p, exclude_restriction_ids)
        ]
        items.sort(key=lambda p: p.name)
        return items[offset: offset + limit]

    async def get_restrictions(self, product_id):
        return [
            self.restrictions[i]
            for i in sorted(self.forbidden.get(product_id, set()))
            if i in self.restrictions
        ]

    async def get_category_ids(self, exclude_restriction_ids=None):
        return sorted({
            p.category_id for p in self.products.values()
            if self._allowed(p, exclude_restriction_ids)
        })


class FakeRecipeRepository(RecipeRepository):
    def __init__(self) -> None:
        self.recipes: dict[int, Recipe] = {}
        self._next_id = 1

    async def get_by_id(self, recipe_id):
        return self.recipes.get(recipe_id)

    async def save(self, recipe):
        recipe.id = self._next_id
        self._next_id += 1
        self.recipes[recipe.id] = recipe
        return recipe


class FakeSavedRecipeRepository(SavedRecipeRepository):
    def __init__(self, recipes: FakeRecipeRepository | None = None) -> None:
        self.recipes = recipes or FakeRecipeRepository()
        self.links: set[tuple[UUID, int]] = set()
        self.link_fails = False

    async def save(self, user_id, recipe_id):
        if self.link_fails:
            return False
        self.links.add((user_id, recipe_id))
        return True

    async def get_all_by_user_id(self, user_id, limit=None, offset=0):
        items = sorted(
            (self.recipes.recipes[rid] for uid, rid in self.links if uid == user_id),
            key=lambda r: (r.title, r.id),
        )

        return items[offset: offset + limit] if limit is not None else items[offset:]

    async def count_by_user_id(self, user_id):
        return sum(1 for uid, _ in self.links if uid == user_id)

    async def get_by_id(self, user_id, recipe_id):
        if (user_id, recipe_id) in self.links:
            return self.recipes.recipes.get(recipe_id)
        return None

    async def delete(self, user_id, recipe_id):
        if (user_id, recipe_id) not in self.links:
            return False
        self.links.discard((user_id, recipe_id))
        if not any(rid == recipe_id for _, rid in self.links):
            self.recipes.recipes.pop(recipe_id, None)
        return True

    async def delete_all_by_user_id(self, user_id):
        for link in [l for l in self.links if l[0] == user_id]:
            await self.delete(*link)
