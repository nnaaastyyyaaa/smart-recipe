"""Компонентні тести репозиторіїв SQLAlchemy на реальному PostgreSQL."""
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.recipe import Recipe
from app.domain.entities.session import Session
from app.domain.entities.user import User
from app.infrastructure.database.repositories.category_repository import SQLAlchemyCategoryRepository
from app.infrastructure.database.repositories.dietary_restriction_repository import (
    SQLAlchemyDietaryRestrictionRepository,
)
from app.infrastructure.database.repositories.product_repository import SQLAlchemyProductRepository
from app.infrastructure.database.repositories.recipe_repository import SQLAlchemyRecipeRepository
from app.infrastructure.database.repositories.saved_recipe_repository import SQLAlchemySavedRecipeRepository
from app.infrastructure.database.repositories.session_repository import SqlAlchemySessionRepository
from app.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from tests.helpers import req


def make_user(email="a@example.com", name="Anna") -> User:
    return User(email=email, password_hash="hash", name=name)


def make_recipe(title="Омлет") -> Recipe:
    return Recipe(title=title, description="d", ingredients="i", instructions="s", cooking_time=5)



async def test_user_save_get_update_delete(db):
    repo = SqlAlchemyUserRepository(db)
    user = make_user()

    await repo.save(user)
    assert (await repo.get_by_id(user.id)).email == "a@example.com"
    assert (await repo.get_by_email("a@example.com")).id == user.id
    assert await repo.get_by_email("missing@example.com") is None

    user.rename("Olena")
    user.change_email("new@example.com")
    await repo.save(user)
    reloaded = await repo.get_by_id(user.id)
    assert (reloaded.name, reloaded.email) == ("Olena", "new@example.com")

    await repo.delete(user.id)
    assert await repo.get_by_id(user.id) is None


@req("FR-A3")
async def test_database_enforces_unique_email(db):
    from app.domain.exceptions import EmailAlreadyExistsError

    repo = SqlAlchemyUserRepository(db)
    await repo.save(make_user("same@example.com"))
    with pytest.raises(EmailAlreadyExistsError):
        await repo.save(make_user("same@example.com", "Other"))



async def test_session_lifecycle_and_cascade_on_user_delete(db):
    from datetime import datetime, timedelta, timezone

    users, sessions = SqlAlchemyUserRepository(db), SqlAlchemySessionRepository(db)
    user = make_user()
    await users.save(user)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    await sessions.save(Session("hash-1", user.id, expires))
    await sessions.save(Session("hash-2", user.id, expires))

    stored = await sessions.get_by_token_hash("hash-1")
    assert stored.user_id == user.id and not stored.is_expired()

    await sessions.delete_by_token_hash("hash-1")
    assert await sessions.get_by_token_hash("hash-1") is None

    await sessions.save(Session("hash-3", user.id, expires))
    await sessions.delete_all_by_user_id(user.id, except_token_hash="hash-3")
    assert await sessions.get_by_token_hash("hash-2") is None
    assert await sessions.get_by_token_hash("hash-3") is not None

    await users.delete(user.id)
    await db.flush()
    db.expire_all()
    assert await sessions.get_by_token_hash("hash-3") is None 


async def test_session_requires_existing_user(db):
    from datetime import datetime, timedelta, timezone

    sessions = SqlAlchemySessionRepository(db)

    with pytest.raises(IntegrityError):
        await sessions.save(Session("orphan", uuid4(), datetime.now(timezone.utc) + timedelta(hours=1)))



async def test_category_and_restriction_repositories(db, catalog):
    categories = SQLAlchemyCategoryRepository(db)
    restrictions = SQLAlchemyDietaryRestrictionRepository(db)

    assert (await categories.get_by_name("  Овочі ")).id == catalog.categories["veg"]
    assert await categories.get_by_name("Немає") is None
    assert len(await categories.get_all()) == 4

    assert (await restrictions.get_by_name("Веганське")).id == catalog.restrictions["vegan"]
    assert await restrictions.get_by_name("Немає такого") is None
    assert await restrictions.get_by_id(99999) is None
    found = await restrictions.get_by_ids([catalog.restrictions["vegan"], 99999])
    assert [r.name for r in found] == ["Веганське"]
    assert len(await restrictions.get_all()) == 3


@req("FR-B2")
async def test_product_repository_excludes_by_restrictions(db, catalog):
    repo = SQLAlchemyProductRepository(db)
    vegan, gluten, lactose = (catalog.restrictions[k] for k in ("vegan", "gluten", "lactose"))

    async def names(*ids):
        return {p.name for p in await repo.get_all(limit=100, exclude_restriction_ids=list(ids))}

    assert len(await names()) == 11
    assert await names(vegan) == {"Помідор", "Огірок", "Морква", "Картопля", "Рис", "Борошно", "Макарони"}
    assert await names(gluten) == {"Помідор", "Огірок", "Морква", "Картопля", "Рис", "Куряче філе", "Яловичина", "Молоко", "Сир"}
    assert await names(vegan, gluten, lactose) == {"Помідор", "Огірок", "Морква", "Картопля", "Рис"}


@req("FR-B2")
async def test_product_get_by_ids_respects_restrictions(db, catalog):
    repo = SQLAlchemyProductRepository(db)
    ids = catalog.ids("tomato", "milk", "flour")

    assert len(await repo.get_by_ids(ids)) == 3
    allowed = await repo.get_by_ids(ids, exclude_restriction_ids=[catalog.restrictions["vegan"]])
    assert {p.name for p in allowed} == {"Помідор", "Борошно"}
    assert await repo.get_by_ids([]) == []


async def test_product_restrictions_are_sorted_by_name(db, catalog):
    repo = SQLAlchemyProductRepository(db)

    restrictions = await repo.get_restrictions(catalog.products["milk"])

    assert [r.name for r in restrictions] == sorted(r.name for r in restrictions)
    assert {r.name for r in restrictions} == {"Веганське", "Безлактозне"}


async def test_product_search_and_pagination_in_repository(db, catalog):
    repo = SQLAlchemyProductRepository(db)

    assert [p.name for p in await repo.get_all(search="сир")] == ["Сир"]
    assert [p.name for p in await repo.get_all(category_id=catalog.categories["grains"], limit=2)] != []
    assert await repo.get_all(limit=5, offset=100) == []
    assert (await repo.get_by_id(catalog.products["rice"])).name == "Рис"
    assert await repo.get_by_id(99999) is None


async def test_catalog_names_are_unique(db, catalog, session_factory):
    from app.infrastructure.database.models import ProductModel

    async with session_factory() as other:
        other.add(ProductModel(name="Помідор", category_id=catalog.categories["veg"]))

        with pytest.raises(IntegrityError):
            await other.commit()

@req("FR-S1", "FR-A12")
async def test_saved_recipe_repository_basic_flow(db):
    users = SqlAlchemyUserRepository(db)
    recipes, saved = SQLAlchemyRecipeRepository(db), SQLAlchemySavedRecipeRepository(db)
    user = make_user()
    await users.save(user)

    recipe = await recipes.save(make_recipe("Бета"))
    other = await recipes.save(make_recipe("Альфа"))
    assert await saved.save(user.id, recipe.id) is True
    assert await saved.save(user.id, other.id) is True
    assert await saved.save(user.id, recipe.id) is False 

    assert [r.title for r in await saved.get_all_by_user_id(user.id)] == ["Альфа", "Бета"]
    assert (await saved.get_by_id(user.id, recipe.id)).title == "Бета"
    assert await saved.get_by_id(uuid4(), recipe.id) is None
    assert (await recipes.get_by_id(recipe.id)).title == "Бета"


async def test_recipe_is_deleted_only_when_last_link_is_removed(db):
    users = SqlAlchemyUserRepository(db)
    recipes, saved = SQLAlchemyRecipeRepository(db), SQLAlchemySavedRecipeRepository(db)
    first, second = make_user("a@example.com"), make_user("b@example.com", "Bob")
    await users.save(first)
    await users.save(second)
    recipe = await recipes.save(make_recipe())
    await saved.save(first.id, recipe.id)
    await saved.save(second.id, recipe.id)

    assert await saved.delete(first.id, recipe.id) is True
    assert await recipes.get_by_id(recipe.id) is not None 

    assert await saved.delete(second.id, recipe.id) is True
    assert await recipes.get_by_id(recipe.id) is None

    assert await saved.delete(second.id, recipe.id) is False


async def test_delete_all_keeps_recipes_shared_with_other_users(db):
    users = SqlAlchemyUserRepository(db)
    recipes, saved = SQLAlchemyRecipeRepository(db), SQLAlchemySavedRecipeRepository(db)
    first, second = make_user("a@example.com"), make_user("b@example.com", "Bob")
    await users.save(first)
    await users.save(second)
    shared, private = await recipes.save(make_recipe("Спільний")), await recipes.save(make_recipe("Приватний"))
    await saved.save(first.id, shared.id)
    await saved.save(second.id, shared.id)
    await saved.save(first.id, private.id)

    await saved.delete_all_by_user_id(first.id)

    assert await recipes.get_by_id(private.id) is None
    assert await recipes.get_by_id(shared.id) is not None
    assert await saved.get_all_by_user_id(first.id) == []
    assert len(await saved.get_all_by_user_id(second.id)) == 1


async def test_database_rejects_non_positive_cooking_time(db):
    from sqlalchemy import text

    with pytest.raises(IntegrityError):
        await db.execute(text(
            "INSERT INTO recipes (title, description, ingredients, instructions, cooking_time) "
            "VALUES ('t','d','i','s',0)"
        ))


@req("NFR-1")
async def test_check_database_connection_succeeds_against_real_database(db_engine):
    from app.infrastructure.database.database import check_database_connection

    await check_database_connection()


@req("FR-B2")
async def test_product_repository_category_ids_respect_restrictions(db, catalog):
    repo = SQLAlchemyProductRepository(db)
    vegan, gluten = catalog.restrictions["vegan"], catalog.restrictions["gluten"]
    veg, meat, dairy, grains = (catalog.categories[k] for k in ("veg", "meat", "dairy", "grains"))

    assert set(await repo.get_category_ids()) == {veg, meat, dairy, grains}
    assert set(await repo.get_category_ids([])) == {veg, meat, dairy, grains}
    assert set(await repo.get_category_ids([vegan])) == {veg, grains}
    assert set(await repo.get_category_ids([gluten])) == {veg, meat, dairy, grains} 
    assert len(await repo.get_category_ids([vegan])) == 2 


@req("FR-A13")
async def test_saved_recipe_repository_limit_offset_and_count(db):
    users = SqlAlchemyUserRepository(db)
    recipes, saved = SQLAlchemyRecipeRepository(db), SQLAlchemySavedRecipeRepository(db)
    user, other = make_user("a@example.com"), make_user("b@example.com", "Bob")
    await users.save(user)
    await users.save(other)

    for index in range(7):
        recipe = await recipes.save(make_recipe(f"Рецепт {index}"))
        await saved.save(user.id, recipe.id)
    await saved.save(other.id, (await recipes.save(make_recipe("Чужий"))).id)

    assert await saved.count_by_user_id(user.id) == 7
    assert await saved.count_by_user_id(other.id) == 1
    assert await saved.count_by_user_id(uuid4()) == 0
    assert [r.title for r in await saved.get_all_by_user_id(user.id, limit=3, offset=0)] == ["Рецепт 0", "Рецепт 1", "Рецепт 2"]
    assert [r.title for r in await saved.get_all_by_user_id(user.id, limit=3, offset=6)] == ["Рецепт 6"]
    assert len(await saved.get_all_by_user_id(user.id)) == 7
    assert len(await saved.get_all_by_user_id(user.id, offset=5)) == 2


@req("NFR-3")
async def test_session_repository_deletes_only_expired_sessions(db):
    from datetime import datetime, timedelta, timezone

    users, sessions = SqlAlchemyUserRepository(db), SqlAlchemySessionRepository(db)
    user = make_user()
    await users.save(user)
    now = datetime.now(timezone.utc)
    await sessions.save(Session("old", user.id, now - timedelta(minutes=1)))
    await sessions.save(Session("fresh", user.id, now + timedelta(hours=1)))

    await sessions.delete_expired()

    assert await sessions.get_by_token_hash("old") is None
    assert await sessions.get_by_token_hash("fresh") is not None
