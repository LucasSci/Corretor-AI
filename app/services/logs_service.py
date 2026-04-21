from collections import deque
from pathlib import Path

from app.core.config import settings


def _tail_file(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        return list(deque((line.rstrip("\n") for line in fh), maxlen=limit))


def tail_logs(limit: int = 200, source: str = "combined") -> dict[str, list[str]]:
    safe_limit = max(1, min(limit, 500))
    output_path = Path(settings.OUTPUT_LOG_PATH)
    error_path = Path(settings.ERROR_LOG_PATH)

    if source == "stdout":
        return {"stdout": _tail_file(output_path, safe_limit), "stderr": []}
    if source == "stderr":
        return {"stdout": [], "stderr": _tail_file(error_path, safe_limit)}
    return {
        "stdout": _tail_file(output_path, safe_limit),
        "stderr": _tail_file(error_path, safe_limit),
    }
