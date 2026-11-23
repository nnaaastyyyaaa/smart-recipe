"""Системні тести нефункціональних вимог: ліміт Gemini, мова промптів, продуктивність."""
import asyncio
import re
import time
from types import SimpleNamespace

import pytest

from app.infrastructure.ai import rate_limiter as rate_limiter_module
from app.infrastructure.ai.gemini_recipe_generator import GeminiRecipeGenerator
from app.infrastructure.ai.rate_limiter import InMemoryGeminiRateLimiter
from google.genai import errors
from tests.helpers import API, PERF, register, req, set_restrictions, start_generation


class ScriptedGemini:
    """Імітує відповіді Gemini на рівні клієнта SDK (справжній GeminiRecipeGenerator поверх нього)."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.error: Exception | None = None

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        prompt = kwargs["contents"]

        if "Користувач обрав рецепт" in prompt:
            text = (
                '{"title": "Страва", "description": "Опис", "ingredients": "Продукт — 100 г",'
                ' "instructions": "1. Приготувати", "cooking_time": 15}'
            )
        else:
            ids = [int(i) for i in re.findall(r"ID: (\d+)", prompt)]
            recipes = ",".join(
                f'{{"title": "Страва {n}", "description": "Опис", "cooking_time": 10, "used_product_ids": {ids[:2]}}}'
                for n in range(1, 4)
            )
            text = f'{{"recipes": [{recipes}]}}'

        return SimpleNamespace(parsed=None, text=text)


@pytest.fixture
def real_generator(api_app):
    """Підміняє підроблений ШІ на справжній адаптер із RPM=2 та скриптованим клієнтом SDK."""
    models = ScriptedGemini()
    generator = GeminiRecipeGenerator("k", "m", InMemoryGeminiRateLimiter(requests_per_minute=2))
    generator.aio = SimpleNamespace(models=models)
    api_app.state.recipe_generator = generator
    return generator, models


async def basket(client, catalog):
    generation_id = await start_generation(client)
    await set_restrictions(client, generation_id, [catalog.restrictions["vegan"]])
    return generation_id, catalog.ids("tomato", "carrot")

@req("NFR-4")
async def test_exceeding_rpm_returns_429_with_retry_after_and_ukrainian_message(authed, catalog, real_generator):
    generation_id, products = await basket(authed, catalog)
    url = f"{API}/generations/{generation_id}/suggestions"

    first = await authed.post(url, json={"product_ids": products})
    second = await authed.post(url, json={"product_ids": products})
    third = await authed.post(url, json={"product_ids": products})

    assert (first.status_code, second.status_code) == (200, 200)
    assert third.status_code == 429
    assert 1 <= int(third.headers["retry-after"]) <= 61
    assert third.json()["detail"]["code"] == "AI_REQUEST_LIMIT_REACHED"
    assert "Спробуйте ще раз" in third.json()["detail"]["message"]
    assert len(real_generator[1].calls) == 2 


@req("NFR-4")
async def test_service_recovers_after_rpm_window_passes(authed, catalog, real_generator, monkeypatch):
    clock = {"now": 5000.0}
    monkeypatch.setattr(rate_limiter_module.time, "monotonic", lambda: clock["now"])
    generation_id, products = await basket(authed, catalog)
    url = f"{API}/generations/{generation_id}/suggestions"

    await authed.post(url, json={"product_ids": products})
    await authed.post(url, json={"product_ids": products})
    assert (await authed.post(url, json={"product_ids": products})).status_code == 429

    clock["now"] += 61

    assert (await authed.post(url, json={"product_ids": products})).status_code == 200


@req("NFR-4")
async def test_rpm_limit_is_shared_by_all_users(client_factory, catalog, real_generator):
    results = []

    for index in range(3):
        client = client_factory()
        await register(client)
        generation_id, products = await basket(client, catalog)
        response = await client.post(f"{API}/generations/{generation_id}/suggestions", json={"product_ids": products})
        results.append(response.status_code)

    assert results == [200, 200, 429] 


@req("NFR-4")
async def test_gemini_quota_error_is_reported_as_temporary_unavailability(authed, catalog, real_generator):
    _, models = real_generator
    models.error = errors.ClientError(429, {"error": {"message": "quota exceeded"}})
    generation_id, products = await basket(authed, catalog)

    response = await authed.post(f"{API}/generations/{generation_id}/suggestions", json={"product_ids": products})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AI_PROVIDER_LIMIT_REACHED"
    assert "спробуйте пізніше" in response.json()["detail"]["message"].lower()


async def test_gemini_outage_does_not_break_other_endpoints(authed, catalog, real_generator):
    real_generator[1].error = errors.ServerError(503, {"error": {"message": "down"}})
    generation_id, products = await basket(authed, catalog)

    failed = await authed.post(f"{API}/generations/{generation_id}/suggestions", json={"product_ids": products})

    assert failed.status_code == 503
    assert (await authed.get(f"{API}/products")).status_code == 200
    assert (await authed.get(f"{API}/auth/me")).status_code == 200


@req("NFR-5", "FR-G1")
async def test_every_prompt_sent_to_gemini_demands_ukrainian_and_contains_restrictions(authed, catalog, real_generator):
    _, models = real_generator
    generation_id, products = await basket(authed, catalog)
    url = f"{API}/generations/{generation_id}"

    page = (await authed.post(f"{url}/suggestions", json={"product_ids": products})).json()
    await authed.post(f"{url}/recipe", json={"suggestion_id": page["items"][0]["id"]})

    assert len(models.calls) == 2
    for call in models.calls:
        assert "українською" in call["config"].system_instruction
        assert "українською мовою" in call["contents"]
        assert "Веганське" in call["contents"]


@req("NFR-5", "FR-G6")
async def test_full_recipe_through_real_adapter(authed, catalog, real_generator):
    generation_id, products = await basket(authed, catalog)
    url = f"{API}/generations/{generation_id}"
    await authed.post(f"{url}/suggestions", json={"product_ids": products})

    response = await authed.post(f"{url}/recipe", json={"suggestion_id": 0})

    assert response.status_code == 200
    assert response.json()["cooking_time"] == 15 and response.json()["instructions"]


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered) * 0.95) - 1)]


@pytest.mark.performance
@req("NFR-1")
async def test_catalog_page_response_time(authed, catalog):
    timings = []

    for _ in range(40):
        started = time.perf_counter()
        response = await authed.get(f"{API}/products", params={"limit": 12})
        timings.append((time.perf_counter() - started) * 1000)
        assert response.status_code == 200

    PERF["catalog_page_p95_ms"] = round(p95(timings), 1)
    PERF["catalog_page_avg_ms"] = round(sum(timings) / len(timings), 1)
    assert p95(timings) < 500, f"p95={p95(timings):.0f} мс"


@pytest.mark.performance
@req("NFR-1")
async def test_registration_with_password_hashing_time(client):
    started = time.perf_counter()
    response = await client.post(f"{API}/auth/register", json={"name": "Anna", "email": "perf@example.com", "password": "Passw0rd!"})
    elapsed = (time.perf_counter() - started) * 1000

    PERF["registration_ms"] = round(elapsed, 1)
    assert response.status_code == 201 and elapsed < 2000


@pytest.mark.performance
@req("NFR-1")
async def test_generation_flow_overhead_without_real_ai(authed, catalog, fake_ai):
    started = time.perf_counter()
    generation_id = await start_generation(authed)
    await set_restrictions(authed, generation_id, [catalog.restrictions["vegan"]])
    await authed.get(f"{API}/generations/{generation_id}/products", params={"limit": 12})
    page = (await authed.post(
        f"{API}/generations/{generation_id}/suggestions", json={"product_ids": catalog.ids("tomato", "carrot")}
    )).json()
    await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": page["items"][0]["id"]})
    elapsed = (time.perf_counter() - started) * 1000

    PERF["generation_flow_overhead_ms"] = round(elapsed, 1)
    assert elapsed < 2000, "власні витрати бекенду (без очікування ШІ) мають бути малими"


@pytest.mark.performance
@req("NFR-1")
async def test_server_handles_concurrent_requests(authed, catalog):
    started = time.perf_counter()
    responses = await asyncio.gather(*(authed.get(f"{API}/products", params={"limit": 12}) for _ in range(30)))
    elapsed = (time.perf_counter() - started) * 1000

    PERF["concurrent_30_requests_ms"] = round(elapsed, 1)
    assert all(r.status_code == 200 for r in responses)
    assert elapsed < 5000


@req("NFR-1")
async def test_concurrent_generations_by_different_users_are_independent(client_factory, catalog, fake_ai):
    async def run(index: int):
        client = client_factory()
        await register(client)
        generation_id = await start_generation(client)
        await set_restrictions(client, generation_id, [])
        response = await client.post(
            f"{API}/generations/{generation_id}/suggestions",
            json={"product_ids": catalog.ids("tomato", "carrot")},
        )
        return response.status_code, response.json()["total"]

    results = await asyncio.gather(*(run(i) for i in range(6)))

    assert all(status == 200 and total == 10 for status, total in results)
