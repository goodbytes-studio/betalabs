"""Local, dependency-free team interface. Files remain on the operator's machine."""

from __future__ import annotations

import json
import re
import subprocess
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

HTML = r"""<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>BETA Labs · Machine événements</title><style>
body{font:16px/1.5 system-ui,sans-serif;max-width:1050px;margin:2rem auto;padding:0 1rem;color:#172b31;background:#f4f7f5}
h1{font-size:2rem}h2{font-size:1.2rem}main{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
section{background:white;padding:1.2rem;border:1px solid #d6e1de;border-radius:8px}section.wide{grid-column:1/-1}
label{display:block;font-weight:600;margin:.8rem 0 .25rem}input,textarea{box-sizing:border-box;width:100%;font:inherit;padding:.55rem;border:1px solid #9aafaa;border-radius:4px}
textarea{height:220px;font:13px/1.45 monospace}input[type=file],input[type=checkbox]{width:auto}button{background:#174f46;color:white;border:0;border-radius:4px;padding:.7rem 1rem;font:inherit;cursor:pointer}
button:disabled{opacity:.5}a{color:#15584d}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf4f2;padding:1rem}
.muted{color:#536c65}#result{min-height:3rem}@media(max-width:740px){main{display:block}section{margin-bottom:1rem}}
</style><h1>Machine événements BETA Labs</h1><p>Recherche de l’événement, qualification ICP traçable et revue humaine. Les fichiers restent sur cette machine. Les intentions et angles d’approche sont des hypothèses.</p>
<main><section><h2>1. Événement et ICP</h2><label for="event">Événement (JSON)</label><textarea id="event">{"id":"hop-2026","name":"HOP! Le Sommet du commerce de détail 2026","url":"https://www.cqcd.org/mega-evenements/hop-le-sommet-du-commerce-de-detail-2026/","edition":"2026","date":"2026-10-27"}</textarea>
<label for="icps">Profils clients (JSON)</label><textarea id="icps">{"clients":[{"id":"client-demo","name":"Client démo","target":{"company_types":["retailer"],"role_functions":["marketing","digital"],"seniority":["executive","vp_clevel","director"]},"conversation_angle":"Vérifier les priorités du commerce numérique.","discovery_question":"Quel projet numérique est prioritaire ?"}]}</textarea>
<label><input type="checkbox" id="offline"> Mode hors ligne (utilise reference_pages dans le JSON)</label></section>
<section><h2>2. Données</h2><label>Participants CSV (obligatoire)</label><input id="participants" type="file" accept=".csv,text/csv"><label>Entreprises CSV</label><input id="accounts" type="file" accept=".csv,text/csv"><label>Relations existantes CSV</label><input id="relations" type="file" accept=".csv,text/csv"><label>Preuves et signaux CSV</label><input id="evidence" type="file" accept=".csv,text/csv"><p class="muted">Une ligne de sortie est créée par participant et par profil client. Le CA n’est vérifié que si année, CAD, statut et URL source sont présents.</p><button id="run">Lancer l’analyse</button></section>
<section class="wide"><h2>3. Résultats</h2><div id="result">Aucune analyse lancée.</div><div id="downloads"></div></section>
<section class="wide"><h2>4. Retour humain</h2><p>Téléchargez le modèle de revue, remplissez les décisions puis importez-le. Les corrections changent le rang des futures analyses après assez de cas; elles ne modifient pas automatiquement les règles d’exclusion.</p><label>CSV de revue complété</label><input id="reviews" type="file" accept=".csv,text/csv"><button id="feedback">Enregistrer la revue</button><pre id="feedback-result"></pre></section></main>
<section><h2>5. Connexion Clay d’Elizabeth</h2><p>L’authentification s’ouvre dans le navigateur local. Après connexion, vérifiez l’identité affichée et choisissez le workspace de destination. Les jetons restent gérés par le CLI Clay sur cet ordinateur.</p>
<button id="clay-login">Connecter Clay</button> <button id="clay-refresh">Vérifier la connexion</button>
<pre id="clay-status">Vérification…</pre><label>Workspace actif</label><select id="clay-workspaces"></select><button id="clay-switch">Utiliser ce workspace</button>
<button id="clay-pin">Confirmer ce compte et ce workspace</button><p class="muted">Si le navigateur ne s’ouvre pas, lancer <code>clay login --device</code> dans un terminal de cet ordinateur, puis cliquer « Vérifier la connexion ».</p>
<label>Table de sortie</label><select id="clay-table"><option>matches</option><option>participants</option><option>accounts</option><option>evidence</option></select>
<label>URL Webhook d’entrée de la table Clay</label><input id="clay-webhook" type="password" autocomplete="off" placeholder="https://…clay.com/…">
<button id="clay-save-webhook">Enregistrer la destination</button><p class="muted">L’URL est stockée localement avec accès limité; elle n’apparaît pas dans le dépôt.</p>
<button id="clay-preview">Prévisualiser l’envoi</button> <button id="clay-apply">Envoyer les lignes en attente</button><pre id="clay-result"></pre></section>
<script>
let currentRun=null;const $=id=>document.getElementById(id);
const fileText=async id=>$(id).files[0]?await $(id).files[0].text():"";
async function request(path,body){const res=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw Error(data.error||res.statusText);return data}
$("run").onclick=async()=>{const btn=$("run");btn.disabled=true;$("result").textContent="Analyse en cours…";try{const inputs={};for(const id of ["participants","accounts","relations","evidence"])inputs[id]=await fileText(id);
const data=await request("/api/run",{event:JSON.parse($("event").value),icps:JSON.parse($("icps").value),inputs,offline:$("offline").checked});currentRun=data.run_id;
$("result").textContent=`${data.manifest.counts.participants} participants · ${data.manifest.counts.accounts} entreprises · ${data.manifest.counts.matches} matchs · ${data.manifest.counts.event_pages} pages événement`;
$("downloads").innerHTML=data.files.map(f=>`<p><a href="/runs/${currentRun}/${f}" download>${f}</a></p>`).join("");}catch(e){$("result").textContent=e.message}finally{btn.disabled=false}};
$("feedback").onclick=async()=>{try{if(!currentRun)throw Error("Lancez une analyse ici avant la revue.");const reviews=await fileText("reviews");if(!reviews)throw Error("Choisissez le CSV de revue.");const data=await request("/api/feedback",{run_id:currentRun,reviews});$("feedback-result").textContent=JSON.stringify(data,null,2)}catch(e){$("feedback-result").textContent=e.message}};
async function clayStatus(){try{const res=await fetch("/api/clay/status");const data=await res.json();$("clay-status").textContent=JSON.stringify(data,null,2);const list=data.active.signed_in_workspaces||[];$("clay-workspaces").replaceChildren(...list.map(w=>{const el=document.createElement("option");el.value=w.id;el.textContent=`${w.name||w.id} (${w.id})${w.active?" · actif":""}`;if(w.active)el.selected=true;return el}));}catch(e){$("clay-status").textContent=e.message}}
$("clay-refresh").onclick=clayStatus;
for(const [id,action,data] of [["clay-login","login",()=>({})],["clay-switch","switch",()=>({workspace_id:$("clay-workspaces").value})],["clay-pin","pin",()=>({})],["clay-save-webhook","webhook",()=>({table:$("clay-table").value,url:$("clay-webhook").value})],["clay-preview","push",()=>({table:$("clay-table").value,run_id:currentRun,apply:false})],["clay-apply","push",()=>({table:$("clay-table").value,run_id:currentRun,apply:true})]]){
$(id).onclick=async()=>{try{if(action==="push"&&!currentRun)throw Error("Lancez une analyse dans cette session avant l’envoi.");const result=await request("/api/clay",{action,...data()});$("clay-result").textContent=JSON.stringify(result,null,2);await clayStatus()}catch(e){$("clay-result").textContent=e.message}}}
clayStatus();
</script></html>"""


def serve(port: int, data_dir: Path) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("port must be 1-65535")
    root = data_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    db = root / "feedback.sqlite3"
    login_process: subprocess.Popen | None = None

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
            if path == "/":
                return self.send_data(200, HTML.encode(), "text/html; charset=utf-8")
            if path == "/api/clay/status":
                from .clay import connection_status
                result = connection_status(root)
                result["login_state"] = ("running" if login_process and login_process.poll() is None else
                                          "completed" if login_process and login_process.returncode == 0 else
                                          "failed" if login_process else "not_started")
                return self.send_json(200, result)
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
                        login_process = subprocess.Popen(["clay", "login"], stdin=subprocess.DEVNULL,
                                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return self.send_json(200, {"login_state": "started", "next": "Complete Clay authorization in the browser, then refresh the connection status"})
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
