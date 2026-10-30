from dataclasses import dataclass

from app.domain.exceptions import (
    InvalidRecipeTitleError,
    InvalidRecipeDescriptionError,
    InvalidRecipeIngredientsError,
    InvalidRecipeInstructionsError,
    InvalidRecipeCookingTimeError
)


@dataclass
class Recipe:
    title: str
    description: str
    ingredients: str
    instructions: str
    cooking_time: int
    id: int | None = None

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.ingredients = self.ingredients.strip()
        self.instructions = self.instructions.strip()

        self.validate()

    def validate(self) -> None:
        if not self.title:
            raise InvalidRecipeTitleError(
                "Назва рецепта не може бути порожньою."
            )

        if len(self.title) > 80:
            raise InvalidRecipeTitleError(
                "Назва рецепта не може перевищувати 80 символів."
            )

        if not self.description:
            raise InvalidRecipeDescriptionError(
                "Опис рецепта не може бути порожнім."
            )

        if not self.ingredients:
            raise InvalidRecipeIngredientsError(
                "Список інгредієнтів не може бути порожнім."
            )

        if not self.instructions:
            raise InvalidRecipeInstructionsError(
                "Інструкція приготування не може бути порожньою."
            )

        if self.cooking_time <= 0:
            raise InvalidRecipeCookingTimeError(
                "Час приготування має бути більшим за 0."
            )