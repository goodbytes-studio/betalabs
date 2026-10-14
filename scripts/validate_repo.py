#!/usr/bin/env python3
"""Validate source integrity, row provenance, dataset consistency and authored links."""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
errors = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        errors.append(message)


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        parsed = list(reader)
        check(bool(reader.fieldnames), f"Missing CSV header: {path}")
        check(len(reader.fieldnames) == len(set(reader.fieldnames)), f"Duplicate header: {path}")
        check(all(None not in row and all(v is not None for v in row.values()) for row in parsed), f"CSV width: {path}")
    return parsed


def main():
    manifest = json.loads((ROOT / "sources/manifest.json").read_text())
    sources = {source["id"]: source for source in manifest["sources"]}
    check(len(sources) == len(manifest["sources"]), "Duplicate source IDs")
    actual = {p.resolve() for p in (ROOT / "sources/originals").iterdir() if p.is_file()}
    declared = {(ROOT / source["path"]).resolve() for source in sources.values()}
    check(actual == declared, "Originals not exactly covered by manifest")
    for sid, source in sources.items():
        path = ROOT / source["path"]
        check(path.resolve().is_relative_to(ROOT / "sources/originals"), f"Source escapes originals: {sid}")
        check(path.stat().st_size == source["bytes"], f"Source size changed: {sid}")
        check(hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"], f"Original checksum mismatch: {sid}")
        extracted = ROOT / f"sources/text/{sid}.md"
        check(extracted.exists() and extracted.stat().st_size > 100, f"Empty extraction: {sid}")
        if source["format"] == "docx":
            with zipfile.ZipFile(path) as archive:
                check(archive.testzip() is None, f"Corrupt DOCX: {sid}")
                ET.fromstring(archive.read("word/document.xml"))
    derived = ROOT / "data/derived"
    build = json.loads((derived / "build-manifest.json").read_text())
    as_of = dt.date.fromisoformat(build["as_of"])
    for name, digest in build["outputs"].items():
        check(hashlib.sha256((derived / name).read_bytes()).hexdigest() == digest, f"Generated output modified: {name}")
    tables = {name: rows(derived / name) for name in ["accounts.csv", "event-prospects.csv", "crm-accounts.csv", "organizer-contacts.csv", "events.csv"]}
    for name, records in tables.items():
        field = "account_id" if name == "accounts.csv" else "event_id" if name == "events.csv" else "record_id"
        check(len(records) == len({row[field] for row in records}), f"Duplicate IDs: {name}")
    accounts = {row["account_id"] for row in tables["accounts.csv"]}
    events = {row["event_id"]: row for row in tables["events.csv"]}
    for row in tables["accounts.csv"]:
        check(all(sid in sources for sid in row["source_ids"].split(";")), "Account source ID missing")
    for name in ["event-prospects.csv", "crm-accounts.csv"]:
        check(all(row["account_id"] in accounts for row in tables[name]), f"Orphan account reference: {name}")
    mappings = {"S07": "event-prospects.csv", "S10": "event-prospects.csv", "S23": "crm-accounts.csv", "S20": "organizer-contacts.csv"}
    for sid, name in mappings.items():
        original = rows(ROOT / sources[sid]["path"])
        mapped = [row for row in tables[name] if row["source_id"] == sid]
        check(len(original) == len(mapped), f"Source rows lost: {sid}")
        check({int(row["source_row"]) for row in mapped} == set(range(2,len(original)+2)), f"Source row coverage: {sid}")
        for row in mapped:
            check(row["source_path"] == sources[sid]["path"], f"Wrong path: {sid}")
            raw = original[int(row["source_row"])-2]
            if sid in {"S07", "S10"}:
                check(all(row.get(column) == value for column, value in raw.items()), f"Prospect raw values changed: {row['record_id']}")
                check(row["independently_verified_at"] == "", "Unsubstantiated independent verification")
                check(row["event_id"] in events, "Unknown campaign event")
                start = dt.date.fromisoformat(events[row["event_id"]]["date_start"])
                check(int(row["days_to_event"]) == (start-as_of).days, "Incorrect campaign day count")
                check(row["as_of"] == str(as_of), "Wrong analysis date")
                if events[row["event_id"]]["temporal_status"] == "passe_selon_source":
                    check(row["activation_status"] == "historique", "Past campaign incorrectly active")
                if row["participation_status"] == "unconfirmed_lead" and row["event_temporal_status"] != "passe_selon_source":
                    check(row["activation_status"] == "confirmer_inscription", "Unconfirmed lead routed to active sponsor")
            elif sid == "S23":
                preserved = {"Company":"company", "Status":"status_source", "Buyer":"buyer", "User":"user", "Solution":"solution", "Industry":"industry", "Company Size":"company_size_raw", "1st talk --> GO":"days_to_go_raw", "1st talk --> Deposit":"days_to_deposit_raw", "Event":"event_raw", "Attendee Type":"attendee_type", "Package Price":"package_price_raw", "Matches":"matches_raw"}
                check(all(raw[old] == row[new] for old,new in preserved.items()), f"CRM raw values changed: {row['record_id']}")
                check(row["payment_status"] == "not_verified", "Payment fabricated from CRM")
            else:
                preserved = {"Événement":"event_raw", "Contact":"contact_name", "Rôle":"role", "Organisation":"organization", "Email":"email", "Téléphone":"phone", "LinkedIn":"linkedin", "Priorité":"priority_source", "Notes":"notes"}
                check(all(raw[old] == row[new] for old,new in preserved.items()), f"Contact raw values changed: {row['record_id']}")
    original_events = rows(ROOT / sources["S39"]["path"])
    mapped_events = [row for row in tables["events.csv"] if row["source_row"]]
    check(len(original_events) == len(mapped_events), "Event source rows lost")
    for row in tables["events.csv"]:
        check(all(sid in sources for sid in row["source_ids"].split(";")), "Unknown event provenance")
        check(row["independently_verified_at"] == "", "Event verification fabricated")
        if row["source_row"]:
            raw = original_events[int(row["source_row"])-2]
            check(row["name"] == raw["name"] and row["date_raw"] == raw["date"], "Event name/date changed")
            check(all(row.get(k) == v for k,v in raw.items() if k not in {"name","date"}), "Event source values changed")
        if row["date_precision"] == "partial_or_unknown":
            check(row["date_start"] == row["date_end"] == row["days_to_event"] == "", "Day invented for partial date")
    allowed_claims = {"documented_coherent", "computed_from_csv", "source_cleared_unverified_here", "needs_evidence", "conflicted", "rejected_in_latest_sources", "historical_or_hypothesis"}
    for path in (ROOT / "data/registers").glob("*.csv"):
        records = rows(path)
        id_field = next(iter(records[0]))
        check(len(records) == len({row[id_field] for row in records}), f"Duplicate registry IDs: {path}")
        for row in records:
            check(all(sid in sources for sid in row["source_ids"].split(";")), f"Registry source missing: {path}")
            if path.name == "claims.csv":
                check(row["status"] in allowed_claims, "Unknown claim status")
    generated_or_external = {".git", ".event-machine", "node_modules", "dist"}
    docs = [path for path in ROOT.rglob("*.md") if not path.is_relative_to(ROOT / "sources")
            and not generated_or_external.intersection(path.parts)]
    links = 0
    for path in docs + [ROOT / "sources/README.md"]:
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", path.read_text()):
            if target.startswith(("https://", "http://", "#", "mailto:")):
                continue
            target = unquote(target.split("#",1)[0])
            links += 1
            check((path.parent/target).exists(), f"Broken link: {path.relative_to(ROOT)} -> {target}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    source_rows = sum(len(rows(ROOT / source["path"])) for source in sources.values() if source["format"] == "csv")
    print(f"PASS: {checks} integrity checks; {len(sources)} sources; {source_rows} CSV source rows traced; {links} local links; as-of {as_of}.")


if __name__ == "__main__":
    main()
