import asyncio
from unittest.mock import AsyncMock, patch

import httpx


from app.main import app
from app.core.config import settings


def _post_json(path: str, payload: dict) -> httpx.Response:
    async def _run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(_run())


def _post_raw(path: str, content: bytes, content_type: str = "application/json") -> httpx.Response:
    async def _run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, content=content, headers={"Content-Type": content_type})

    return asyncio.run(_run())


def test_webhook_invalid_json():
    response = _post_raw("/webhook", b"{invalid")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON payload"


def test_webhook_ignored_event():
    payload = {"event": "connection.update"}
    response = _post_json("/webhook", payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored event"


def test_webhook_ignored_from_me():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": True, "remoteJid": "5511999999999@s.whatsapp.net"},
            "message": {"conversation": "oi"},
        },
    }
    with patch.object(settings, "ALLOW_FROM_ME_TEST", False):
        response = _post_json("/webhook", payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored fromMe"


def test_webhook_ignored_without_remote_jid():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False},
            "message": {"conversation": "oi"},
        },
    }
    response = _post_json("/webhook", payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored no remoteJid"


def test_webhook_ignored_lid_bypass():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "abc123@lid"},
            "message": {"conversation": "oi"},
        },
    }
    with patch.object(settings, "WHATSAPP_TEST_NUMBER", ""):
        response = _post_json("/webhook", payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored @lid bypass"


def test_webhook_ignored_without_text():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5511999999999@s.whatsapp.net"},
            "message": {},
        },
    }
    response = _post_json("/webhook", payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored no text"


def test_webhook_processed_conversation():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5511999999999@s.whatsapp.net"},
            "message": {"conversation": "tem 2 quartos?"},
        },
    }

    with patch("app.api.webhook.ai_service.get_context_from_db", new=AsyncMock(return_value="contexto mock")) as mock_ctx:
        with patch(
            "app.api.webhook.ai_service.generate_response",
            new=AsyncMock(return_value="Temos sim, vou te mostrar as opcoes."),
        ) as mock_gen:
            with patch("app.api.webhook.whatsapp_service.send_message", new=AsyncMock(return_value={"ok": True})) as mock_send:
                response = _post_json("/webhook", payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["reply"] == "Temos sim, vou te mostrar as opcoes."
    mock_ctx.assert_awaited_once_with("tem 2 quartos?")
    mock_gen.assert_awaited_once_with("tem 2 quartos?", "contexto mock")
    mock_send.assert_awaited_once_with("5511999999999@s.whatsapp.net", "Temos sim, vou te mostrar as opcoes.")


def test_webhook_processed_extended_text_message():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5511888888888@s.whatsapp.net"},
            "message": {"extendedTextMessage": {"text": "qual valor?"}},
        },
    }

    with patch("app.api.webhook.ai_service.get_context_from_db", new=AsyncMock(return_value="ctx")):
        with patch("app.api.webhook.ai_service.generate_response", new=AsyncMock(return_value="Resposta mock")):
            with patch("app.api.webhook.whatsapp_service.send_message", new=AsyncMock(return_value={"ok": True})):
                response = _post_json("/webhook", payload)

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["reply"] == "Resposta mock"


def test_webhook_error_when_ai_fails():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5511777777777@s.whatsapp.net"},
            "message": {"conversation": "oi"},
        },
    }

    with patch("app.api.webhook.ai_service.get_context_from_db", new=AsyncMock(return_value="ctx")):
        with patch("app.api.webhook.ai_service.generate_response", new=AsyncMock(side_effect=RuntimeError("falha"))):
            response = _post_json("/webhook", payload)

    assert response.status_code == 200
    assert response.json()["status"] == "error"
