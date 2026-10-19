#!/usr/bin/env python3
"""Vérifie les fiches de prospects et écrit le CSV d'import de la plateforme.

  build_cards_csv.py --cards <client>-cards.json --client-signature "Elisa-Eve, Mirego" --out <client>-import.csv

Le JSON est une liste d'objets avec les colonnes de la plateforme ; `conversation_starter` est une liste
de 3 phrases. Le script refuse d'écrire le CSV si une règle d'écriture n'est pas respectée et liste
les problèmes, fiche par fiche.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

COLUMNS = ["match_query", "job_title", "full_name", "company_name", "brief", "company_url", "linkedin_url",
           "profile_image_url", "profile_picture", "interests", "match_reason_short", "match_reason_long",
           "conversation_starter", "suggested_outreach", "match_score", "language", "external_link", "email"]
ALWAYS_EMPTY = ("match_query", "profile_image_url", "profile_picture", "language")
DASHES = ("—", "–")
REVENUE = re.compile(r"\d[\d,.]*\s*(M\$|millions?\s+de\s+dollars|G\$|milliards?)", re.IGNORECASE)
TU = re.compile(r"\b(tu|toi|ton|ta|tes|t'es)\b", re.IGNORECASE)


def words(text: str) -> int:
    return len(str(text or "").split())


def check(card: dict, signature: str) -> list[str]:
    problems = []
    for col in COLUMNS:
        value = card.get(col, "")
        text = "; ".join(value) if isinstance(value, list) else str(value or "")
        if any(d in text for d in DASHES):
            problems.append(f"{col} : tiret long ou moyen")
    for col in ALWAYS_EMPTY:
        if card.get(col):
            problems.append(f"{col} : doit rester vide")
    for col in ("job_title", "full_name", "company_name", "brief", "interests", "match_reason_short",
                "match_reason_long", "suggested_outreach", "match_score"):
        if not str(card.get(col, "")).strip():
            problems.append(f"{col} : vide")
    if not 50 <= words(card.get("brief")) <= 75:
        problems.append(f"brief : {words(card.get('brief'))} mots (viser 50 à 75)")
    if words(card.get("match_reason_short")) > 10:
        problems.append(f"match_reason_short : {words(card.get('match_reason_short'))} mots (10 au maximum)")
    if not 30 <= words(card.get("match_reason_long")) <= 60:
        problems.append(f"match_reason_long : {words(card.get('match_reason_long'))} mots (viser environ 50)")
    tags = [t.strip() for t in str(card.get("interests", "")).split(";") if t.strip()]
    if not 4 <= len(tags) <= 7:
        problems.append(f"interests : {len(tags)} tags (4 à 7 : type; secteur; tranche; rôle; critères ICP prouvés)")
    if re.search(r"\bCA\b", str(card.get("interests", ""))):
        problems.append("interests : enlever « CA » devant la tranche")
    starters = card.get("conversation_starter", [])
    if not isinstance(starters, list) or len(starters) != 3:
        problems.append("conversation_starter : 3 phrases attendues (liste)")
    else:
        for s in starters:
            if ";" in s or re.match(r"^\s*\d+[.)]", s):
                problems.append("conversation_starter : pas de numéro ni de « ; » dans une phrase")
            if s.count("?") != 1 or s.count(".") > 1:
                problems.append(f"conversation_starter : une seule phrase interrogative ({s[:40]}...)")
    outreach = str(card.get("suggested_outreach", ""))
    if re.match(r"\s*objet\s*:", outreach, re.IGNORECASE):
        problems.append("suggested_outreach : enlever l'objet")
    if TU.search(outreach):
        problems.append("suggested_outreach : tutoiement détecté (vouvoyer)")
    if signature and signature not in outreach:
        problems.append(f"suggested_outreach : signature « {signature} » absente")
    if not 50 <= words(outreach) <= 110:
        problems.append(f"suggested_outreach : {words(outreach)} mots (viser 60 à 90)")
    for col in ("brief", "match_reason_long", "match_reason_short", "suggested_outreach"):
        if REVENUE.search(str(card.get(col, ""))):
            problems.append(f"{col} : chiffre d'affaires cité (réservé aux tags)")
    if not str(card.get("match_score", "")).isdigit() or not 0 <= int(card.get("match_score", -1)) <= 100:
        problems.append("match_score : entier de 0 à 100 attendu")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cards", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--client-signature", default="", help="signature attendue à la fin du brouillon")
    args = ap.parse_args()
    cards = json.loads(args.cards.read_text(encoding="utf-8"))
    failures = {}
    for card in cards:
        problems = check(card, args.client_signature)
        if problems:
            failures[card.get("full_name") or "?"] = problems
    if failures:
        for name, problems in failures.items():
            print(f"✗ {name}")
            for p in problems:
                print(f"  - {p}")
        sys.exit(f"{len(failures)} fiche(s) à corriger : CSV non écrit")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for card in cards:
            row = {c: card.get(c, "") for c in COLUMNS}
            row["conversation_starter"] = "; ".join(card["conversation_starter"])
            writer.writerow(row)
    print(json.dumps({"cards": len(cards), "csv": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
