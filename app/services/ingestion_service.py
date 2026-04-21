import importlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

from app.services.job_manager import JobContext


def _manual_source_files(sources: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in sources:
        path = Path(raw).expanduser()
        if not path.exists():
            continue
        if path.is_dir():
            files.extend(sorted([item for item in path.rglob("*") if item.is_file()]))
        elif path.is_file():
            files.append(path)
    return files


def _read_text_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc).strip()
    if suffix in {".txt", ".md", ".csv", ".json", ".log"}:
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    return ""


async def run_ingestion_job(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any]:
    kind = str(payload.get("kind") or "linktree_full").strip()
    if kind == "manual_documents":
        return await _run_manual_documents(ctx, payload)
    return await _run_linktree_pipeline(ctx)


async def _run_linktree_pipeline(ctx: JobContext) -> dict[str, Any]:
    await ctx.update(progress=15, message="Carregando pipeline de ingestao", log="Pipeline de ingestao carregado")
    module = importlib.import_module("scripts.ingest")

    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        await module.main()

    for line in stdout.getvalue().splitlines()[-25:]:
        clean = line.strip()
        if clean:
            await ctx.update(log=clean)
    for line in stderr.getvalue().splitlines()[-25:]:
        clean = line.strip()
        if clean:
            await ctx.update(log=f"stderr: {clean}")

    summary_path = Path("data/ingest_summary.json")
    base_path = Path("data/base_conhecimento.jsonl")
    total_items = 0
    if summary_path.exists():
        try:
            total_items = len(json.loads(summary_path.read_text(encoding="utf-8")))
        except Exception:
            total_items = 0

    await ctx.update(progress=90, message="Consolidando resultado da ingestao", log="Resumo consolidado")
    return {
        "kind": "linktree_full",
        "summary_path": str(summary_path.resolve()) if summary_path.exists() else None,
        "base_conhecimento_path": str(base_path.resolve()) if base_path.exists() else None,
        "total_items": total_items,
    }


async def _run_manual_documents(ctx: JobContext, payload: dict[str, Any]) -> dict[str, Any]:
    sources = payload.get("sources") or []
    if not isinstance(sources, list):
        raise ValueError("sources precisa ser uma lista de caminhos")

    module = importlib.import_module("scripts.ingest")
    files = _manual_source_files([str(item) for item in sources])
    if not files:
        raise ValueError("Nenhum arquivo valido encontrado para ingestao manual")

    extracted_root = Path("data/extracted/manual")
    extracted_root.mkdir(parents=True, exist_ok=True)
    base_path = Path("data/base_conhecimento.jsonl")

    processed: list[dict[str, Any]] = []
    total = len(files)
    for index, file_path in enumerate(files, start=1):
        await ctx.update(
            progress=10 + (index - 1) * (70 / max(total, 1)),
            message=f"Processando {file_path.name}",
            log=f"Lendo {file_path}",
        )
        text = _read_text_file(file_path)
        if not text:
            await ctx.update(log=f"Arquivo ignorado sem texto extraivel: {file_path.name}")
            continue

        cleaned = module.limpar_texto(text)
        chunks = module.chunk_text(cleaned, chunk_size=1000, overlap=200)
        target_jsonl = extracted_root / f"{file_path.stem}.jsonl"
        lines_written = 0
        with target_jsonl.open("w", encoding="utf-8") as fh:
            for chunk_index, chunk in enumerate(chunks):
                record = {
                    "id": f"manual#{file_path.stem}#chunk{chunk_index}",
                    "source_url": str(file_path.resolve()),
                    "site_origem": "Manual",
                    "site_slug": "manual",
                    "arquivo": file_path.name,
                    "chunk_index": chunk_index,
                    "total_chunks": len(chunks),
                    "texto": chunk,
                    "crawl_date": datetime.now(timezone.utc).isoformat(),
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                module.salvar_para_base_conhecimento(record, arquivo=str(base_path))
                lines_written += 1

        processed.append(
            {
                "file": str(file_path.resolve()),
                "jsonl": str(target_jsonl.resolve()),
                "chunks": lines_written,
            }
        )

    await ctx.update(progress=90, message="Finalizando ingestao manual", log="Arquivos manuais processados")
    return {
        "kind": "manual_documents",
        "processed_files": processed,
        "base_conhecimento_path": str(base_path.resolve()) if base_path.exists() else None,
    }
