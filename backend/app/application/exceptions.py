class ProductsNotFoundError(Exception):
    pass


class NoSuitableRecipesError(Exception):
    pass


class AIProviderRateLimitError(Exception):
    pass


class AIProviderUnavailableError(Exception):
    pass


class AIProviderInvalidResponseError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class DietaryRestrictionsNotFoundError(Exception):
    pass


class ProductsViolateRestrictionsError(Exception):
    pass


class ProductNotFoundError(Exception):
    pass



class GenerationNotFoundError(Exception):
    """Сесії немає, її термін дії минув або вона належить іншому користувачу."""


class GenerationRestrictionsNotSelectedError(Exception):
    """Крок вибору дієтичних обмежень ще не пройдено."""


class GenerationSuggestionsNotReadyError(Exception):
    """Варіанти рецептів ще не згенеровані."""


class GenerationStateChangedError(Exception):
    """Під час запиту до ШІ сесія була змінена (наприклад, обмеження)."""


class SuggestionNotFoundError(Exception):
    pass


class SuggestionsPageNotFoundError(Exception):
    pass
