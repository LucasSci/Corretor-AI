import base64
import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _normalize_number(raw: str) -> str:
    value = (raw or "").strip()
    if "@" in value:
        value = value.split("@", 1)[0]
    return "".join(ch for ch in value if ch.isdigit())


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


def _parse_number_list(raw: str) -> set[str]:
    items = set()
    for part in (raw or "").split(","):
        normalized = _normalize_number(part)
        if normalized:
            items.add(normalized)
    return items


class AdminCommandService:
    def __init__(self) -> None:
        self.qr_output = Path("qrcode_bot.png")

    def is_command_message(self, text: str) -> bool:
        stripped = (text or "").strip()
        return stripped.startswith("/")

    def is_authorized(self, sender_number: str) -> bool:
        allowed = _parse_number_list(settings.WHATSAPP_COMMAND_NUMBERS or settings.WHATSAPP_ALLOWED_NUMBERS)
        if not allowed:
            return False

        sender_candidates = _candidate_number_forms(sender_number)
        for item in allowed:
            if sender_candidates.intersection(_candidate_number_forms(item)):
                return True
        return False

    async def handle_command(self, text: str) -> str:
        stripped = (text or "").strip()
        if not stripped:
            return "Comando vazio. Use /help."

        parts = stripped.split(None, 1)
        command = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if command in {"/help", "/ajuda", "/comandos"}:
            return self._help_text()
        if command == "/ping":
            return "pong"
        if command == "/status":
            return await self._status_text()
        if command == "/evolution":
            return await self._evolution_text()
        if command == "/webhook":
            return await self._configure_webhook()
        if command == "/qr":
            return await self._refresh_qr()
        if command in {"/uploads", "/arquivos"}:
            return self._recent_uploads(arg)

        return "Comando nao reconhecido. Use /help."

    def _help_text(self) -> str:
        return (
            "Comandos disponiveis:\n"
            "/help - lista comandos\n"
            "/ping - teste rapido\n"
            "/status - status geral do bot\n"
            "/evolution - status da instancia WhatsApp\n"
            "/webhook - reconfigura webhook local\n"
            "/qr - gera novo QR em qrcode_bot.png\n"
            "/uploads [n] - ultimos arquivos salvos"
        )

    async def _fetch_instances(self) -> list[dict[str, Any]]:
        headers = {"apikey": settings.API_KEY_EVOLUTION}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{settings.URL_EVOLUTION.rstrip('/')}/instance/fetchInstances", headers=headers)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []

    async def _resolve_instance_name(self) -> str:
        instances = await self._fetch_instances()
        names = [
            item.get("instance", {}).get("instanceName")
            for item in instances
            if isinstance(item, dict)
        ]
        names = [name for name in names if isinstance(name, str) and name.strip()]

        preferred = (settings.EVOLUTION_INSTANCE or "").strip()
        if preferred and preferred in names:
            return preferred
        if len(names) == 1:
            return names[0]
        if names:
            return names[0]
        return preferred or "BotRiva"

    async def _status_text(self) -> str:
        evolution = await self._evolution_summary()
        uploads_dir = Path(settings.WHATSAPP_UPLOADS_DIR)
        uploads_count = len([p for p in uploads_dir.rglob("*") if p.is_file() and not p.name.endswith(".json")]) if uploads_dir.exists() else 0
        gemini_state = "configurada" if (settings.GEMINI_API_KEY or "").strip() else "ausente"

        return (
            "Bot online\n"
            f"instancia: {evolution['instance']}\n"
            f"evolution: {evolution['status']}\n"
            f"webhook: {settings.EVOLUTION_WEBHOOK_URL}\n"
            f"gemini_key: {gemini_state}\n"
            f"uploads: {uploads_count}"
        )

    async def _evolution_summary(self) -> dict[str, str]:
        try:
            instances = await self._fetch_instances()
            instance_name = await self._resolve_instance_name()
            for item in instances:
                instance = item.get("instance", {}) if isinstance(item, dict) else {}
                if instance.get("instanceName") == instance_name:
                    return {
                        "instance": instance_name,
                        "status": str(instance.get("status") or "desconhecido"),
                    }
            return {"instance": instance_name, "status": "nao encontrada"}
        except Exception as exc:
            logger.error("Falha ao consultar Evolution: %s", exc)
            return {"instance": settings.EVOLUTION_INSTANCE or "BotRiva", "status": "erro"}

    async def _evolution_text(self) -> str:
        summary = await self._evolution_summary()
        return f"instancia: {summary['instance']}\nstatus: {summary['status']}"

    async def _configure_webhook(self) -> str:
        instance_name = await self._resolve_instance_name()
        headers = {
            "apikey": settings.API_KEY_EVOLUTION,
            "Content-Type": "application/json",
        }
        payload = {
            "url": settings.EVOLUTION_WEBHOOK_URL,
            "webhook_by_events": False,
            "webhook_base64": False,
            "events": ["MESSAGES_UPSERT"],
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{settings.URL_EVOLUTION.rstrip('/')}/webhook/set/{instance_name}",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
            return f"Webhook configurado para {settings.EVOLUTION_WEBHOOK_URL}"
        except Exception as exc:
            logger.error("Falha ao configurar webhook: %s", exc)
            return f"Falha ao configurar webhook: {exc}"

    async def _refresh_qr(self) -> str:
        instance_name = await self._resolve_instance_name()
        headers = {"apikey": settings.API_KEY_EVOLUTION}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.URL_EVOLUTION.rstrip('/')}/instance/connect/{instance_name}",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            logger.error("Falha ao renovar QR: %s", exc)
            return f"Falha ao renovar QR: {exc}"

        qr_base64 = str(data.get("base64") or "")
        if qr_base64:
            if "," in qr_base64:
                qr_base64 = qr_base64.split(",", 1)[1]
            self.qr_output.write_bytes(base64.b64decode(qr_base64))
            return f"QR atualizado em {self.qr_output.resolve()}"

        pairing_code = data.get("pairingCode")
        if pairing_code:
            return f"Pairing code: {pairing_code}"

        return f"Sem QR novo. Resposta: {data}"

    def _recent_uploads(self, arg: str) -> str:
        try:
            limit = int(arg) if arg else 5
        except ValueError:
            limit = 5
        limit = max(1, min(limit, 20))

        root = Path(settings.WHATSAPP_UPLOADS_DIR)
        if not root.exists():
            return "Nenhum upload salvo ainda."

        files = [
            path for path in root.rglob("*")
            if path.is_file() and not path.name.endswith(".json")
        ]
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        if not files:
            return "Nenhum upload salvo ainda."

        lines = ["Ultimos uploads:"]
        for path in files[:limit]:
            try:
                relative = path.relative_to(root)
            except ValueError:
                relative = path
            lines.append(f"- {relative}")
        return "\n".join(lines)


admin_command_service = AdminCommandService()
