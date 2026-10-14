#!/usr/bin/env python3
"""Étape 1 : contrôle du format des entrées et file de recherche entreprises.

Sorties dans --out :
  prevalidation-report.md   problèmes bloquants, avertissements, chiffres clés
  participant-issues.csv    une ligne par problème de participant
  account-issues.csv        une ligne par problème d'entreprise
  accounts-normalized.csv   une ligne par domaine (première valeur non vide conservée)
  research-queue.csv        entreprises à faire qualifier par les agents de recherche
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from _common import (DECISION_LEVELS, ORG_TYPES, SENIORITY, load_core, read_csv, read_json,
                     write_csv)

STUDENT_HINTS = ("etud.", "etudiant", "student", ".edu", "mail.mcgill", "ecoles.")
ASSOCIATION_HINTS = ("conseil", "association", "chambre de commerce", "federation", "fédération",
                     "cqcd", "detail quebec", "détail québec", "sdc ", "pme mtl", "developpement",
                     "développement", "economique", "économique", "ville de", "university", "universite",
                     "université", "college", "collège", "cegep", "cégep", "ecole", "école")
PARTICIPANT_REQUIRED = [("email",), ("company_name", "company", "entreprise")]
NAME_COLUMNS = (("full_name",), ("first_name", "last_name"))


def has_column(header: list[str], core, *names: str) -> bool:
    keys = {core.norm(h) for h in header}
    return any(core.norm(n) in keys for n in names)


def check_icps(icps: dict, core) -> list[str]:
    problems = []
    clients = icps.get("clients")
    if not isinstance(clients, list) or not clients:
        return ["ICP : la clé `clients` doit être une liste non vide"]
    sectors = set(core.SECTOR_TERMS)
    functions = set(core.ROLE_TERMS) | {"executive"}
    seen = set()
    for client in clients:
        cid = client.get("id") or "?"
        if cid in seen:
            problems.append(f"ICP {cid} : identifiant en double")
        seen.add(cid)
        for key in ("id", "target", "signals"):
            if key not in client:
                problems.append(f"ICP {cid} : champ `{key}` manquant")
        target = client.get("target", {})
        for key in ("sectors_allow", "sectors_exclude"):
            bad = [s for s in target.get(key, []) if s not in sectors]
            if bad:
                problems.append(f"ICP {cid} : secteurs inconnus du moteur dans `{key}` : {', '.join(bad)} "
                                f"(valeurs permises : {', '.join(sorted(sectors))})")
        bad = [t for t in target.get("company_types", []) if t not in ORG_TYPES]
        if bad:
            problems.append(f"ICP {cid} : types d'organisation inconnus : {', '.join(bad)}")
        bad = [s for s in target.get("seniority", []) if s not in SENIORITY]
        if bad:
            problems.append(f"ICP {cid} : niveaux inconnus : {', '.join(bad)}")
        bad = [f for f in target.get("role_functions", []) if f not in functions]
        if bad:
            problems.append(f"ICP {cid} : fonctions inconnues : {', '.join(bad)}")
        for key in ("revenue_min_cad", "revenue_max_cad"):
            if key in target and not isinstance(target[key], (int, float)):
                problems.append(f"ICP {cid} : `{key}` doit être un nombre en CAD")
        for signal in client.get("signals", []):
            if not signal.get("field"):
                problems.append(f"ICP {cid} : un signal n'a pas de `field`")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--participants", required=True, type=Path)
    ap.add_argument("--accounts", type=Path, help="CSV entreprises (optionnel mais recommandé)")
    ap.add_argument("--icps", required=True, type=Path)
    ap.add_argument("--event", type=Path, help="event.json, pour vérifier le marqueur d'inscription")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--repo", type=Path)
    args = ap.parse_args()
    core = load_core(args.repo)
    args.out.mkdir(parents=True, exist_ok=True)

    blocking, warnings = [], []
    p_rows = read_csv(args.participants)
    a_rows = read_csv(args.accounts) if args.accounts else []
    try:
        icps = read_json(args.icps)
        blocking += check_icps(icps, core)
    except json.JSONDecodeError as exc:
        icps = {"clients": []}
        blocking.append(f"ICP : JSON invalide ({exc})")
    event = read_json(args.event) if args.event else {}
    marker = event.get("registration_marker", "")

    # --- Participants: columns
    header = list(p_rows[0].keys()) if p_rows else []
    if not p_rows:
        blocking.append("Participants : fichier vide")
    for names in PARTICIPANT_REQUIRED:
        if header and not has_column(header, core, *names):
            blocking.append(f"Participants : colonne manquante ({' ou '.join(names)})")
    if header and not (has_column(header, core, "full_name", "name") or
                       (has_column(header, core, "first_name") and has_column(header, core, "last_name"))):
        blocking.append("Participants : il faut `full_name` ou `first_name` + `last_name`")
    if header and not has_column(header, core, "role", "job_title", "title", "poste"):
        warnings.append("Participants : aucune colonne de poste (`role`/`job_title`) ; le niveau de décision sera inconnu")

    accounts, by_key, by_name = core.parse_accounts(a_rows)
    people = core.parse_people(p_rows, event.get("id", "event"), by_key, by_name, marker)

    # --- Participants: rows
    p_issues = []
    emails = Counter(p["email"] for p in people if p["email"])
    for person, row in zip(people, p_rows):
        def issue(kind, detail=""):
            p_issues.append({"source_row": person["source_row"], "person_name": person["name"],
                             "email": person["email"], "company_supplied": person["company_supplied"],
                             "issue": kind, "detail": detail})
        email_domain = core.domain(person["email"])
        if not person["email"]:
            issue("email_manquant")
        elif emails[person["email"]] > 1:
            issue("email_en_double")
        if email_domain in core.GENERIC_EMAIL_DOMAINS:
            issue("email_personnel", email_domain + " : rattachement par nom d'entreprise seulement")
        if any(h in (email_domain or "") for h in STUDENT_HINTS):
            issue("domaine_etudiant_ou_ecole", email_domain)
        if not person["company_supplied"]:
            issue("entreprise_manquante")
        if not person["job_title"]:
            issue("poste_manquant")
        else:
            _, seniority = core.role_features(person["job_title"])
            if seniority == "unknown":
                issue("niveau_poste_non_reconnu", person["job_title"])
        if not person["country"]:
            issue("pays_manquant")
        if person["name"] == "À confirmer":
            issue("nom_manquant")
        if marker and person["attendance_status"] != "marker_confirmed":
            issue("marqueur_inscription_absent", marker)
        if "name_domain_conflict" in person["company_link_status"]:
            account = by_key.get(person["account_id"], {})
            issue("conflit_nom_domaine", f"saisi « {person['company_supplied']} » ; domaine {person['account_id']} = « {account.get('name', '')} »")
        if "ambiguous_name" in person["company_link_status"]:
            issue("nom_entreprise_ambigu")
    write_csv(args.out / "participant-issues.csv", p_issues,
              ["source_row", "person_name", "email", "company_supplied", "issue", "detail"])

    # --- Accounts
    a_issues = []
    names_by_domain: dict[str, set[str]] = defaultdict(set)
    linkedin_domains: dict[str, set[str]] = defaultdict(set)
    for row in a_rows:
        dom = core.domain(core.first(row, "domain", "company_domain") or core.first(row, "website_url", "website"))
        name = core.first(row, "name", "company_name")
        if not dom:
            a_issues.append({"account_id": "name:" + core.norm(name), "name": name, "issue": "domaine_manquant", "detail": ""})
            continue
        names_by_domain[dom].add(name)
        site = core.domain(core.first(row, "website_url", "website"))
        if site and site != dom and not site.endswith("." + dom) and not dom.endswith("." + site):
            a_issues.append({"account_id": dom, "name": name, "issue": "site_different_du_domaine", "detail": site})
        li = core.first(row, "linkedin_url")
        if li:
            linkedin_domains[li.rstrip("/").lower()].add(dom)
    for dom, names in names_by_domain.items():
        if len({core.norm(n) for n in names}) > 1:
            a_issues.append({"account_id": dom, "name": sorted(names)[0], "issue": "plusieurs_noms_meme_domaine",
                             "detail": " | ".join(sorted(names))})
    for li, doms in linkedin_domains.items():
        if len(doms) > 1:
            a_issues.append({"account_id": " | ".join(sorted(doms)), "name": "", "issue": "meme_linkedin_plusieurs_domaines", "detail": li})

    # Account-level stats from participants
    stats: dict[str, dict] = defaultdict(lambda: {"participants": 0, "decision_makers": 0, "titles": []})
    for person in people:
        if not person["account_id"]:
            continue
        s = stats[person["account_id"]]
        s["participants"] += 1
        _, seniority = core.role_features(person["job_title"])
        if seniority in DECISION_LEVELS:
            s["decision_makers"] += 1
            if len(s["titles"]) < 3:
                s["titles"].append(person["job_title"])

    raw_by_domain = {}
    for row in a_rows:
        dom = core.domain(core.first(row, "domain", "company_domain") or core.first(row, "website_url", "website"))
        if dom:
            prev = raw_by_domain.setdefault(dom, {})
            for k, v in row.items():
                if v and not prev.get(k):
                    prev[k] = v

    normalized, queue = [], []
    all_accounts = {**{a["account_id"]: a for a in accounts}, **by_key}
    for key, account in all_accounts.items():
        raw = raw_by_domain.get(account.get("domain") or "", {})
        org, org_basis = core.infer_org_type(account)
        sector, sector_basis = core.infer_sector(account)
        s = stats.get(key, {"participants": 0, "decision_makers": 0, "titles": []})
        row = {
            "account_id": key, "name": account.get("name", ""), "domain": account.get("domain", ""),
            "website_url": account.get("website") or raw.get("website_url", ""),
            "linkedin_url": raw.get("linkedin_url", ""), "industry": account.get("industry", ""),
            "estimated_num_employees": raw.get("estimated_num_employees", ""),
            "country": account.get("country", ""), "org_type": account.get("org_type", ""),
            "sector": account.get("sector", ""), "sector_source_url": account.get("sector_source_url", ""),
            "business_model": account.get("business_model", ""),
            "business_model_source_url": account.get("business_model_source_url", ""),
            "revenue": account.get("revenue_raw", ""), "revenue_currency": account.get("revenue_currency", ""),
            "revenue_year": account.get("revenue_year", ""), "revenue_verified": account.get("revenue_verified", ""),
            "revenue_source_url": account.get("revenue_source_url", ""),
            "engine_org_type": org, "engine_org_basis": org_basis,
            "engine_sector": sector, "engine_sector_basis": sector_basis,
            "participants": s["participants"], "decision_makers": s["decision_makers"],
            "source": "accounts_csv" if key in {a["account_id"] for a in accounts} else "participants_only",
        }
        normalized.append(row)
        label = " ".join((row["name"], row["industry"])).casefold()
        if org == "retailer" and any(h in label for h in ASSOCIATION_HINTS):
            a_issues.append({"account_id": key, "name": row["name"], "issue": "detaillant_douteux",
                             "detail": "industrie « retail » mais le nom évoque une association, une école ou un organisme"})
        missing = []
        if org == "unknown" or org_basis != "company_input":
            missing.append("org_type")
        if org in ("retailer", "unknown") and sector_basis != "company_input":
            missing.append("sector")
        if org in ("retailer", "unknown") and not (row["business_model"] and row["business_model_source_url"]):
            missing.append("business_model")
        if not row["country"]:
            missing.append("country")
        if org in ("seller", "ecosystem", "manufacturer") and org_basis == "company_input":
            missing = []  # type déjà fourni : l'ICP l'exclut ou le traite sans recherche
        if s["decision_makers"] and missing:
            queue.append({
                "account_id": key, "name": row["name"], "domain": row["domain"], "website_url": row["website_url"],
                "linkedin_url": row["linkedin_url"], "industry": row["industry"],
                "estimated_num_employees": row["estimated_num_employees"],
                "engine_org_type": org, "engine_sector": sector, "decision_makers": s["decision_makers"],
                "participants": s["participants"], "sample_titles": " | ".join(s["titles"]),
                "fields_to_research": " ".join(missing),
                "research_priority": "high" if org in ("retailer", "unknown") else "low",
            })
    # Détaillants et inconnus d'abord ; les agences/organismes devinés servent surtout à exclure proprement.
    queue.sort(key=lambda r: (r["research_priority"] != "high", -r["decision_makers"], -r["participants"], r["name"]))
    # Le moteur rattache aussi les personnes par nom : garder chaque variante de nom comme ligne alias
    # (domaine seul), placée après la ligne principale pour que ses valeurs restent prioritaires.
    primary_names = {(r["domain"], core.norm(r["name"])) for r in normalized}
    aliases = []
    for dom, names in sorted(names_by_domain.items()):
        for name in sorted(names):
            if name and (dom, core.norm(name)) not in primary_names:
                primary_names.add((dom, core.norm(name)))
                aliases.append({"account_id": dom, "name": name, "domain": dom, "source": "alias"})
    write_csv(args.out / "accounts-normalized.csv", normalized + aliases, list(normalized[0].keys()) if normalized else None)
    write_csv(args.out / "research-queue.csv", queue)
    write_csv(args.out / "account-issues.csv", a_issues, ["account_id", "name", "issue", "detail"])

    # --- Report
    if not a_rows:
        warnings.append("Aucun CSV entreprises : type, secteur et CA resteront inconnus, la liste prioritaire sera vide")
    p_counts = Counter(i["issue"] for i in p_issues)
    a_counts = Counter(i["issue"] for i in a_issues)
    org_counts = Counter(r["engine_org_type"] for r in normalized)
    lines = [
        f"# Prévalidation des entrées — {event.get('name', args.participants.name)}", "",
        f"- Participants : **{len(people)}** lignes ; entreprises distinctes : **{len(normalized)}** "
        f"(dont {sum(1 for r in normalized if r['source'] == 'participants_only')} vues seulement chez les participants).",
        f"- Clients ICP : {', '.join(c.get('id', '?') for c in icps.get('clients', []))}.",
        f"- Types d'organisation selon le moteur : " + ", ".join(f"{k} {v}" for k, v in org_counts.most_common()) + ".",
        f"- File de recherche : **{len(queue)}** entreprises avec au moins un décideur et un champ à qualifier.", "",
        "## Bloquant", "",
        *([f"- {b}" for b in blocking] or ["- Aucun. La machine peut tourner."]), "",
        "## Avertissements", "",
        *([f"- {w}" for w in warnings] or ["- Aucun."]), "",
        "## Participants", "",
        "| Problème | Lignes |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in p_counts.most_common()], "",
        "Détail : `participant-issues.csv`.", "",
        "## Entreprises", "",
        "| Problème | Comptes |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in a_counts.most_common()], "",
        "Détail : `account-issues.csv`.", "",
        "## Prochaine étape", "",
        "Qualifier `research-queue.csv` avec les agents de recherche (type, secteur, modèle d'affaires, pays), "
        "puis `merge_research.py`.",
    ]
    (args.out / "prevalidation-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"blocking": len(blocking), "warnings": len(warnings), "participants": len(people),
                      "accounts": len(normalized), "research_queue": len(queue),
                      "report": str(args.out / "prevalidation-report.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
