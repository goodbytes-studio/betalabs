"""Deterministic, source-aware ICP matching. No generative inference is a verified fact."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


GENERIC_EMAIL_DOMAINS = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com", "live.ca", "videotron.ca"}
ROLE_TERMS = {
    "marketing": ("marketing", "publicite", "advertising", "brand", "marque", "communications", "cmo"),
    "digital": ("numerique", "digital", "ecommerce", "e commerce", "commerce electronique", "web"),
    "operations": ("operations", "exploitation", "magasins", "retail operations", "coo"),
    "it": ("technologie", "technology", "informatique", "innovation", " ti ", " cio ", " cto ",
           "information officer", "systemes d information", "technologies de l information"),
    "hr": ("ressources humaines", "human resources", "recrutement", "talent", " rh "),
    "finance": ("finance", "financial", "comptabilite", "cfo"),
    "legal": ("juridique", "legal", "conformite"),
    "logistics": ("logistique", "logistics", "supply chain"),
    "sales": ("vente", "sales", "business development", "developpement des affaires"),
    # Fonction distincte du marketing : chaque ICP choisit de la cibler ou non (décision S47).
    "customer_experience": ("experience client", "customer experience", "client experience", "experience consommateur"),
}
SECTOR_TERMS = {
    "cpg": ("consumer packaged goods", "cpg", "produits de consommation"),
    "pharmacy": ("pharmacie", "pharmacy", "drugstore"),
    "insurance": ("assurance", "insurance"),
    "grocery": ("epicerie", "grocery", "supermarket", "alimentation"),
    "beauty": ("beaute", "beauty", "cosmetic"),
    "sport_outdoor": ("sport", "outdoor", "plein air", "tennis"),
    "fashion": ("mode", "fashion", "apparel", "vetement", "friperie"),
    "electronics": ("electronique", "electronics", "electromenager", "photo"),
    "furniture_home": ("meuble", "furniture", "decoration", "decor", "ameublement"),
    "hardware": ("quincaillerie", "hardware", "outils", "renovation"),
    "books": ("librairie", "books", "livres"),
    "automotive": ("automobile", "automotive", "dealership"),
    "food_beverage": ("boisson", "beverage", "restaurant", "food"),
    # Créneaux ajoutés le 2026-10-18 (décision S46) ; placés en dernier pour ne pas changer les inférences existantes.
    "footwear": ("chaussure", "footwear", "shoes"),
    "jewelry": ("bijou", "joaillerie", "jewelry", "jewellery"),
    "pets": ("animalerie", "pet store", "animaux"),
    "optical": ("optometri", "optique", "lunetterie", "opticien", "eyewear"),
    "cannabis": ("cannabis",),
    "convenience": ("depanneur", "convenience store"),
}


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def domain(value: object) -> str:
    raw = str(value or "").strip().lower()
    if "@" in raw and not raw.startswith("http"):
        raw = raw.rsplit("@", 1)[-1]
    if "://" in raw:
        raw = urlparse(raw).hostname or ""
    return raw.removeprefix("www.").split("/", 1)[0].strip(". ")


def first(row: dict, *names: str) -> str:
    lookup = {norm(k): str(v or "").strip() for k, v in row.items()}
    return next((lookup[norm(name)] for name in names if lookup.get(norm(name))), "")


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    names = fields or list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def parse_accounts(rows: list[dict]) -> tuple[list[dict], dict, dict]:
    accounts: dict[str, dict] = {}
    by_name: dict[str, set[str]] = defaultdict(set)
    for index, row in enumerate(rows, 1):
        name = first(row, "name", "company_name", "company", "entreprise", "account_name")
        website = first(row, "website", "website_url", "site")
        dom = domain(first(row, "domain", "company_domain", "email_domain") or website)
        key = dom or "name:" + norm(name)
        if not name and not dom:
            continue
        account = accounts.setdefault(key, {
            "account_id": key, "name": name or dom, "domain": dom, "website": website,
            "org_type": "", "industry": "", "sector": "", "country": "",
            "revenue_raw": "", "revenue_currency": "", "revenue_year": "",
            "revenue_verified": "", "revenue_source_url": "", "source_rows": [],
        })
        account["source_rows"].append(str(index))
        for field, aliases in {
            "org_type": ("org_type", "company_type", "organization_type"),
            "industry": ("industry", "industrie"),
            "sector": ("sector", "secteur"),
            "sector_source_url": ("sector_source_url", "sector_evidence_url"),
            "country": ("country", "pays"),
            "revenue_raw": ("revenue", "annual_revenue", "revenue_cad", "annual_revenue_exact"),
            "revenue_currency": ("revenue_currency", "currency", "devise"),
            "revenue_year": ("revenue_year", "fiscal_year", "année_revenu"),
            "revenue_verified": ("revenue_verified", "revenue_status"),
            "revenue_source_url": ("revenue_source_url", "revenue_evidence_url"),
            "business_model": ("business_model", "modele_affaires"),
            "business_model_source_url": ("business_model_source_url", "business_model_evidence_url"),
            "revenue_estimate_band": ("revenue_estimate_band", "revenue_band", "annual_revenue_range"),
            "revenue_estimate_currency": ("revenue_estimate_currency", "revenue_band_currency"),
            "revenue_estimate_source": ("revenue_estimate_source", "revenue_band_source"),
        }.items():
            value = first(row, *aliases)
            if value and not account.get(field):
                account[field] = value
        if name:
            by_name[norm(name)].add(key)
    for account in accounts.values():
        account["source_rows"] = " | ".join(account["source_rows"])
    return list(accounts.values()), accounts, by_name


def parse_people(rows: list[dict], event_id: str, accounts_by_key: dict, accounts_by_name: dict,
                 registration_marker: str = "") -> list[dict]:
    people = []
    seen = set()
    for index, row in enumerate(rows, 1):
        name = first(row, "full_name", "name", "nom et prénom", "nom prénom")
        if not name:
            name = " ".join(x for x in (first(row, "first_name", "prénom"), first(row, "last_name", "nom")) if x)
        email = first(row, "email", "work_email", "courriel").lower()
        company = first(row, "company_name", "company", "entreprise", "employer")
        explicit_domain = domain(first(row, "company_domain", "email_domain"))
        email_domain = domain(email)
        candidate_domain = explicit_domain or (email_domain if email_domain not in GENERIC_EMAIL_DOMAINS else "")
        account_key = ""
        link_status = "unknown"
        if candidate_domain and candidate_domain in accounts_by_key:
            account_key = candidate_domain
            link_status = "domain_match"
            if company and norm(company) != norm(accounts_by_key[account_key]["name"]):
                candidates = accounts_by_name.get(norm(company), set())
                if account_key not in candidates:
                    link_status = "name_domain_conflict"
        elif company:
            candidates = accounts_by_name.get(norm(company), set())
            if len(candidates) == 1:
                account_key = next(iter(candidates))
                link_status = "name_match"
            elif len(candidates) > 1:
                link_status = "ambiguous_name"
        if not account_key and company:
            account_key = candidate_domain or "name:" + norm(company)
            link_status = "participant_supplied" if not candidate_domain else "email_domain_candidate"
            accounts_by_key.setdefault(account_key, {
                "account_id": account_key, "name": company, "domain": candidate_domain,
                "website": "", "org_type": "", "industry": "", "sector": first(row, "sector", "secteur"),
                "country": first(row, "country", "pays"), "revenue_raw": "", "revenue_currency": "",
                "revenue_year": "", "revenue_verified": "", "revenue_source_url": "", "source_rows": "participant",
            })
        identifier = email or stable_id(norm(name), norm(company), str(index))
        person_id = stable_id(event_id, identifier)
        if person_id in seen:
            person_id = stable_id(event_id, identifier, str(index))
            link_status += ";duplicate_identifier"
        seen.add(person_id)
        markers = " | ".join(str(v) for k, v in row.items() if "slug" in k.lower() and v)
        attendance_status = ("marker_confirmed" if registration_marker and registration_marker in markers else
                             "marker_unverified" if registration_marker else "list_supplied")
        people.append({
            "event_id": event_id, "person_id": person_id, "source_row": str(index), "name": name or "À confirmer",
            "email": email, "company_supplied": company, "account_id": account_key,
            "company_link_status": link_status, "job_title": first(row, "role", "job_title", "title", "poste"),
            "country": first(row, "country", "pays"),
            "profile_url": first(row, "linkedin_url", "profile_url"),
            "attendance_marker": markers, "attendance_status": attendance_status,
        })
    return people


def role_features(title: str) -> tuple[set[str], str]:
    value = " " + norm(title) + " "
    if not title or norm(title) in {"nan", "none", "null"}:
        return set(), "unknown"
    functions = {function for function, terms in ROLE_TERMS.items() if any(term in value for term in terms)}
    vp = bool(re.search(r"\b(vp|vice president|vice presidente|vice president e)\b", value))
    if any(term in value for term in (" pdg ", " ceo ", " president ", " presidente ", " chief executive ", " owner ", " proprietaire ",
                                          " founder ", " cofounder ", " fondateur ", " fondatrice ", " cofondateur ", " cofondatrice ",
                                          " directrice generale ", " directeur general ")) and not vp:
        functions.add("executive")
        return functions, "executive"
    if vp or any(term in value for term in (" chief ", " cmo ", " coo ", " cio ", " cto ")):
        # Un VP régional dirige un territoire comme un DG régional (décision D19, source S42).
        if vp and re.search(r"\b(regional|regionale|regionaux)\b", value):
            functions.add("executive")
        return functions, "vp_clevel"
    if any(term in value for term in (" directeur ", " directrice ", " director ", " head of ")):
        return functions, "director"
    if any(term in value for term in (" manager ", " gestionnaire ", " responsable ", " chef ")):
        return functions, "manager"
    return functions, "unknown"


def infer_org_type(account: dict) -> tuple[str, str]:
    explicit = norm(account.get("org_type", ""))
    aliases = {"retailer": "retailer", "detaillant": "retailer", "seller": "seller", "vendeur": "seller",
               "manufacturer": "manufacturer", "fabricant": "manufacturer", "ecosystem": "ecosystem", "ecosysteme": "ecosystem",
               "distributor": "distributor", "distributeur": "distributor"}
    if explicit in aliases:
        return aliases[explicit], "company_input"
    value = " " + norm(account.get("industry", "")) + " "
    if any(x in value for x in (" retail ", " commerce de detail ", " apparel ", " fashion retail ")):
        return "retailer", "industry_inferred"
    if any(x in value for x in (" software ", " consulting ", " advertising ", " marketing services ", " information technology ", " logistics ")):
        return "seller", "industry_inferred"
    if any(x in value for x in (" manufacturing ", " production ")):
        return "manufacturer", "industry_inferred"
    if any(x in value for x in (" government ", " association ", " university ", " non profit ")):
        return "ecosystem", "industry_inferred"
    return "unknown", "unverified"


def infer_sector(account: dict) -> tuple[str, str]:
    raw = account.get("sector", "")
    if raw:
        key = norm(raw).replace(" ", "_")
        if key in SECTOR_TERMS or key == "other":
            return key, "company_input"
    value = " " + norm(" ".join((raw, account.get("industry", ""), account.get("name", "")))) + " "
    for sector, terms in SECTOR_TERMS.items():
        if any(term in value for term in terms):
            return sector, "inferred_from_text"
    return "unknown", "unverified"


def verified_revenue(account: dict) -> tuple[float | None, str]:
    raw = str(account.get("revenue_raw", "")).replace(",", "").replace("$", "").strip()
    try:
        amount = float(raw)
    except ValueError:
        return None, "missing_or_non_numeric"
    valid = norm(account.get("revenue_verified", "")) in {"yes", "true", "verified", "confirme", "1"}
    currency = str(account.get("revenue_currency", "")).upper()
    year = str(account.get("revenue_year", ""))
    if not valid or currency != "CAD" or not re.fullmatch(r"20\d{2}", year) or not account.get("revenue_source_url"):
        return None, "raw_only_currency_year_scope_or_source_unverified"
    return amount, "verified_input"


# Bornes prudentes USD -> CAD pour une fourchette estimée : le bas est converti au taux bas,
# le haut au taux haut, pour qu'une fourchette ne franchisse un seuil que si elle le fait sans ambiguïté.
USD_CAD_LOW, USD_CAD_HIGH = 1.25, 1.45
BAND_UNITS = {"": 1, "k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}


def estimated_revenue_band(account: dict) -> tuple[float, float] | None:
    """Fourchette de CA estimée (ex. « 200M-500M » d'un fournisseur de données), convertie en CAD."""
    band = str(account.get("revenue_estimate_band", "")).replace("$", "").replace(" ", "").lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([kmbt]?)-(\d+(?:\.\d+)?)([kmbt]?)", band)
    if not match:
        return None
    low = float(match.group(1)) * BAND_UNITS[match.group(2) or match.group(4)]
    high = float(match.group(3)) * BAND_UNITS[match.group(4)]
    currency = str(account.get("revenue_estimate_currency", "")).upper()
    if currency == "CAD":
        return low, high
    if currency == "USD":
        return low * USD_CAD_LOW, high * USD_CAD_HIGH
    return None


def person_event_hypothesis(title: str, org_type: str) -> tuple[str, str, str]:
    """Conversation hypotheses only; never claim a person's actual intent."""
    functions, _ = role_features(title)
    focus = next((name for name in ("digital", "marketing", "operations", "it", "hr", "sales") if name in functions), "general")
    needs = {
        "digital": ("Comparer les approches de commerce numérique et d'expérience client.", "Identifier un projet numérique et les partenaires capables de le livrer."),
        "marketing": ("Explorer acquisition, fidélisation et croissance de marque.", "Repérer des solutions marketing adaptées à un objectif de croissance."),
        "operations": ("Examiner l'efficacité des opérations de détail.", "Repérer un levier concret pour les opérations des magasins."),
        "it": ("Évaluer les technologies applicables au commerce de détail.", "Qualifier une solution compatible avec la feuille de route TI."),
        "hr": ("Comparer les pratiques de recrutement et de culture.", "Identifier une piste pour attirer ou retenir les talents."),
        "sales": ("Rencontrer des décideurs du commerce de détail.", "Identifier des comptes et projets commerciaux pertinents."),
        "general": ("Faire de la veille et rencontrer l'écosystème du détail.", "Définir un projet ou un partenariat à explorer."),
    }
    if org_type == "retailer":
        typology = "Buyer [Déduit]"
        reason, objective = needs[focus]
    elif org_type == "seller":
        typology = "Seller [Déduit]"
        reason, objective = ("Rencontrer des détaillants et partenaires potentiels.",
                             "Qualifier de nouveaux comptes ou partenariats dans le détail.")
    elif org_type == "ecosystem":
        typology = "Écosystème [Déduit]"
        reason, objective = ("Suivre les priorités du commerce de détail et développer le réseau.",
                             "Identifier des collaborations ou thèmes à soutenir.")
    else:
        typology = "À confirmer"
        reason, objective = needs[focus]
    return typology, "[Déduit] " + reason, "[Déduit] " + objective


def parse_evidence(rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    evidence: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = domain(first(row, "domain_join_key", "account_domain", "domain"))
        field = first(row, "field", "signal_field")
        if not key or not field:
            continue
        evidence[key][field].append({
            "value": first(row, "value", "observed_value"), "source_url": first(row, "source_url", "evidence_url"),
            "checked_at": first(row, "checked_at", "checked_date"),
            "confidence": first(row, "confidence"), "caveat": first(row, "caveat", "limit_or_open_question"),
        })
    return evidence


def signal_state(evidence: dict, rule: dict) -> tuple[str, str]:
    field = rule["field"]
    values = evidence.get(field, [])
    accepted = {norm(v) for v in rule.get("positive_values", ["yes", "true", "confirmed", "active"])}
    for item in values:
        if item["source_url"] and norm(item["confidence"]) in {"high", "elevee", "verified"} and norm(item["value"]) in accepted:
            return "verified_yes", item["source_url"]
    for item in values:
        if item["source_url"] and norm(item["confidence"]) in {"high", "elevee", "verified"} and norm(item["value"]) in {"no", "false", "absent"}:
            return "verified_no", item["source_url"]
    return "unknown", ""


def match_person(person: dict, account: dict, profile: dict, evidence: dict, relation: dict | None,
                 learning_bias: float = 0, reviewed: dict | None = None) -> dict:
    functions, seniority = role_features(person["job_title"])
    org, org_basis = infer_org_type(account)
    sector, sector_basis = infer_sector(account)
    typology, why_attend, business_objective = person_event_hypothesis(person["job_title"], org)
    reasons, blockers, sources = [], [], []
    target = profile.get("target", {})
    types = set(target.get("company_types", ["retailer"]))
    if org != "unknown" and org not in types:
        if org_basis == "company_input":
            blockers.append("organisation hors ICP : " + org)
        else:
            reasons.append("type d'organisation potentiellement hors ICP à confirmer")
    elif org == "unknown":
        reasons.append("type d'organisation à confirmer")
    if person["company_link_status"] in {"name_domain_conflict", "ambiguous_name", "unknown", "email_domain_candidate"}:
        reasons.append("rattachement entreprise à vérifier")
    if person.get("attendance_status") == "marker_unverified":
        reasons.append("inscription à confirmer")
    forbidden = set(target.get("sectors_exclude", []))
    allowed = set(target.get("sectors_allow", []))
    if sector in forbidden:
        if sector_basis == "company_input":
            blockers.append("secteur exclu : " + sector)
        else:
            reasons.append("secteur potentiellement exclu à confirmer")
    elif allowed and sector != "unknown" and sector not in allowed:
        if sector_basis == "company_input" and target.get("sectors_allow_strict", True):
            blockers.append("secteur hors cible : " + sector)
        elif sector_basis == "company_input":
            # Liste ouverte : un secteur hors liste se valide à la main au lieu d'exclure.
            reasons.append("à valider : secteur hors liste (" + sector + ")")
        else:
            reasons.append("secteur potentiellement hors cible à confirmer")
    elif sector == "unknown":
        reasons.append("secteur à confirmer")
    allowed_functions = set(target.get("role_functions", []))
    allowed_seniority = set(target.get("seniority", []))
    if not functions:
        reasons.append("fonction du poste à confirmer")
    elif allowed_functions and not functions.intersection(allowed_functions):
        blockers.append("fonction hors ICP : " + person["job_title"])
    if seniority == "unknown":
        reasons.append("niveau de décision à confirmer")
    elif allowed_seniority and seniority not in allowed_seniority:
        blockers.append("niveau hors ICP : " + seniority)
    geography = {norm(v) for v in target.get("geographies", [])}
    country = norm(person.get("country") or account.get("country"))
    if geography and country and country not in geography:
        blockers.append("géographie hors ICP : " + country)
    elif geography and not country:
        reasons.append("géographie à confirmer")
    models = {norm(v) for v in target.get("business_models", [])}
    account_model = norm(account.get("business_model", ""))
    model_source = account.get("business_model_source_url", "")
    if models:
        if not account_model or not model_source:
            reasons.append("modèle d'affaires à confirmer")
        elif account_model not in models and account_model != "b2b b2c":
            blockers.append("modèle d'affaires hors ICP : " + account_model)
        else:
            sources.append(model_source)
    amount, revenue_basis = verified_revenue(account)
    revenue_min = target.get("revenue_min_cad")
    revenue_max = target.get("revenue_max_cad")
    for tier in target.get("revenue_tiers", []):
        if sector in tier.get("sectors", []):
            revenue_min = tier.get("min_cad", revenue_min)
            revenue_max = tier.get("max_cad", revenue_max)
            break
    band = estimated_revenue_band(account) if target.get("revenue_estimate_ok") else None
    # Marge propre au client sur les seuils, appliquée aux seules fourchettes estimées.
    tolerance = float(target.get("revenue_estimate_tolerance", 0) or 0)
    estimate_ok = False
    if revenue_min is not None or revenue_max is not None:
        if amount is None and band:
            low, high = band
            soft_min = revenue_min * (1 - tolerance) if revenue_min is not None else None
            soft_max = revenue_max * (1 + tolerance) if revenue_max is not None else None
            # Une fourchette estimée n'exclut que si elle est loin du seuil (facteur propre au client).
            hard = float(target.get("revenue_estimate_hard_factor", 0) or 0)
            if revenue_min is not None and high < revenue_min:
                if hard and high >= revenue_min / hard:
                    reasons.append("à valider : CA estimé (fourchette) sous le seuil")
                else:
                    blockers.append("CA estimé (fourchette) sous le seuil")
            elif revenue_max is not None and low > revenue_max:
                if hard and low <= revenue_max * hard:
                    reasons.append("à valider : CA estimé (fourchette) au-dessus du seuil")
                else:
                    blockers.append("CA estimé (fourchette) au-dessus du seuil")
            elif (soft_min is None or low >= soft_min) and (soft_max is None or high <= soft_max):
                reasons.append("CA estimé (fourchette) dans la fourchette ICP")
                estimate_ok = True
            else:
                reasons.append("CA estimé (fourchette) chevauche le seuil")
            revenue_basis = "estimated_band"
        elif amount is None:
            reasons.append("CA annuel CAD non vérifié")
        elif revenue_min is not None and amount < revenue_min:
            blockers.append("CA CAD sous le seuil")
        elif revenue_max is not None and amount > revenue_max:
            blockers.append("CA CAD au-dessus du seuil")
        else:
            reasons.append("CA CAD vérifié dans la fourchette")
            sources.append(account["revenue_source_url"])
    signal_results = []
    for rule in profile.get("signals", []):
        state, url = signal_state(evidence, rule)
        signal_results.append({"field": rule["field"], "state": state, "url": url})
        if rule.get("required") and state == "unknown":
            reasons.append("signal à vérifier : " + rule["field"])
        if rule.get("negative_excludes") and state == "verified_no":
            blockers.append("signal négatif vérifié : " + rule["field"])
        if url:
            sources.append(url)
    identity_gaps = ("rattachement", "type d'organisation", "secteur", "fonction du poste",
                     "niveau de décision", "inscription", "géographie")
    unknown_gate = any(x.startswith(identity_gaps) for x in reasons)
    pending_checks = [x for x in reasons if x not in ("CA CAD vérifié dans la fourchette",
                                                      "CA estimé (fourchette) dans la fourchette ICP")]
    all_required = all(item["state"] == "verified_yes" for item in signal_results if next((r.get("required") for r in profile.get("signals", []) if r["field"] == item["field"]), False))
    revenue_required = revenue_min is not None or revenue_max is not None
    if blockers:
        machine_status = "exclu"
    elif unknown_gate:
        machine_status = "à confirmer"
    elif (not revenue_required or amount is not None or estimate_ok) and all_required and not pending_checks:
        machine_status = "fort"
    else:
        machine_status = "possible"
    role_score = {"executive": 16, "vp_clevel": 13, "director": 10, "manager": 3, "unknown": 0}[seniority]
    score = 45 + role_score + (8 if org == "retailer" else 0) + (5 if sector != "unknown" else 0)
    score += sum(6 for s in signal_results if s["state"] == "verified_yes")
    if relation:
        score += 5
    score = max(0, min(100, round(score + learning_bias)))
    if machine_status == "exclu":
        score = min(score, 20)
    elif machine_status == "à confirmer":
        score = min(score, 49)
    result = {
        "match_key": "|".join((person["event_id"], person["person_id"], profile["id"])),
        "event_id": person["event_id"], "person_id": person["person_id"], "account_id": person["account_id"],
        "client_id": profile["id"], "client_name": profile.get("name", profile["id"]),
        "person_name": person["name"], "company_name": account.get("name", "À confirmer"),
        "job_title": person["job_title"], "org_type": org, "org_basis": org_basis,
        "typology": typology, "role_influence": seniority,
        "why_attend": why_attend, "business_objective": business_objective,
        "sector": sector, "sector_basis": sector_basis, "role_functions": " | ".join(sorted(functions)),
        "seniority": seniority, "company_link_status": person["company_link_status"],
        "attendance_status": person.get("attendance_status", "list_supplied"),
        "machine_status": machine_status, "fit_status": machine_status,
        "priority_score": score, "learned_priority_delta": round(learning_bias, 2),
        "fit_reasons": " | ".join(reasons), "exclusion_reasons": " | ".join(blockers),
        "revenue_raw": account.get("revenue_raw", ""), "revenue_basis": revenue_basis,
        "revenue_estimate_band": " ".join(x for x in (account.get("revenue_estimate_band", ""), account.get("revenue_estimate_currency", "")) if x),
        "signal_results_json": json.dumps(signal_results, ensure_ascii=False),
        "relationship": relation.get("relation_type", "") if relation else "",
        "relationship_owner": relation.get("owner", "") if relation else "",
        "evidence_urls": " | ".join(sorted(set(x for x in sources if x))),
        "opportunity_hypothesis": "[Déduit] " + profile.get("conversation_angle", "Vérifier le projet, le décideur et le calendrier."),
        "next_question": profile.get("discovery_question", "Quel projet concret est prioritaire et qui en décide ?"),
        "reviewed_by": "", "review_note": "",
    }
    if reviewed:
        result["fit_status"] = reviewed["reviewed_fit"] + " (revue humaine)"
        result["reviewed_by"] = reviewed["reviewer"]
        result["review_note"] = reviewed["note"]
    return result


def validate_profiles(config: dict) -> list[dict]:
    clients = config.get("clients", [])
    if not isinstance(clients, list) or not clients:
        raise ValueError("ICP JSON requires a non-empty clients array")
    seen = set()
    for client in clients:
        if not client.get("id") or not isinstance(client.get("target"), dict):
            raise ValueError("Each client requires id and target")
        if client["id"] in seen:
            raise ValueError("Duplicate client id: " + client["id"])
        seen.add(client["id"])
        for key in ("revenue_min_cad", "revenue_max_cad"):
            if client["target"].get(key) is not None and not isinstance(client["target"][key], (int, float)):
                raise ValueError(key + " must be numeric")
        for tier in client["target"].get("revenue_tiers", []):
            if not isinstance(tier.get("sectors"), list):
                raise ValueError("revenue_tiers requires sectors list")
            for key in ("min_cad", "max_cad"):
                if tier.get(key) is not None and not isinstance(tier[key], (int, float)):
                    raise ValueError("revenue_tiers " + key + " must be numeric")
    return clients


def relations_by_key(rows: list[dict]) -> dict[tuple[str, str], dict]:
    result = {}
    for row in rows:
        key = (domain(first(row, "domain", "account_domain")), first(row, "client_id", "client"))
        if all(key):
            result[key] = {"relation_type": first(row, "relation_type", "type"),
                           "owner": first(row, "owner", "relationship_owner"),
                           "last_interaction": first(row, "last_interaction")}
    return result


def review_queue(matches: list[dict]) -> list[dict]:
    rows = []
    for match in matches:
        if match["machine_status"] == "exclu":
            continue
        rows.append({
            "match_key": match["match_key"], "client_id": match["client_id"],
            "person_name": match["person_name"], "company_name": match["company_name"],
            "fit_status": match["fit_status"], "priority_score": match["priority_score"],
            "primary_gap": match["fit_reasons"].split(" | ")[0] if match["fit_reasons"] else "Aucune",
            "next_question": match["next_question"],
        })
    return sorted(rows, key=lambda x: (-x["priority_score"], x["company_name"], x["person_name"]))


def feedback_template(matches: list[dict]) -> list[dict]:
    return [{"match_key": r["match_key"], "reviewed_fit": "", "reviewer": "", "note": "",
             "evidence_url": "", "scope": "person_event"} for r in matches if r["machine_status"] != "exclu"]


def run_manifest(event: dict, pages: list[dict], errors: list[dict], people: list[dict], accounts: list[dict], matches: list[dict]) -> dict:
    return {"event_id": event["id"], "event_name": event["name"], "event_date": event.get("date", ""),
            "as_of": date.today().isoformat(), "version": "0.1.0",
            "counts": {"participants": len(people), "accounts": len(accounts), "matches": len(matches),
                       "match_statuses": dict(Counter(r["fit_status"] for r in matches)),
                       "event_pages": len(pages), "research_errors": len(errors)},
            "limits": ["Un statut possible n'est pas un ICP validé", "Les intentions de présence sont déduites",
                       "La recherche réseau peut être partielle", "Le feedback apprend le rang et conserve une revue humaine distincte"]}
