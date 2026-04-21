import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_DESKTOP_SETTINGS_PATH = "data/desktop_settings.json"

DEFAULT_SETTINGS_DOCUMENT: dict[str, Any] = {
    "llm": {
        "provider": "gemini",
        "modelName": "gemini-2.5-flash",
        "geminiApiKey": "",
        "openaiApiKey": "",
        "temperature": 0.6,
        "chromaK": 4,
    },
    "evolution": {
        "baseUrl": "http://127.0.0.1:8080",
        "apiKey": "",
        "instance": "BotRiva1",
        "webhookUrl": "http://host.docker.internal:8000/webhook",
    },
    "storage": {
        "dbUrl": "sqlite+aiosqlite:///./data/app.db",
        "uploadsDir": "data/whatsapp_uploads",
        "mediaAutoSave": True,
    },
    "network": {
        "host": "0.0.0.0",
        "port": 8000,
        "corsOrigins": [
            "http://127.0.0.1:1420",
            "http://localhost:1420",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
    },
    "operator": {
        "allowedNumbers": "",
        "commandNumbers": "",
        "testNumber": "",
        "botNumber": "",
        "allowFromMeTest": True,
        "loopGuardTtlSec": 30,
    },
}


def resolve_settings_path(raw_path: str | os.PathLike[str] | None = None) -> Path:
    value = str(raw_path or os.getenv("DESKTOP_SETTINGS_PATH") or DEFAULT_DESKTOP_SETTINGS_PATH)
    return Path(value).expanduser()


def deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def read_settings_document(raw_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    path = resolve_settings_path(raw_path)
    if not path.exists():
        return deepcopy(DEFAULT_SETTINGS_DOCUMENT)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return deepcopy(DEFAULT_SETTINGS_DOCUMENT)
        return deep_merge_dict(DEFAULT_SETTINGS_DOCUMENT, data)
    except Exception:
        return deepcopy(DEFAULT_SETTINGS_DOCUMENT)


def write_settings_document(document: dict[str, Any], raw_path: str | os.PathLike[str] | None = None) -> Path:
    path = resolve_settings_path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def flatten_settings_document(document: dict[str, Any]) -> dict[str, Any]:
    llm = document.get("llm", {})
    evolution = document.get("evolution", {})
    storage = document.get("storage", {})
    network = document.get("network", {})
    operator = document.get("operator", {})

    return {
        "MODEL_NAME": llm.get("modelName"),
        "GEMINI_API_KEY": llm.get("geminiApiKey"),
        "OPENAI_API_KEY": llm.get("openaiApiKey"),
        "AI_TEMPERATURE": llm.get("temperature"),
        "CHROMA_K": llm.get("chromaK"),
        "URL_EVOLUTION": evolution.get("baseUrl"),
        "API_KEY_EVOLUTION": evolution.get("apiKey"),
        "EVOLUTION_INSTANCE": evolution.get("instance"),
        "EVOLUTION_WEBHOOK_URL": evolution.get("webhookUrl"),
        "DB_URL": storage.get("dbUrl"),
        "WHATSAPP_UPLOADS_DIR": storage.get("uploadsDir"),
        "WHATSAPP_MEDIA_AUTO_SAVE": storage.get("mediaAutoSave"),
        "HOST": network.get("host"),
        "PORT": network.get("port"),
        "CORS_ORIGINS": network.get("corsOrigins"),
        "WHATSAPP_ALLOWED_NUMBERS": operator.get("allowedNumbers"),
        "WHATSAPP_COMMAND_NUMBERS": operator.get("commandNumbers"),
        "WHATSAPP_TEST_NUMBER": operator.get("testNumber"),
        "WHATSAPP_BOT_NUMBER": operator.get("botNumber"),
        "ALLOW_FROM_ME_TEST": operator.get("allowFromMeTest"),
        "WEBHOOK_LOOP_GUARD_TTL_SEC": operator.get("loopGuardTtlSec"),
    }
