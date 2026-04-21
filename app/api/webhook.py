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

from app.services.admin_command_service import admin_command_service
from app.services.ai_service import ai_service
from app.services.media_storage_service import whatsapp_media_storage_service
from app.services.message_event_service import record_message_event, update_message_event
from app.services.whatsapp_service import whatsapp_service

router = APIRouter()
logger = logging.getLogger(__name__)
_RECENT_OUTGOING: dict[tuple[str, str], float] = {}
_AI_FALLBACK_REPLIES = {
    "Estou com instabilidade no sistema agora, podemos falar mais tarde?",
    "Vou verificar essa informacao e ja te retorno!",
}


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
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

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

    remote_jid = None
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
    text = ""

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


def _normalize_number(raw: str) -> str:
    value = (raw or "").strip()
    if "@" in value:
        value = value.split("@", 1)[0]
    return "".join(ch for ch in value if ch.isdigit())


def _get_allowed_numbers() -> set[str]:
    raw = (settings.WHATSAPP_ALLOWED_NUMBERS or "").strip()
    if not raw:
        return set()
    numbers: set[str] = set()
    for item in raw.split(","):
        num = _normalize_number(item)
        if num:
            numbers.add(num)
    return numbers


def _candidate_number_forms(number: str) -> set[str]:
    normalized = _normalize_number(number)
    if not normalized:
        return set()

    candidates = {normalized}
    if normalized.startswith("55") and len(normalized) > 2:
        candidates.add(normalized[2:])
    elif len(normalized) in {10, 11}:
        candidates.add(f"55{normalized}")
    return candidates


def _is_allowed_number(sender_number: str, allowed_numbers: set[str]) -> bool:
    if not allowed_numbers:
        return True

    sender_candidates = _candidate_number_forms(sender_number)
    for allowed in allowed_numbers:
        if sender_candidates.intersection(_candidate_number_forms(allowed)):
            return True
    return False


async def _build_reply(contact_id: str, text: str) -> str:
    context = await ai_service.get_context_from_db(text)
    ai_response = await ai_service.generate_response(text, context)

    if handle_message is not None and ai_response in _AI_FALLBACK_REPLIES:
        try:
            agent_result = await handle_message(contact_id, text)
            agent_reply = str(agent_result.get("reply") or "").strip()
            if agent_reply:
                return agent_reply
        except Exception as exc:
            logger.error("Falha ao gerar resposta local do agente: %s", exc)

    return ai_response


async def _record_outbound_event(
    *,
    contact_id: str,
    remote_jid: str,
    text: str,
    send_result: dict[str, Any],
) -> None:
    await _safe_record_message_event(
        direction="outbound",
        contact_id=contact_id,
        remote_jid=remote_jid,
        text=text,
        channel="whatsapp",
        status="sent" if send_result.get("ok") else "failed",
        meta=send_result,
    )


async def _safe_record_message_event(**kwargs) -> dict[str, Any] | None:
    try:
        return await record_message_event(**kwargs)
    except Exception as exc:
        logger.error("Falha ao registrar evento de mensagem: %s", exc)
        return None


async def _safe_update_message_event(event_id: int | None, **kwargs) -> dict[str, Any] | None:
    if event_id is None:
        return None
    try:
        return await update_message_event(event_id, **kwargs)
    except Exception as exc:
        logger.error("Falha ao atualizar evento de mensagem %s: %s", event_id, exc)
        return None


class MessageIn(BaseModel):
    contact_id: str = Field(..., max_length=80)
    text: str = Field(..., max_length=1000)


@router.post("/chat")
async def chat(payload: MessageIn):
    if handle_message is None:
        raise HTTPException(status_code=503, detail="Servico de lead indisponivel no momento")

    result = await handle_message(payload.contact_id, payload.text)
    await _safe_record_message_event(
        direction="inbound",
        contact_id=payload.contact_id,
        remote_jid=payload.contact_id,
        text=payload.text,
        channel="chat",
        status="processed",
        meta={"source": "chat"},
    )
    return {"contact_id": payload.contact_id, **result}


@router.post("/webhook")
async def webhook_evolution(request: Request):
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

    allowed_numbers = _get_allowed_numbers()
    sender_number = _normalize_number(remote_jid)
    if not _is_allowed_number(sender_number, allowed_numbers):
        logger.info("Mensagem ignorada de numero nao permitido: %s", remote_jid)
        return {"status": "ignored not allowed number"}
    contact_id = sender_number or remote_jid

    message_obj = ctx.get("message", {}) if isinstance(ctx.get("message"), dict) else {}
    saved_media: list[dict[str, Any]] = []
    try:
        saved_media = await whatsapp_media_storage_service.save_incoming_media(
            payload=body,
            message_obj=message_obj,
            remote_jid=remote_jid,
        )
    except Exception as exc:
        logger.error("Falha ao salvar midia recebida: %s", exc)

    text = _extract_text(body, message_obj)
    if not text and not saved_media:
        logger.info("Nenhum texto extraido e nenhuma midia para salvar")
        return {"status": "ignored no text"}
    inbound_event = await _safe_record_message_event(
        direction="inbound",
        contact_id=contact_id,
        remote_jid=remote_jid,
        text=text or "[media]",
        channel="whatsapp",
        status="received",
        meta={
            "event": event_norm or "messages.upsert",
            "from_me": bool(ctx.get("from_me")),
            "saved_files": [item.get("saved_path") for item in saved_media],
        },
    )

    if admin_command_service.is_command_message(text):
        if not admin_command_service.is_authorized(sender_number):
            logger.info("Comando ignorado de numero sem permissao: %s", remote_jid)
            await _safe_update_message_event(inbound_event["id"] if inbound_event else None, status="ignored unauthorized command")
            return {"status": "ignored unauthorized command"}

        command_reply = await admin_command_service.handle_command(text)
        send_result = await whatsapp_service.send_message(remote_jid, command_reply)
        _remember_outgoing(remote_jid, command_reply)
        await _safe_update_message_event(inbound_event["id"] if inbound_event else None, status="processed command")
        await _record_outbound_event(
            contact_id=contact_id,
            remote_jid=remote_jid,
            text=command_reply,
            send_result=send_result,
        )
        return {"status": "processed command", "reply": command_reply}

    if ctx.get("from_me") is True:
        if _is_recent_outgoing(remote_jid, text):
            logger.info("Mensagem eco do bot ignorada para %s", remote_jid)
            await _safe_update_message_event(inbound_event["id"] if inbound_event else None, status="ignored bot echo")
            return {"status": "ignored bot echo"}
        if not settings.ALLOW_FROM_ME_TEST:
            await _safe_update_message_event(inbound_event["id"] if inbound_event else None, status="ignored fromMe")
            return {"status": "ignored fromMe"}

    if not text and saved_media:
        file_count = len(saved_media)
        ack = (
            f"Arquivo recebido e salvo com sucesso. "
            f"Total desta mensagem: {file_count}. "
            f"Pasta base: {settings.WHATSAPP_UPLOADS_DIR}"
        )
        send_result = await whatsapp_service.send_message(remote_jid, ack)
        _remember_outgoing(remote_jid, ack)
        await _safe_update_message_event(inbound_event["id"] if inbound_event else None, status="processed media")
        await _record_outbound_event(
            contact_id=contact_id,
            remote_jid=remote_jid,
            text=ack,
            send_result=send_result,
        )
        return {
            "status": "processed media",
            "saved_files": [item.get("saved_path") for item in saved_media],
        }

    logger.info("Mensagem recebida de %s: %s", remote_jid, text)

    try:
        ai_response = await _build_reply(contact_id, text)

        send_result = await whatsapp_service.send_message(remote_jid, ai_response)
        _remember_outgoing(remote_jid, ai_response)
        await _safe_update_message_event(inbound_event["id"] if inbound_event else None, status="processed")
        await _record_outbound_event(
            contact_id=contact_id,
            remote_jid=remote_jid,
            text=ai_response,
            send_result=send_result,
        )

        result: Dict[str, Any] = {"status": "processed", "reply": ai_response}
        if saved_media:
            result["saved_files"] = [item.get("saved_path") for item in saved_media]
        return result
    except Exception as exc:
        logger.error("Erro ao processar a mensagem do webhook: %s", exc)
        await _safe_update_message_event(
            inbound_event["id"] if inbound_event else None,
            status="error",
            meta_patch={"error": str(exc)},
        )
        return {"status": "error"}
