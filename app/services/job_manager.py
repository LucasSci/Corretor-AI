import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from sqlalchemy import desc, select, update

from app.db.models import JobRun
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

JobRunner = Callable[["JobContext", dict[str, Any]], Awaitable[dict[str, Any] | None]]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_dumps(value: Any, default: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return default


def _json_loads(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw) if raw else fallback
    except Exception:
        return fallback


def serialize_job_run(job: JobRun) -> dict[str, Any]:
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "payload": _json_loads(job.payload_json, {}),
        "result": _json_loads(job.result_json, {}),
        "logs": _json_loads(job.log_json, []),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@dataclass(slots=True)
class JobContext:
    job_id: str
    manager: "JobManager"

    async def update(
        self,
        *,
        progress: float | None = None,
        message: str | None = None,
        log: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any] | None:
        return await self.manager.update_job(
            self.job_id,
            progress=progress,
            message=message,
            log=log,
            status=status,
        )


class JobManager:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, kind: str, payload: dict[str, Any], runner: JobRunner) -> dict[str, Any]:
        job_id = uuid4().hex
        async with SessionLocal() as session:
            session.add(
                JobRun(
                    id=job_id,
                    kind=kind,
                    status="queued",
                    progress=0.0,
                    message="Job enfileirado",
                    payload_json=_json_dumps(payload, "{}"),
                    result_json="{}",
                    log_json="[]",
                )
            )
            await session.commit()

        self._tasks[job_id] = asyncio.create_task(self._run_job(job_id, kind, payload, runner))
        return await self.get_job(job_id) or {"id": job_id, "kind": kind, "status": "queued", "progress": 0}

    async def _run_job(self, job_id: str, kind: str, payload: dict[str, Any], runner: JobRunner) -> None:
        ctx = JobContext(job_id=job_id, manager=self)
        await self.update_job(
            job_id,
            status="running",
            progress=5,
            message=f"Iniciando job {kind}",
            log=f"{_utcnow().isoformat()} Job {kind} iniciado",
            started_at=_utcnow(),
        )
        try:
            result = await runner(ctx, payload)
            await self.update_job(
                job_id,
                status="completed",
                progress=100,
                message="Job concluido",
                log=f"{_utcnow().isoformat()} Job concluido",
                result=result or {},
                finished_at=_utcnow(),
            )
        except Exception as exc:
            logger.exception("Falha ao executar job %s", job_id)
            await self.update_job(
                job_id,
                status="failed",
                progress=100,
                message=str(exc),
                log=f"{_utcnow().isoformat()} Falha: {exc}",
                result={"error": str(exc)},
                finished_at=_utcnow(),
            )
        finally:
            self._tasks.pop(job_id, None)

    async def update_job(
        self,
        job_id: str,
        *,
        progress: float | None = None,
        message: str | None = None,
        log: str | None = None,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        async with self._lock:
            async with SessionLocal() as session:
                job = await session.get(JobRun, job_id)
                if job is None:
                    return None

                values: dict[str, Any] = {"updated_at": _utcnow()}
                if progress is not None:
                    values["progress"] = max(0.0, min(float(progress), 100.0))
                if message is not None:
                    values["message"] = message
                if status is not None:
                    values["status"] = status
                if result is not None:
                    values["result_json"] = _json_dumps(result, "{}")
                if started_at is not None:
                    values["started_at"] = started_at
                if finished_at is not None:
                    values["finished_at"] = finished_at
                if log is not None:
                    logs = _json_loads(job.log_json, [])
                    logs.append(log)
                    values["log_json"] = _json_dumps(logs[-200:], "[]")

                await session.execute(update(JobRun).where(JobRun.id == job_id).values(**values))
                await session.commit()
                refreshed = await session.get(JobRun, job_id)
        return serialize_job_run(refreshed) if refreshed is not None else None

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        async with SessionLocal() as session:
            job = await session.get(JobRun, job_id)
        return serialize_job_run(job) if job is not None else None

    async def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(JobRun).order_by(desc(JobRun.created_at)).limit(max(1, min(limit, 100)))
                )
            ).scalars().all()
        return [serialize_job_run(row) for row in rows]


job_manager = JobManager()
