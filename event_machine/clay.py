"""Append-only Clay table webhook transport with identity check and local send ledger."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from .core import read_csv

TABLES = {"participants", "accounts", "matches", "evidence"}


def current_identity() -> dict:
    try:
        result = subprocess.run(["clay", "whoami"], text=True, capture_output=True, timeout=25, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Clay CLI unavailable or timed out") from exc
    if result.returncode:
        raise RuntimeError("Clay authentication unavailable: use the Connect Clay button or run 'clay login'")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Clay whoami did not return JSON") from exc
    return data


def identity(expected_workspace: str, expected_email: str = "", expected_user_id: str = "") -> dict:
    if not expected_workspace or not (expected_email or expected_user_id):
        raise ValueError("Expected Clay workspace ID and user identity are required")
    data = current_identity()
    workspace = data.get("workspace", {})
    user = data.get("user", {})
    if str(workspace.get("id", "")) != str(expected_workspace):
        raise ValueError("Active Clay workspace differs from configured destination")
    if expected_email and str(user.get("email", "")).casefold() != expected_email.casefold():
        raise ValueError("Active Clay user differs from Elizabeth's configured email")
    if expected_user_id and str(user.get("id", "")) != expected_user_id:
        raise ValueError("Active Clay user differs from the pinned user")
    return {"workspace_id": str(workspace["id"]), "workspace_name": workspace.get("name"),
            "user_email": user.get("email"), "user_id": user.get("id")}


def webhook_url(table: str, supplied: str = "") -> str:
    url = (supplied or os.environ.get("BETA_CLAY_WEBHOOK_" + table.upper(), "")).strip()
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in {"clay.com", "api.clay.com", "app.clay.com"} and not host.endswith(".clay.com"):
        raise ValueError("Configure a Clay HTTPS table webhook URL for " + table)
    return url


def config_path(data_dir: Path) -> Path:
    return data_dir / "clay-connection.json"


def read_config(data_dir: Path) -> dict:
    path = config_path(data_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def save_config(data_dir: Path, value: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = config_path(data_dir)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    path.chmod(0o600)


def pin_current(data_dir: Path) -> dict:
    who = current_identity()
    user = who.get("user", {})
    workspace = who.get("workspace", {})
    if not user.get("id") or not workspace.get("id"):
        raise ValueError("Clay did not return a user and workspace ID")
    old = read_config(data_dir)
    same = old.get("user_id") == user["id"] and old.get("workspace_id") == str(workspace["id"])
    config = {"user_id": user["id"], "user_email": user.get("email"),
              "workspace_id": str(workspace["id"]), "workspace_name": workspace.get("name"),
              "webhooks": old.get("webhooks", {}) if same else {}}
    save_config(data_dir, config)
    return {k: v for k, v in config.items() if k != "webhooks"}


def set_webhook(data_dir: Path, table: str, url: str) -> dict:
    if table not in TABLES:
        raise ValueError("Unsupported table")
    config = read_config(data_dir)
    if not config:
        raise ValueError("Pin the Clay user and workspace first")
    identity(config["workspace_id"], expected_user_id=config["user_id"])
    valid = webhook_url(table, url)
    config.setdefault("webhooks", {})[table] = valid
    save_config(data_dir, config)
    return {"table": table, "destination_fingerprint": hashlib.sha256(valid.encode()).hexdigest()[:16]}


def connection_status(data_dir: Path) -> dict:
    config = read_config(data_dir)
    try:
        who = current_identity()
        active = {"user_id": who.get("user", {}).get("id"), "user_email": who.get("user", {}).get("email"),
                  "workspace_id": str(who.get("workspace", {}).get("id", "")),
                  "workspace_name": who.get("workspace", {}).get("name"),
                  "signed_in_workspaces": who.get("signedInWorkspaces", [])}
    except RuntimeError as exc:
        active = {"error": str(exc)}
    pinned = {key: config.get(key) for key in ("user_id", "user_email", "workspace_id", "workspace_name") if key in config}
    return {"active": active, "pinned": pinned, "configured_tables": sorted(config.get("webhooks", {}))}


def switch_workspace(workspace_id: str) -> dict:
    if not workspace_id.isdigit():
        raise ValueError("Invalid workspace ID")
    result = subprocess.run(["clay", "workspaces", "switch", workspace_id], text=True,
                            capture_output=True, timeout=25, check=False)
    if result.returncode:
        raise RuntimeError("Could not switch Clay workspace; check account access")
    return current_identity()


def push(*, run_dir: Path, table: str, workspace_id: str, account_email: str,
         ledger_path: Path, apply: bool = False, expected_user_id: str = "", webhook: str = "") -> dict:
    if table not in TABLES:
        raise ValueError("Unsupported table: " + table)
    source = run_dir / (table + ".csv")
    if not source.is_file():
        raise ValueError("Missing output CSV: " + str(source))
    rows = read_csv(source)
    who = identity(workspace_id, account_email, expected_user_id)
    url = webhook_url(table, webhook)
    destination = hashlib.sha256(url.encode()).hexdigest()[:16]
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ledger_path)
    db.execute("CREATE TABLE IF NOT EXISTS sent(destination TEXT, table_name TEXT, row_hash TEXT, sent_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(destination,table_name,row_hash))")
    pending = []
    for row in rows:
        body = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(body).hexdigest()
        if not db.execute("SELECT 1 FROM sent WHERE destination=? AND table_name=? AND row_hash=?", (destination, table, digest)).fetchone():
            pending.append((digest, body))
    result = {"identity": who, "table": table, "source_rows": len(rows), "pending": len(pending),
              "already_sent": len(rows) - len(pending), "destination_fingerprint": destination,
              "transport": "Clay incoming table webhook; append-only", "applied": False}
    if not apply:
        db.close()
        return result
    sent = 0
    try:
        for digest, body in pending:
            request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "BETA-Labs-EventMachine/0.1"}, method="POST")
            with urllib.request.urlopen(request, timeout=30) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError("Clay webhook rejected a row: HTTP " + str(response.status))
            db.execute("INSERT INTO sent(destination,table_name,row_hash) VALUES(?,?,?)", (destination, table, digest))
            db.commit()
            sent += 1
    finally:
        db.close()
    result.update({"applied": True, "sent": sent})
    return result
