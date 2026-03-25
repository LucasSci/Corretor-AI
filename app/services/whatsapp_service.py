import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self) -> None:
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

    async def send_message(self, remote_jid: str, text: str) -> Optional[Dict[str, Any]]:
        if not self.base_url or not self.api_key:
            logger.warning("Credenciais da Evolution API ausentes. Simulando envio no console.")
            print(f"[{remote_jid}] WhatsApp Bot: {text}")
            return None

        if not self.instance:
            logger.warning("EVOLUTION_INSTANCE ausente. Simulando envio no console.")
            print(f"[{remote_jid}] WhatsApp Bot: {text}")
            return None

        endpoint = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        # Evolution API v1.8 payload format com delay e presence
        payload = {
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
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10)

                if response.status_code == 400:
                    print(f"❌ Erro 400 Evolution API - Bad Request. Verifique o payload ou os headers: {response.text}")
                    logger.error(f"Erro 400 Evolution API - Bad Request: {response.text}")
                elif response.status_code == 404:
                    print(f"❌ Erro 404 Evolution API - Not Found. A instância {self.instance} pode não existir ou a URL está errada: {response.text}")
                    logger.error(f"Erro 404 Evolution API - Not Found: {response.text}")
                elif response.status_code >= 400:
                    print(f"❌ Erro Evolution API [{response.status_code}]: {response.text}")
                    logger.error(f"Erro Evolution API [{response.status_code}]: {response.text}")

                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            print(f"❌ Erro de conexão com a Evolution API: {e}")
            logger.error(f"Erro de conexão com a Evolution API: {e}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"❌ Erro HTTP da Evolution API: {e.response.status_code} - {e.response.text}")
            logger.error(f"Erro HTTP da Evolution API: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"❌ Erro inesperado ao enviar mensagem WhatsApp: {e}")
            logger.error(f"Erro inesperado ao enviar mensagem WhatsApp: {e}")
            return None

whatsapp_service = WhatsAppService()
