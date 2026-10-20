#!/usr/bin/env python3
"""Estimation du CA par agents : fusion des réponses en un CSV de revue, puis application après revue.

  revenue_estimate.py propose --dir 03-estimation-ca --accounts accounts.csv --out 03-estimation-ca
  revenue_estimate.py apply --review 03-estimation-ca/revenue-estimate-review.csv --accounts accounts.csv --out accounts-new.csv

`propose` n'approuve rien : toute estimation passe par une revue humaine (colonne `approve`). `apply` écrit la
fourchette dans `revenue_estimate_band` (CAD), jamais dans `revenue_raw`, car une estimation par calcul reste une estimation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import read_csv, write_csv, yes

FIELDS = ["account_id", "name", "current_band", "revenue_estimate_band", "low_cad", "central_cad", "high_cad", "confidence",
          "methods", "inputs_sourced", "inputs_hypothesis", "flags", "to_narrow", "problem", "approve"]


def band_text(low: float, high: float) -> str:
    def fmt(v: float) -> str:
        if v >= 1e6:
            return f"{v / 1e6:g}M"
        return f"{v / 1e3:g}K"
    return f"{fmt(low)}-{fmt(high)}"


def propose(args) -> None:
    accounts = {r["account_id"]: r for r in read_csv(args.accounts) if r.get("source") != "alias"}
    rows = []
    for path in sorted(args.dir.glob("batch-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for e in data.get("estimates", []):
            key = e.get("account_id", "")
            account = accounts.get(key, {})
            methods = e.get("methods") or []
            sourced = sum(1 for m in methods for i in m.get("inputs", []) if i.get("kind") == "sourced")
            hypo = sum(1 for m in methods for i in m.get("inputs", []) if i.get("kind") == "hypothesis")
            problems = []
            low, high = e.get("low_cad"), e.get("high_cad")
            if not methods or low is None or high is None:
                problems.append("aucune_estimation")
            elif not (low <= (e.get("central_cad") or low) <= high):
                problems.append("fourchette_incoherente")
            if str(e.get("confidence", "")).lower() == "high":
                problems.append("confiance_haute_interdite")
            band = band_text(float(low), float(high)) if low is not None and high is not None and not problems else ""
            rows.append({"account_id": key, "name": account.get("name", key), "current_band": account.get("revenue_estimate_band", ""),
                         "revenue_estimate_band": band, "low_cad": low, "central_cad": e.get("central_cad"), "high_cad": high,
                         "confidence": e.get("confidence", ""),
                         "methods": " | ".join(f"{m.get('id')}: {m.get('formula')}" for m in methods),
                         "inputs_sourced": sourced, "inputs_hypothesis": hypo, "flags": " | ".join(e.get("flags") or []),
                         "to_narrow": " | ".join(e.get("to_narrow") or []), "problem": " ".join(problems), "approve": ""})
    write_csv(args.out / "revenue-estimate-review.csv", rows, FIELDS)
    print(json.dumps({"estimates": len(rows), "without_band": sum(1 for r in rows if not r["revenue_estimate_band"]),
                      "review": str(args.out / "revenue-estimate-review.csv")}, ensure_ascii=False))


def apply(args) -> None:
    accounts = read_csv(args.accounts)
    by_id = {r["account_id"]: r for r in accounts if r.get("source") != "alias"}
    applied = 0
    for row in read_csv(args.review):
        if not yes(row.get("approve")) or not row.get("revenue_estimate_band"):
            continue
        account = by_id.get(row["account_id"])
        if not account:
            continue
        account["revenue_estimate_band"] = row["revenue_estimate_band"]
        account["revenue_estimate_currency"] = "CAD"
        account["revenue_estimate_source"] = f"Estimation par calcul (agent, confiance {row['confidence']}) : {row['methods']}"[:400]
        applied += 1
    fields = list(dict.fromkeys(k for r in accounts for k in r))
    write_csv(args.out, accounts, fields)
    print(json.dumps({"applied": applied, "accounts": str(args.out)}, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose")
    p.add_argument("--dir", required=True, type=Path)
    p.add_argument("--accounts", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = sub.add_parser("apply")
    a.add_argument("--review", required=True, type=Path)
    a.add_argument("--accounts", required=True, type=Path)
    a.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    {"propose": propose, "apply": apply}[args.cmd](args)


if __name__ == "__main__":
    main()
