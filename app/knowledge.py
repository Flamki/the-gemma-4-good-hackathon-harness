from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_knowledge(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def rank_knowledge(
    records: list[dict[str, Any]], incident: str, hazard: str, top_k: int = 4
) -> list[dict[str, Any]]:
    query = f"{incident} {hazard}".lower()
    tokens = set(query.split())
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        text = f"{record.get('title', '')} {record.get('content', '')}".lower()
        score = sum(1 for token in tokens if token in text)
        if hazard and hazard in text:
            score += 3
        if score > 0:
            scored.append((score, record))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [record for _, record in scored[:top_k]]
