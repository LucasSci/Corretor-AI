import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.services.agent import handle_message
from app.services.whatsapp_service import whatsapp_service
from app.services.ai_service import ai_service

router = APIRouter()
logger = logging.getLogger(__name__)

class MessageIn(BaseModel):
    contact_id: str = Field(..., max_length=80)
    text: str = Field(..., max_length=1000)

@router.post("/chat")
async def chat(payload: MessageIn) -> Dict[str, Any]:
    """
    Rota legada ou genérica para testes diretos (não Evolution API).
    """
    result = await handle_message(payload.contact_id, payload.text)
    return {"contact_id": payload.contact_id, **result}

@router.post("/webhook")
async def webhook_evolution(request: Request) -> Dict[str, str]:
    """
    Webhook principal para receber eventos da Evolution API.
    """
    try:
        body: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.error(f"Erro ao parsear JSON do webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extrai o evento
    event_type: str = body.get("event", "")
    if event_type != "messages.upsert":
        return {"status": "ignored event"}

    # Extrai os dados da mensagem
    data: Dict[str, Any] = body.get("data", {})
    message: Dict[str, Any] = data.get("message", {})

    # Identifica o remetente (remoteJid) ignorando self
    key: Dict[str, Any] = data.get("key", {})
    if key.get("fromMe") is True:
        return {"status": "ignored fromMe"}

    remote_jid: str = key.get("remoteJid", "")

    if not remote_jid:
        logger.warning("remoteJid não encontrado no payload")
        return {"status": "ignored no remoteJid"}

    # Bypass para ignorar os @lid (gerados em testes/contas especificas)
    if "@lid" in remote_jid:
        logger.info(f"Bypass de teste: Ignorando processamento para {remote_jid}")
        return {"status": "ignored @lid bypass"}

    # Extrai o texto da mensagem (considerando estrutura da Evolution)
    text: str = ""
    if "conversation" in message:
        text = message["conversation"]
    elif "extendedTextMessage" in message:
        text = message.get("extendedTextMessage", {}).get("text", "")

    if not text:
        logger.info("Nenhum texto extraído da mensagem")
        return {"status": "ignored no text"}

    logger.info(f"Mensagem recebida de {remote_jid}: {text}")

    try:
        # Busca contexto no RAG
        context: str = await ai_service.get_context_from_db(text)

        # Gera a resposta via Gemini
        ai_response: str = await ai_service.generate_response(text, context)

        # Envia de volta para o WhatsApp
        await whatsapp_service.send_message(remote_jid, ai_response)

        return {"status": "processed", "reply": ai_response}

    except Exception as e:
        logger.error(f"Erro ao processar a mensagem do webhook: {e}")
        # Mesmo com erro, retornamos 200 pro webhook não ficar retentando
        return {"status": "error"}
