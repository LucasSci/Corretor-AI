import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.api.admin as admin_api
import app.db.init_db as init_db_module
import app.db.session as session_module
import app.services.job_manager as job_manager_module
import app.services.lead_service as lead_service_module
import app.services.message_event_service as message_event_service_module
from app.db.models import Base
from app.main import app
from app.services.job_manager import job_manager
from app.services.lead_service import get_or_create_lead
from app.services.message_event_service import list_message_events, record_message_event


def _request(method: str, path: str, payload: dict | None = None) -> httpx.Response:
    async def _run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(_run())


@pytest.fixture(autouse=True)
def _isolated_sqlite():
    tmp_dir = Path(tempfile.mkdtemp())
    db_path = tmp_dir / "admin_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_local = async_sessionmaker(engine, expire_on_commit=False)

    session_module.engine = engine
    session_module.SessionLocal = session_local
    init_db_module.engine = engine
    lead_service_module.SessionLocal = session_local
    message_event_service_module.SessionLocal = session_local
    job_manager_module.SessionLocal = session_local

    async def _prepare() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_prepare())
    yield
    asyncio.run(engine.dispose())


def test_admin_status_returns_counts():
    asyncio.run(get_or_create_lead("21975907217"))
    asyncio.run(
        record_message_event(
            direction="inbound",
            contact_id="21975907217",
            remote_jid="21975907217@s.whatsapp.net",
            text="oi",
            status="processed",
        )
    )

    with patch(
        "app.api.admin.evolution_service.get_status",
        new=AsyncMock(
            return_value={
                "reachable": True,
                "instance": "BotRiva",
                "status": "open",
                "base_url": "http://127.0.0.1:8080",
                "webhook_url": "http://host.docker.internal:8000/webhook",
            }
        ),
    ):
        response = _request("GET", "/admin/status")

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["leads"]["total"] == 1
    assert body["counts"]["messages"]["total"] == 1
    assert body["backend"]["healthy"] is True


def test_admin_settings_validate_and_save():
    tmp_file = Path(tempfile.mkdtemp()) / "desktop_settings.json"
    payload = {
        "llm": {"modelName": "gemini-2.5-flash", "geminiApiKey": "abc", "openaiApiKey": "", "temperature": 0.5, "chromaK": 4},
        "evolution": {"baseUrl": "http://127.0.0.1:8080", "apiKey": "token", "instance": "BotRiva", "webhookUrl": "http://host.docker.internal:8000/webhook"},
        "storage": {"dbUrl": "sqlite+aiosqlite:///./data/app.db", "uploadsDir": "data/whatsapp_uploads", "mediaAutoSave": True},
        "network": {"host": "0.0.0.0", "port": 8000, "corsOrigins": ["http://127.0.0.1:1420"]},
        "operator": {"allowedNumbers": "21975907217", "commandNumbers": "21975907217", "testNumber": "", "botNumber": "", "allowFromMeTest": True, "loopGuardTtlSec": 30},
    }

    with patch(
        "app.api.admin.evolution_service.get_status",
        new=AsyncMock(return_value={"reachable": True, "instance": "BotRiva", "status": "open"}),
    ):
        with patch("app.services.settings_service.settings.DESKTOP_SETTINGS_PATH", str(tmp_file)):
            validate_response = _request("POST", "/admin/settings/validate", payload)
            save_response = _request("POST", "/admin/settings", payload)

    assert validate_response.status_code == 200
    assert save_response.status_code == 200
    assert tmp_file.exists()
    assert save_response.json()["saved"] is True


def test_admin_job_endpoints():
    fake_job = {
        "id": "job-123",
        "kind": "linktree_full",
        "status": "completed",
        "progress": 100,
        "message": "ok",
        "payload": {},
        "result": {"ok": True},
        "logs": ["inicio", "fim"],
    }

    with patch.object(admin_api.job_manager, "create_job", new=AsyncMock(return_value=fake_job)):
        with patch.object(admin_api.job_manager, "get_job", new=AsyncMock(return_value=fake_job)):
            create_response = _request("POST", "/admin/ingestion/jobs", {"kind": "linktree_full", "sources": []})
            get_response = _request("GET", "/admin/ingestion/jobs/job-123")

    assert create_response.status_code == 200
    assert get_response.status_code == 200
    assert create_response.json()["status"] == "completed"
    assert get_response.json()["result"]["ok"] is True


def test_admin_uploads_messages_and_logs():
    tmp_dir = Path(tempfile.mkdtemp())
    uploads_root = tmp_dir / "uploads"
    uploads_root.mkdir(parents=True, exist_ok=True)
    file_path = uploads_root / "document" / "2026-04-21"
    file_path.mkdir(parents=True, exist_ok=True)
    saved_file = file_path / "contrato.pdf"
    saved_file.write_bytes(b"pdf")

    stdout_log = tmp_dir / "output.log"
    stderr_log = tmp_dir / "output.err.log"
    stdout_log.write_text("linha stdout\n", encoding="utf-8")
    stderr_log.write_text("linha stderr\n", encoding="utf-8")

    asyncio.run(
        record_message_event(
            direction="outbound",
            contact_id="21975907217",
            remote_jid="21975907217@s.whatsapp.net",
            text="resposta",
            status="sent",
        )
    )

    with patch("app.api.admin.settings.WHATSAPP_UPLOADS_DIR", str(uploads_root)):
        with patch("app.services.logs_service.settings.OUTPUT_LOG_PATH", str(stdout_log)):
            with patch("app.services.logs_service.settings.ERROR_LOG_PATH", str(stderr_log)):
                uploads_response = _request("GET", "/admin/uploads")
                messages_response = _request("GET", "/admin/messages")
                logs_response = _request("GET", "/admin/logs/tail?source=combined")

    assert uploads_response.status_code == 200
    assert len(uploads_response.json()["items"]) == 1
    assert messages_response.status_code == 200
    assert messages_response.json()["items"][0]["text"] == "resposta"
    assert logs_response.status_code == 200
    assert logs_response.json()["stdout"][-1] == "linha stdout"
    assert logs_response.json()["stderr"][-1] == "linha stderr"


def test_admin_evolution_endpoints():
    with patch("app.api.admin.evolution_service.get_status", new=AsyncMock(return_value={"reachable": True, "instance": "BotRiva", "status": "open"})):
        with patch("app.api.admin.evolution_service.refresh_qr", new=AsyncMock(return_value={"ok": True, "instance": "BotRiva", "has_qr": False})):
            with patch("app.api.admin.evolution_service.configure_webhook", new=AsyncMock(return_value={"ok": True, "instance": "BotRiva", "url": "http://host.docker.internal:8000/webhook"})):
                status_response = _request("GET", "/admin/evolution/status")
                qr_response = _request("POST", "/admin/evolution/qr")
                webhook_response = _request("POST", "/admin/evolution/webhook", {"url": "http://host.docker.internal:8000/webhook"})

    assert status_response.status_code == 200
    assert qr_response.status_code == 200
    assert webhook_response.status_code == 200
    assert webhook_response.json()["ok"] is True


def test_message_events_are_persisted():
    asyncio.run(
        record_message_event(
            direction="outbound",
            contact_id="5521975907217",
            remote_jid="5521975907217@s.whatsapp.net",
            text="mensagem persistida",
            status="sent",
        )
    )
    items = asyncio.run(list_message_events(limit=10))
    assert len(items) == 1
    assert items[0]["text"] == "mensagem persistida"


def test_job_manager_persists_completed_job():
    async def _run():
        async def fake_runner(ctx, payload):
            await ctx.update(progress=55, message="andando", log="meio")
            return {"ok": True, "payload": payload}

        created = await job_manager.create_job("manual_documents", {"sources": ["C:/temp/file.pdf"]}, fake_runner)
        for _ in range(20):
            current = await job_manager.get_job(created["id"])
            if current is not None and current["status"] in {"completed", "failed"}:
                return current
            await asyncio.sleep(0.05)
        return await job_manager.get_job(created["id"])

    result = asyncio.run(_run())
    assert result is not None
    assert result["status"] == "completed"
    assert result["result"]["ok"] is True
