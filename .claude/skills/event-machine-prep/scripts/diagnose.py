#!/usr/bin/env python3
"""Étape 5 : diagnostic d'une analyse de la machine, avec comparaison optionnelle.

  diagnose.py --run .event-machine/<event>/runs/final --previous .event-machine/<event>/runs/baseline \
              --out .event-machine/<event>/prep/05-diagnostic

Écrit diagnostic.md et shortlist-<client>.csv (matchs `fort` puis `possible`, triés par score).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from _common import read_csv, write_csv

STATUSES = ["fort", "possible", "à confirmer", "exclu"]
SHORTLIST_FIELDS = ["client_name", "machine_status", "priority_score", "person_name", "job_title", "company_name",
                    "sector", "relationship", "relationship_owner", "fit_reasons", "evidence_urls",
                    "opportunity_hypothesis", "next_question", "match_key"]


def counts(matches: list[dict]) -> dict[str, Counter]:
    out: dict[str, Counter] = defaultdict(Counter)
    for m in matches:
        out[m["client_id"]][m["machine_status"]] += 1
    return out


def parts(text: str) -> list[str]:
    return [p.strip() for p in (text or "").split("|") if p.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--previous", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()
    matches = read_csv(args.run / "matches.csv")
    manifest = json.loads((args.run / "run-manifest.json").read_text(encoding="utf-8"))
    prev = counts(read_csv(args.previous / "matches.csv")) if args.previous else {}
    now = counts(matches)
    names = {m["client_id"]: m["client_name"] for m in matches}
    args.out.mkdir(parents=True, exist_ok=True)

    def cell(cid: str, status: str) -> str:
        value = now[cid][status]
        if not args.previous:
            return str(value)
        delta = value - prev.get(cid, Counter())[status]
        return f"{value} ({delta:+d})" if delta else str(value)

    lines = [f"# Diagnostic — {manifest.get('event_name') or manifest.get('event_id', '')}", "",
             f"Analyse : `{args.run}`" + (f" ; comparée à `{args.previous}`" if args.previous else "") + ".", "",
             "## Résultat par client", "",
             "| Client | " + " | ".join(STATUSES) + " |", "|---|" + "---|" * len(STATUSES)]
    for cid in names:
        lines.append(f"| {names[cid]} | " + " | ".join(cell(cid, s) for s in STATUSES) + " |")

    lines += ["", "## Listes courtes", ""]
    for cid, cname in names.items():
        short = [m for m in matches if m["client_id"] == cid and m["machine_status"] in ("fort", "possible")]
        short.sort(key=lambda m: (m["machine_status"] != "fort", -int(m["priority_score"] or 0), m["company_name"]))
        write_csv(args.out / f"shortlist-{cid}.csv", short, SHORTLIST_FIELDS)
        lines += [f"### {cname} — {len(short)} matchs (`shortlist-{cid}.csv`)", ""]
        if not short:
            lines += ["Aucun match `fort` ou `possible`. Voir les blocages ci-dessous.", ""]
            continue
        lines += ["| Statut | Score | Personne | Poste | Entreprise | Relation |", "|---|---|---|---|---|---|"]
        for m in short[:args.top]:
            lines.append(f"| {m['machine_status']} | {m['priority_score']} | {m['person_name']} | {m['job_title']} | "
                         f"{m['company_name']} | {m['relationship'] or '—'} |")
        if len(short) > args.top:
            lines.append(f"| … | | {len(short) - args.top} autres dans le CSV | | | |")
        lines.append("")

    lines += ["## Ce qui empêche `possible` → `fort`", ""]
    for cid, cname in names.items():
        pending = Counter(p for m in matches if m["client_id"] == cid and m["machine_status"] == "possible"
                          for p in parts(m["fit_reasons"]) if p != "CA CAD vérifié dans la fourchette")
        if pending:
            lines.append(f"- **{cname}** : " + " ; ".join(f"{k} ({v})" for k, v in pending.most_common(5)))
    lines += ["", "## Ce qui bloque les `à confirmer`", ""]
    for cid, cname in names.items():
        gaps = Counter(p for m in matches if m["client_id"] == cid and m["machine_status"] == "à confirmer"
                       for p in parts(m["fit_reasons"]))
        lines.append(f"- **{cname}** : " + " ; ".join(f"{k} ({v})" for k, v in gaps.most_common(6)))

    unlock: dict[str, dict] = defaultdict(lambda: {"n": 0, "clients": set(), "gaps": Counter(), "name": ""})
    for m in matches:
        if m["machine_status"] != "à confirmer" or m["seniority"] not in ("executive", "vp_clevel", "director"):
            continue
        u = unlock[m["account_id"]]
        u["n"] += 1
        u["name"] = m["company_name"]
        u["clients"].add(m["client_id"])
        u["gaps"].update(p for p in parts(m["fit_reasons"]) if "à confirmer" in p or "vérifier" in p)
    top = sorted(unlock.items(), key=lambda kv: -kv[1]["n"])[:20]
    lines += ["", "## Comptes à débloquer en priorité", "",
              "Décideurs en `à confirmer`, par compte. Résoudre ces lacunes fait monter le plus de matchs.", "",
              "| Compte | Matchs décideurs | Clients | Lacunes principales |", "|---|---|---|---|"]
    for key, u in top:
        lines.append(f"| {u['name']} (`{key}`) | {u['n']} | {', '.join(sorted(u['clients']))} | "
                     + " ; ".join(k for k, _ in u["gaps"].most_common(3)) + " |")

    excl = Counter(p for m in matches if m["machine_status"] == "exclu" for p in parts(m["exclusion_reasons"]))
    links = Counter(m["company_link_status"] for m in matches if m["client_id"] == next(iter(names)))
    lines += ["", "## Exclusions les plus fréquentes", "",
              *[f"- {k} : {v}" for k, v in excl.most_common(8)], "",
              "## Qualité des rattachements (par personne)", "",
              *[f"- {k} : {v}" for k, v in links.most_common()], "",
              "## Limites", "",
              "- Un statut `possible` n'est pas un ICP validé : CA, modèle d'affaires ou signaux restent à prouver.",
              "- Les motifs de présence et objectifs sont `[Déduit]`.",
              "- Les décisions humaines passent par `feedback-template.csv` puis `python3 -m event_machine feedback`."]
    (args.out / "diagnostic.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"diagnostic": str(args.out / "diagnostic.md"),
                      "counts": {c: dict(v) for c, v in now.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
