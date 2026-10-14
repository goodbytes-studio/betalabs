#!/usr/bin/env bash
set -euo pipefail
umask 077

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"

if [[ ! -f event_machine/frontend/dist/index.html ]]; then
  echo "Interface compilée manquante : cd event_machine/frontend && npm ci && npm run build" >&2
  exit 1
fi

machine_data_dir="${BETA_MACHINE_DATA_DIR:-$repo_dir/.event-machine}"
machine_port="${BETA_MACHINE_PORT:-8765}"
mkdir -p "$machine_data_dir"
chmod 700 "$machine_data_dir"

echo "BETA Labs cloud workspace : interface privée sur http://127.0.0.1:$machine_port" >&2
echo "Données de travail : $machine_data_dir (sauvegarde externe à prévoir pour une conservation durable)" >&2
exec python3 -m event_machine serve --port "$machine_port" --data-dir "$machine_data_dir"
