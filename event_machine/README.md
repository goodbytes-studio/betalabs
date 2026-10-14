# Machine événements BETA Labs

Application locale en Python 3.10+ pour partir d'une liste d'inscrits et de profils ICP, rechercher le contexte d'un événement, rapprocher les entreprises, qualifier chaque participant pour chaque client, puis intégrer les corrections des analystes. Aucune dépendance Python externe.

## Démarrage

Depuis la racine du dépôt :

```bash
python3 -m event_machine serve
```

Ouvrir `http://127.0.0.1:8765`. Les CSV et les résultats restent dans `.event-machine/` sur l'ordinateur qui lance le serveur. Le serveur n'écoute que l'interface locale.

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

## Connexion à Clay d'Elizabeth

Dans l'interface locale, Elizabeth peut :

1. Cliquer **Connecter Clay** et autoriser le CLI Clay dans son navigateur. Si le navigateur local ne s'ouvre pas, lancer `clay login --device` dans un terminal du même ordinateur, puis cliquer **Vérifier la connexion**.
2. Lire l'identité Clay retournée par `clay whoami`, choisir un workspace autorisé et cliquer **Confirmer ce compte et ce workspace**. Aucun email n'est à fournir au développeur : l'ID utilisateur et l'ID workspace vérifiés sont enregistrés dans `.event-machine/clay-connection.json` (permissions locales 0600).
3. Créer une source **Webhook d'entrée** dans la table de sortie souhaitée dans Clay, puis coller son URL dans l'interface. Elle reste dans le fichier local protégé et n'est jamais ajoutée au dépôt.
4. Lancer une analyse, cliquer **Prévisualiser l'envoi**, puis **Envoyer les lignes en attente**. Le connecteur revérifie l'ID utilisateur et le workspace juste avant l'envoi.

L'accès d'Elizabeth au dépôt Git n'authentifie pas son compte Clay. Le webhook est un transport **d'ajout de lignes**; il ne remplace pas et ne met pas à jour les lignes existantes dans Clay. Le registre local empêche de renvoyer une ligne inchangée vers la même destination depuis cette installation. Si une réponse réseau se perd après réception par Clay, une relance peut produire un doublon distant; utiliser `match_key` pour contrôler la table.

Le même parcours peut être fait en ligne de commande lorsque l'interface n'est pas utilisée :

```bash
clay login
clay whoami
export BETA_CLAY_WEBHOOK_MATCHES='https://…clay.com/…'
python3 -m event_machine clay \
  --run-dir .event-machine/hop-2026 \
  --table matches \
  --workspace-id 'ID_DU_WORKSPACE_ELIZABETH' \
  --account-email 'elizabeth@domaine.example'
# Après contrôle de l'identité, de la destination et du nombre de lignes :
python3 -m event_machine clay \
  --run-dir .event-machine/hop-2026 \
  --table matches \
  --workspace-id 'ID_DU_WORKSPACE_ELIZABETH' \
  --account-email 'elizabeth@domaine.example' --apply
```

La même commande accepte `participants`, `accounts` ou `evidence`, avec `BETA_CLAY_WEBHOOK_PARTICIPANTS`, `BETA_CLAY_WEBHOOK_ACCOUNTS` ou `BETA_CLAY_WEBHOOK_EVIDENCE`. Ne jamais mettre les URL webhook ou clés dans Git. Si l'objectif est de **remplacer** une table Clay existante, utiliser l'import CSV avec l'option de remplacement dans l'interface Clay après vérification des colonnes. Le CLI et le MCP Clay disponibles dans cette session ne proposent pas d'écriture de lignes dans les tables existantes; aucun résultat de la machine n'a été synchronisé avec le compte d'Elizabeth ici.

## Contrôles

```bash
python3 -m unittest discover -s tests -p 'test_event_machine.py' -v
```

Les tests couvrent l'inscription non prouvée, la prudence sur le CA, l'import de retours et un parcours hors ligne complet. Le moteur recherche des pages et classe selon des règles traçables; il ne remplace pas la validation humaine d'une identité, d'un budget, d'une intention ou d'une offre exposant.
