#!/usr/bin/env python3
"""Étape 3 : CSV d'import Clay pour l'enrichissement final.

  clay_export.py --accounts accounts-prevalidated.csv --matches <run>/matches.csv \
                 --icps icps.json --out 03-clay/clay-enrichment-import.csv

Garde les entreprises détaillantes (selon le moteur) qui portent au moins un match `possible` ou
`à confirmer` : les autres ne peuvent pas devenir `fort`. `--include-unknown` ajoute les types
inconnus, à éviter tant que la recherche ne les a pas qualifiés (crédits Clay). Ajoute des colonnes
vides pour le CA, le modèle d'affaires et chaque signal des ICP.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from _common import read_csv, read_json, write_csv

BASE = ["account_id", "domain", "name", "website_url", "linkedin_url", "industry", "estimated_num_employees",
        "country", "org_type", "sector", "business_model", "clients_concerned", "candidate_people",
        "best_status", "priority_hint"]
REVENUE = ["revenue_raw", "revenue_currency", "revenue_year", "revenue_source_url", "revenue_is_estimate",
           "revenue_estimate_band", "revenue_estimate_currency", "business_model_source_url"]
RANK = {"fort": 3, "possible": 2, "à confirmer": 1, "exclu": 0}


def signal_fields(icps: dict) -> list[str]:
    return list(dict.fromkeys(s["field"] for c in icps.get("clients", []) for s in c.get("signals", [])))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accounts", required=True, type=Path)
    ap.add_argument("--matches", required=True, type=Path)
    ap.add_argument("--icps", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--include-unknown", action="store_true", help="inclure les organisations de type inconnu")
    args = ap.parse_args()

    accounts = {r["account_id"]: r for r in read_csv(args.accounts) if r.get("source") != "alias"}
    icps = read_json(args.icps)
    signals = signal_fields(icps)
    keep = {"retailer", "unknown"} if args.include_unknown else {"retailer"}
    agg: dict[str, dict] = defaultdict(lambda: {"clients": set(), "people": set(), "best": 0, "score": 0,
                                                "org": "", "sector": ""})
    for m in read_csv(args.matches):
        if m["machine_status"] == "exclu" or m["org_type"] not in keep:
            continue
        a = agg[m["account_id"]]
        a["clients"].add(m["client_id"])
        a["people"].add(m["person_id"])
        a["best"] = max(a["best"], RANK.get(m["machine_status"], 0))
        a["score"] = max(a["score"], int(m["priority_score"] or 0))
        a["org"], a["sector"] = m["org_type"], m["sector"]
    rows = []
    for key, a in agg.items():
        acc = accounts.get(key, {"account_id": key})
        if not acc.get("domain"):
            continue  # Clay a besoin d'un domaine pour enrichir
        row = {k: acc.get(k, "") for k in BASE}
        row.update({"org_type": acc.get("org_type") or a["org"],
                    "sector": acc.get("sector") or ("" if a["sector"] == "unknown" else a["sector"]),
                    "clients_concerned": " ".join(sorted(a["clients"])), "candidate_people": len(a["people"]),
                    "best_status": {v: k for k, v in RANK.items()}[a["best"]], "priority_hint": a["score"]})
        for k in REVENUE:
            row[k] = acc.get(k, "") if k != "revenue_is_estimate" else ""
        row["revenue_raw"] = acc.get("revenue_raw") or acc.get("revenue", "")
        for s in signals:
            row[s] = row[f"{s}_source_url"] = row[f"{s}_quote"] = ""
        rows.append(row)
    rows.sort(key=lambda r: (-RANK[r["best_status"]], -int(r["candidate_people"]), -int(r["priority_hint"])))
    fields = BASE + REVENUE + [x for s in signals for x in (s, f"{s}_source_url", f"{s}_quote")]
    write_csv(args.out, rows, fields)
    skipped = sum(1 for k in agg if not accounts.get(k, {}).get("domain"))
    print(json.dumps({"companies": len(rows), "skipped_without_domain": skipped, "signals": signals,
                      "file": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
