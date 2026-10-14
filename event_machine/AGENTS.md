# Agents de la machine événements

Ce dossier définit la collaboration des agents Codex pour une analyse BETA Labs. Claude Code peut utiliser les mêmes contrats de fichiers, mais le runtime livré et vérifié ici est Codex Cloud. Lire aussi `../AGENTS.md` pour la provenance des données internes.

## Orchestrateur

Partir d'un `run-manifest.json` et de `agent-handoff.md` produits par la machine. Confier des sous-tâches indépendantes aux rôles ci-dessous dans **la même tâche cloud**. Chaque agent lit seulement les fichiers nécessaires et écrit dans un dossier `agent-work/` privé à l'analyse. Ne pas donner à un agent de recherche le webhook ou la configuration Clay.

| Rôle | Entrées minimales | Sortie attendue | Accès utile |
|---|---|---|---|
| Recherche événement | `event.json`, `event-pages.json`, `research-errors.json` | Note sourcée avec acheteurs, vendeurs, contexte, lacunes | Web public, domaine de l'événement |
| Résolution des comptes | `participants.csv`, `accounts.csv` | Tableau des rattachements douteux, sans modification automatique | Recherche entreprise publique si disponible |
| Signaux entreprises | `accounts.csv`, `icps.json`, `review-queue.csv` | JSON `company-signals.schema.json` | Sites publics; Clay MCP seulement si connecté au bon compte |
| Contrôle des preuves | Note événement, JSON des signaux, sources | Corrections et éléments à valider par un humain | Pages sources et registres BETA Labs |
| Publication Clay | Exports revus, identité Clay, aperçu d'envoi | Reçu d'envoi ou blocage expliqué | Clay CLI/MCP du compte autorisé |

Ne pas lancer le rôle Clay avant la revue du lot et la vérification de l'utilisateur et du workspace d'Elizabeth. L'accès au dépôt n'est pas un accès à son compte Clay. Le connecteur existant ajoute des lignes et vérifie l'identité avant l'envoi.

## Règles de transfert

- Un fait d'événement ou d'entreprise porte une URL, une date et, pour un signal, une citation exacte. Une page de programme ne prouve jamais qu'une personne est inscrite.
- L'entreprise rattachée à un participant reste incertaine en cas de conflit de domaine ou de nom. Ne pas inventer de CA, budget, campagne payante, CMS ou intention d'achat.
- Un motif de présence ou objectif inféré conserve `[Déduit]`.
- Un agent ne modifie pas `machine_status`, une exclusion ICP, un seuil client, ni les CSV source. Il propose des preuves. `core.match_person` calcule le statut après import d'entrées revues.
- Convertir les propositions `company-signals` avec `python3 -m event_machine agent-ingest --out <outputs> --artifact <json>`. Le CSV reste en confiance `low` jusqu'à revue humaine. Une nouvelle analyse peut ensuite importer le CSV vérifié dans le champ Preuves et signaux.
- Les corrections humaines passent par `feedback-template.csv` et le flux de revue. Ne pas transformer la sortie d'un agent en décision humaine.

## Disponibilité des outils

Avant une recherche live, vérifier l'accès réel au domaine cible. Si la politique réseau le bloque, utiliser les `reference_pages` fournies et inscrire la lacune dans `research-errors.json` ou la note; ne pas annoncer une vérification web. Avant d'utiliser Clay, vérifier l'identité retournée par l'outil/CLI et la destination. Le CLI Codex présent dans un conteneur peut être connecté en apparence alors que son API est bloquée par la politique réseau; dans ce cas, utiliser les sous-agents de la tâche Codex et les contrats de fichiers, sans prétendre qu'un runner CLI a fonctionné.
