import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self):
        self.reload_from_settings()

    def reload_from_settings(self) -> None:
        self.base_url = settings.URL_EVOLUTION.rstrip("/") if settings.URL_EVOLUTION else ""
        self.api_key = settings.API_KEY_EVOLUTION
        self.instance = settings.EVOLUTION_INSTANCE

    @staticmethod
    def _normalize_remote_jid(remote_jid: str) -> str:
        if not remote_jid:
            return ""
        if "@" in remote_jid:
            return remote_jid.split("@", 1)[0]
        return remote_jid

    async def send_message(self, remote_jid: str, text: str) -> Dict[str, Any]:
        if not self.base_url or not self.api_key:
            logger.warning("Credenciais da Evolution API ausentes. Simulando envio no console.")
            logger.info("[%s] WhatsApp Bot: %s", remote_jid, text)
            return {"ok": True, "mocked": True, "reason": "missing_credentials"}

        if not self.instance:
            logger.warning("EVOLUTION_INSTANCE ausente. Simulando envio no console.")
            logger.info("[%s] WhatsApp Bot: %s", remote_jid, text)
            return {"ok": True, "mocked": True, "reason": "missing_instance"}

        endpoint = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {"Content-Type": "application/json"}
        if self.api_key.lower().startswith("bearer "):
            headers["Authorization"] = self.api_key
        else:
            headers["apikey"] = self.api_key

        payload = {
            "number": self._normalize_remote_jid(remote_jid),
            "options": {
                "delay": 1500,
                "presence": "composing",
            },
            "textMessage": {
                "text": text,
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10)

                if response.status_code in [400, 404]:
                    logger.error("Erro Evolution API [%s]: %s", response.status_code, response.text)

                response.raise_for_status()
                return {"ok": True, "mocked": False, "response": response.json()}
        except httpx.RequestError as exc:
            logger.error("Erro de conexao com a Evolution API: %s", exc)
            return {"ok": False, "error": str(exc), "kind": "request"}
        except httpx.HTTPStatusError as exc:
            logger.error("Erro HTTP da Evolution API: %s - %s", exc.response.status_code, exc.response.text)
            return {
                "ok": False,
                "error": exc.response.text,
                "kind": "http",
                "status_code": exc.response.status_code,
            }
        except Exception as exc:
            logger.error("Erro inesperado ao enviar mensagem WhatsApp: %s", exc)
            return {"ok": False, "error": str(exc), "kind": "unexpected"}


whatsapp_service = WhatsAppService()
