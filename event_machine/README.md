# Machine événements BETA Labs

Application privée en Python 3.10+ pour partir d'une liste d'inscrits et de profils ICP, rechercher le contexte d'un événement, rapprocher les entreprises, qualifier chaque participant pour chaque client, puis intégrer les corrections des analystes. Aucune dépendance Python externe.

L'interface React utilise des composants shadcn/ui adaptés localement (Radix, Tailwind et CVA). Les fichiers compilés sont inclus dans le dépôt : Node.js n'est nécessaire que pour **modifier** l'interface, pas pour la lancer. La palette crème/charbon/lime, le logo original et Inter viennent du guide BETA Labs ; l'accent Newsreader est une proposition v2 sous licence OFL. Cette interface ne prétend pas reproduire le site actuel.

## Démarrage

Depuis la racine du dépôt :

```bash
python3 -m event_machine serve
```

Ouvrir `http://127.0.0.1:8765`. Les CSV et les résultats restent dans `.event-machine/` de l'environnement qui lance le serveur. Le serveur n'écoute que l'interface locale de cet environnement.

Parcours recommandé : **Vue d'ensemble → Nouvelle analyse → Résultats & revue → Export Clay**. L'événement se saisit dans des champs guidés, les CSV sont chargés séparément, et les ICP restent un JSON explicite que l'équipe peut importer ou coller. La vue des résultats permet de filtrer par client et statut, d'ouvrir les raisons d'une ligne, de télécharger le dossier et d'importer des corrections. Le bouton **Charger l'exemple HOP** préremplit l'événement et les trois ICP ; il ne fournit pas les CSV de personnes.

Pour reconstruire l'interface après une modification :

```bash
cd event_machine/frontend
npm ci
npm run build
```

Le build est écrit dans `event_machine/frontend/dist/` et servi par la même application Python. Les licences des polices sont dans `event_machine/frontend/public/brand/`.

Pour lancer la machine dans une tâche Codex Cloud et faire travailler les agents spécialisés, suivre le [guide cloud](CLOUD.md). Le serveur reste en aperçu privé. Chaque run contient désormais `agent-handoff.md`; l'onglet **Agents & preuves** accepte les propositions JSON du rôle Signaux entreprises et produit un CSV de candidats à vérifier.

Pour une analyse reproductible en ligne de commande :

```bash
python3 -m event_machine run \
  --event examples/event-machine/hop-2026-event.json \
  --participants '/chemin/vers/data hop-2026.csv' \
  --accounts '/chemin/vers/data.companies.hop-2026.csv' \
  --icps examples/event-machine/hop-2026-icps.json \
  --out .event-machine/hop-2026 \
  --db .event-machine/feedback.sqlite3 \
  --offline
```

Retirer `--offline` pour consulter le site de l'événement et jusqu'à six pages de programme, conférences, partenaires ou exposants du même domaine. Les pages inaccessibles sont consignées dans `research-errors.json`; une erreur réseau ne devient jamais une affirmation. L'exemple HOP comprend une **synthèse fournie, datée du 14 octobre 2026**, pour fonctionner hors ligne; la remplacer ou relancer la recherche pour une édition ultérieure. L'outil ne crée pas de preuve d'inscription à partir d'une page publique.

## Entrées

| Entrée | Champs principaux | Règle |
|---|---|---|
| `event.json` | `id`, `name`, `url`, `date`, `registration_marker`, `reference_pages` | Un marqueur fourni, par exemple `pairconnex-test-a`, est vérifié ligne par ligne. Sans ce marqueur, l'inscription reste à confirmer. |
| Participants CSV | `full_name` ou `first_name` + `last_name`, `company_name`, `email`, `role`, `country`, `project_slugs[0..]` | Obligatoire. Le rapprochement privilégie le domaine, puis un nom unique. Les conflits sont visibles. |
| ICP JSON | `clients[]` avec `id`, `target`, `signals`, angle et question | Obligatoire. Un résultat par personne et par client. Seuils CAD, secteurs, rôle et signaux sont indépendants par client. |
| Entreprises CSV | `name`, `domain`, `website_url`, `industry`, `sector`, `org_type`, `business_model`, chiffres d'affaires | Optionnel. Les montants seulement estimés restent bruts. |
| Relations CSV | `domain`, `client_id`, `relation_type`, `owner`, `last_interaction` | Optionnel. Sert aussi de liste de comptes existants. Une relation augmente la priorité et expose son propriétaire. |
| Preuves CSV | `domain_join_key`, `field`, `value`, `source_url`, `checked_at`, `confidence`, `caveat` | Optionnel. Les signaux `required` deviennent confirmés seulement avec URL, confiance haute et valeur explicite. |

Les modèles CSV sont dans `examples/event-machine/`. Un CA est utilisable pour un seuil uniquement avec montant numérique, `revenue_verified=yes`, `revenue_currency=CAD`, `revenue_year=20xx` et `revenue_source_url`. `business_model` exige aussi `business_model_source_url` pour être vérifié. Un champ vide ne devient jamais zéro. Les motifs de présence et objectifs individuels sont marqués `[Déduit]`.

## Sorties et décision

- `event-brief.md` : thèmes avec sources, lecture acheteurs/vendeurs, volumes du roster et limites.
- `participants.csv` : rattachement, marqueur d'inscription, typologie, niveau d'influence, raison de présence et objectif déduits.
- `accounts.csv` : comptes rapprochés avec valeurs brutes et sources disponibles.
- `matches.csv` : statut machine, score de priorité, raisons, exclusions, preuves, relation, angle et question pour chaque couple personne×client.
- `clay-import-priority.csv`, `clay-import-all.csv` : fichiers simplifiés pour l'import manuel dans Clay, sans webhook.
- `review-queue.csv` : cas à vérifier, ordonnés pour l'analyste.
- `feedback-template.csv` : modèle de correction humaine.
- `event-pages.json`, `research-errors.json`, `evidence.csv`, `run-manifest.json` : traçabilité, dont SHA-256 des entrées.

`fort` signifie que les règles vérifiables disponibles sont remplies; `possible` qu'un seuil ou signal requis manque; `à confirmer` qu'une identité, une inscription ou une dimension fondamentale reste incertaine; `exclu` qu'une règle dure échoue. Le score sert au tri; il ne convertit pas un cas incertain en match confirmé. Pour les profils HOP fournis, l'absence de CA CAD vérifié ou de signaux propres aux clients empêche un statut `fort`.

## Apprentissage par revue

Compléter `feedback-template.csv` avec `reviewed_fit` (`fort`, `possible`, `à confirmer`, `exclu`), `reviewer`, `note`, `scope=person_event`. Une décision `fort` exige une `evidence_url`. Puis :

```bash
python3 -m event_machine feedback \
  --db .event-machine/feedback.sqlite3 \
  --matches .event-machine/hop-2026/matches.csv \
  --reviews /chemin/vers/reviews.csv
python3 -m event_machine stats --db .event-machine/feedback.sqlite3
```

Une nouvelle analyse reprend la décision humaine sur le même couple événement/personne/client. Après six revues `fort`/`exclu` pour un client, avec au moins trois cas pour une caractéristique, le système ajuste **seulement la priorité de tri** à partir du type d'organisation, du secteur et du niveau de poste. L'ajustement est plafonné à ±12 points; il ne change jamais un seuil ICP ou une exclusion. Les corrections modifient le classement futur sans faire passer une hypothèse pour un fait. La base SQLite peut être sauvegardée avec l'équipe; elle contient des informations de prospection internes.

## Import dans Clay sans webhook

Après chaque analyse, la machine produit deux fichiers de destination :

- `clay-import-priority.csv` : statuts `fort` et `possible` seulement. À vérifier avant prospection.
- `clay-import-all.csv` : tous les couples participant × client, y compris `à confirmer` et `exclu`.

Chaque ligne comporte `match_key` (clé stable événement/personne/client), l'événement, le client, l'email si fourni, le domaine de l'entreprise, le statut, la priorité, les raisons, les questions et les sources. Les autres exports (`participants.csv`, `accounts.csv`, `evidence.csv`) restent disponibles séparément.

Dans **Export Clay**, Elizabeth télécharge le lot souhaité. Elle ouvre ensuite le workspace voulu dans Clay, choisit l'import d'un CSV, vérifie l'aperçu des colonnes et le nombre de lignes, puis confirme elle-même l'import. Garder `match_key` pour repérer les doublons lors d'un nouvel import. Cette opération ne nécessite **aucune URL de webhook** dans la machine. Les limites de lignes ou de crédits du compte Clay restent celles de son abonnement; la machine ne prétend pas vérifier l'import dans Clay.

Le code du connecteur webhook historique reste disponible en ligne de commande pour les workspaces qui disposent déjà de cette fonction Clay. Il est facultatif et absent du parcours principal. Le CLI et le MCP Clay observés ici ne proposent pas d'écriture directe de lignes dans une table existante; aucun résultat n'a été importé dans le compte d'Elizabeth par cette session.

## Contrôles

```bash
python3 -m unittest discover -s tests -p 'test_event_machine.py' -v
```

Les tests couvrent l'inscription non prouvée, la prudence sur le CA, l'import de retours et un parcours hors ligne complet. Le moteur recherche des pages et classe selon des règles traçables; il ne remplace pas la validation humaine d'une identité, d'un budget, d'une intention ou d'une offre exposant.
