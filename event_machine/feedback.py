"""Human-reviewed corrections and conservative cross-event ranking calibration."""

from __future__ import annotations

import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .core import read_csv


SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    match_key TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    person_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    reviewed_fit TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    note TEXT NOT NULL,
    evidence_url TEXT NOT NULL,
    scope TEXT NOT NULL,
    org_type TEXT NOT NULL,
    sector TEXT NOT NULL,
    seniority TEXT NOT NULL,
    role_functions TEXT NOT NULL,
    reviewed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_client ON reviews(client_id);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection


def import_feedback(db_path: Path, reviewed_path: Path, matches_path: Path) -> dict:
    matches = {row["match_key"]: row for row in read_csv(matches_path)}
    reviews = read_csv(reviewed_path)
    accepted = {"fort", "possible", "exclu", "à confirmer"}
    count = 0
    connection = connect(db_path)
    try:
        with connection:
            for row in reviews:
                outcome = row.get("reviewed_fit", "").strip().lower()
                if not outcome:
                    continue
                key = row.get("match_key", "")
                if key not in matches:
                    raise ValueError("Unknown match_key in feedback: " + key)
                if outcome not in accepted:
                    raise ValueError("Invalid reviewed_fit for " + key + ": " + outcome)
                reviewer = row.get("reviewer", "").strip()
                note = row.get("note", "").strip()
                url = row.get("evidence_url", "").strip()
                scope = row.get("scope", "person_event").strip() or "person_event"
                if not reviewer or not note or scope != "person_event":
                    raise ValueError("Feedback requires reviewer, note and scope=person_event for " + key)
                if outcome == "fort" and not url:
                    raise ValueError("Confirmed fit requires an evidence_url for " + key)
                original = matches[key]
                connection.execute("""
                    INSERT INTO reviews(match_key,event_id,person_id,client_id,account_id,reviewed_fit,reviewer,note,evidence_url,scope,org_type,sector,seniority,role_functions,reviewed_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(match_key) DO UPDATE SET
                      reviewed_fit=excluded.reviewed_fit,reviewer=excluded.reviewer,note=excluded.note,
                      evidence_url=excluded.evidence_url,org_type=excluded.org_type,sector=excluded.sector,
                      seniority=excluded.seniority,role_functions=excluded.role_functions,reviewed_at=excluded.reviewed_at
                """, (key, original["event_id"], original["person_id"], original["client_id"], original["account_id"],
                      outcome, reviewer, note, url, scope, original["org_type"], original["sector"], original["seniority"],
                      original["role_functions"], datetime.now(timezone.utc).isoformat()))
                count += 1
    finally:
        connection.close()
    return {"reviews_imported_or_updated": count, "rows_in_feedback_file": len(reviews)}


def exact_review(connection: sqlite3.Connection, match_key: str, account_id: str) -> dict | None:
    row = connection.execute("SELECT reviewed_fit, reviewer, note, evidence_url FROM reviews WHERE match_key=? AND account_id=?", (match_key, account_id)).fetchone()
    return dict(row) if row else None


def ranking_bias(connection: sqlite3.Connection, client_id: str, org_type: str, sector: str, seniority: str) -> float:
    """Feedback changes only ranking. Three reviews are required for any learned feature."""
    rows = connection.execute("SELECT reviewed_fit, org_type, sector, seniority FROM reviews WHERE client_id=? AND reviewed_fit IN ('fort','exclu')", (client_id,)).fetchall()
    if len(rows) < 6:
        return 0.0
    positives = sum(row["reviewed_fit"] == "fort" for row in rows)
    baseline = (positives + 2) / (len(rows) + 4)
    delta = 0.0
    for field, value in (("org_type", org_type), ("sector", sector), ("seniority", seniority)):
        if not value or value == "unknown":
            continue
        subset = [row for row in rows if row[field] == value]
        if len(subset) < 3:
            continue
        local_positive = sum(row["reviewed_fit"] == "fort" for row in subset)
        local = (local_positive + 2 * baseline) / (len(subset) + 2)
        local = min(.95, max(.05, local))
        base = min(.95, max(.05, baseline))
        delta += 4 * (math.log(local / (1 - local)) - math.log(base / (1 - base)))
    return max(-12.0, min(12.0, delta))


def feedback_metrics(db_path: Path) -> dict:
    connection = connect(db_path)
    try:
        rows = connection.execute("SELECT client_id, reviewed_fit, count(*) AS n FROM reviews GROUP BY client_id, reviewed_fit").fetchall()
        return {"reviews": [dict(row) for row in rows],
                "learning_policy": "Only reviewed fort/exclu labels affect future priority_score; exact event-person reviews override displayed fit."}
    finally:
        connection.close()
