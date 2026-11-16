#!/usr/bin/env python3
"""Fusionne les extractions d'événements S86 (Vendelux), S87 (Lensmor) et S88 (Congrès Montréal)
dans la base maîtresse BETA Labs (schéma universel). Python standard seulement.

Règles : tout champ du schéma est toujours présent ; une valeur absente ou non fiable vaut
« inconnu ». Les valeurs d'origine restent consultables dans les originaux (provenance par ligne).
"""
import csv
import datetime as dt
import difflib
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/derived"
UNKNOWN = "inconnu"
SOURCES = {"vendelux": "S86", "lensmor": "S87", "congresmtl": "S88"}
PRIORITY = ["vendelux", "lensmor", "congresmtl"]  # ordre de préférence pour les champs communs
DATE_TOLERANCE_DAYS = 31  # même nom normalisé + début à moins de 31 jours = même événement

EN_MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
FR_MONTHS = {m: i for i, m in enumerate(
    "janvier fevrier mars avril mai juin juillet aout septembre octobre novembre decembre".split(), 1)}

FIELDS = [
    "event_id", "name", "name_variants", "start_date", "end_date", "date_raw", "date_conflict",
    "event_format", "venue", "city", "region", "country", "organizer",
    "industries", "topics_keywords", "description",
    "attendees", "attendees_expected", "exhibitors", "price_min", "price_max", "price_currency",
    "url", "lensmor_url", "vendelux_verified",
    "sources", "source_count", "source_refs", "match_method", "conflicts", "inferred_fields", "last_retrieved",
]
LIST_FIELDS = {"name_variants", "industries", "topics_keywords", "sources", "source_refs", "conflicts", "inferred_fields"}


def norm(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def load(sid):
    path = next((ROOT / "sources/originals").glob({"S86": "vendelux-*", "S87": "lensmor-*", "S88": "congresmtl-*"}[sid]))
    return json.loads(path.read_text(encoding="utf-8"))


def clean(value):
    if value is None:
        return UNKNOWN
    if isinstance(value, str):
        value = value.strip()
        return value if value and value.upper() != "TBA" else UNKNOWN
    return value


COUNTRY_ALIASES = {"uk": "United Kingdom", "usa": "United States", "the bahamas": "Bahamas", "turkey": "Türkiye"}
INVALID_COUNTRIES = {"MI"}  # code de province (Milan) saisi comme pays dans S86


def country_of(value):
    """Renvoie (pays normalisé, note éventuelle). Les variantes de nom sont unifiées, les codes invalides deviennent inconnus."""
    value = clean(value)
    if value in INVALID_COUNTRIES:
        return UNKNOWN, f"country: valeur source invalide « {value} » ignorée"
    return COUNTRY_ALIASES.get(value.lower(), value) if value != UNKNOWN else value, None


def positive(value):
    """0 est un placeholder dans les extractions (pas un compte réel) : traité comme inconnu."""
    return value if isinstance(value, (int, float)) and value > 0 else UNKNOWN


def parse_lensmor_date(text):
    m = re.fullmatch(r"(\w{3}) (\d+)(?: – (?:(\w{3}) )?(\d+))?, (\d{4})", text.strip())
    if not m:
        return None
    a, d1, b, d2, year = m.groups()
    m1, m2, year = EN_MONTHS[a], EN_MONTHS[b] if b else EN_MONTHS[a], int(year)
    start_year = year - 1 if m2 < m1 else year
    return dt.date(start_year, m1, int(d1)), dt.date(year, m2, int(d2) if d2 else int(d1))


def parse_french_date(text):
    t = norm(text)
    # formes : « 9 novembre 2026 », « 8 au 10 novembre 2026 », « 27 novembre au 1 decembre 2026 »
    m = (re.fullmatch(r"(\d+) (\w+) (\d{4})", t) and ("single", *re.fullmatch(r"(\d+) (\w+) (\d{4})", t).groups())) or \
        (re.fullmatch(r"(\d+) au (\d+) (\w+) (\d{4})", t) and ("same", *re.fullmatch(r"(\d+) au (\d+) (\w+) (\d{4})", t).groups())) or \
        (re.fullmatch(r"(\d+) (\w+) au (\d+) (\w+) (\d{4})", t) and ("cross", *re.fullmatch(r"(\d+) (\w+) au (\d+) (\w+) (\d{4})", t).groups())) or \
        (re.fullmatch(r"(\d+) (\w+) (\d{4}) au (\d+) (\w+) (\d{4})", t) and ("years", *re.fullmatch(r"(\d+) (\w+) (\d{4}) au (\d+) (\w+) (\d{4})", t).groups()))
    if not m:
        return None
    kind, g = m[0], m[1:]
    if kind == "single":
        d = dt.date(int(g[2]), FR_MONTHS[g[1]], int(g[0]))
        return d, d
    if kind == "same":
        return dt.date(int(g[3]), FR_MONTHS[g[2]], int(g[0])), dt.date(int(g[3]), FR_MONTHS[g[2]], int(g[1]))
    if kind == "cross":
        start_year = int(g[4]) - 1 if FR_MONTHS[g[3]] < FR_MONTHS[g[1]] else int(g[4])
        return dt.date(start_year, FR_MONTHS[g[1]], int(g[0])), dt.date(int(g[4]), FR_MONTHS[g[3]], int(g[2]))
    return dt.date(int(g[2]), FR_MONTHS[g[1]], int(g[0])), dt.date(int(g[5]), FR_MONTHS[g[4]], int(g[3]))


def from_vendelux(raw, index, retrieved):
    loc = raw.get("location") or {}
    fmt = {"In-person": "in_person", "Hybrid": "hybrid", "Virtual": "virtual"}.get(raw.get("event_type"), UNKNOWN)
    pmin, pmax = raw.get("price_lower", 0), raw.get("price_upper", 0)
    prices_known = bool(pmin or pmax)  # 0/0 = non renseigné ou gratuit : indistinguable, donc inconnu
    return dict(
        source="vendelux", index=index, retrieved=retrieved, name=raw["name"],
        start=dt.date.fromisoformat(raw["start_date"][:10]), end=dt.date.fromisoformat(raw["end_date"][:10]),
        date_raw=f"{raw['start_date'][:10]} → {raw['end_date'][:10]}", event_format=fmt,
        venue=clean(loc.get("venue")), city=clean(loc.get("city")), region=clean(loc.get("region")),
        country=country_of(loc.get("country"))[0], organizer=UNKNOWN,
        industries=[], topics=raw.get("topics") or [], description=clean(raw.get("description")),
        attendees=positive(raw.get("attendees")), attendees_expected=positive(raw.get("expected_attendees")),
        exhibitors=UNKNOWN, price_min=pmin if prices_known else UNKNOWN, price_max=pmax if prices_known else UNKNOWN,
        url=clean(raw.get("url")), lensmor_url=UNKNOWN, verified=raw.get("verified"),
        citation=raw.get("name_citation"), inferred=[],
        notes=[n for n in [country_of(loc.get("country"))[1]] if n])


def from_lensmor(raw, index, retrieved):
    dates = parse_lensmor_date(raw["date"])
    city, _, country = (x.strip() for x in raw["location"].rpartition(","))
    return dict(
        source="lensmor", index=index, retrieved=retrieved, name=raw["name"],
        start=dates[0] if dates else None, end=dates[1] if dates else None, date_raw=raw["date"],
        event_format=UNKNOWN, venue=UNKNOWN, city=clean(city), region=UNKNOWN, country=country_of(country)[0],
        organizer=UNKNOWN, industries=[i.strip() for i in raw["industry"].split(", ") if i.strip()] if raw.get("industry") else [],
        topics=[], description=UNKNOWN, attendees=positive(raw.get("attendees")), attendees_expected=UNKNOWN,
        exhibitors=positive(raw.get("exhibitors")), price_min=UNKNOWN, price_max=UNKNOWN,
        url=UNKNOWN, lensmor_url=clean(raw.get("url")), verified=None, citation=raw.get("source_url"), inferred=[],
        notes=[], status_raw=raw.get("status"))


def from_congresmtl(raw, index, retrieved):
    dates = parse_french_date(raw["date"])
    return dict(
        source="congresmtl", index=index, retrieved=retrieved, name=raw["name"],
        start=dates[0] if dates else None, end=dates[1] if dates else None, date_raw=raw["date"],
        event_format=UNKNOWN, venue="Palais des congrès de Montréal", city="Montréal", region="Québec", country="Canada",
        organizer=clean(raw.get("organizer")), industries=[], topics=[], description=UNKNOWN,
        attendees=UNKNOWN, attendees_expected=UNKNOWN, exhibitors=UNKNOWN, price_min=UNKNOWN, price_max=UNKNOWN,
        url=clean(raw.get("url")), lensmor_url=UNKNOWN, verified=None, citation=raw.get("source_url"),
        notes=[], inferred=["venue", "city", "region", "country"])  # déduits du calendrier du Palais, absents de chaque ligne


def first(records, field):
    for rec in records:
        if rec[field] not in (UNKNOWN, None, []):
            return rec[field]
    return UNKNOWN


def iso(d):
    return d.isoformat() if d else UNKNOWN


def merge_group(records, method):
    records = sorted(records, key=lambda r: PRIORITY.index(r["source"]))
    out = {f: UNKNOWN for f in FIELDS}
    conflicts = []
    name = records[0]["name"]
    out["name"] = name
    out["name_variants"] = sorted({r["name"] for r in records if r["name"] != name})
    dated = [r for r in records if r["start"]]
    if dated:
        out["start_date"], out["end_date"] = iso(dated[0]["start"]), iso(dated[0]["end"])
        for r in dated[1:]:
            if (r["start"], r["end"]) != (dated[0]["start"], dated[0]["end"]):
                conflicts.append(f"dates {r['source']}: {iso(r['start'])} → {iso(r['end'])} (retenu {dated[0]['source']})")
    out["date_conflict"] = any(c.startswith("dates") for c in conflicts)
    out["date_raw"] = " | ".join(f"{r['source']}: {r['date_raw']}" for r in records)
    for f in ("event_format", "venue", "city", "region", "country", "organizer", "description", "url", "lensmor_url",
              "attendees", "attendees_expected", "exhibitors", "price_min", "price_max"):
        out[f] = first(records, f)
    for f, key in (("city", "city"), ("country", "country")):
        vals = {norm(r[key]): r[key] for r in records if r[key] != UNKNOWN}
        if len(vals) > 1:
            conflicts.append(f"{f}: " + " / ".join(f"{r['source']}={r[key]}" for r in records if r[key] != UNKNOWN))
    # attendees : les deux sources comptent différemment (S86 vs S87), l'écart n'est pas un conflit ; valeur retenue = priorité S86
    conflicts.extend(n for r in records for n in r["notes"])
    out["industries"] = sorted({i for r in records for i in r["industries"]})
    out["topics_keywords"] = sorted({t for r in records for t in r["topics"]})
    verified = [r["verified"] for r in records if r["verified"] is not None]
    out["vendelux_verified"] = verified[0] if verified else UNKNOWN
    out["price_currency"] = UNKNOWN  # aucune source ne donne la devise
    out["sources"] = [r["source"] for r in records]
    out["source_count"] = len(records)
    out["source_refs"] = [f"{SOURCES[r['source']]}#{r['index']}" for r in records]
    out["match_method"] = method
    out["conflicts"] = conflicts
    out["inferred_fields"] = sorted({f"{f} ({r['source']})" for r in records for f in r["inferred"]
                                      if out[f] == r[f]})
    out["last_retrieved"] = max(r["retrieved"] for r in records)
    key = f"{norm(name)}|{out['start_date']}"
    out["event_id"] = "BL-EVT-" + hashlib.sha1(key.encode()).hexdigest()[:10]
    return out


def build():
    vendelux, lensmor, congres = load("S86"), load("S87"), load("S88")
    vdata, ldata, cdata = vendelux["data"], lensmor["data"], congres["data"]
    recs = {
        "vendelux": [from_vendelux(e, i, vdata["retrieved_at"][:10]) for i, e in enumerate(vdata["events"])],
        "lensmor": [from_lensmor(e, i, ldata["retrieved_at"]) for i, e in enumerate(ldata["events"])],
        "congresmtl": [from_congresmtl(e, i, "2026-11-09") for i, e in enumerate(cdata["events"])],
    }
    # 1) fusion : même nom normalisé, début à moins de 31 jours, appariement un-pour-un
    groups = []  # liste de (records, method)
    index = {}
    for src in PRIORITY:
        for rec in recs[src]:
            candidates = [g for g in index.get(norm(rec["name"]), [])
                          if src not in {r["source"] for r in g["records"]}
                          and rec["start"] and g["records"][0]["start"]
                          and abs((rec["start"] - g["records"][0]["start"]).days) <= DATE_TOLERANCE_DAYS]
            if candidates:
                g = min(candidates, key=lambda g: abs((rec["start"] - g["records"][0]["start"]).days))
                g["records"].append(rec)
                continue
            g = {"records": [rec]}
            groups.append(g)
            index.setdefault(norm(rec["name"]), []).append(g)
    events = [merge_group(g["records"], "nom_normalise+dates" if len(g["records"]) > 1 else "source_unique") for g in groups]
    ids = [e["event_id"] for e in events]
    if len(ids) != len(set(ids)):
        raise ValueError("Collision d'identifiants événement")
    events.sort(key=lambda e: (e["start_date"] == UNKNOWN, e["start_date"], norm(e["name"])))
    return events, recs, groups, (vdata, ldata, cdata)


def review_candidates(groups):
    """Paires inter-sources non fusionnées qui ressemblent à un doublon : à relire, jamais fusionnées."""
    singles = [g["records"][0] for g in groups if len(g["records"]) == 1 and g["records"][0]["start"]]
    by_date = {}
    for r in singles:
        by_date.setdefault(r["start"], []).append(r)
    out = []
    for r in singles:
        for delta in (-1, 0, 1):
            for o in by_date.get(r["start"] + dt.timedelta(days=delta), []):
                if o["source"] <= r["source"] or r["source"] == o["source"]:
                    continue
                a, b = re.sub(r"\b20\d\d\b", "", norm(r["name"])).strip(), re.sub(r"\b20\d\d\b", "", norm(o["name"])).strip()
                ratio = difflib.SequenceMatcher(None, a, b).ratio()
                same_dom = bool(r["url"] != UNKNOWN and o["url"] != UNKNOWN and
                                urlparse(r["url"]).netloc.removeprefix("www.") == urlparse(o["url"]).netloc.removeprefix("www."))
                if ratio >= 0.8 or same_dom:
                    out.append(dict(source_a=f"{r['source']}#{r['index']}", name_a=r["name"], start_a=iso(r["start"]),
                                    source_b=f"{o['source']}#{o['index']}", name_b=o["name"], start_b=iso(o["start"]),
                                    similarity=round(ratio, 3), same_url_domain=same_dom))
    return sorted(out, key=lambda c: -c["similarity"])


def cell(value, field):
    if field in LIST_FIELDS:
        return "; ".join(value) if value else UNKNOWN
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write(events, candidates, recs, meta):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "events-master.csv").open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, FIELDS, lineterminator="\n")
        w.writeheader()
        for e in events:
            w.writerow({f: cell(e[f], f) for f in FIELDS})
    # JSON : listes natives, mais « inconnu » pour une liste vide
    jevents = [{f: (e[f] if e[f] != [] else UNKNOWN) for f in FIELDS} for e in events]
    (OUT / "events-master.json").write_text(json.dumps(dict(schema=FIELDS, unknown_value=UNKNOWN, events=jevents),
                                                      ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    with (OUT / "events-merge-review.csv").open("w", encoding="utf-8", newline="") as h:
        cols = ["source_a", "name_a", "start_a", "source_b", "name_b", "start_b", "similarity", "same_url_domain"]
        w = csv.DictWriter(h, cols, lineterminator="\n")
        w.writeheader()
        w.writerows(candidates)
    fill = {f: sum(1 for e in events if e[f] not in (UNKNOWN, [])) for f in FIELDS}
    combos = {}
    for e in events:
        k = "+".join(e["sources"])
        combos[k] = combos.get(k, 0) + 1
    quality = dict(
        input_rows={s: len(r) for s, r in recs.items()},
        master_rows=len(events),
        rows_by_source_combination=combos,
        duplicates_merged=sum(len(r) for r in recs.values()) - len(events),
        date_conflicts=sum(e["date_conflict"] for e in events),
        events_with_conflict_notes=sum(bool(e["conflicts"]) for e in events),
        unparsed_dates=sum(1 for r in recs.values() for x in r if not x["start"]),
        possible_duplicates_not_merged=len(candidates),
        filled_values_per_field=fill,
        notes=["« inconnu » = champ conservé sans valeur ; un 0 des extractions (participants, exposants, prix) est traité comme inconnu.",
               "Devise des prix inconnue (aucune source ne la donne).",
               "Congrès Montréal : lieu, ville, région et pays déduits du calendrier du Palais des congrès (colonne inferred_fields).",
               "Les `topics` Vendelux sont des mots-clés bruts, parfois tronqués (ex. « Busines ») : ne pas les employer comme taxonomie."],
        retrieved=dict(vendelux=meta[0]["retrieved_at"], lensmor=meta[1]["retrieved_at"]),
    )
    (OUT / "events-master-quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return quality


if __name__ == "__main__":
    events, recs, groups, meta = build()
    q = write(events, review_candidates(groups), recs, meta)
    print(json.dumps({k: q[k] for k in ("input_rows", "master_rows", "rows_by_source_combination", "date_conflicts", "unparsed_dates", "possible_duplicates_not_merged")}, ensure_ascii=False))
