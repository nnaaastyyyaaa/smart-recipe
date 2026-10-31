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
