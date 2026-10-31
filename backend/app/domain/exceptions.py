class DomainError(Exception):
    """Базова помилка доменного рівня."""


class EmailAlreadyExistsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Користувач із таким email уже існує.")


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Невірний email або пароль.")


class InvalidCurrentPasswordError(DomainError):
    def __init__(self) -> None:
        super().__init__("Невірний поточний пароль.")


class InvalidUserNameError(DomainError):
    pass


class InvalidUserPasswordHashError(DomainError):
    pass


class InvalidProductNameError(DomainError):
    pass


class InvalidCategoryNameError(DomainError):
    pass


class InvalidDietaryRestrictionNameError(DomainError):
    pass


class InvalidRecipeTitleError(DomainError):
    pass


class InvalidRecipeDescriptionError(DomainError):
    pass


class InvalidRecipeIngredientsError(DomainError):
    pass


class InvalidRecipeInstructionsError(DomainError):
    pass


class InvalidRecipeCookingTimeError(DomainError):
    pass