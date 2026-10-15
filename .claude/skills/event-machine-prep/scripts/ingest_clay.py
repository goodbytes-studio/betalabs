#!/usr/bin/env python3
"""Étape 4 : réintégrer l'export Clay enrichi, après revue humaine.

  ingest_clay.py propose --export clay-export.csv --icps icps.json --out 04-clay-ingest
  ingest_clay.py apply   --review 04-clay-ingest/clay-review.csv --accounts accounts-prevalidated.csv \
                         --out 04-clay-ingest

`propose` écrit clay-review.csv (une ligne par CA, fourchette estimée, modèle d'affaires ou signal).
`approve` est prérempli à `yes` seulement quand la preuve est complète : CA numérique en CAD, daté,
sourcé et non estimé ; fourchette estimée lisible avec devise ; signal yes/no avec URL HTTPS et
citation. Une personne relit avant `apply` (une fourchette invraisemblable se rejette ici).

`apply` écrit accounts-final.csv (CA vérifié seulement pour les lignes approuvées ; sinon CA brut)
et evidence-final.csv (confiance `high` seulement pour les signaux approuvés).
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from _common import BUSINESS_MODELS, is_https, read_csv, read_json, today, write_csv, yes

REVIEW_FIELDS = ["account_id", "domain", "name", "kind", "field", "value", "currency", "year", "is_estimate",
                 "source_url", "quote", "problem", "approve"]
MULT = {"k": 1e3, "m": 1e6, "mm": 1e6, "b": 1e9, "g": 1e9}


def parse_amount(raw: str) -> float | None:
    text = str(raw or "").strip().lower().replace("$", "").replace("cad", "").replace("usd", "")
    text = text.replace(" ", " ").replace(" ", "")
    if not text:
        return None
    if re.search(r"\d[-–]\d", text):
        return None  # fourchette : pas un montant
    if re.fullmatch(r"\d{1,3}([,.]\d{3})+", text):
        text = re.sub(r"[,.]", "", text)  # séparateurs de milliers
    match = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)(k|mm|m|b|g)?", text)
    if not match:
        return None
    return float(match.group(1).replace(",", ".")) * MULT.get(match.group(2) or "", 1)


def signal_fields(icps: dict) -> list[str]:
    return list(dict.fromkeys(s["field"] for c in icps.get("clients", []) for s in c.get("signals", [])))


def propose(args) -> None:
    rows = read_csv(args.export)
    if not rows:
        raise SystemExit("Export Clay vide")
    signals = signal_fields(read_json(args.icps))
    missing_cols = [c for c in ["account_id", "domain", "revenue_raw"] + signals if c not in rows[0]]
    review = []
    for row in rows:
        base = {"account_id": row.get("account_id") or row.get("domain", ""), "domain": row.get("domain", ""),
                "name": row.get("name", "")}
        raw = row.get("revenue_raw", "")
        if raw:
            amount = parse_amount(raw)
            currency = (row.get("revenue_currency") or "").strip().upper()
            year = (row.get("revenue_year") or "").strip()
            url = row.get("revenue_source_url", "")
            estimate = yes(row.get("revenue_is_estimate"))
            problems = []
            if amount is None:
                problems.append("montant_non_numerique")
            if currency != "CAD":
                problems.append("devise_non_cad")
            if not re.fullmatch(r"20\d{2}", year):
                problems.append("annee_absente")
            if not is_https(url):
                problems.append("source_absente")
            if estimate:
                problems.append("estimation")
            review.append({**base, "kind": "revenue", "field": "revenue", "value": "" if amount is None else f"{amount:.0f}",
                           "currency": currency, "year": year, "is_estimate": "yes" if estimate else "",
                           "source_url": url, "quote": raw, "problem": " ".join(problems),
                           "approve": "" if problems else "yes"})
        band = (row.get("revenue_estimate_band") or "").strip()
        if band:
            band_currency = (row.get("revenue_estimate_currency") or "").strip().upper()
            problems = [p for p, bad in (("fourchette_illisible", not re.fullmatch(r"[\d.]+[kmbtKMBT]?-[\d.]+[kmbtKMBT]?", band.replace(" ", "").replace("$", ""))),
                                         ("devise_absente", band_currency not in {"CAD", "USD"})) if bad]
            review.append({**base, "kind": "revenue_estimate", "field": "revenue_estimate_band", "value": band,
                           "currency": band_currency, "is_estimate": "yes",
                           "source_url": row.get("revenue_estimate_source", "Clay"),
                           "problem": " ".join(problems), "approve": "" if problems else "yes"})
        model = (row.get("business_model") or "").strip().lower()
        model_url = row.get("business_model_source_url", "")
        if model and model_url:
            problems = [p for p, bad in (("valeur_non_permise", model not in BUSINESS_MODELS),
                                         ("source_absente", not is_https(model_url))) if bad]
            review.append({**base, "kind": "business_model", "field": "business_model", "value": model,
                           "source_url": model_url, "problem": " ".join(problems), "approve": "" if problems else "yes"})
        for s in signals:
            value = (row.get(s) or "").strip().lower()
            if not value:
                continue
            url, quote = row.get(f"{s}_source_url", ""), row.get(f"{s}_quote", "")
            problems = [p for p, bad in (("valeur_non_yes_no", value not in {"yes", "no"}),
                                         ("source_absente", not is_https(url)),
                                         ("citation_absente", len(quote.strip()) < 3)) if bad]
            review.append({**base, "kind": "signal", "field": s, "value": value, "source_url": url, "quote": quote,
                           "problem": " ".join(problems), "approve": "" if problems else "yes"})
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / "clay-review.csv"
    write_csv(out, review, REVIEW_FIELDS)
    by = Counter((r["field"], "auto_yes" if r["approve"] else "à revoir") for r in review)
    print(json.dumps({"companies": len(rows), "review_rows": len(review), "missing_columns": missing_cols,
                      "by_field": {f"{k[0]}:{k[1]}": v for k, v in sorted(by.items())}, "review": str(out)},
                     ensure_ascii=False, indent=1))


def apply(args) -> None:
    accounts = read_csv(args.accounts)
    primary = [r for r in accounts if r.get("source") != "alias"]
    by_id = {r["account_id"]: r for r in primary}
    by_domain = {r.get("domain"): r for r in primary if r.get("domain")}
    evidence, applied = [], Counter()
    checked = args.checked_at or today()
    for row in read_csv(args.review):
        account = by_id.get(row["account_id"]) or by_domain.get(row.get("domain"))
        if not account:
            applied["compte_inconnu"] += 1
            continue
        ok = yes(row.get("approve"))
        if row["kind"] == "revenue":
            # Le moteur lit le CA dans la colonne `revenue` ; `revenue_raw` garde la valeur Clay d'origine.
            account["revenue"] = row["value"] or row.get("quote", "")
            account["revenue_raw"] = row.get("quote", "")
            account["revenue_currency"] = row.get("currency", "")
            account["revenue_year"] = row.get("year", "")
            account["revenue_source_url"] = row.get("source_url", "")
            account["revenue_verified"] = "yes" if ok else ""
            applied["revenue_verified" if ok else "revenue_raw_only"] += 1
        elif row["kind"] == "revenue_estimate":
            if ok:
                account["revenue_estimate_band"] = row["value"]
                account["revenue_estimate_currency"] = row.get("currency", "")
                account["revenue_estimate_source"] = row.get("source_url", "")
            applied["revenue_estimate" if ok else "revenue_estimate_rejected"] += 1
        elif row["kind"] == "business_model" and ok:
            account["business_model"] = row["value"]
            account["business_model_source_url"] = row["source_url"]
            applied["business_model"] += 1
        elif row["kind"] == "signal":
            if not is_https(row.get("source_url", "")):
                applied["signal_sans_source"] += 1
                continue
            evidence.append({"domain_join_key": account.get("domain") or row.get("domain"), "field": row["field"],
                             "value": row["value"], "source_url": row["source_url"], "checked_at": checked,
                             "confidence": "high" if ok else "medium",
                             "caveat": (row.get("quote") or "")[:300] + ("" if ok else " [non approuvé]")})
            applied[f"signal_{'high' if ok else 'medium'}"] += 1
    args.out.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in accounts for k in r))
    write_csv(args.out / "accounts-final.csv", accounts, fields)
    write_csv(args.out / "evidence-final.csv", evidence,
              ["domain_join_key", "field", "value", "source_url", "checked_at", "confidence", "caveat"])
    print(json.dumps({"applied": dict(applied), "accounts": str(args.out / "accounts-final.csv"),
                      "evidence": str(args.out / "evidence-final.csv")}, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose")
    p.add_argument("--export", required=True, type=Path)
    p.add_argument("--icps", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = sub.add_parser("apply")
    a.add_argument("--review", required=True, type=Path)
    a.add_argument("--accounts", required=True, type=Path)
    a.add_argument("--out", required=True, type=Path)
    a.add_argument("--checked-at", help="date de vérification des preuves (défaut : aujourd'hui)")
    args = ap.parse_args()
    {"propose": propose, "apply": apply}[args.cmd](args)


if __name__ == "__main__":
    main()
