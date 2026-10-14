"""Command line entrypoint and reusable pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from .core import (feedback_template, infer_org_type, infer_sector, match_person, person_event_hypothesis,
                   parse_accounts, parse_evidence, parse_people, read_csv, relations_by_key,
                   review_queue, role_features, run_manifest, stable_id, validate_profiles, write_csv)
from .feedback import connect, exact_review, feedback_metrics, import_feedback, ranking_bias
from .research import research_event, scan_account_website, summarize_event
from .agents import ingest_company_signals, write_handoff


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def run_pipeline(*, event_path: Path, participants_path: Path, icps_path: Path, out: Path,
                 accounts_path: Path | None = None, relations_path: Path | None = None,
                 evidence_path: Path | None = None, db_path: Path | None = None,
                 offline: bool = False, max_pages: int = 6, research_accounts: int = 0) -> dict:
    if not 0 <= max_pages <= 20 or not 0 <= research_accounts <= 100:
        raise ValueError("max_pages must be 0-20 and research_accounts must be 0-100")
    event = load_json(event_path)
    if not event.get("id") or not event.get("name"):
        raise ValueError("event.json requires id and name")
    profiles = validate_profiles(load_json(icps_path))
    raw_people = read_csv(participants_path)
    if not raw_people:
        raise ValueError("Participant CSV is empty")
    raw_accounts = read_csv(accounts_path) if accounts_path else []
    raw_relations = read_csv(relations_path) if relations_path else []
    raw_evidence = read_csv(evidence_path) if evidence_path else []
    out.mkdir(parents=True, exist_ok=True)
    pages, research_errors = research_event(event, max_pages=max_pages, allow_network=not offline)
    accounts, accounts_by_key, accounts_by_name = parse_accounts(raw_accounts)
    people = parse_people(raw_people, event["id"], accounts_by_key, accounts_by_name,
                          event.get("registration_marker", ""))
    accounts = sorted(accounts_by_key.values(), key=lambda a: a["account_id"])
    for person in people:
        account = accounts_by_key.get(person["account_id"], {})
        functions, seniority = role_features(person["job_title"])
        typology, why, objective = person_event_hypothesis(person["job_title"], infer_org_type(account)[0])
        person.update({"typology": typology, "role_functions": " | ".join(sorted(functions)),
                       "role_influence": seniority, "why_attend": why, "business_objective": objective})
    if research_accounts > 0 and not offline:
        scanned = 0
        for account in accounts:
            if scanned >= research_accounts:
                break
            if not account.get("website"):
                continue
            try:
                observations = scan_account_website(account["website"])
            except (OSError, ValueError) as exc:
                research_errors.append({"url": account["website"], "error": type(exc).__name__, "detail": str(exc)[:180]})
                continue
            scanned += 1
            for item in observations:
                raw_evidence.append({"domain_join_key": account["domain"], **item})
    evidence = parse_evidence(raw_evidence)
    relations = relations_by_key(raw_relations)
    connection = connect(db_path or out / "feedback.sqlite3")
    matches = []
    try:
        for person in people:
            account = accounts_by_key.get(person["account_id"], {})
            org, _ = infer_org_type(account)
            sector, _ = infer_sector(account)
            _, seniority = role_features(person["job_title"])
            for profile in profiles:
                match_key = "|".join((event["id"], person["person_id"], profile["id"]))
                bias = ranking_bias(connection, profile["id"], org, sector, seniority)
                reviewed = exact_review(connection, match_key, person["account_id"])
                matches.append(match_person(person, account, profile,
                                            evidence.get(account.get("domain", ""), {}),
                                            relations.get((account.get("domain", ""), profile["id"])),
                                            bias, reviewed))
    finally:
        connection.close()
    manifest = run_manifest(event, pages, research_errors, people, accounts, matches)
    manifest["inputs"] = {key: {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                          for key, path in {"event": event_path, "participants": participants_path, "icps": icps_path,
                                            "accounts": accounts_path, "relations": relations_path, "evidence": evidence_path}.items() if path}
    manifest["client_counts"] = {profile["id"]: dict(Counter(r["machine_status"] for r in matches if r["client_id"] == profile["id"])) for profile in profiles}
    (out / "event-brief.md").write_text(summarize_event(event, pages, research_errors, people, accounts, profiles), encoding="utf-8")
    (out / "event-pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "research-errors.json").write_text(json.dumps(research_errors, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(out / "participants.csv", people)
    write_csv(out / "accounts.csv", accounts)
    write_csv(out / "matches.csv", matches)
    people_by_id = {person["person_id"]: person for person in people}
    accounts_by_id = {account["account_id"]: account for account in accounts}
    clay_columns = ["match_key", "event_id", "event_name", "run_as_of", "client_id", "client_name",
                    "person_id", "person_name", "email", "profile_url", "company_name", "account_id",
                    "company_domain", "job_title", "typology", "role_influence", "why_attend",
                    "business_objective", "fit_status", "machine_status", "priority_score", "attendance_status",
                    "company_link_status", "fit_reasons", "exclusion_reasons", "evidence_urls",
                    "opportunity_hypothesis", "next_question", "relationship", "relationship_owner",
                    "reviewed_by", "review_note"]
    clay_rows = []
    for match in sorted(matches, key=lambda item: (-int(item["priority_score"]), item["match_key"])):
        person = people_by_id[match["person_id"]]
        account = accounts_by_id.get(match["account_id"], {})
        row = {key: match.get(key, "") for key in clay_columns}
        row.update({"event_name": event["name"], "run_as_of": manifest["as_of"],
                    "email": person.get("email", ""), "profile_url": person.get("profile_url", ""),
                    "company_domain": account.get("domain", "")})
        clay_rows.append(row)
    write_csv(out / "clay-import-all.csv", clay_rows, clay_columns)
    write_csv(out / "clay-import-priority.csv", [row for row in clay_rows
              if row["machine_status"] in {"fort", "possible"}], clay_columns)
    write_csv(out / "review-queue.csv", review_queue(matches),
              ["match_key", "client_id", "person_name", "company_name", "fit_status", "priority_score", "primary_gap", "next_question"])
    write_csv(out / "feedback-template.csv", feedback_template(matches),
              ["match_key", "reviewed_fit", "reviewer", "note", "evidence_url", "scope"])
    write_csv(out / "evidence.csv", raw_evidence, None if raw_evidence else
              ["domain_join_key", "field", "value", "source_url", "checked_at", "confidence", "caveat"])
    (out / "run-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_handoff(out, manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="event-machine", description="BETA Labs event ICP machine")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Research an event and qualify its roster")
    run.add_argument("--event", type=Path, required=True)
    run.add_argument("--participants", type=Path, required=True)
    run.add_argument("--icps", type=Path, required=True)
    run.add_argument("--accounts", type=Path)
    run.add_argument("--relations", type=Path)
    run.add_argument("--evidence", type=Path)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--db", type=Path)
    run.add_argument("--offline", action="store_true")
    run.add_argument("--max-pages", type=int, default=6)
    run.add_argument("--research-accounts", type=int, default=0)
    feedback = sub.add_parser("feedback", help="Import human-reviewed matches for future runs")
    feedback.add_argument("--db", type=Path, required=True)
    feedback.add_argument("--matches", type=Path, required=True)
    feedback.add_argument("--reviews", type=Path, required=True)
    stats = sub.add_parser("stats", help="Show reviewed outcomes")
    stats.add_argument("--db", type=Path, required=True)
    agent_ingest = sub.add_parser("agent-ingest", help="Validate agent signal proposals for human review")
    agent_ingest.add_argument("--out", type=Path, required=True, help="Output directory of an existing run")
    agent_ingest.add_argument("--artifact", type=Path, required=True, help="JSON from the company-signals agent")
    serve = sub.add_parser("serve", help="Launch the local team interface")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--data-dir", type=Path, default=Path(".event-machine"))
    clay = sub.add_parser("clay", help="Check identity and append a run CSV to a Clay table webhook")
    clay.add_argument("--run-dir", type=Path, required=True)
    clay.add_argument("--table", choices=["participants", "accounts", "matches", "evidence"], required=True)
    clay.add_argument("--workspace-id", required=True)
    clay.add_argument("--account-email", required=True)
    clay.add_argument("--ledger", type=Path, default=Path(".event-machine/clay-sends.sqlite3"))
    clay.add_argument("--apply", action="store_true", help="Send pending rows; default is a dry run")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        result = run_pipeline(event_path=args.event, participants_path=args.participants,
                              icps_path=args.icps, accounts_path=args.accounts,
                              relations_path=args.relations, evidence_path=args.evidence,
                              out=args.out, db_path=args.db, offline=args.offline,
                              max_pages=args.max_pages, research_accounts=args.research_accounts)
    elif args.command == "feedback":
        result = import_feedback(args.db, args.reviews, args.matches)
    elif args.command == "stats":
        result = feedback_metrics(args.db)
    elif args.command == "agent-ingest":
        result = ingest_company_signals(args.out, args.artifact)
    elif args.command == "clay":
        from .clay import push
        result = push(run_dir=args.run_dir, table=args.table, workspace_id=args.workspace_id,
                      account_email=args.account_email, ledger_path=args.ledger, apply=args.apply)
    else:
        from .web import serve
        serve(args.port, args.data_dir)
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))
