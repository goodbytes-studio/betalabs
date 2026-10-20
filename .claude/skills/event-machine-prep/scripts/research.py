#!/usr/bin/env python3
"""Étape 2 : lots pour les agents de recherche, fusion de leurs réponses, application après revue.

  research.py split   --queue research-queue.csv --size 15 --out 02-research
  research.py propose --research-dir 02-research --accounts accounts-normalized.csv --out 02-research
  research.py apply   --review 02-research/research-review.csv --accounts accounts-normalized.csv \
                      --out accounts-prevalidated.csv

`propose` écrit research-review.csv avec une colonne `approve` préremplie (`yes` seulement pour une
confiance haute, une URL HTTPS et une citation). Une personne relit et corrige avant `apply`.
Seules les lignes `approve=yes` deviennent des entrées entreprise ; les autres restent inconnues.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from _common import (BUSINESS_MODELS, FRANCHISE_VALUES, ORG_TYPES, RESEARCH_FIELDS, is_https, load_core, read_csv,
                     write_csv, yes)

REVIEW_FIELDS = ["account_id", "name", "field", "current_value", "proposed_value", "confidence",
                 "source_url", "quote", "quote_from", "domain_matches_name", "notes", "problem", "approve"]


def split(args) -> None:
    rows = read_csv(args.queue)
    args.out.mkdir(parents=True, exist_ok=True)
    batches = [rows[i:i + args.size] for i in range(0, len(rows), args.size)]
    for n, batch in enumerate(batches, 1):
        write_csv(args.out / f"batch-{n:02d}.csv", batch)
    print(json.dumps({"batches": len(batches), "companies": len(rows), "dir": str(args.out)}))


def allowed_values(field: str, core) -> set[str]:
    if field == "org_type":
        return set(ORG_TYPES)
    if field == "sector":
        return set(core.SECTOR_TERMS) | {"other"}
    if field == "business_model":
        return set(BUSINESS_MODELS)
    if field == "franchise":
        return set(FRANCHISE_VALUES)
    return set()


def propose(args) -> None:
    core = load_core(args.repo)
    accounts = {r["account_id"]: r for r in read_csv(args.accounts) if r.get("source") != "alias"}
    review, errors = [], []
    files = sorted(args.research_dir.glob("batch-*.json"))
    if not files:
        raise SystemExit(f"Aucun batch-*.json dans {args.research_dir}")
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name} : JSON invalide ({exc})")
            continue
        for company in data.get("companies", []):
            key = company.get("account_id", "")
            account = accounts.get(key)
            if not account:
                errors.append(f"{path.name} : account_id inconnu « {key} »")
                continue
            fields = company.get("fields") or []
            if not fields:
                review.append({"account_id": key, "name": account["name"], "field": "", "notes": company.get("notes", ""),
                               "domain_matches_name": company.get("domain_matches_name", ""),
                               "problem": "aucun_resultat", "approve": ""})
            for item in fields:
                field = item.get("field", "")
                value = str(item.get("value", "")).strip()
                if field != "leader":
                    value = value.lower()
                problems = []
                if field not in RESEARCH_FIELDS:
                    problems.append("champ_non_permis")
                permitted = allowed_values(field, core)
                if permitted and value not in permitted:
                    problems.append("valeur_non_permise")
                if field == "employees" and not re.fullmatch(r"\d{1,6}", value):
                    problems.append("valeur_non_permise")
                if not is_https(item.get("source_url", "")):
                    problems.append("url_non_https")
                if len(str(item.get("quote", ""))) < 12:
                    problems.append("citation_absente")
                if company.get("domain_matches_name") is False:
                    problems.append("domaine_a_verifier")
                if field == "sector" and value == "other":
                    problems.append("secteur_hors_vocabulaire")
                confidence = str(item.get("confidence", "low")).lower()
                quote_from = str(item.get("quote_from", "")).lower()
                if quote_from != "page":
                    problems.append("citation_non_verifiee_sur_page")
                review.append({
                    "account_id": key, "name": account["name"], "field": field,
                    "current_value": account.get(field, ""), "proposed_value": value,
                    "confidence": confidence, "source_url": item.get("source_url", ""),
                    "quote": item.get("quote", ""), "quote_from": quote_from, "domain_matches_name": company.get("domain_matches_name", ""),
                    "notes": company.get("notes", ""), "problem": " ".join(problems),
                    "approve": "yes" if confidence == "high" and not problems else "",
                })
    out = args.out / "research-review.csv"
    write_csv(out, review, REVIEW_FIELDS)
    counts = Counter((r["field"] or "aucun", "auto_yes" if r["approve"] else "à revoir") for r in review)
    summary = {"rows": len(review), "auto_approved": sum(1 for r in review if r["approve"]),
               "to_review": sum(1 for r in review if not r["approve"]), "errors": errors,
               "by_field": {f"{k[0]}:{k[1]}": v for k, v in sorted(counts.items())}, "review": str(out)}
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def apply(args) -> None:
    accounts = read_csv(args.accounts)
    by_id = {r["account_id"]: r for r in accounts if r.get("source") != "alias"}
    applied, skipped = Counter(), Counter()
    for row in read_csv(args.review):
        if not yes(row.get("approve")) or not row.get("field"):
            skipped[row.get("field") or "aucun"] += 1
            continue
        account = by_id.get(row["account_id"])
        if not account:
            skipped["compte_inconnu"] += 1
            continue
        field, value, url = row["field"], row["proposed_value"].strip(), row["source_url"]
        if field != "leader":
            value = value.lower()
        if field == "sector" and value == "other":
            # « other » approuvé reste un secteur connu : le moteur le fait valider au lieu de l'exclure.
            account["sector_detail"] = row.get("notes", "") or "other"
        account[field] = value
        if field in ("sector", "business_model", "org_type"):
            account[f"{field}_source_url"] = url
        account["research_checked"] = "yes"
        applied[field] += 1
    fields = list(dict.fromkeys(k for r in accounts for k in r))
    for extra in ("org_type_source_url", "sector_detail", "research_checked"):
        if extra not in fields:
            fields.append(extra)
    write_csv(args.out, accounts, fields)
    print(json.dumps({"applied": dict(applied), "skipped": dict(skipped), "accounts": str(args.out)}, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("--queue", required=True, type=Path)
    s.add_argument("--size", type=int, default=15)
    s.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("propose")
    p.add_argument("--research-dir", required=True, type=Path)
    p.add_argument("--accounts", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--repo", type=Path)
    a = sub.add_parser("apply")
    a.add_argument("--review", required=True, type=Path)
    a.add_argument("--accounts", required=True, type=Path)
    a.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    {"split": split, "propose": propose, "apply": apply}[args.cmd](args)


if __name__ == "__main__":
    main()
