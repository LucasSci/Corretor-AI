import base64
import asyncio
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest


with patch("app.db.init_db.init_db", new_callable=AsyncMock):
    from app.main import app
from app.core.config import settings
from app.services.media_storage_service import whatsapp_media_storage_service


@pytest.fixture(autouse=True)
def _reset_allowed_numbers():
    with patch.object(settings, "WHATSAPP_ALLOWED_NUMBERS", ""):
        yield


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


def test_webhook_ignored_not_allowed_number():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5511999999999@s.whatsapp.net"},
            "message": {"conversation": "oi"},
        },
    }

    with patch.object(settings, "WHATSAPP_ALLOWED_NUMBERS", "5521975907217"):
        response = _post_json("/webhook", payload)

    assert response.status_code == 200
    assert response.json()["status"] == "ignored not allowed number"


def test_webhook_allows_brazilian_number_without_country_code():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5521975907217@s.whatsapp.net"},
            "message": {"conversation": "oi"},
        },
    }

    with patch.object(settings, "WHATSAPP_ALLOWED_NUMBERS", "21975907217"):
        with patch("app.api.webhook.ai_service.get_context_from_db", new=AsyncMock(return_value="ctx")):
            with patch("app.api.webhook.ai_service.generate_response", new=AsyncMock(return_value="Resposta mock")):
                with patch("app.api.webhook.whatsapp_service.send_message", new=AsyncMock(return_value={"ok": True})):
                    response = _post_json("/webhook", payload)

    assert response.status_code == 200
    assert response.json()["status"] == "processed"


def test_webhook_processes_admin_command():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5521975907217@s.whatsapp.net"},
            "message": {"conversation": "/ping"},
        },
    }

    with patch.object(settings, "WHATSAPP_COMMAND_NUMBERS", "21975907217"):
        with patch("app.api.webhook.admin_command_service.handle_command", new=AsyncMock(return_value="pong")) as mock_cmd:
            with patch("app.api.webhook.whatsapp_service.send_message", new=AsyncMock(return_value={"ok": True})) as mock_send:
                response = _post_json("/webhook", payload)

    assert response.status_code == 200
    assert response.json()["status"] == "processed command"
    assert response.json()["reply"] == "pong"
    mock_cmd.assert_awaited_once_with("/ping")
    mock_send.assert_awaited_once_with("5521975907217@s.whatsapp.net", "pong")


def test_webhook_ignores_unauthorized_admin_command():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5511999999999@s.whatsapp.net"},
            "message": {"conversation": "/status"},
        },
    }

    with patch.object(settings, "WHATSAPP_ALLOWED_NUMBERS", ""):
        with patch.object(settings, "WHATSAPP_COMMAND_NUMBERS", "21975907217"):
            response = _post_json("/webhook", payload)

    assert response.status_code == 200
    assert response.json()["status"] == "ignored unauthorized command"


def test_webhook_media_only_saves_file_by_type():
    encoded = base64.b64encode(b"conteudo-doc-teste").decode("ascii")
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5511666666666@s.whatsapp.net"},
            "message": {
                "documentMessage": {
                    "fileName": "Contrato Cliente.pdf",
                    "mimetype": "application/pdf",
                    "base64": encoded,
                }
            },
        },
    }

    old_root = whatsapp_media_storage_service.root_dir
    tmp = tempfile.mkdtemp()
    try:
        with patch.object(settings, "WHATSAPP_MEDIA_AUTO_SAVE", True):
            with patch.object(settings, "WHATSAPP_UPLOADS_DIR", tmp):
                whatsapp_media_storage_service.root_dir = Path(tmp)
                with patch("app.api.webhook.whatsapp_service.send_message", new=AsyncMock(return_value={"ok": True})):
                    response = _post_json("/webhook", payload)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "processed media"
        assert len(body["saved_files"]) == 1

        saved_path = Path(body["saved_files"][0])
        assert saved_path.exists()
        assert "document" in str(saved_path)
        assert saved_path.suffix == ".pdf"
        assert saved_path.read_bytes() == b"conteudo-doc-teste"
    finally:
        whatsapp_media_storage_service.root_dir = old_root
        shutil.rmtree(tmp, ignore_errors=True)


def test_webhook_text_plus_media_saves_and_replies():
    encoded = base64.b64encode(b"imagem-fake").decode("ascii")
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"fromMe": False, "remoteJid": "5511555555555@s.whatsapp.net"},
            "message": {
                "conversation": "olha esse arquivo",
                "imageMessage": {
                    "mimetype": "image/jpeg",
                    "base64": encoded,
                },
            },
        },
    }

    old_root = whatsapp_media_storage_service.root_dir
    tmp = tempfile.mkdtemp()
    try:
        with patch.object(settings, "WHATSAPP_MEDIA_AUTO_SAVE", True):
            with patch.object(settings, "WHATSAPP_UPLOADS_DIR", tmp):
                whatsapp_media_storage_service.root_dir = Path(tmp)
                with patch("app.api.webhook.ai_service.get_context_from_db", new=AsyncMock(return_value="ctx")):
                    with patch("app.api.webhook.ai_service.generate_response", new=AsyncMock(return_value="Resposta IA")):
                        with patch("app.api.webhook.whatsapp_service.send_message", new=AsyncMock(return_value={"ok": True})):
                            response = _post_json("/webhook", payload)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "processed"
        assert body["reply"] == "Resposta IA"
        assert len(body.get("saved_files", [])) == 1
        assert Path(body["saved_files"][0]).exists()
    finally:
        whatsapp_media_storage_service.root_dir = old_root
        shutil.rmtree(tmp, ignore_errors=True)
