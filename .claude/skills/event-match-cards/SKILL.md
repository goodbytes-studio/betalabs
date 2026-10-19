---
name: event-match-cards
description: Rédige les fiches de prospects livrées aux commanditaires d'un événement BETA Labs (HOP, ALL IN, etc.) et produit le CSV d'import de la plateforme. Construit d'abord le référentiel de tags du client (type, secteur standardisé, tranche de CA, rôle), puis pour chaque prospect retenu - description de l'entreprise, raison du match courte et longue, angles de conversation, brouillon d'ouverture - et vérifie le tout avec un script. À utiliser dès qu'on parle de fiches, de cartes de profil, de brief, de match reason, de conversation starters, de suggested outreach ou d'import CSV pour une sélection de prospects, même si l'utilisateur ne nomme pas le skill.
---

# Fiches de prospects et CSV d'import

Ce skill part d'une **sélection finale** (une personne par entreprise, déjà validée par Elizabeth) et produit le livrable du commanditaire : une fiche par prospect et un CSV à importer dans la plateforme. Il ne choisit pas les prospects : la sélection vient de `event-machine-prep` et de la revue humaine.

Pourquoi ce découpage : la recherche coûte cher et elle est déjà faite pendant la sélection. Ici, on réutilise les faits sourcés et on se concentre sur l'écriture. Le livrable est lu par quelqu'un qui a 15 profils à parcourir, parfois pendant l'événement : chaque mot doit servir.

Communiquer avec Elizabeth en français, sans jargon technique. Les fiches sont en français québécois professionnel.

## Entrées

| Entrée | Où la trouver |
|---|---|
| Sélection finale | `livrables-<événement>/selection-<client>.csv` (personne, poste, entreprise, `match_key`, notes « pourquoi » et « à savoir ») |
| Faits sourcés par prospect | `livrables-<événement>/briefing/briefing-<client>.md`, ou à défaut `accounts-final.csv`, `evidence-final.csv` et la revue de recherche dans `.event-machine/<événement>/prep*/` |
| Coordonnées | liste d'inscrits (`inputs*/participants.csv`) : courriel, profil LinkedIn |
| Profil du client | `references/client-profiles.md` (offre, ICP, angle, signature), complété par l'ICP JSON |

Toutes ces données sont internes : ne jamais les committer. Les fiches et le CSV vont dans `livrables-<événement>/fiches/` (non versionné).

## Étape 0 - Vérifier le profil du client

Ouvrir `references/client-profiles.md`. Confirmer avec Elizabeth, si ce n'est pas déjà fait dans la conversation : l'offre à mettre de l'avant, la personne qui signe, et les sujets à éviter. Mettre le fichier à jour quand une consigne change (exemple : Mirego veut aussi mettre de l'avant son offre d'IA).

## Étape 1 - Référentiel de tags du client

Les tags (colonne `interests`) disent au client, d'un coup d'œil, que le prospect répond à **son ICP**. Ils ne décrivent pas l'entreprise en général.

1. Lire les critères de l'ICP du client (type d'entreprise, secteurs, taille, fonctions ciblées).
2. Construire 4 familles de tags, dans cet ordre :
   - **Type** : Détaillant, Distributeur (seulement les types acceptés par l'ICP).
   - **Secteur standardisé** : regrouper les entreprises de la sélection dans une liste courte de secteurs (viser 8 à 12 pour 15 prospects). Deux entreprises du même métier ont le même secteur. Exemples : Mobilier et décoration ; Piscines, spas et extérieur ; Rénovation et quincaillerie ; Mode et vêtements ; Sport et plein air ; Beauté ; Animalerie ; Optique ; Pneus et automobile ; Cannabis.
   - **Tranche de CA** (CAD) : définir 3 à 5 tranches qui séparent bien la sélection, sans le mot « CA ». Exemple pour Mirego : 40-100 M$ ; 100-250 M$ ; 250-500 M$ ; 500 M$ et plus. Une tranche s'appuie sur la meilleure estimation disponible ; si une estimation est en USD ou incertaine, choisir la tranche la plus plausible en CAD et le noter dans le référentiel.
   - **Rôle** : la fonction ciblée par l'ICP qui correspond au prospect (Direction générale, Marketing, Numérique et e-commerce, TI, Opérations, Expérience client...).
   - **Critères ICP prouvés** (facultatif, 3 au maximum) : seulement si l'ICP du client les exige et qu'ils sont prouvés pour ce prospect. Exemple pour Ursa : Boutique en ligne ; Google ads actives ; Meta ads actives.
3. Ne pas mettre de tags hors ICP : pas de plateforme (Shopify) ni de région pour Mirego, pas de « multi-enseignes ».
4. Écrire `livrables-<événement>/fiches/<client>-tags-reference.md` : les familles, la liste des secteurs avec les entreprises de chaque secteur, les tranches avec les entreprises de chaque tranche, et une note sur le caractère estimé des tranches.
5. Montrer le référentiel à Elizabeth avant de rédiger les fiches : un changement de taxonomie après coup oblige à tout reprendre.

Format dans la fiche et le CSV : `Type; Secteur; Tranche; Rôle` puis, s'il y a lieu, les critères ICP prouvés (séparateur « ; », 4 à 7 tags).

## Étape 2 - Une fiche test

Rédiger **une seule fiche** d'abord (choisir un prospect avec beaucoup de faits sourcés), la faire valider, puis faire les autres. Les consignes de style changent souvent à la première fiche.

## Étape 3 - Rédiger les fiches

Gabarit et exemple : `references/card-template.md`. Une fiche par prospect, en Markdown, nommée `<client>-<rang>-<prénom-nom>-<entreprise>.md`.

### Règles d'écriture

- **Description de l'entreprise (`brief`)** : 50 à 75 mots, 2 ou 3 phrases courtes. Ce que fait l'entreprise, sa taille parlante (nombre de magasins, enseignes, marchés), et une actualité si elle existe. Aucun mot de remplissage, aucun superlatif.
- **Raison du match longue (`match_reason_long`)** : environ 50 mots. Le lien entre la situation du prospect (le signal) et l'offre du client, puis pourquoi cette personne est la bonne porte.
- **Raison du match courte (`match_reason_short`)** : 10 mots au maximum.
- **Angles de conversation** : partir de la recherche d'actualités (skill event-prospect-research) et varier la forme des questions d'une fiche à l'autre (pas la même question type répétée). En proposer 5 dans la fiche, une seule phrase chacun, sous forme de question. Mélanger : certains montrent qu'on connaît l'entreprise (un fait précis), d'autres sont des questions qu'un pair attentif poserait à n'importe quel dirigeant du secteur. Jamais sur le parcours personnel ou l'historique LinkedIn de la personne : ça fait enquête. Sélectionner les **3 meilleurs** pour le CSV (un précis, un sur le cœur de l'offre du client, un ouvert), garder les 2 autres dans la fiche comme choix.
- **À aborder** : si un sujet est incontournable (actualité de l'entreprise, changement récent), l'écrire en une phrase.
- **Brouillon d'ouverture (`suggested_outreach`)** : envoyé par le client, dans sa voix. Sans objet. Vouvoiement, professionnel sans être formel, comme un vrai humain l'écrirait. Structure : « Bonjour [Prénom], » ; une phrase qui situe HOP et s'accroche au signal ; une phrase sur l'offre du client (voir `client-profiles.md`) ; l'invitation « Êtes-vous disponible pour prendre un café sur place pour échanger ? » ; la signature du client. Viser 60 à 90 mots.
- **Prospect partagé entre clients** : si la même personne (ou une collègue de la même entreprise) reçoit aussi une fiche d'un autre client, réécrire le brouillon du second client avec une autre structure (autre ouverture, autre formulation de l'invitation au café) pour qu'elle ne reçoive pas deux fois le même gabarit. Le signaler à Elizabeth.
- **Jamais de tiret long ni moyen** (« — », « – ») dans aucun champ. Utiliser une virgule, deux-points ou une nouvelle phrase.
- **Ne jamais mentionner les campagnes publicitaires en cours du prospect** dans les textes (description, raison du match, angles, brouillon) : c'est intrusif. Si c'est un critère de l'ICP, il va seulement dans les tags.
- **Ne rien inventer.** Un fait absent du briefing ne va pas dans la fiche. Un fait qui vient d'un résumé de recherche non lu en entier s'écrit de façon prudente (« une quinzaine » plutôt que « 16 ») et se signale dans la section interne.
- **Ne jamais citer de chiffre d'affaires** dans la description, la raison du match ou le brouillon : ce sont des estimations internes. La tranche n'apparaît que dans les tags.
- Ne pas mentionner les autres clients de BETA Labs, ni qu'un prospect est proposé à plusieurs clients, ni le contenu confidentiel d'un client (portefeuille, exclusions).

### Section interne (pour Elizabeth seulement)

Sous une ligne de séparation : ce qui est à vérifier avant l'envoi, les confusions possibles (homonymes, entreprises au nom proche), et les sources (URL et citation courte). Cette section ne va pas dans le CSV.

## Étape 4 - CSV d'import

Écrire un fichier JSON (liste d'objets, une clé par colonne ci-dessous, `conversation_starter` en liste de 3 phrases) dans `livrables-<événement>/fiches/<client>-cards.json`, puis :

```bash
python3 .claude/skills/event-match-cards/scripts/build_cards_csv.py \
  --cards livrables-<événement>/fiches/<client>-cards.json \
  --client-signature "Elisa-Eve, Mirego" \
  --out livrables-<événement>/fiches/<client>-import.csv
```

Colonnes de la plateforme, dans cet ordre : `match_query` (vide), `job_title`, `full_name`, `company_name`, `brief`, `company_url`, `linkedin_url` (profil du prospect), `profile_image_url` (vide), `profile_picture` (vide), `interests` (tags), `match_reason_short`, `match_reason_long`, `conversation_starter` (3 angles séparés par « ; », sans numéros), `suggested_outreach` (sans objet), `match_score` (score de priorité sur 100), `language` (vide), `external_link` (page LinkedIn de l'entreprise, vide si introuvable), `email`.

Le script refuse le fichier si une règle n'est pas respectée : longueurs, tirets longs, nombre d'angles, objet dans le brouillon, tutoiement, signature absente, chiffre d'affaires cité. Corriger la fiche plutôt que forcer.

## Étape 5 - Remise

Envoyer à Elizabeth le référentiel de tags, les fiches et le CSV. Rappeler ce qui reste à vérifier (section interne) et les colonnes laissées vides faute de source (ex. `external_link`). Un brouillon ne vaut jamais instruction d'envoi.
