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