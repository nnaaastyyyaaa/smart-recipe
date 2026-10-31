from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.recipe import Recipe
from app.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.infrastructure.database.models.associations import saved_recipes
from app.infrastructure.database.models.recipe_model import RecipeModel


class SQLAlchemySavedRecipeRepository(SavedRecipeRepository):

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save(self, user_id: UUID, recipe_id: int) -> bool:
        statement = (
            insert(saved_recipes)
            .values(
                user_id=user_id,
                recipe_id=recipe_id,
            )
            .on_conflict_do_nothing()
        )

        result = await self.db.execute(statement)

        return result.rowcount == 1

    async def get_all_by_user_id(
        self,
        user_id: UUID,
    ) -> list[Recipe]:
        statement = (
            select(RecipeModel)
            .join(
                saved_recipes,
                saved_recipes.c.recipe_id == RecipeModel.id,
            )
            .where(saved_recipes.c.user_id == user_id)
            .order_by(RecipeModel.title)
        )

        result = await self.db.execute(statement)
        models = result.scalars().all()

        return [
            self._to_entity(model)
            for model in models
        ]

    async def get_by_id(
        self,
        user_id: UUID,
        recipe_id: int,
    ) -> Recipe | None:
        statement = (
            select(RecipeModel)
            .join(
                saved_recipes,
                saved_recipes.c.recipe_id == RecipeModel.id,
            )
            .where(
                saved_recipes.c.user_id == user_id,
                RecipeModel.id == recipe_id,
            )
        )

        result = await self.db.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def delete(
        self,
        user_id: UUID,
        recipe_id: int,
    ) -> bool:
        statement = (
            delete(saved_recipes)
            .where(
                saved_recipes.c.user_id == user_id,
                saved_recipes.c.recipe_id == recipe_id,
            )
            .returning(saved_recipes.c.recipe_id)
        )

        result = await self.db.execute(statement)
        deleted_recipe_id = result.scalar_one_or_none()

        if deleted_recipe_id is None:
            return False

        remaining_count = await self.db.scalar(
            select(func.count())
            .select_from(saved_recipes)
            .where(saved_recipes.c.recipe_id == recipe_id)
        )

        if remaining_count == 0:
            await self.db.execute(
                delete(RecipeModel).where(RecipeModel.id == recipe_id)
            )

        await self.db.flush()

        return True

    async def delete_all_by_user_id(self, user_id: UUID) -> None:
        result = await self.db.execute(
            delete(saved_recipes)
            .where(saved_recipes.c.user_id == user_id)
            .returning(saved_recipes.c.recipe_id)
        )

        recipe_ids = [row[0] for row in result.all()]

        if recipe_ids:
            still_used = select(saved_recipes.c.recipe_id).where(
                saved_recipes.c.recipe_id.in_(recipe_ids)
            )

            await self.db.execute(
                delete(RecipeModel).where(
                    RecipeModel.id.in_(recipe_ids),
                    RecipeModel.id.not_in(still_used),
                )
            )

        await self.db.flush()

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