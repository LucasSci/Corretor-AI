import csv
from pathlib import Path
from typing import Any

DATA_PATH = Path("data/catalog.csv")

def load_catalog() -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

def match_properties(
    bairro: str | None,
    renda: float | None,
    entrada: float | None,
    fgts: bool | None,
    mcmv: bool | None,
    tipo: str | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    items = load_catalog()

    def to_float(x: str) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0

    results = []
    for it in items:
        if bairro and it["bairro"].strip().lower() != bairro.strip().lower():
            continue
        if tipo and it["tipo"].strip().lower() != tipo.strip().lower():
            continue

        renda_min = to_float(it.get("renda_min", "0"))
        entrada_min = to_float(it.get("entrada_min", "0"))
        preco = to_float(it.get("preco", "0"))

        if renda is not None and renda < renda_min:
            continue
        if entrada is not None and entrada < entrada_min:
            continue

        fgts_aceita = (it.get("fgts_aceita", "nao").lower() == "sim")
        if fgts is True and not fgts_aceita:
            continue

        is_mcmv = (it.get("mcmv", "nao").lower() == "sim")
        if mcmv is True and not is_mcmv:
            continue

        # score simples (quanto mais “perto” do mínimo, mais relevante)
        score = 0.0
        if renda is not None:
            score += max(0.0, renda - renda_min)
        if entrada is not None:
            score += max(0.0, entrada - entrada_min)

        results.append((score, {**it, "preco": preco}))

    results.sort(key=lambda x: x[0])  # mais justo primeiro
    return [r[1] for r in results[:limit]]
