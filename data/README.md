# Données GTM

Les CSV sont en UTF-8, séparateur virgule, champs manquants vides. Les valeurs commerciales d’origine ne sont pas corrigées silencieusement.

| Fichier dérivé | Grain | Taille au 13 octobre 2026 |
|---|---|---:|
| [accounts.csv](derived/accounts.csv) | Identité normalisée issue des campagnes et du CRM | 230 |
| [event-prospects.csv](derived/event-prospects.csv) | Une organisation dans un snapshot de campagne | 221 |
| [crm-accounts.csv](derived/crm-accounts.csv) | Une ligne CRM reçue | 15 |
| [organizer-contacts.csv](derived/organizer-contacts.csv) | Un contact dans l’export organisateurs | 9 |
| [events.csv](derived/events.csv) | Un événement S39 ou une campagne ajoutée | 17 |

| [events-master.csv](derived/events-master.csv) / [.json](derived/events-master.json) | Un événement du marché, tous catalogues fusionnés (**base maîtresse BETA Labs**) | 3 170 au 2026-11-09 |
| [events-merge-review.csv](derived/events-merge-review.csv) | Paires inter-sources ressemblantes **non** fusionnées, à relire | 36 |
| [events-master-quality.json](derived/events-master-quality.json) | Compteurs, remplissage par champ, notes | — |

Les [originaux CSV](../sources/README.md) constituent la couche brute. La table d’événements contient 16 lignes S39 et HOP ajouté depuis S08/S09 ; ALL IN est relié au même ID dans le catalogue et dans les prospects. Elle n’inclut pas toute la recherche internationale.

## Dictionnaire des champs ajoutés

| Champ | Sens |
|---|---|
| `record_id` | ID stable de la ligne, avec source et numéro |
| `account_id` | Clé de liaison vers accounts.csv, pas un identifiant CRM officiel |
| `source_id`, `source_ids`, `source_row`, `source_path` | Provenance du fichier et de la ligne CSV |
| `source_snapshot_date` | Date attribuée au snapshot par les documents accompagnateurs |
| `independently_verified_at` | Vide : aucune vérification externe nouvelle |
| `as_of` | Date choisie pour le calcul du calendrier |
| `days_to_event` | Jours jusqu’au début annoncé ; vide si date inconnue/estimée dans le catalogue |
| `event_temporal_status`, `temporal_status` | Passé/en cours/à venir **selon les dates de source** |
| `participation_status` | reported_confirmed, unconfirmed_lead, former_partner_absent, organizer ou unknown |
| `commercial_filter` | candidate, qualify, excluded, organizer ou unknown ; dérivé du tier source |
| `activation_status` | historique, hors_cible_commerciale, confirmer_inscription ou revalidation_et_capacite_requises |
| `status_source` | Client/Prospect tel que reçu, sans nouvelle validation |
| `payment_status` | not_verified ; le pipeline ne déduit pas un paiement du statut |
| `company_size_raw`, `matches_raw`, `package_price_raw` | Mentions intactes, notamment les formats ambigus |
| `*_exact`, `package_amount`, `days_to_deposit` | Conversion numérique seulement quand le champ est non ambigu |
| `currency` | unspecified ; pas d’inférence CAD/USD à partir de `$` |

Les colonnes originales `action`, `forfait_recommande`, `confiance_donnees`, `source` et les relations chaudes restent présentes dans les prospects. Elles contiennent les recommandations et évaluations **du snapshot**, même lorsqu’elles sont historiques ou contradictoires. Consulter `activation_status` et le dossier de campagne avant de les employer.

## Filtres utiles

- Bilan ALL IN : `event_id=allin-2026`, sans convertir les 172 lignes en pipeline gagné.
- HOP à revalider : `event_id=hop-2026`, `participation_status=reported_confirmed`, `commercial_filter=candidate`.
- Pistes exposants : `participation_status=unconfirmed_lead`, séparées de la vente sponsor.
- Institutions et inconnus : `commercial_filter` excluded/organizer/unknown, en dehors de la file commerciale.

Les données de contacts restent des éléments internes de travail. La présence d’une adresse, d’un numéro ou d’une connexion ne prouve ni actualité, ni disponibilité, ni demande de contact.

Voir [quality-report.json](derived/quality-report.json) pour les compteurs, valeurs vides et statistiques CRM, et [les registres](../intelligence/09-preuves-decisions.md) pour leur interprétation. Les tables générées se reconstruisent avec les commandes du README ; les registres restent éditoriaux et ne sont pas réapprouvés automatiquement.

## Base maîtresse d'événements (S86, S87, S88)

`python3 scripts/merge_events.py` fusionne trois extractions du 2026-11-09 : **S86** Vendelux (2 639), **S87** Lensmor (1 031) et **S88** calendrier du Palais des congrès de Montréal (228). Résultat : 3 170 événements (728 présents dans Vendelux et Lensmor ; aucun recoupement avec Montréal). Les 3 898 lignes sources sont toutes retrouvables via `source_refs` (`S86#i` = i-ième événement du JSON, base 0). Ce catalogue du marché est distinct de `events.csv` (campagnes BETA Labs) ; aucun lien n'a été établi entre les deux.

Règle : chaque colonne existe pour chaque événement ; une valeur absente vaut `inconnu` (jamais vide, jamais 0). Les 0 des extractions (participants, exposants, prix 0/0) sont traités comme inconnus, car un placeholder n'est pas un compte réel ; les originaux gardent la valeur brute.

| Champ | Origine |
|---|---|
| `event_id` | `BL-EVT-` + hash du nom normalisé et de la date de début retenue ; change si la date est corrigée |
| `name`, `name_variants` | S86 > S87 > S88 ; autres graphies conservées |
| `start_date`, `end_date`, `date_raw`, `date_conflict` | Dates ISO (S86 ; S87 et S88 converties depuis le texte) ; `date_raw` garde chaque formulation ; `date_conflict` = les sources divergent (S86 retenue) |
| `event_format` | S86 : in_person / hybrid / virtual ; inconnu pour S87 et S88 |
| `venue`, `city`, `region`, `country` | S86, complété par S87 (ville, pays) ; « TBA » → inconnu ; pays unifiés (UK, USA, The Bahamas) ; « MI » invalide → inconnu |
| `organizer`, `url` | S88 ; `url` aussi S86 |
| `industries` (S87), `topics_keywords` (S86) | Listes séparées par `; ` ; les mots-clés S86 sont bruts et parfois tronqués, pas une taxonomie |
| `description`, `vendelux_verified` | S86 |
| `attendees` | S86 sinon S87 ; les deux sources ne comptent pas pareil, l'écart n'est pas signalé comme conflit |
| `attendees_expected`, `price_min`, `price_max` | S86 ; `price_currency` toujours inconnu (aucune devise dans les sources) |
| `exhibitors`, `lensmor_url` | S87 |
| `sources`, `source_count`, `source_refs`, `match_method`, `last_retrieved` | Provenance et méthode (même nom normalisé, début à moins de 31 jours, un-pour-un) |
| `conflicts`, `inferred_fields` | Divergences de ville ou de pays ; champs déduits (S88 : lieu = Palais des congrès de Montréal, pris du calendrier et non de chaque ligne) |

Éditions répétées d'un même nom dans S88 (ex. Stratégies PME 2026/2027/2028) restent des événements distincts. Aucune vérification externe n'a été faite ; `verified` de Vendelux est reproduit tel quel (45 vrais sur 2 639).
