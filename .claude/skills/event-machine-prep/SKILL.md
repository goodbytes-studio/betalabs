---
name: event-machine-prep
description: Prépare et diagnostique une analyse de la machine événements BETA Labs, de bout en bout. Prévalidation du format des inputs (CSV participants/inscrits, CSV entreprises, ICP JSON des clients), agents de recherche web qui qualifient type d'organisation, secteur, modèle d'affaires et pays, CSV d'import Clay pour l'enrichissement final (CA, signaux), réintégration de l'export Clay, relance de la machine, diagnostic et listes de matchs par client. À utiliser dès qu'on parle de préparer, valider ou nettoyer une liste d'inscrits ou d'entreprises pour un événement (HOP, ALL IN, etc.), de générer des listes de matchs curées pour les clients ou commanditaires, de préparer un enrichissement Clay, ou de comprendre pourquoi la machine sort peu de matchs `fort`/`possible`, même si l'utilisateur ne nomme pas le skill.
---

# Préparation et diagnostic de la machine événements

Ce skill entoure le moteur `python3 -m event_machine` sans le remplacer : le moteur garde le calcul ICP, les exclusions et les statuts. Le skill prépare des entrées propres, fait chercher ce qui manque, organise l'enrichissement Clay, puis lit les résultats.

Pourquoi ce découpage : le moteur refuse à juste titre de transformer une absence d'information en match. Une liste brute donne donc surtout des `à confirmer`. Le gain vient de la qualité des entrées entreprises (type, secteur, modèle, CA, signaux), et chaque valeur ajoutée doit rester sourcée et relue par une personne.

Lire d'abord `event_machine/README.md` et `event_machine/AGENTS.md` si ce n'est pas déjà fait dans la conversation : les règles de preuve s'appliquent ici aussi.

## Conventions

- Scripts : `S=.claude/skills/event-machine-prep/scripts` (lancer depuis la racine du dépôt). Python standard, aucune dépendance.
- Dossier de travail : `W=.event-machine/<event_id>` (ignoré par Git ; contient des données de prospection, ne jamais le committer).
- Sous-dossiers : `prep/01-prevalidation`, `prep/02-research`, `prep/03-clay`, `prep/04-clay-ingest`, `prep/05-diagnostic`, `runs/<nom>`.
- Communiquer en français avec l'utilisatrice, en langage non technique. Montrer des chiffres et des noms, pas des chemins internes, sauf pour les fichiers à ouvrir.

## Étape 0 — Rassembler les entrées

Il faut : participants CSV (obligatoire), ICP JSON (obligatoire), event JSON (marqueur d'inscription, date), entreprises CSV (fortement recommandé), relations CSV (optionnel). Les exemples HOP sont dans `examples/event-machine/`. Si un fichier manque, le demander ; ne pas inventer de liste.

## Étape 1 — Prévalidation du format

```bash
python3 $S/prevalidate.py --participants P.csv --accounts A.csv --icps I.json --event E.json --out $W/prep/01-prevalidation
python3 -m event_machine run --event E.json --participants P.csv --accounts A.csv --icps I.json \
  --out $W/runs/baseline --db $W/feedback.sqlite3 --offline
```

Lire `prevalidation-report.md` et le résumer : blocages (colonnes manquantes, ICP invalide, vocabulaire inconnu du moteur), puis avertissements chiffrés (postes vides ou non reconnus, conflits nom/domaine, domaines étudiants, emails personnels, noms multiples pour un domaine, faux détaillants). S'il y a un blocage, s'arrêter et proposer la correction avant toute recherche. Le run `baseline` sert de point de comparaison pour le diagnostic.

Les corrections de format (renommer une colonne, retirer une ligne de test) se font dans une **copie** du fichier, jamais dans l'original reçu.

## Étape 2 — Agents de recherche

`research-queue.csv` liste les entreprises avec au moins un décideur et un champ à qualifier, triées par nombre de décideurs.

1. Dire combien d'entreprises et de lots, et demander l'accord avant de lancer (chaque agent consomme des recherches web). Proposer de commencer par les 30 premières si la file est longue.
2. Découper : `python3 $S/research.py split --queue $W/prep/01-prevalidation/research-queue.csv --size 15 --out $W/prep/02-research`
3. Lancer **un agent par lot, tous dans le même message** (outil Agent, type `general-purpose`, en arrière-plan). Le prompt de chaque agent est le texte de `references/research-agent.md`, avec les chemins absolus du lot (`batch-NN.csv`) et du fichier de sortie (`batch-NN.json`), la date du jour et la liste des secteurs permis (`python3 -c "import sys; sys.path.insert(0,'.'); from event_machine.core import SECTOR_TERMS; print(', '.join(SECTOR_TERMS))"`). Ne jamais donner aux agents un webhook, un jeton ou la configuration Clay.
4. Quand tous ont fini : `python3 $S/research.py propose --research-dir $W/prep/02-research --accounts $W/prep/01-prevalidation/accounts-normalized.csv --out $W/prep/02-research`
5. **Revue humaine.** Présenter `research-review.csv` : ce qui est approuvé d'office (confiance haute, URL HTTPS, citation), ce qui est à revoir (`problem`), les domaines suspects. L'utilisatrice corrige la colonne `approve` (ou dit « approuve tout sauf X », et tu modifies une copie). Les valeurs approuvées deviendront des entrées entreprise que le moteur traite comme fiables, y compris pour **exclure** : c'est pourquoi la revue est nécessaire.
6. `python3 $S/research.py apply --review $W/prep/02-research/research-review.csv --accounts $W/prep/01-prevalidation/accounts-normalized.csv --out $W/prep/accounts-prevalidated.csv`
7. Relancer la machine avec `--accounts $W/prep/accounts-prevalidated.csv --out $W/runs/prevalidated`.

Si l'environnement bloque l'ouverture des pages web (WebFetch refusé, proxy 403) et que seule la recherche fonctionne, les agents citent des extraits de résultats (`quote_from=search_snippet`, confiance `medium` au plus) : rien n'est approuvé d'office. Le dire à l'utilisatrice, proposer d'approuver les valeurs `medium` venant du site officiel de l'entreprise, et laisser les sources secondaires (annuaires, offres d'emploi) à revoir. Autoriser les domaines nécessaires dans la politique réseau de l'environnement donne de meilleures preuves.

Un secteur `other` (animalerie, piscines, alcool…) n'existe pas dans le moteur : il reste inconnu et est signalé dans `sector_detail`. Le mentionner au diagnostic plutôt que de forcer un secteur voisin.

## Étape 3 — CSV d'import Clay

```bash
python3 $S/clay_export.py --accounts $W/prep/accounts-prevalidated.csv --matches $W/runs/prevalidated/matches.csv \
  --icps I.json --out $W/prep/03-clay/clay-enrichment-import.csv
```

Le fichier ne garde que les entreprises encore utiles (au moins un match non exclu, type détaillant ou inconnu, domaine présent) et ajoute des colonnes vides pour le CA, le modèle d'affaires et chaque signal des ICP. Donner le fichier à l'utilisatrice et lui expliquer la marche à suivre dans Clay en suivant `references/clay-enrichment.md` (import, colonnes d'enrichissement, prompts Claygent par signal, export). Rappeler que l'enrichissement consomme des crédits Clay et qu'il vaut mieux tester sur 5 lignes. Ne pas faire l'enrichissement à sa place via un connecteur sans accord explicite sur le coût.

## Étape 4 — Réintégrer l'export Clay

```bash
python3 $S/ingest_clay.py propose --export clay-export.csv --icps I.json --out $W/prep/04-clay-ingest
```

Vérifier `missing_columns` : si des colonnes ont été renommées dans Clay, renommer dans une copie de l'export puis relancer. Présenter `clay-review.csv` : CA approuvés d'office (CAD, année, URL, non estimé), CA restés bruts et pourquoi (devise USD, estimation, fourchette), signaux avec preuve. Après la revue :

```bash
python3 $S/ingest_clay.py apply --review $W/prep/04-clay-ingest/clay-review.csv \
  --accounts $W/prep/accounts-prevalidated.csv --out $W/prep/04-clay-ingest
python3 -m event_machine run --event E.json --participants P.csv --icps I.json \
  --accounts $W/prep/04-clay-ingest/accounts-final.csv --evidence $W/prep/04-clay-ingest/evidence-final.csv \
  --out $W/runs/final --db $W/feedback.sqlite3 --offline
```

Ne pas convertir un CA USD en CAD pour franchir un seuil : un montant converti reste une estimation. Le signaler, et laisser l'utilisatrice décider de chercher un chiffre CAD sourcé.

## Étape 5 — Diagnostic

```bash
python3 $S/diagnose.py --run $W/runs/final --previous $W/runs/baseline --out $W/prep/05-diagnostic
```

Résumer `diagnostic.md` en quelques lignes : évolution des statuts par client, liste courte de chaque client (les meilleurs noms, avec entreprise et poste), ce qui empêche encore `fort`, les comptes qui débloqueraient le plus de matchs, les exclusions dominantes. Proposer la suite la plus rentable (ex. « trouver le CA CAD de ces 5 comptes ferait passer 12 matchs »). Les `shortlist-<client>.csv` sont les listes à remettre ; pour les envoyer dans Clay, utiliser l'import CSV ou le connecteur de la machine (`python3 -m event_machine clay`, aperçu avant `--apply`).

Le diagnostic peut aussi se lancer seul sur n'importe quel run existant, sans les étapes précédentes.

## Ce que le skill ne fait pas

- Il ne modifie pas `machine_status`, les seuils ICP ni les CSV reçus.
- Il ne présente pas une hypothèse d'agent ou une estimation Clay comme un fait : seules les lignes approuvées deviennent des entrées.
- Il n'envoie aucun message aux prospects et n'écrit rien dans Clay sans un aperçu puis un accord explicite.
