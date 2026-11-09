import asyncio
import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

import bcrypt
import jwt

from app.core.config import JWT_ALGORITHM, JWT_SECRET


def _hash_password_sync(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

DUMMY_PASSWORD_HASH = _hash_password_sync("dummy-password-for-timing")


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash_password_sync, password)


async def verify_password(password: str, password_hash: str) -> bool:
    try:
        return await asyncio.to_thread(
            bcrypt.checkpw,
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: UUID, session_id: str, expires_at: datetime) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": session_id,
            "iat": datetime.now(timezone.utc),
            "exp": expires_at,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub", "jti"]},
        )
    except jwt.PyJWTError:
        return None


def session_hash_from_token(token: str) -> str | None:
    claims = decode_access_token(token)

    if claims is None:
        return None

    return hash_session_token(claims["jti"])
