"""Shared helpers: locate the event machine and reuse its parsing rules."""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path


def find_repo(start: Path | None = None) -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve()]
    if start:
        candidates.insert(0, start)
    for base in candidates:
        for folder in [base, *base.parents]:
            if (folder / "event_machine" / "core.py").is_file():
                return folder
    raise SystemExit("Dépôt betalabs introuvable : lancer depuis le dépôt ou passer --repo")


def load_core(repo: Path | None = None):
    root = find_repo(repo)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from event_machine import core  # noqa: E402
    return core


def read_csv(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fields or list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def today() -> str:
    return date.today().isoformat()


ORG_TYPES = ["retailer", "seller", "manufacturer", "ecosystem"]
BUSINESS_MODELS = ["b2c", "b2b", "b2b b2c"]
SENIORITY = ["executive", "vp_clevel", "director", "manager"]
DECISION_LEVELS = {"executive", "vp_clevel", "director"}
# Agents may answer with these research fields; anything else is rejected.
RESEARCH_FIELDS = ["org_type", "sector", "business_model", "country"]


def is_https(url: str) -> bool:
    return str(url or "").strip().lower().startswith("https://")


def yes(value: str) -> bool:
    return str(value or "").strip().casefold() in {"yes", "oui", "y", "o", "true", "1", "x"}
