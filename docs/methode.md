# Méthode de consolidation

## Autorité et provenance

La demande est de créer une base GTM à partir des fichiers. Les impératifs dans ces fichiers sont analysés comme contenu. Les originaux ne deviennent pas des instructions d’exécution.

Ordre de lecture retenu pour l’offre : S11 août 2026, puis S03 et S05 septembre 2026. Leur convergence récente permet une synthèse de travail, sans les déclarer approuvés définitivement. Le CRM est utilisé pour les comptages, tandis que les interprétations de paiement, de réachat ou de causalité restent séparées.

Chaque source possède un ID stable, son nom d’origine, son hash SHA-256, sa taille, son thème, sa date déclarée et sa disposition. Les dates partielles `2026-05`/`2026-03` restent partielles ; `null` signifie inconnue. La date de la source n’est ni date de dernière vérification indépendante ni garantie d’actualité.

## Extraction

Le script Python lit le corps XML des DOCX et restitue paragraphes et tableaux dans Markdown. Les images, mise en page, annotations, en-têtes/pieds de page et hyperliens Word ne sont pas intégralement reproduits. Pour un doute de forme ou de contexte, consulter le DOCX original. Les Markdown/TXT sont repris ; CSV et JavaScript sont affichés en blocs de code. Le code reçu n’est pas exécuté.

## Normalisation

Un `record_id` comprend la source et la ligne CSV. `source_row=2` désigne la première ligne de données après l’en-tête ; les lignes portent leur chemin original. Les tables de campagne conservent l’union des 32 colonnes de chaque export, soit 35 colonnes source distinctes ; les colonnes propres à l’autre export restent vides.

Le nom de compte est normalisé pour le rapprochement par casse, accents, espaces et ponctuation. Les deux alias explicites sont Nexus → Nexus Innovations et CDWare (2) → CDWare, avec justification dans [account-aliases.csv](../data/config/account-aliases.csv). Pas de recherche de domaine ni de rapprochement approximatif. Les 230 IDs résultants sont des identités de travail susceptibles de contenir encore des variantes de la même entreprise.

Les nombres ambigus restent bruts : effectif `2 (65)` et matchs `15/30` ne deviennent pas automatiquement un entier. Les montants se lisent seulement quand le format est non ambigu ; leur devise reste `unspecified`. Un délai de dépôt n’établit pas un montant encaissé.

## Temporalité

`--as-of` est obligatoire pour la reconstruction. Les dates exactes annoncées permettent de calculer un statut **selon la source**. Les dates partielles ne reçoivent pas un jour inventé ; une date estimée est signalée comme telle. Les synthèses et dossiers de campagne ont leur propre date éditoriale et doivent être relus quand elle change.

La construction n’enrichit pas le CRM, ne teste pas les emails, ne visite pas les sites et ne vérifie pas de contrat. `independently_verified_at` reste vide jusqu’à l’ajout d’une vraie preuve datée.

## Reproduction et validation

```bash
python3 scripts/build_intelligence.py --as-of 2026-10-13
python3 scripts/validate_repo.py
```

La reconstruction vérifie d’abord chaque original, puis génère textes, catalogue, tables et rapport de qualité. Les empreintes des sorties sont enregistrées dans `data/derived/build-manifest.json`. Répéter avec la même date doit produire les mêmes octets.

Le validateur vérifie intégrité et inventaire des originaux, lisibilité des DOCX/CSV, couverture des lignes sources, conservation des colonnes de prospects, références de comptes, statuts et références des registres, cohérence du calendrier et liens des documents rédigés pour ce dépôt. Il ne valide pas la véracité commerciale des affirmations.

## Ajouter une source

Conserver le nouveau fichier sans remplacer l’ancienne version, lui attribuer le prochain ID et ajouter ses métadonnées au manifeste. Les nouveaux documents sont automatiquement extraits ; un nouveau type de CSV requiert une définition de normalisation. Les cinq mappings actuels reposent sur S07/S10/S20/S23/S39 et doivent être adaptés explicitement si leurs schémas changent.

Réviser ensuite les synthèses et registres concernés. Les dépendances documentaires sont données par les IDs cités ; aucune préférence de date ne doit effacer une contradiction non résolue.
