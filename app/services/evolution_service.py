import base64
import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EvolutionService:
    def __init__(self) -> None:
        self.qr_output = Path("qrcode_bot.png")

    def _build_headers(self) -> dict[str, str]:
        token = (settings.API_KEY_EVOLUTION or "").strip()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if not token:
            return headers
        if token.lower().startswith("bearer "):
            headers["Authorization"] = token
        else:
            headers["apikey"] = token
        return headers

    def _base_url(self) -> str:
        return (settings.URL_EVOLUTION or "").rstrip("/")

    async def fetch_instances(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self._base_url()}/instance/fetchInstances",
                headers=self._build_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []

    async def resolve_instance_name(self, instances: list[dict[str, Any]] | None = None) -> str:
        known = instances if instances is not None else await self.fetch_instances()
        preferred = (settings.EVOLUTION_INSTANCE or "").strip()
        names = [
            item.get("instance", {}).get("instanceName")
            for item in known
            if isinstance(item, dict)
        ]
        names = [name for name in names if isinstance(name, str) and name.strip()]
        if preferred and preferred in names:
            return preferred
        if names:
            return names[0]
        return preferred or "BotRiva"

    async def get_status(self) -> dict[str, Any]:
        try:
            instances = await self.fetch_instances()
            instance_name = await self.resolve_instance_name(instances)
            for item in instances:
                instance = item.get("instance", {}) if isinstance(item, dict) else {}
                if instance.get("instanceName") == instance_name:
                    return {
                        "reachable": True,
                        "instance": instance_name,
                        "status": str(instance.get("status") or "desconhecido"),
                        "base_url": settings.URL_EVOLUTION,
                        "webhook_url": settings.EVOLUTION_WEBHOOK_URL,
                    }
            return {
                "reachable": True,
                "instance": instance_name,
                "status": "nao encontrada",
                "base_url": settings.URL_EVOLUTION,
                "webhook_url": settings.EVOLUTION_WEBHOOK_URL,
            }
        except Exception as exc:
            logger.error("Falha ao consultar Evolution: %s", exc)
            return {
                "reachable": False,
                "instance": settings.EVOLUTION_INSTANCE or "BotRiva",
                "status": "erro",
                "base_url": settings.URL_EVOLUTION,
                "webhook_url": settings.EVOLUTION_WEBHOOK_URL,
                "error": str(exc),
            }

    async def configure_webhook(self, webhook_url: str | None = None) -> dict[str, Any]:
        target_url = (webhook_url or settings.EVOLUTION_WEBHOOK_URL or "").strip()
        instance_name = await self.resolve_instance_name()
        payload = {
            "url": target_url,
            "webhook_by_events": False,
            "webhook_base64": False,
            "events": ["MESSAGES_UPSERT"],
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self._base_url()}/webhook/set/{instance_name}",
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json() if response.content else {}
        return {
            "ok": True,
            "instance": instance_name,
            "url": target_url,
            "response": data,
        }

    async def refresh_qr(self) -> dict[str, Any]:
        instance_name = await self.resolve_instance_name()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base_url()}/instance/connect/{instance_name}",
                headers=self._build_headers(),
            )
            response.raise_for_status()
            data = response.json()

        qr_base64 = str(data.get("base64") or "")
        saved_path = None
        if qr_base64:
            payload = qr_base64.split(",", 1)[1] if "," in qr_base64 else qr_base64
            self.qr_output.write_bytes(base64.b64decode(payload))
            saved_path = str(self.qr_output.resolve())

        return {
            "ok": True,
            "instance": instance_name,
            "qr_path": saved_path,
            "pairing_code": data.get("pairingCode"),
            "has_qr": bool(saved_path),
            "raw": data,
        }


evolution_service = EvolutionService()
