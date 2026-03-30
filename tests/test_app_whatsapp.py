import asyncio
import sys
import types
from unittest.mock import patch

import httpx


fake_bot = types.ModuleType("bot_corretor")


def _fake_gerar_resposta_whatsapp(*args, **kwargs):
    return {"resposta": "Resposta mock", "modelo_usado": "mock-model"}


fake_bot.gerar_resposta_whatsapp = _fake_gerar_resposta_whatsapp
sys.modules["bot_corretor"] = fake_bot

fake_learning = types.ModuleType("learning_system")


class _FakeLearningSystem:
    def process_interaction(self, payload):
        return None


fake_learning.learning_system = _FakeLearningSystem()
sys.modules["learning_system"] = fake_learning

import app.main as app_main  # noqa: E402


def _post_json(path: str, payload: dict) -> httpx.Response:
    async def _run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app_main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)

    return asyncio.run(_run())


def test_whatsapp_webhook_ignored_event():
    response = _post_json("/webhook", {"event": "connection.update"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ignorado"
    assert body["motivo"] == "evento"


def test_whatsapp_webhook_ignored_no_number():
    response = _post_json("/webhook", {"event": "messages.upsert", "data": {}})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ignorado"
    assert body["motivo"] == "numero_nao_encontrado"


def test_whatsapp_webhook_ignored_group_message():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "12345@g.us", "fromMe": False},
            "message": {"conversation": "oi"},
        },
    }
    response = _post_json("/webhook", payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ignorado"
    assert body["motivo"] == "grupo_ou_status"


def test_whatsapp_webhook_processed_success():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "Quero saber o valor"},
        },
    }

    with patch("app_whatsapp.gerar_resposta_whatsapp", return_value={"resposta": "Retorno IA", "modelo_usado": "mock-1"}):
        with patch("app_whatsapp.learning_system.process_interaction") as mock_learning:
            with patch("app_whatsapp.enviar_mensagem_whatsapp", return_value=True) as mock_send:
                response = _post_json("/webhook", payload)

    assert response.status_code == 200
    assert response.json()["status"] == "sucesso"
    mock_learning.assert_called_once()
    mock_send.assert_called_once()
