from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.recipe import Recipe
from app.domain.repositories.recipe_repository import RecipeRepository
from app.infrastructure.database.models.recipe_model import RecipeModel


class SQLAlchemyRecipeRepository(RecipeRepository):

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, recipe_id: int) -> Recipe | None:
        model = await self.db.get(RecipeModel, recipe_id)

        if model is None:
            return None

        return self._to_entity(model)

    async def save(self, recipe: Recipe) -> Recipe:
        model = RecipeModel(
            title=recipe.title,
            description=recipe.description,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            cooking_time=recipe.cooking_time,
        )

        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)

        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: RecipeModel) -> Recipe:
        return Recipe(
            id=model.id,
            title=model.title,
            description=model.description,
            ingredients=model.ingredients,
            instructions=model.instructions,
            cooking_time=model.cooking_time,
        )