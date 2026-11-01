from app.application.auth_service import normalize_email
from app.core.security import (
    hash_password,
    hash_session_token,
    verify_password,
)
from app.domain.entities.user import User
from app.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCurrentPasswordError,
)
from app.domain.repositories.saved_recipe_repository import SavedRecipeRepository
from app.domain.repositories.session_repository import SessionRepository
from app.domain.repositories.user_repository import UserRepository


class UserService:

    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        saved_recipes: SavedRecipeRepository,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.saved_recipes = saved_recipes

    async def update_profile(
        self,
        user: User,
        name: str | None,
        email: str | None,
    ) -> User:

        if email is not None:
            email = normalize_email(email)

            if email != user.email:
                existing = await self.users.get_by_email(email)

                if existing is not None and existing.id != user.id:
                    raise EmailAlreadyExistsError()

        if name is not None:
            user.rename(name)

        if email is not None:
            user.change_email(email)

        await self.users.save(user)

        return user

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        current_session_token: str | None,
    ) -> None:

        if not await verify_password(current_password, user.password_hash):
            raise InvalidCurrentPasswordError()

        user.update_password_hash(await hash_password(new_password))
        await self.users.save(user)

        except_token_hash = (
            hash_session_token(current_session_token)
            if current_session_token
            else None
        )

        await self.sessions.delete_all_by_user_id(
            user.id,
            except_token_hash=except_token_hash,
        )

    async def delete_account(self, user: User) -> None:
        await self.saved_recipes.delete_all_by_user_id(user.id)
        await self.sessions.delete_all_by_user_id(user.id)
        await self.users.delete(user.id)
