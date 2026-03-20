import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings

try:
    from app.services.agent import handle_message
except Exception:
    handle_message = None

from app.services.ai_service import ai_service
from app.services.whatsapp_service import whatsapp_service

router = APIRouter()
logger = logging.getLogger(__name__)
_RECENT_OUTGOING: dict[tuple[str, str], float] = {}


def _cleanup_recent_outgoing(now_ts: float) -> None:
    ttl = max(1, int(settings.WEBHOOK_LOOP_GUARD_TTL_SEC))
    expired = [k for k, ts in _RECENT_OUTGOING.items() if (now_ts - ts) > ttl]
    for k in expired:
        _RECENT_OUTGOING.pop(k, None)


def _remember_outgoing(remote_jid: str, text: str) -> None:
    remote_jid = (remote_jid or "").strip()
    text = (text or "").strip()
    if not remote_jid or not text:
        return
    now_ts = time.time()
    _cleanup_recent_outgoing(now_ts)
    _RECENT_OUTGOING[(remote_jid, text)] = now_ts


def _is_recent_outgoing(remote_jid: str, text: str) -> bool:
    remote_jid = (remote_jid or "").strip()
    text = (text or "").strip()
    if not remote_jid or not text:
        return False

    now_ts = time.time()
    _cleanup_recent_outgoing(now_ts)
    ts = _RECENT_OUTGOING.get((remote_jid, text))
    if ts is None:
        return False
    return (now_ts - ts) <= max(1, int(settings.WEBHOOK_LOOP_GUARD_TTL_SEC))


def _extract_message_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    data: Dict[str, Any] = payload.get("data") if isinstance(payload.get("data"), dict) else {}

    key_obj: Dict[str, Any] = {}
    message_obj: Dict[str, Any] = {}

    if isinstance(data.get("message"), dict):
        message_obj = data.get("message", {})
        key_obj = data.get("key", {}) if isinstance(data.get("key"), dict) else {}

    if (not message_obj) and isinstance(data.get("messages"), list) and data["messages"]:
        first = data["messages"][0]
        if isinstance(first, dict):
            if isinstance(first.get("message"), dict):
                message_obj = first["message"]
            elif isinstance(first.get("text"), dict):
                message_obj = {"text": first["text"]}
            key_obj = first.get("key", {}) if isinstance(first.get("key"), dict) else {}

    if (not message_obj) and isinstance(payload.get("messages"), list) and payload["messages"]:
        first = payload["messages"][0]
        if isinstance(first, dict):
            if isinstance(first.get("message"), dict):
                message_obj = first["message"]
            elif isinstance(first.get("text"), dict):
                message_obj = {"text": first["text"]}
            key_obj = first.get("key", {}) if isinstance(first.get("key"), dict) else {}

    remote_jid: Any = None
    if isinstance(data.get("key"), dict):
        remote_jid = data["key"].get("remoteJid")
    if not remote_jid and isinstance(key_obj, dict):
        remote_jid = key_obj.get("remoteJid")
    if not remote_jid:
        remote_jid = data.get("from") or payload.get("from")
    if (not remote_jid) and isinstance(payload.get("messages"), list) and payload["messages"]:
        first = payload["messages"][0]
        if isinstance(first, dict):
            remote_jid = first.get("from")

    from_me = False
    if isinstance(data.get("key"), dict):
        from_me = bool(data["key"].get("fromMe"))
    if not from_me and isinstance(key_obj, dict):
        from_me = bool(key_obj.get("fromMe"))

    return {
        "data": data,
        "message": message_obj,
        "key": key_obj,
        "remote_jid": remote_jid,
        "from_me": from_me,
    }


def _extract_text(payload: Dict[str, Any], message_obj: Dict[str, Any]) -> str:
    text: str = ""

    if "conversation" in message_obj and isinstance(message_obj.get("conversation"), str):
        text = message_obj["conversation"]
    elif isinstance(message_obj.get("extendedTextMessage"), dict):
        text = message_obj["extendedTextMessage"].get("text", "")
    elif isinstance(message_obj.get("text"), dict):
        text = message_obj["text"].get("body", "")
    elif isinstance(message_obj.get("text"), str):
        text = message_obj["text"]
    elif isinstance(message_obj.get("imageMessage"), dict):
        text = message_obj["imageMessage"].get("caption", "")
    elif isinstance(message_obj.get("videoMessage"), dict):
        text = message_obj["videoMessage"].get("caption", "")

    if not text and isinstance(payload.get("body"), str):
        text = payload["body"]

    return text.strip()


class MessageIn(BaseModel):
    contact_id: str = Field(..., max_length=80)
    text: str = Field(..., max_length=1000)


@router.post("/chat")
async def chat(payload: MessageIn) -> Dict[str, Any]:
    if handle_message is None:
        raise HTTPException(status_code=503, detail="Servico de lead indisponivel no momento")

    result = await handle_message(payload.contact_id, payload.text)
    return {"contact_id": payload.contact_id, **result}


@router.post("/webhook")
async def webhook_evolution(request: Request) -> Dict[str, Any]:
    try:
        body: Dict[str, Any] = await request.json()
    except Exception as exc:
        logger.error("Erro ao parsear JSON do webhook: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_raw = str(body.get("event", "")).strip()
    event_norm = event_raw.lower().replace("_", ".")
    if event_raw and event_norm != "messages.upsert":
        return {"status": "ignored event"}

    ctx = _extract_message_context(body)
    remote_jid = str(ctx.get("remote_jid") or "").strip()

    if not remote_jid:
        logger.warning("remoteJid nao encontrado no payload")
        return {"status": "ignored no remoteJid"}

    if "@lid" in remote_jid:
        if settings.WHATSAPP_TEST_NUMBER:
            logger.info("Bypass @lid ativo. Redirecionando para %s", settings.WHATSAPP_TEST_NUMBER)
            remote_jid = settings.WHATSAPP_TEST_NUMBER
        else:
            logger.info("Bypass @lid sem numero de teste: %s", remote_jid)
            return {"status": "ignored @lid bypass"}

    text = _extract_text(body, ctx.get("message", {}))
    if not text:
        logger.info("Nenhum texto extraido da mensagem")
        return {"status": "ignored no text"}

    if ctx.get("from_me") is True:
        if _is_recent_outgoing(remote_jid, text):
            logger.info("Mensagem eco do bot ignorada para %s", remote_jid)
            return {"status": "ignored bot echo"}
        if not settings.ALLOW_FROM_ME_TEST:
            return {"status": "ignored fromMe"}

    logger.info("Mensagem recebida de %s: %s", remote_jid, text)

    try:
        context = await ai_service.get_context_from_db(text)
        ai_response = await ai_service.generate_response(text, context)

        await whatsapp_service.send_message(remote_jid, ai_response)
        _remember_outgoing(remote_jid, ai_response)

        return {"status": "processed", "reply": ai_response}
    except Exception as exc:
        logger.error("Erro ao processar a mensagem do webhook: %s", exc)
        # We don't want to crash the FastApi server nor give 500 when it's an external API failing in a webhook context.
        return {"status": "error", "message": "Failed to process message"}
