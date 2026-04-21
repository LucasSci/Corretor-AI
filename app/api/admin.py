from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.evolution_service import evolution_service
from app.services.ingestion_service import run_ingestion_job
from app.services.job_manager import job_manager
from app.services.lead_service import get_lead_counts, list_leads
from app.services.logs_service import tail_logs
from app.services.message_event_service import (
    get_message_event_counts,
    get_recent_activity,
    list_message_events,
    record_message_event,
)
from app.services.settings_service import (
    get_current_settings_document,
    save_settings_document,
    validate_settings_document,
)
from app.services.whatsapp_service import whatsapp_service

router = APIRouter(prefix="/admin", tags=["admin"])


class SettingsPayload(BaseModel):
    llm: dict[str, Any] = Field(default_factory=dict)
    evolution: dict[str, Any] = Field(default_factory=dict)
    storage: dict[str, Any] = Field(default_factory=dict)
    network: dict[str, Any] = Field(default_factory=dict)
    operator: dict[str, Any] = Field(default_factory=dict)


class IngestionJobPayload(BaseModel):
    kind: str = Field(default="linktree_full", max_length=48)
    sources: list[str] = Field(default_factory=list)


class EvolutionWebhookPayload(BaseModel):
    url: str | None = None


class ChatTestPayload(BaseModel):
    contact_id: str = Field(..., max_length=80)
    text: str = Field(..., max_length=1000)
    remote_jid: str | None = Field(default=None, max_length=120)


def _upload_entries(limit: int) -> list[dict[str, Any]]:
    root = Path(settings.WHATSAPP_UPLOADS_DIR)
    if not root.exists():
        return []

    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and not path.name.endswith(".json")
    ]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    results = []
    for item in files[: max(1, min(limit, 100))]:
        meta_path = item.with_suffix(item.suffix + ".json")
        results.append(
            {
                "path": str(item.resolve()),
                "name": item.name,
                "type": item.parent.parent.name if item.parent.parent.exists() else item.suffix.lstrip("."),
                "modified_at": item.stat().st_mtime,
                "metadata_path": str(meta_path.resolve()) if meta_path.exists() else None,
            }
        )
    return results


@router.get("/status")
async def admin_status():
    lead_counts = await get_lead_counts()
    message_counts = await get_message_event_counts()
    evolution = await evolution_service.get_status()
    uploads = _upload_entries(10)
    jobs = await job_manager.list_jobs(limit=5)
    activity = await get_recent_activity(limit=8)
    return {
        "backend": {
            "app_name": settings.APP_NAME,
            "healthy": True,
            "host": settings.HOST,
            "port": settings.PORT,
            "settings_path": settings.DESKTOP_SETTINGS_PATH,
        },
        "evolution": evolution,
        "counts": {
            "leads": lead_counts,
            "messages": message_counts,
            "uploads": len(uploads),
        },
        "recent_jobs": jobs,
        "recent_activity": activity,
        "uploads": uploads[:5],
    }


@router.get("/evolution/status")
async def evolution_status():
    return await evolution_service.get_status()


@router.post("/evolution/qr")
async def evolution_qr():
    return await evolution_service.refresh_qr()


@router.post("/evolution/webhook")
async def evolution_webhook(payload: EvolutionWebhookPayload):
    return await evolution_service.configure_webhook(payload.url)


@router.get("/settings")
async def get_settings():
    return get_current_settings_document()


@router.post("/settings")
async def save_settings(payload: SettingsPayload):
    result = await save_settings_document(payload.model_dump())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/settings/validate")
async def validate_settings(payload: SettingsPayload):
    result = await validate_settings_document(payload.model_dump())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/ingestion/jobs")
async def create_ingestion_job(payload: IngestionJobPayload):
    job = await job_manager.create_job(payload.kind, payload.model_dump(), run_ingestion_job)
    return job


@router.get("/ingestion/jobs/{job_id}")
async def get_ingestion_job(job_id: str):
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/uploads")
async def get_uploads(limit: int = Query(default=20, ge=1, le=100)):
    return {"items": _upload_entries(limit)}


@router.get("/leads")
async def get_leads(limit: int = Query(default=50, ge=1, le=200)):
    return {"items": await list_leads(limit=limit)}


@router.get("/messages")
async def get_messages(
    limit: int = Query(default=50, ge=1, le=200),
    contact_id: str | None = Query(default=None),
):
    return {"items": await list_message_events(limit=limit, contact_id=contact_id)}


@router.get("/logs/tail")
async def get_logs(limit: int = Query(default=200, ge=1, le=500), source: str = "combined"):
    return tail_logs(limit=limit, source=source)


@router.post("/chat/test")
async def send_chat_test(payload: ChatTestPayload):
    remote_jid = payload.remote_jid or payload.contact_id
    send_result = await whatsapp_service.send_message(remote_jid, payload.text)
    status = "sent" if send_result.get("ok") else "failed"
    await record_message_event(
        direction="outbound",
        contact_id=payload.contact_id,
        remote_jid=remote_jid,
        text=payload.text,
        channel="whatsapp",
        status=status,
        meta=send_result,
    )
    return {"ok": bool(send_result.get("ok")), "send_result": send_result}
