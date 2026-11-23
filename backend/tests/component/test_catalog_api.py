"""Компонентні тести каталогу: категорії, продукти, обмеження, пошук, пагінація."""
import pytest

from app.infrastructure.database.models import CategoryModel, ProductModel
from tests.helpers import API, req


def ids(items):
    return [item["id"] for item in items]


def names(items):
    return {item["name"] for item in items}

@req("FR-B3")
async def test_list_categories(authed, catalog):
    response = await authed.get(f"{API}/categories")

    assert response.status_code == 200
    assert names(response.json()) == {"Овочі", "М'ясо", "Молочні продукти", "Крупи та борошно"}
    assert all(set(c) == {"id", "name"} for c in response.json())


async def test_get_category(authed, catalog):
    response = await authed.get(f"{API}/categories/{catalog.categories['veg']}")

    assert response.status_code == 200 and response.json()["name"] == "Овочі"


async def test_get_missing_category_returns_404(authed, catalog):
    response = await authed.get(f"{API}/categories/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Категорія не знайдена."

@req("FR-B1")
async def test_list_dietary_restrictions(authed, catalog):
    response = await authed.get(f"{API}/dietary-restrictions")

    assert response.status_code == 200
    assert names(response.json()) == {"Веганське", "Без глютену", "Безлактозне"}


async def test_get_dietary_restriction_and_missing(authed, catalog):
    ok = await authed.get(f"{API}/dietary-restrictions/{catalog.restrictions['vegan']}")
    missing = await authed.get(f"{API}/dietary-restrictions/99999")

    assert ok.status_code == 200 and ok.json()["name"] == "Веганське"
    assert missing.status_code == 404

@req("FR-B3")
async def test_list_all_products(authed, catalog):
    response = await authed.get(f"{API}/products")

    assert response.status_code == 200
    assert len(response.json()) == 11
    assert all(set(p) == {"id", "name", "category_id"} for p in response.json())


@req("FR-B3")
async def test_filter_products_by_category(authed, catalog):
    response = await authed.get(f"{API}/products", params={"category_id": catalog.categories["veg"]})

    assert names(response.json()) == {"Помідор", "Огірок", "Морква", "Картопля"}
    assert {p["category_id"] for p in response.json()} == {catalog.categories["veg"]}


async def test_products_of_unknown_category_returns_404(authed, catalog):
    response = await authed.get(f"{API}/products", params={"category_id": 99999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Категорія не знайдена."


@req("FR-B3")
@pytest.mark.parametrize("term", ["Молоко", "молоко", "МОЛОКО", "мол", "олок"])
async def test_search_is_case_insensitive_for_common_inputs(authed, catalog, term):
    response = await authed.get(f"{API}/products", params={"search": term})

    assert names(response.json()) == {"Молоко"}


@req("FR-B3")
async def test_search_combined_with_category(authed, catalog):
    response = await authed.get(
        f"{API}/products", params={"search": "о", "category_id": catalog.categories["dairy"]}
    )

    assert names(response.json()) == {"Молоко"}


@pytest.mark.parametrize("term", ["%", "_", "\\", "'; DROP TABLE products;--"])
async def test_search_treats_special_characters_literally(authed, catalog, term):
    response = await authed.get(f"{API}/products", params={"search": term})

    assert response.status_code == 200
    assert response.json() == []
    assert len((await authed.get(f"{API}/products")).json()) == 11 


async def test_search_with_no_match_returns_empty_list(authed, catalog):
    assert (await authed.get(f"{API}/products", params={"search": "Ананас"})).json() == []


@req("FR-B5")
async def test_products_are_paginated_without_gaps_or_overlap(authed, session_factory, catalog):
    async with session_factory() as session:
        category_id = catalog.categories["veg"]
        session.add_all([ProductModel(name=f"Тест {i:02d}", category_id=category_id) for i in range(30)])
        await session.commit()

    full = (await authed.get(f"{API}/products", params={"limit": 200})).json()
    page1 = (await authed.get(f"{API}/products", params={"limit": 12, "offset": 0})).json()
    page2 = (await authed.get(f"{API}/products", params={"limit": 12, "offset": 12})).json()
    page3 = (await authed.get(f"{API}/products", params={"limit": 12, "offset": 24})).json()
    page4 = (await authed.get(f"{API}/products", params={"limit": 12, "offset": 36})).json()

    assert len(full) == 41
    assert [len(page1), len(page2), len(page3), len(page4)] == [12, 12, 12, 5]
    assert ids(page1) + ids(page2) + ids(page3) + ids(page4) == ids(full) 


@req("FR-B5")
async def test_default_page_size_is_50(authed, session_factory, catalog):
    async with session_factory() as session:
        session.add_all([ProductModel(name=f"Багато {i:03d}", category_id=catalog.categories["veg"]) for i in range(60)])
        await session.commit()

    assert len((await authed.get(f"{API}/products")).json()) == 50


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 201}, {"limit": -1}, {"offset": -1}, {"category_id": 0}, {"category_id": -3}, {"search": ""}, {"search": "я" * 61}],
)
async def test_products_query_validation(authed, catalog, params):
    assert (await authed.get(f"{API}/products", params=params)).status_code == 422


@req("FR-B2")
async def test_products_filtered_by_one_restriction(authed, catalog):
    response = await authed.get(f"{API}/products", params={"restriction_ids": [catalog.restrictions["vegan"]]})

    assert names(response.json()) == {"Помідор", "Огірок", "Морква", "Картопля", "Рис", "Борошно", "Макарони"}


@req("FR-B2")
async def test_products_filtered_by_several_restrictions(authed, catalog):
    response = await authed.get(
        f"{API}/products",
        params={"restriction_ids": [catalog.restrictions["vegan"], catalog.restrictions["gluten"]]},
    )

    assert names(response.json()) == {"Помідор", "Огірок", "Морква", "Картопля", "Рис"}


@req("FR-B2")
async def test_restriction_filter_combines_with_category_and_search(authed, catalog):
    response = await authed.get(
        f"{API}/products",
        params={"restriction_ids": [catalog.restrictions["lactose"]], "category_id": catalog.categories["dairy"]},
    )

    assert response.json() == [] 


async def test_unknown_restriction_in_filter_returns_404(authed, catalog):
    response = await authed.get(f"{API}/products", params={"restriction_ids": [catalog.restrictions["vegan"], 99999]})

    assert response.status_code == 404
    assert response.json()["detail"] == "Одне або декілька дієтичних обмежень не знайдені."


async def test_duplicate_restriction_ids_in_filter_are_tolerated(authed, catalog):
    vegan = catalog.restrictions["vegan"]

    response = await authed.get(f"{API}/products", params={"restriction_ids": [vegan, vegan]})

    assert response.status_code == 200 and len(response.json()) == 7


async def test_get_product_and_missing(authed, catalog):
    ok = await authed.get(f"{API}/products/{catalog.products['milk']}")
    missing = await authed.get(f"{API}/products/99999")

    assert ok.status_code == 200 and ok.json()["name"] == "Молоко"
    assert missing.status_code == 404 and missing.json()["detail"] == "Продукт не знайдено."


@req("FR-B2")
async def test_product_restrictions_list(authed, catalog):
    milk = await authed.get(f"{API}/products/{catalog.products['milk']}/restrictions")
    tomato = await authed.get(f"{API}/products/{catalog.products['tomato']}/restrictions")

    assert names(milk.json()) == {"Веганське", "Безлактозне"}
    assert tomato.json() == []


async def test_restrictions_of_missing_product_returns_404(authed, catalog):
    assert (await authed.get(f"{API}/products/99999/restrictions")).status_code == 404

@pytest.mark.parametrize(
    "path,params",
    [
        ("/products/99999999999", None),
        ("/categories/99999999999", None),
        ("/dietary-restrictions/99999999999", None),
        ("/products/99999999999/restrictions", None),
        ("/products", {"category_id": 99999999999}),
        ("/products", {"restriction_ids": [99999999999]}),
        ("/products", {"offset": 99999999999999999999}),
        ("/recipes/saved/99999999999", None),
    ],
)
async def test_huge_identifiers_never_cause_server_error(authed, catalog, path, params):
    response = await authed.get(f"{API}{path}", params=params)

    assert response.status_code in (404, 422)
