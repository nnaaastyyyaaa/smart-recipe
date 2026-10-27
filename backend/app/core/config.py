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