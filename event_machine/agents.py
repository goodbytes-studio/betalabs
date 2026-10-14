"""Versioned handoffs between the deterministic machine and Codex/Claude agents.

Agents propose research. Their output never changes a fit status until an
analyst reviews the evidence and runs the machine again.
"""

from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .core import read_csv


ROLES = (
    ("event-research", "Recherche événement", "Programme, marché, acheteurs et vendeurs, avec URL et date pour chaque fait."),
    ("account-identity", "Résolution des comptes", "Doublons, domaines et rattachements ambigus; aucun lien forcé."),
    ("company-signals", "Signaux entreprises", "Signaux ICP par compte, avec citation exacte et page source."),
    ("evidence-qa", "Contrôle des preuves", "Contradictions, fraîcheur, champs manquants et hypothèses à confirmer."),
    ("clay-publisher", "Publication Clay", "Identité d’Elizabeth, workspace, aperçu et envoi autorisé."),
)


def write_handoff(out: Path, manifest: dict) -> None:
    """Create a run-specific brief that a Codex task can delegate to specialists."""
    inputs = manifest.get("inputs", {})
    lines = ["# Mission des agents — " + manifest["event_name"], "",
             "Exécuter ces rôles dans une tâche Codex cloud, depuis le même dépôt et le même répertoire privé de données.",
             "Le moteur Python attribue seul les statuts ICP et les exclusions. Les agents proposent des faits ou des questions.", "",
             "## Entrées de cette analyse", ""]
    for name, item in inputs.items():
        lines.append(f"- `{name}` : `{item['path']}` ; SHA-256 `{item['sha256']}`")
    lines.append(f"- `accounts.csv` calculé : SHA-256 `{hashlib.sha256((out / 'accounts.csv').read_bytes()).hexdigest()}`")
    lines += ["", "## Rôles", ""]
    for role, title, purpose in ROLES:
        lines.append(f"- **{title}** (`{role}`) : {purpose}")
    lines += ["", "## Transfert contrôlé", "",
              "1. Recherche événement : lire `event-pages.json`, `research-errors.json` et la page officielle. Écrire une note sourcée distincte; ne jamais déduire une inscription d’un programme public.",
              "2. Résolution des comptes : examiner `accounts.csv` et les lignes incertaines de `participants.csv`. Produire les conflits à revoir, sans modifier les CSV originaux.",
              "3. Signaux entreprises : lire `accounts.csv`, le JSON ICP et `review-queue.csv`. Produire un JSON conforme à `event_machine/agents/company-signals.schema.json`.",
              "4. Contrôle des preuves : ouvrir chaque source, vérifier la citation, la date, le domaine et l’identité de la société. Conserver `[Déduit]` pour toute intention supposée.",
              "5. Transformer le JSON en candidats CSV avec `python3 -m event_machine agent-ingest --out <dossier-sorties> --artifact <json>`. Le fichier obtenu garde une confiance `low` jusqu’à la revue humaine. Importer le CSV revu comme entrée `Preuves et signaux`, puis relancer l’analyse.",
              "6. Clay : vérifier l’utilisateur et le workspace actifs, prévisualiser la destination et les lignes; envoyer seulement depuis un contexte autorisé. Le connecteur vérifie l’identité avant chaque envoi.", "",
              "Les rôles détaillés sont dans `event_machine/AGENTS.md`. Les agents n’ont pas d’autorité sur une connexion Clay ou un budget par la seule lecture du dépôt.", ""]
    (out / "agent-handoff.md").write_text("\n".join(lines), encoding="utf-8")


def _source_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if host in {"localhost", "localhost.localdomain"} or "." not in host:
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        return parsed.scheme == "https" and not parsed.username and not parsed.password and parsed.port in (None, 443)
    except ValueError:
        return False


def ingest_company_signals(out: Path, artifact: Path) -> dict:
    """Validate agent proposals and keep them separate from verified evidence."""
    manifest = json.loads((out / "run-manifest.json").read_text(encoding="utf-8"))
    icps_entry = manifest["inputs"]["icps"]
    icps_path = Path(icps_entry["path"])
    if hashlib.sha256(icps_path.read_bytes()).hexdigest() != icps_entry["sha256"]:
        raise ValueError("ICP input changed after this run; start a new analysis")
    icps = json.loads(icps_path.read_text(encoding="utf-8-sig"))
    allowed_fields = {signal["field"] for client in icps["clients"] for signal in client.get("signals", [])}
    accounts_path = out / "accounts.csv"
    known_domains = {row.get("domain", "").lower() for row in read_csv(accounts_path) if row.get("domain")}
    raw = artifact.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("role") != "company-signals":
        raise ValueError("Expected a version 1 company-signals artifact")
    if (data.get("event_id") != manifest["event_id"] or
            data.get("icps_sha256") != icps_entry["sha256"] or
            data.get("accounts_sha256") != hashlib.sha256(accounts_path.read_bytes()).hexdigest()):
        raise ValueError("Agent artifact belongs to different event, ICP or account inputs")
    observations = data.get("observations")
    if not isinstance(observations, list) or len(observations) > 100:
        raise ValueError("Expected at most 100 observations")
    rows = []
    for index, item in enumerate(observations, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Observation {index} must be an object")
        domain = str(item.get("domain_join_key", "")).strip().lower()
        field = str(item.get("field", "")).strip()
        value = str(item.get("value", "")).strip()
        url = str(item.get("source_url", "")).strip()
        quote = str(item.get("source_quote", "")).strip()
        checked = str(item.get("checked_at", "")).strip()
        if domain not in known_domains or not re.fullmatch(r"[a-z0-9.-]+", domain):
            raise ValueError(f"Observation {index}: unknown account domain")
        if field not in allowed_fields or not 0 < len(value) <= 200:
            raise ValueError(f"Observation {index}: invalid ICP field or value")
        if not _source_url(url) or not 12 <= len(quote) <= 500:
            raise ValueError(f"Observation {index}: HTTPS source and 12-500 character quote required")
        try:
            observed_date = date.fromisoformat(checked)
        except ValueError as exc:
            raise ValueError(f"Observation {index}: invalid checked_at date") from exc
        if observed_date > date.today():
            raise ValueError(f"Observation {index}: future checked_at date")
        rows.append({"domain_join_key": domain, "field": field, "value": value,
                     "source_url": url, "checked_at": checked, "confidence": "low",
                     "caveat": "Proposition d’agent; citation et interprétation à vérifier avant promotion.",
                     "source_quote": quote, "agent_role": "company-signals",
                     "agent_claimed_confidence": str(item.get("confidence", ""))[:30]})
    target = out / "agent-work"
    target.mkdir(mode=0o700, exist_ok=True)
    target.chmod(0o700)
    digest = hashlib.sha256(raw).hexdigest()
    csv_path = target / f"evidence-candidates-{digest[:12]}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["domain_join_key", "field", "value", "source_url",
                                                      "checked_at", "confidence", "caveat", "source_quote",
                                                      "agent_role", "agent_claimed_confidence"])
        writer.writeheader()
        writer.writerows(rows)
    csv_path.chmod(0o600)
    receipt = {"artifact_sha256": digest, "candidates": len(rows), "csv_path": str(csv_path),
               "status": "review_required", "run_event_id": manifest["event_id"]}
    receipt_path = target / f"receipt-{digest[:12]}.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_path.chmod(0o600)
    return receipt
