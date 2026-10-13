# Données GTM

Les CSV sont en UTF-8, séparateur virgule, champs manquants vides. Les valeurs commerciales d’origine ne sont pas corrigées silencieusement.

| Fichier dérivé | Grain | Taille au 13 octobre 2026 |
|---|---|---:|
| [accounts.csv](derived/accounts.csv) | Identité normalisée issue des campagnes et du CRM | 230 |
| [event-prospects.csv](derived/event-prospects.csv) | Une organisation dans un snapshot de campagne | 221 |
| [crm-accounts.csv](derived/crm-accounts.csv) | Une ligne CRM reçue | 15 |
| [organizer-contacts.csv](derived/organizer-contacts.csv) | Un contact dans l’export organisateurs | 9 |
| [events.csv](derived/events.csv) | Un événement S39 ou une campagne ajoutée | 17 |

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
