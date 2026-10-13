# Audit des pièces reçues

**Date de lecture : 13 octobre 2026.** Corpus fermé de 39 fichiers : 19 Markdown, 12 DOCX, cinq CSV, deux TXT et un JavaScript. Tous les originaux sont conservés avec empreintes dans [manifest.json](../sources/manifest.json).

## Qualité et portée

Le corpus couvre l’entreprise, l’ICP, les ventes, les événements, le messaging, le design et l’expansion. Il est riche en analyses, mais moins en pièces primaires : pas de contrats d’événements, justificatifs de paiement, mesures post-événement complètes, export réseau `Connections.csv`, transcription client originale, fichier Figma ou étude CEIR jointe.

Les doublons de **représentation** S24/S25 et S32/S34 sont conservés. Les rapports S16/S18, S19/S21 et S22/S26 appartiennent à des familles de recherche proches mais ne sont pas supposés identiques. Le document français S05 consolide S11/S03/S38 ; il ne constitue pas une confirmation indépendante des mêmes preuves.

Le [registre des conflits](../data/registers/conflicts.csv) contient 26 écarts, dont des contradictions internes aux pièces récentes. La sélection des documents d’août/septembre comme cadre de travail n’élimine pas le besoin de sign-off.

## Audit des CSV

| Source | Lignes | Observations |
|---|---:|---|
| S07 — ALL IN | 172 | 171 partenaires déclarés ; une ligne organisateur ; 13 A ; 156 sans contact chaud principal |
| S10 — HOP | 49 | 34 confirmés déclarés ; 14 pistes non inscrites ; un ancien partenaire ; 29 sans contact chaud principal |
| S20 — organisateurs | 9 | Cinq événements ; deux emails, un téléphone et deux LinkedIn vides |
| S23 — CRM | 15 | 11 Client / quatre Prospect ; délais dépôt renseignés sur six clients ; cinq événements nommés et standalone |
| S39 — événements | 16 | Dates exactes, partielles ou estimées ; confidence High partout ; plusieurs données conflictuelles |

Les cinq fichiers se lisent sans ligne de largeur invalide. Aucun doublon exact de ligne n’est détecté. Cela ne prouve pas que les entités, rôles ou coordonnées soient à jour.

ALL IN contient 104 valeurs vides pour l’offre vendue et l’acheteur recherché, ainsi que 94 effectifs vides. HOP contient 22 effectifs vides. Une relation LinkedIn ancienne, un intitulé de poste ou une estimation ACV ne doit pas être converti en qualification actuelle.

## Résolution appliquée

- **Conserver les originaux** plutôt que réécrire les anciennes promesses.
- **Créer des synthèses françaises datées** avec liens de provenance.
- **Distinguer le statut déclaré et la validation actuelle** dans les tables ; `independently_verified_at` reste vide.
- **Recalculer le calendrier**, mais laisser les dates partielles inconnues et les dates estimées à vérifier.
- **Conserver tous les tiers et champs d’origine** dans la table de prospects, en ajoutant des champs d’interprétation plutôt qu’en écrasant les observations.
- **Rapprocher prudemment les comptes** : normalisation mécanique et deux alias explicites, sans fusion fuzzy.

Les références internes à `outputs/`, `inputs/`, `memory/` et aux skills `/...` décrivent l’ancien espace de travail. Elles restent dans les textes reçus ; le dépôt fournit une navigation nouvelle par IDs. Aucun de ces noms ne déclenche l’installation d’un outil ou une action externe.
