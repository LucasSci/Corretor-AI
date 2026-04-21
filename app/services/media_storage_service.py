import base64
import json
import logging
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

MEDIA_KEY_TO_TYPE = {
    "documentMessage": "document",
    "imageMessage": "image",
    "videoMessage": "video",
    "audioMessage": "audio",
    "stickerMessage": "sticker",
}


class WhatsAppMediaStorageService:
    def __init__(self) -> None:
        self.reload_from_settings()

    def reload_from_settings(self) -> None:
        self.root_dir = Path(settings.WHATSAPP_UPLOADS_DIR)

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        token = (settings.API_KEY_EVOLUTION or "").strip()
        if not token:
            return headers
        if token.lower().startswith("bearer "):
            headers["Authorization"] = token
        else:
            headers["apikey"] = token
        return headers

    @staticmethod
    def _sanitize_stem(name: str) -> str:
        name = (name or "").strip()
        if not name:
            return "arquivo"
        stem = Path(name).stem or "arquivo"
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
        return stem.strip("._-") or "arquivo"

    @staticmethod
    def _extract_name(media_obj: Dict[str, Any], media_type: str) -> str:
        for key in ("fileName", "file_name", "name", "title"):
            value = media_obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return f"{media_type}_arquivo"

    @staticmethod
    def _guess_extension(media_obj: Dict[str, Any], media_type: str) -> str:
        # Prefer extension from original file name when present.
        file_name = WhatsAppMediaStorageService._extract_name(media_obj, media_type)
        suffix = Path(file_name).suffix
        if suffix:
            return suffix.lower()

        mimetype = str(media_obj.get("mimetype") or "").strip().lower()
        guessed = mimetypes.guess_extension(mimetype) if mimetype else None
        if guessed:
            return guessed

        fallback = {
            "document": ".bin",
            "image": ".jpg",
            "video": ".mp4",
            "audio": ".ogg",
            "sticker": ".webp",
        }
        return fallback.get(media_type, ".bin")

    @staticmethod
    def _extract_base64(media_obj: Dict[str, Any], data_obj: Dict[str, Any]) -> Optional[str]:
        for key in ("base64", "fileBase64", "mediaBase64"):
            value = media_obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        # Algumas variantes trazem base64 no objeto data raiz.
        for key in ("base64", "fileBase64", "mediaBase64"):
            value = data_obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    @staticmethod
    def _decode_base64(raw_value: str) -> Optional[bytes]:
        raw = (raw_value or "").strip()
        if not raw:
            return None
        if ";base64," in raw:
            raw = raw.split(";base64,", 1)[1]

        try:
            return base64.b64decode(raw, validate=True)
        except Exception:
            try:
                return base64.b64decode(raw)
            except Exception:
                return None

    @staticmethod
    def _extract_urls(media_obj: Dict[str, Any]) -> List[str]:
        urls: List[str] = []

        for key in ("url", "mediaUrl", "downloadUrl"):
            value = media_obj.get(key)
            if isinstance(value, str) and value.strip():
                urls.append(value.strip())

        direct_path = media_obj.get("directPath")
        if isinstance(direct_path, str) and direct_path.strip() and settings.URL_EVOLUTION:
            base = settings.URL_EVOLUTION.rstrip("/")
            path = direct_path if direct_path.startswith("/") else f"/{direct_path}"
            urls.append(f"{base}{path}")

        # Dedup mantendo ordem.
        seen = set()
        unique_urls: List[str] = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        return unique_urls

    async def _download_bytes(self, urls: List[str]) -> Tuple[Optional[bytes], Optional[str]]:
        if not urls:
            return None, None

        headers = self._build_headers()
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = await client.get(url, headers=headers)
                    if 200 <= resp.status_code < 300 and resp.content:
                        return resp.content, url
                except Exception:
                    continue
        return None, None

    @staticmethod
    def _ensure_unique_path(path: Path) -> Path:
        if not path.exists():
            return path
        idx = 1
        while True:
            candidate = path.with_name(f"{path.stem}_{idx}{path.suffix}")
            if not candidate.exists():
                return candidate
            idx += 1

    async def save_incoming_media(
        self,
        payload: Dict[str, Any],
        message_obj: Dict[str, Any],
        remote_jid: str,
    ) -> List[Dict[str, Any]]:
        if not settings.WHATSAPP_MEDIA_AUTO_SAVE:
            return []

        data_obj = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        saved: List[Dict[str, Any]] = []

        for key, media_type in MEDIA_KEY_TO_TYPE.items():
            media_obj = message_obj.get(key)
            if not isinstance(media_obj, dict):
                continue

            media_bytes: Optional[bytes] = None
            source = "unknown"

            b64_value = self._extract_base64(media_obj, data_obj)
            if b64_value:
                decoded = self._decode_base64(b64_value)
                if decoded:
                    media_bytes = decoded
                    source = "base64"

            if media_bytes is None:
                urls = self._extract_urls(media_obj)
                media_bytes, download_url = await self._download_bytes(urls)
                if media_bytes is not None:
                    source = download_url or "url"

            if media_bytes is None:
                logger.warning("Falha ao salvar midia (%s) para %s: sem bytes disponiveis", key, remote_jid)
                continue

            original_name = self._extract_name(media_obj, media_type)
            extension = self._guess_extension(media_obj, media_type)
            safe_stem = self._sanitize_stem(original_name)
            now_utc = datetime.now(timezone.utc)
            timestamp = now_utc.strftime("%Y%m%d_%H%M%S_%f")

            date_dir = now_utc.strftime("%Y-%m-%d")
            target_dir = self.root_dir / media_type / date_dir
            target_dir.mkdir(parents=True, exist_ok=True)

            file_path = target_dir / f"{timestamp}_{safe_stem}{extension}"
            file_path = self._ensure_unique_path(file_path)
            file_path.write_bytes(media_bytes)

            metadata = {
                "saved_at": now_utc.isoformat(),
                "remote_jid": remote_jid,
                "media_type": media_type,
                "source": source,
                "original_name": original_name,
                "mimetype": media_obj.get("mimetype", ""),
                "bytes": len(media_bytes),
                "saved_path": str(file_path),
            }

            metadata_path = file_path.with_suffix(file_path.suffix + ".json")
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            saved.append(metadata)
            logger.info("Arquivo salvo: %s", file_path)

        return saved


whatsapp_media_storage_service = WhatsAppMediaStorageService()
