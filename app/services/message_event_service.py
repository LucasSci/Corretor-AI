import json
from typing import Any

from sqlalchemy import desc, func, select, update

from app.db.models import MessageEvent
from app.db.session import SessionLocal


def _safe_json_dumps(value: Any, default: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return default


def _parse_json_text(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw) if raw else fallback
    except Exception:
        return fallback


def serialize_message_event(event: MessageEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "direction": event.direction,
        "contact_id": event.contact_id,
        "remote_jid": event.remote_jid,
        "text": event.text,
        "channel": event.channel,
        "status": event.status,
        "meta": _parse_json_text(event.meta_json, {}),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


async def record_message_event(
    *,
    direction: str,
    contact_id: str | None,
    remote_jid: str | None,
    text: str,
    channel: str = "whatsapp",
    status: str = "received",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = MessageEvent(
        direction=direction,
        contact_id=contact_id,
        remote_jid=remote_jid,
        text=text,
        channel=channel,
        status=status,
        meta_json=_safe_json_dumps(meta or {}, "{}"),
    )
    async with SessionLocal() as session:
        session.add(event)
        await session.commit()
        await session.refresh(event)
    return serialize_message_event(event)


async def update_message_event(
    event_id: int,
    *,
    status: str | None = None,
    meta_patch: dict[str, Any] | None = None,
    text: str | None = None,
) -> dict[str, Any] | None:
    async with SessionLocal() as session:
        current = await session.get(MessageEvent, event_id)
        if current is None:
            return None

        values: dict[str, Any] = {}
        if status is not None:
            values["status"] = status
        if text is not None:
            values["text"] = text
        if meta_patch:
            current_meta = _parse_json_text(current.meta_json, {})
            values["meta_json"] = _safe_json_dumps({**current_meta, **meta_patch}, current.meta_json or "{}")

        if not values:
            return serialize_message_event(current)

        await session.execute(update(MessageEvent).where(MessageEvent.id == event_id).values(**values))
        await session.commit()
        refreshed = await session.get(MessageEvent, event_id)
        return serialize_message_event(refreshed) if refreshed is not None else None


async def list_message_events(limit: int = 50, contact_id: str | None = None) -> list[dict[str, Any]]:
    async with SessionLocal() as session:
        stmt = select(MessageEvent).order_by(desc(MessageEvent.created_at)).limit(max(1, min(limit, 200)))
        if contact_id:
            stmt = stmt.where(MessageEvent.contact_id == contact_id)
        rows = (await session.execute(stmt)).scalars().all()
    return [serialize_message_event(row) for row in rows]


async def get_message_event_counts() -> dict[str, int]:
    async with SessionLocal() as session:
        total = await session.scalar(select(func.count()).select_from(MessageEvent))
        inbound = await session.scalar(
            select(func.count()).select_from(MessageEvent).where(MessageEvent.direction == "inbound")
        )
        outbound = await session.scalar(
            select(func.count()).select_from(MessageEvent).where(MessageEvent.direction == "outbound")
        )
    return {
        "total": int(total or 0),
        "inbound": int(inbound or 0),
        "outbound": int(outbound or 0),
    }


async def get_recent_activity(limit: int = 10) -> list[dict[str, Any]]:
    return await list_message_events(limit=max(1, min(limit, 50)))
