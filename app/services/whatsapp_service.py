import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self) -> None:
        self.base_url: str = settings.URL_EVOLUTION.rstrip("/") if settings.URL_EVOLUTION else ""
        self.api_key: str = settings.API_KEY_EVOLUTION

    async def send_message(self, remote_jid: str, text: str) -> Optional[Dict[str, Any]]:
        if not self.base_url or not self.api_key:
            logger.warning("Credenciais da Evolution API ausentes. Simulando envio no console.")
            print(f"[{remote_jid}] WhatsApp Bot: {text}")
            return None

        endpoint: str = f"{self.base_url}/message/sendText"
        headers: Dict[str, str] = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

        # Evolution API v1.8 payload format com delay e presence
        payload: Dict[str, Any] = {
            "number": remote_jid,
            "options": {
                "delay": 1500,
                "presence": "composing"
            },
            "textMessage": {
                "text": text
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10)

                if response.status_code in [400, 404]:
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
            logger.error(f"Erro HTTP da Evolution API: {e.response.status_code}")
            return None
        except Exception as e:
            print(f"❌ Erro inesperado ao enviar mensagem WhatsApp: {e}")
            logger.error(f"Erro inesperado ao enviar mensagem WhatsApp: {e}")
            return None

whatsapp_service = WhatsAppService()
