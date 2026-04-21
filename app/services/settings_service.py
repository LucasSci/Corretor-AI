from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import settings
from app.core.desktop_settings import (
    DEFAULT_SETTINGS_DOCUMENT,
    deep_merge_dict,
    flatten_settings_document,
    resolve_settings_path,
    write_settings_document,
)
from app.services.ai_service import ai_service
from app.services.evolution_service import evolution_service
from app.services.media_storage_service import whatsapp_media_storage_service
from app.services.whatsapp_service import whatsapp_service


def _document_from_runtime() -> dict[str, Any]:
    return {
        "llm": {
            "provider": "gemini",
            "modelName": settings.MODEL_NAME,
            "geminiApiKey": settings.GEMINI_API_KEY,
            "openaiApiKey": settings.OPENAI_API_KEY or "",
            "temperature": settings.AI_TEMPERATURE,
            "chromaK": settings.CHROMA_K,
        },
        "evolution": {
            "baseUrl": settings.URL_EVOLUTION,
            "apiKey": settings.API_KEY_EVOLUTION,
            "instance": settings.EVOLUTION_INSTANCE,
            "webhookUrl": settings.EVOLUTION_WEBHOOK_URL,
        },
        "storage": {
            "dbUrl": settings.DB_URL,
            "uploadsDir": settings.WHATSAPP_UPLOADS_DIR,
            "mediaAutoSave": settings.WHATSAPP_MEDIA_AUTO_SAVE,
        },
        "network": {
            "host": settings.HOST,
            "port": settings.PORT,
            "corsOrigins": list(settings.CORS_ORIGINS),
        },
        "operator": {
            "allowedNumbers": settings.WHATSAPP_ALLOWED_NUMBERS,
            "commandNumbers": settings.WHATSAPP_COMMAND_NUMBERS,
            "testNumber": settings.WHATSAPP_TEST_NUMBER,
            "botNumber": settings.WHATSAPP_BOT_NUMBER,
            "allowFromMeTest": settings.ALLOW_FROM_ME_TEST,
            "loopGuardTtlSec": settings.WEBHOOK_LOOP_GUARD_TTL_SEC,
        },
    }


def _normalize_settings_document(payload: dict[str, Any] | None) -> dict[str, Any]:
    merged = deep_merge_dict(_document_from_runtime(), payload or {})
    merged = deep_merge_dict(DEFAULT_SETTINGS_DOCUMENT, merged)
    merged["network"]["port"] = int(merged["network"].get("port") or 8000)
    merged["llm"]["temperature"] = float(merged["llm"].get("temperature") or 0.6)
    merged["llm"]["chromaK"] = int(merged["llm"].get("chromaK") or 4)
    merged["storage"]["mediaAutoSave"] = bool(merged["storage"].get("mediaAutoSave"))
    merged["operator"]["allowFromMeTest"] = bool(merged["operator"].get("allowFromMeTest"))
    merged["operator"]["loopGuardTtlSec"] = int(merged["operator"].get("loopGuardTtlSec") or 30)
    cors = merged["network"].get("corsOrigins") or []
    if isinstance(cors, str):
        cors = [item.strip() for item in cors.split(",") if item.strip()]
    merged["network"]["corsOrigins"] = cors
    return merged


def _apply_runtime_document(document: dict[str, Any]) -> None:
    flat = flatten_settings_document(document)
    settings.MODEL_NAME = str(flat.get("MODEL_NAME") or settings.MODEL_NAME)
    settings.GEMINI_API_KEY = str(flat.get("GEMINI_API_KEY") or "")
    settings.OPENAI_API_KEY = str(flat.get("OPENAI_API_KEY") or "") or None
    settings.AI_TEMPERATURE = float(flat.get("AI_TEMPERATURE") or settings.AI_TEMPERATURE)
    settings.CHROMA_K = int(flat.get("CHROMA_K") or settings.CHROMA_K)
    settings.URL_EVOLUTION = str(flat.get("URL_EVOLUTION") or settings.URL_EVOLUTION)
    settings.API_KEY_EVOLUTION = str(flat.get("API_KEY_EVOLUTION") or settings.API_KEY_EVOLUTION)
    settings.EVOLUTION_INSTANCE = str(flat.get("EVOLUTION_INSTANCE") or settings.EVOLUTION_INSTANCE)
    settings.EVOLUTION_WEBHOOK_URL = str(flat.get("EVOLUTION_WEBHOOK_URL") or settings.EVOLUTION_WEBHOOK_URL)
    settings.DB_URL = str(flat.get("DB_URL") or settings.DB_URL)
    settings.WHATSAPP_UPLOADS_DIR = str(flat.get("WHATSAPP_UPLOADS_DIR") or settings.WHATSAPP_UPLOADS_DIR)
    settings.WHATSAPP_MEDIA_AUTO_SAVE = bool(flat.get("WHATSAPP_MEDIA_AUTO_SAVE"))
    settings.HOST = str(flat.get("HOST") or settings.HOST)
    settings.PORT = int(flat.get("PORT") or settings.PORT)
    settings.CORS_ORIGINS = list(flat.get("CORS_ORIGINS") or settings.CORS_ORIGINS)
    settings.WHATSAPP_ALLOWED_NUMBERS = str(flat.get("WHATSAPP_ALLOWED_NUMBERS") or "")
    settings.WHATSAPP_COMMAND_NUMBERS = str(flat.get("WHATSAPP_COMMAND_NUMBERS") or "")
    settings.WHATSAPP_TEST_NUMBER = str(flat.get("WHATSAPP_TEST_NUMBER") or "")
    settings.WHATSAPP_BOT_NUMBER = str(flat.get("WHATSAPP_BOT_NUMBER") or "")
    settings.ALLOW_FROM_ME_TEST = bool(flat.get("ALLOW_FROM_ME_TEST"))
    settings.WEBHOOK_LOOP_GUARD_TTL_SEC = int(flat.get("WEBHOOK_LOOP_GUARD_TTL_SEC") or settings.WEBHOOK_LOOP_GUARD_TTL_SEC)

    ai_service.reload_from_settings()
    whatsapp_service.reload_from_settings()
    whatsapp_media_storage_service.reload_from_settings()


def get_current_settings_document() -> dict[str, Any]:
    return _document_from_runtime()


async def validate_settings_document(payload: dict[str, Any] | None) -> dict[str, Any]:
    document = _normalize_settings_document(payload)
    errors: list[str] = []
    warnings: list[str] = []

    def _require_http_url(name: str, raw: str) -> None:
        parsed = urlparse(raw)
        if not parsed.scheme or not parsed.netloc:
            errors.append(f"{name} precisa ser uma URL valida")

    _require_http_url("evolution.baseUrl", str(document["evolution"].get("baseUrl") or ""))
    _require_http_url("evolution.webhookUrl", str(document["evolution"].get("webhookUrl") or ""))

    uploads_dir = Path(str(document["storage"].get("uploadsDir") or "data/whatsapp_uploads"))
    try:
        uploads_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        errors.append(f"storage.uploadsDir nao pode ser criado: {exc}")

    port = int(document["network"].get("port") or 0)
    if port < 1 or port > 65535:
        errors.append("network.port precisa estar entre 1 e 65535")

    restart_required_fields = ["storage.dbUrl", "network.host", "network.port"]
    original_runtime = get_current_settings_document()

    if not errors and document["evolution"]["baseUrl"] and document["evolution"]["apiKey"]:
        try:
            _apply_runtime_document(document)
            status = await evolution_service.get_status()
            if not status.get("reachable"):
                warnings.append("Nao foi possivel validar a Evolution API com os dados informados")
        except Exception as exc:
            warnings.append(f"Falha ao validar Evolution API: {exc}")
        finally:
            _apply_runtime_document(original_runtime)

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "restart_required_fields": restart_required_fields,
        "document": document,
        "changed": document != original_runtime,
    }


async def save_settings_document(payload: dict[str, Any] | None) -> dict[str, Any]:
    validation = await validate_settings_document(payload)
    if not validation["ok"]:
        return validation

    document = validation["document"]
    write_settings_document(document, settings.DESKTOP_SETTINGS_PATH)
    _apply_runtime_document(document)
    return {
        **validation,
        "path": str(resolve_settings_path(settings.DESKTOP_SETTINGS_PATH).resolve()),
        "saved": True,
        "document": get_current_settings_document(),
    }
