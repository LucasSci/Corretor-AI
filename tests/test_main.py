import asyncio
from unittest.mock import AsyncMock, patch

import httpx

from app.main import app


def _post(path: str, payload: dict) -> httpx.Response:
    async def _run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(_run())


def test_health():
    async def _run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/health")

    response = asyncio.run(_run())
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_root():
    async def _run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/")

    response = asyncio.run(_run())
    assert response.status_code == 200
    assert response.json()["status"] == "running"
