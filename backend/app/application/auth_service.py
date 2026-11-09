from datetime import datetime, timedelta, timezone

from app.core.config import SESSION_TTL_MINUTES
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    decode_access_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    session_hash_from_token,
    verify_password,
)
from app.domain.entities.session import Session
from app.domain.entities.user import User
from app.domain.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from app.domain.repositories.session_repository import SessionRepository
from app.domain.repositories.user_repository import UserRepository


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, users: UserRepository, sessions: SessionRepository) -> None:
        self.users = users
        self.sessions = sessions

    async def register(self, name: str, email: str, password: str) -> User:
        email = normalize_email(email)

        if await self.users.get_by_email(email) is not None:
            raise EmailAlreadyExistsError()

        user = User(
            email=email,
            password_hash=await hash_password(password),
            name=name.strip(),
        )

        await self.users.save(user)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(normalize_email(email))

        if user is None:
            await verify_password(password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError()

        if not await verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        return user

    async def create_session(self, user: User) -> str:
        await self.sessions.delete_expired()

        session_id = generate_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=SESSION_TTL_MINUTES)

        await self.sessions.save(
            Session(
                token_hash=hash_session_token(session_id),
                user_id=user.id,
                expires_at=expires_at,
            )
        )

        return create_access_token(user.id, session_id, expires_at)

    async def get_user_by_session(self, token: str) -> User | None:
        claims = decode_access_token(token)

        if claims is None:
            return None

        token_hash = hash_session_token(claims["jti"])
        session = await self.sessions.get_by_token_hash(token_hash)

        if session is None or str(session.user_id) != claims["sub"]:
            return None

        if session.is_expired():
            await self.sessions.delete_by_token_hash(token_hash)
            return None

        return await self.users.get_by_id(session.user_id)

    async def logout(self, token: str) -> None:
        token_hash = session_hash_from_token(token)

        if token_hash is not None:
            await self.sessions.delete_by_token_hash(token_hash)
