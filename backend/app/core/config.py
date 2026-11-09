import os


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

SESSION_COOKIE_NAME = "sid"
SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "10080"))
SESSION_COOKIE_SECURE = _get_bool("COOKIE_SECURE", False)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv("GEMINI_MODEL")

GEMINI_APP_RPM_LIMIT = int(
    os.getenv("GEMINI_APP_RPM_LIMIT", "5")
)

# Скільки хвилин "живе" сесія генерації (оновлюється при кожній дії користувача).
GENERATION_SESSION_TTL_MINUTES = int(
    os.getenv("GENERATION_SESSION_TTL_MINUTES", "120")
)

# Максимум варіантів рецептів, які просимо у Gemini за один запит.
MAX_RECIPE_SUGGESTIONS = 16

# Скільки варіантів рецептів повертається на одній сторінці.
SUGGESTIONS_PAGE_SIZE = 8

# Максимальне значення INTEGER-ідентифікатора в PostgreSQL (int32).
MAX_DB_ID = 2_147_483_647

# JWT: токен авторизації.
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
