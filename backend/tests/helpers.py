from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import httpx
import pytest

API = "/api"
PASSWORD = "Passw0rd!"

_counter = itertools.count(1)


def req(*requirement_ids: str):
    return pytest.mark.req(*requirement_ids)


def user_payload(**overrides) -> dict:
    n = next(_counter)
    payload = {
        "name": f"User{n}",
        "email": f"user{n}@example.com",
        "password": PASSWORD,
    }
    payload.update(overrides)
    return payload


async def register(client: httpx.AsyncClient, **overrides) -> dict:
    payload = user_payload(**overrides)
    response = await client.post(f"{API}/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return {**response.json(), "password": payload["password"]}


async def start_generation(client: httpx.AsyncClient) -> str:
    response = await client.post(f"{API}/generations")
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def set_restrictions(client, generation_id: str, restriction_ids: list[int]):
    return await client.put(
        f"{API}/generations/{generation_id}/restrictions",
        json={"restriction_ids": restriction_ids},
    )


@dataclass
class Catalog:
    categories: dict[str, int] = field(default_factory=dict)
    restrictions: dict[str, int] = field(default_factory=dict)
    products: dict[str, int] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)

    def ids(self, *keys: str) -> list[int]:
        return [self.products[key] for key in keys]


PERF: dict[str, float] = {}
