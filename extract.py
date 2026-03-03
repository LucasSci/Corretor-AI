"""Backward-compatible entrypoint for extraction utilities.

This file keeps older imports (`from extract import ...`) working after the
move to `scripts/extract.py`.
"""

import sys
from pathlib import Path


def _bootstrap_local_venv() -> None:
    project_root = Path(__file__).resolve().parent
    candidates = [
        project_root / ".venv" / "Lib" / "site-packages",
        project_root / "venv" / "Lib" / "site-packages",
    ]

    for py_site in (project_root / ".venv" / "lib").glob("python*/site-packages"):
        candidates.append(py_site)
    for py_site in (project_root / "venv" / "lib").glob("python*/site-packages"):
        candidates.append(py_site)

    for site_packages in candidates:
        if site_packages.exists():
            site_path = str(site_packages)
            if site_path not in sys.path:
                sys.path.insert(0, site_path)


_bootstrap_local_venv()

from scripts.extract import *  # noqa: F401,F403


if __name__ == "__main__":
    import asyncio
    from scripts.extract import executar_automacao_completa

    asyncio.run(executar_automacao_completa())
