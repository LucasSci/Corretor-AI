import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self) -> None:
        self.base_url: str = settings.URL_EVOLUTION.rstrip("/") if settings.URL_EVOLUTION else ""
        self.api_key: str = settings.API_KEY_EVOLUTION
        self.instance: str = settings.EVOLUTION_INSTANCE

    @staticmethod
    def _normalize_remote_jid(remote_jid: str) -> str:
        """
        Extracts just the number from the remoteJid, e.g. from '5511999999999@s.whatsapp.net'
        """
        if not remote_jid:
            return ""
        if "@" in remote_jid:
            return remote_jid.split("@", 1)[0]
        return remote_jid

    async def send_message(self, remote_jid: str, text: str) -> Optional[Dict[str, Any]]:
        """
        Sends a WhatsApp message via the Evolution API using v1.8 schema.
        Handles graceful degradation if credentials are not configured.
        """
        if not self.base_url or not self.api_key:
            logger.warning("Missing Evolution API credentials. Simulating sending in console.")
            print(f"[{remote_jid}] WhatsApp Bot: {text}")
            return None

        if not self.instance:
            logger.warning("Missing EVOLUTION_INSTANCE. Simulating sending in console.")
            print(f"[{remote_jid}] WhatsApp Bot: {text}")
            return None

        endpoint: str = f"{self.base_url}/message/sendText/{self.instance}"
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        # Evolution API v1.8 payload format with delay and presence
        payload: Dict[str, Any] = {
            "number": self._normalize_remote_jid(remote_jid),
            "options": {
                "delay": 1200,
                "presence": "composing"
            },
            "textMessage": {
                "text": text
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response: httpx.Response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)

                if response.status_code in [400, 404]:
                    print(f"❌ Evolution API Error [{response.status_code}]: {response.text}")
                    logger.error("Evolution API Error [%s]: %s", response.status_code, response.text)

                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            print(f"❌ Connection error with Evolution API: {e}")
            logger.error("Connection error with Evolution API: %s", e)
            return None
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP error from Evolution API: {e.response.status_code} - {e.response.text}")
            logger.error("HTTP error from Evolution API: %s - %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            print(f"❌ Unexpected error sending WhatsApp message: {e}")
            logger.error("Unexpected error sending WhatsApp message: %s", e)
            return None

whatsapp_service = WhatsAppService()
