"""Local, dependency-free team interface. Files remain on the operator's machine."""

from __future__ import annotations

import json
import mimetypes
import re
import subprocess
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .cli import run_pipeline
from .feedback import feedback_metrics, import_feedback

MAX_POST = 20_000_000
INPUT_FILES = {"participants": "participants.csv", "accounts": "accounts.csv",
               "relations": "relations.csv", "evidence": "evidence.csv"}
OUTPUT_FILES = {"event-brief.md", "event-pages.json", "research-errors.json", "participants.csv",
                "accounts.csv", "matches.csv", "review-queue.csv", "feedback-template.csv",
                "evidence.csv", "run-manifest.json"}

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend" / "dist"


def serve(port: int, data_dir: Path) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("port must be 1-65535")
    root = data_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    db = root / "feedback.sqlite3"
    login_process: subprocess.Popen | None = None
    login_lines: list[str] = []

    def consume_login(stream) -> None:
        if stream is None:
            return
        for line in stream:
            login_lines.append(line[:500])

    def login_details() -> dict:
        output = "\n".join(login_lines[-20:])
        urls = re.findall(r"https://[^\s<>\"']+", output)
        safe_url = next((url.rstrip(".,);])") for url in urls
                         if (urlsplit(url).hostname or "").lower() in {"clay.com", "app.clay.com"}
                         or (urlsplit(url).hostname or "").lower().endswith(".clay.com")), "")
        code = re.search(r"(?:user.?code|code)\s*[:=]\s*([A-Z0-9-]{4,})", output, re.I)
        if not code:
            code = re.search(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b", output)
        try:
            error = json.loads(output).get("error", {}).get("message", "")
        except json.JSONDecodeError:
            error = ""
        return {"verification_url": safe_url, "user_code": code.group(1) if code else "",
                "login_error": str(error)[:200]}

    class Handler(BaseHTTPRequestHandler):
        def send_data(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status: int, obj: dict) -> None:
            self.send_data(status, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/" or path.startswith(("/assets/", "/brand/", "/examples/")):
                static_path = (FRONTEND_DIR / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
                if not static_path.is_relative_to(FRONTEND_DIR) or not static_path.is_file():
                    return self.send_json(404, {"error": "Asset not found"})
                content_type = mimetypes.guess_type(static_path.name)[0] or "application/octet-stream"
                return self.send_data(200, static_path.read_bytes(), content_type)
            if path == "/api/clay/status":
                from .clay import connection_status
                result = connection_status(root)
                result["login_state"] = ("running" if login_process and login_process.poll() is None else
                                          "completed" if login_process and login_process.returncode == 0 else
                                          "failed" if login_process else "not_started")
                result.update(login_details())
                return self.send_json(200, result)
            if path == "/api/runs/latest":
                candidates = sorted((root / "runs").glob("*/outputs/run-manifest.json"),
                                    key=lambda file: file.stat().st_mtime, reverse=True)
                if not candidates:
                    return self.send_json(404, {"error": "No prior run"})
                manifest_file = candidates[0]
                return self.send_json(200, {"run_id": manifest_file.parent.parent.name,
                                            "manifest": json.loads(manifest_file.read_text(encoding="utf-8")),
                                            "files": sorted(OUTPUT_FILES)})
            match = re.fullmatch(r"/runs/([0-9a-f]{32})/([a-z-]+\.(?:csv|json|md))", path)
            if not match or match[2] not in OUTPUT_FILES:
                return self.send_json(404, {"error": "Not found"})
            file = root / "runs" / match[1] / "outputs" / match[2]
            if not file.is_file():
                return self.send_json(404, {"error": "Not found"})
            mime = "text/csv" if file.suffix == ".csv" else "application/json" if file.suffix == ".json" else "text/markdown"
            return self.send_data(200, file.read_bytes(), mime + "; charset=utf-8")

        def do_POST(self) -> None:
            if self.path not in {"/api/run", "/api/feedback", "/api/clay"}:
                return self.send_json(404, {"error": "Not found"})
            if self.headers.get("Content-Type", "").split(";", 1)[0].lower() != "application/json":
                return self.send_json(415, {"error": "Expected application/json"})
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != self.headers.get("Host"):
                return self.send_json(403, {"error": "Origin mismatch"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_POST:
                    raise ValueError("Invalid or oversized request")
                payload = json.loads(self.rfile.read(length))
                if self.path == "/api/clay":
                    from .clay import (connection_status, pin_current, push, read_config,
                                       set_webhook, switch_workspace)
                    action = payload.get("action")
                    if action == "login":
                        nonlocal login_process
                        if login_process and login_process.poll() is None:
                            return self.send_json(200, {"login_state": "running"})
                        login_lines.clear()
                        login_process = subprocess.Popen(["clay", "login", "--device"], stdin=subprocess.DEVNULL,
                                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                         text=True, bufsize=1)
                        threading.Thread(target=consume_login, args=(login_process.stdout,), daemon=True).start()
                        threading.Thread(target=consume_login, args=(login_process.stderr,), daemon=True).start()
                        return self.send_json(200, {"login_state": "started", "next": "Open the Clay verification URL and enter the displayed code"})
                    if action == "switch":
                        who = switch_workspace(str(payload.get("workspace_id", "")))
                        return self.send_json(200, {"workspace": who.get("workspace"), "user": who.get("user")})
                    if action == "pin":
                        return self.send_json(200, {"pinned": pin_current(root)})
                    if action == "webhook":
                        return self.send_json(200, set_webhook(root, str(payload.get("table", "")), str(payload.get("url", ""))))
                    if action == "push":
                        run_id = str(payload.get("run_id", ""))
                        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
                            raise ValueError("Run an analysis in this session before pushing to Clay")
                        table = str(payload.get("table", ""))
                        config = read_config(root)
                        if not config or table not in config.get("webhooks", {}):
                            raise ValueError("Pin Clay identity and configure this table's webhook first")
                        result = push(run_dir=root / "runs" / run_id / "outputs", table=table,
                                      workspace_id=config["workspace_id"], account_email="",
                                      expected_user_id=config["user_id"], webhook=config["webhooks"][table],
                                      ledger_path=root / "clay-sends.sqlite3", apply=bool(payload.get("apply")))
                        return self.send_json(200, result)
                    raise ValueError("Unsupported Clay action")
                if self.path == "/api/run":
                    if not isinstance(payload.get("event"), dict) or not isinstance(payload.get("icps"), dict):
                        raise ValueError("event and icps must be JSON objects")
                    inputs = payload.get("inputs", {})
                    if not isinstance(inputs, dict) or not inputs.get("participants"):
                        raise ValueError("Participants CSV is required")
                    run_id = uuid.uuid4().hex
                    folder = root / "runs" / run_id
                    source = folder / "inputs"
                    source.mkdir(parents=True)
                    for key in ("event", "icps"):
                        (source / (key + ".json")).write_text(json.dumps(payload[key], ensure_ascii=False), encoding="utf-8")
                    paths = {}
                    for key, name in INPUT_FILES.items():
                        if inputs.get(key):
                            paths[key] = source / name
                            paths[key].write_text(inputs[key], encoding="utf-8")
                    manifest = run_pipeline(event_path=source / "event.json", icps_path=source / "icps.json",
                                            participants_path=paths["participants"], accounts_path=paths.get("accounts"),
                                            relations_path=paths.get("relations"), evidence_path=paths.get("evidence"),
                                            out=folder / "outputs", db_path=db, offline=bool(payload.get("offline")))
                    return self.send_json(200, {"run_id": run_id, "manifest": manifest, "files": sorted(OUTPUT_FILES)})
                run_id = payload.get("run_id", "")
                if not re.fullmatch(r"[0-9a-f]{32}", run_id):
                    raise ValueError("Invalid run_id")
                folder = root / "runs" / run_id
                matches = folder / "outputs" / "matches.csv"
                if not matches.is_file():
                    raise ValueError("Run not found")
                review_path = folder / "inputs" / "reviews.csv"
                review_path.write_text(str(payload.get("reviews", "")), encoding="utf-8")
                imported = import_feedback(db, review_path, matches)
                return self.send_json(200, {**imported, "metrics": feedback_metrics(db)})
            except (ValueError, KeyError, json.JSONDecodeError, RuntimeError, FileNotFoundError) as exc:
                return self.send_json(400, {"error": str(exc)[:500]})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Machine BETA Labs: http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if login_process and login_process.poll() is None:
            login_process.terminate()
