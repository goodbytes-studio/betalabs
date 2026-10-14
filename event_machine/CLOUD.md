# Exécution privée dans Codex Cloud

Le runtime retenu pour cette version est **Codex Cloud**. Le même moteur Python fonctionne dans Claude Code si une équipe installe et autorise séparément ce runtime, mais Claude n'est pas configuré dans l'environnement livré ici.

## Démarrer une session

Dans une tâche Codex ouverte sur ce dépôt :

```bash
cd /workspace/betalabs
./scripts/start_event_machine_codex.sh
```

Ouvrir `http://127.0.0.1:8765/` dans l'aperçu privé de la tâche. `BETA_MACHINE_PORT` et `BETA_MACHINE_DATA_DIR` peuvent être définis pour cette session. Le serveur écoute exclusivement sur `127.0.0.1`; ses routes contiennent les CSV et les résultats et ne doivent pas être publiées directement sur Internet. Le script impose des permissions locales restrictives au répertoire de données.

Les données et la base de feedback sont dans `.event-machine/` par défaut. Ce stockage appartient à l'environnement de la tâche; **sa conservation entre environnements n'est pas garantie**. Pour un service d'équipe permanent, il faut un volume privé sauvegardé, un accès authentifié en amont, une séparation des utilisateurs et une destination d'hébergement choisie. Le simple accès GitHub d'Elizabeth ne fournit ni ce stockage ni sa connexion Clay.

## Agents disponibles

À chaque analyse, télécharger `agent-handoff.md` dans **Résultats → Agents & preuves**. Il donne les chemins et les SHA-256 des entrées. Les consignes détaillées sont dans [`AGENTS.md`](AGENTS.md). Dans la tâche Codex, l'orchestrateur peut déléguer simultanément la recherche événement, la résolution des comptes et les signaux entreprises, puis demander un contrôle des preuves. Le rôle de publication Clay intervient après cette revue.

L'agent Signaux entreprises produit un JSON conforme à [`company-signals.schema.json`](agents/company-signals.schema.json). L'importer dans l'onglet **Agents & preuves**, ou en ligne de commande :

```bash
python3 -m event_machine agent-ingest \
  --out .event-machine/runs/ID_DU_RUN/outputs \
  --artifact /chemin/vers/company-signals.json
```

L'import vérifie le domaine du compte, les champs des ICP de ce run, les URL HTTPS, les dates et la présence d'une citation. Il écrit `agent-work/evidence-candidates-*.csv` avec `confidence=low`, même si l'agent dit `high`. Une personne vérifie les sources et choisit les valeurs à importer comme entrée Preuves et signaux d'une **nouvelle** analyse. Les règles ICP et exclusions restent calculées par Python; le feedback humain reste distinct.

L'application ne lance pas directement un sous-processus `codex exec` depuis le navigateur. Les agents s'exécutent dans la tâche Codex qui héberge l'application. Cette séparation évite de faire exécuter à un modèle des instructions contenues dans un CSV ou une page web et garde les permissions des connecteurs sous le contrôle de la tâche.

## État des accès observé le 14 octobre 2026

| Capacité | État dans cette tâche | Effet |
|---|---|---|
| Interface, calcul ICP, revue SQLite | Fonctionnels dans Codex Cloud | Parcours HOP hors ligne testable |
| Agents Codex de la tâche | Disponibles | Délégation par l'orchestrateur Codex, avec fichiers de transfert |
| Recherche directe de `www.cqcd.org` | Domaine absent de la politique réseau actuelle | Utiliser les snapshots fournis; la recherche live consigne l'échec |
| Connecteur Clay de la tâche Codex | Workspace GoodBytes 659090 accessible en lecture | Les agents peuvent consulter les données permises par ce connecteur; cela n'authentifie pas le CLI ni Elizabeth |
| Clay CLI d'Elizabeth | Non authentifié; domaines Clay absents de la politique | Aucun envoi Clay possible dans cette tâche |
| `codex exec` lancé depuis le conteneur | API bloquée par la politique réseau actuelle | Ne pas le traiter comme un runner d'agents disponible |
| Claude Code | CLI et authentification absents | Non vérifié |

La politique réseau et les connexions du cloud doivent être configurées par le mécanisme de configuration de l'environnement, puis revérifiées. Les domaines nécessaires dépendent de l'événement et des appels réels de Clay; pour HOP, commencer par `www.cqcd.org` et les hôtes Clay retournés par le CLI. N'ajouter aucun jeton, webhook ou CSV de participants au dépôt. Le rôle Clay vérifie l'identité et le workspace actifs avant tout envoi.
