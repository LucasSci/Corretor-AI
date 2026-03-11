import asyncio
from unittest.mock import AsyncMock, patch

import httpx


import app.db.init_db

with patch("app.db.init_db.init_db", new_callable=AsyncMock):
    from app.main import app


def _post(path: str, payload: dict) -> httpx.Response:
    async def _run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(_run())


def test_chat_valid_input():
    with patch("app.services.ai_service.AIService.generate_response", new=AsyncMock(return_value="Mocked response")):
        with patch("app.services.ai_service.AIService.get_context_from_db", new=AsyncMock(return_value="Mock context")):
            response = _post("/chat", {"contact_id": "user123", "text": "hello"})

    assert response.status_code == 200
    assert response.json()["contact_id"] == "user123"


def test_chat_invalid_contact_id():
    response = _post("/chat", {"contact_id": "a" * 81, "text": "hello"})
    assert response.status_code == 422


def test_chat_invalid_text():
    response = _post("/chat", {"contact_id": "user123", "text": "a" * 1001})
    assert response.status_code == 422
