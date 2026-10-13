# BETA Labs — GTM Intelligence

Base de travail interne pour GoodBytes Studio et BETA Labs. **Analyse du corpus au 13 octobre 2026**, sans nouvelle vérification web ni confirmation auprès des clients.

BETA Labs est décrit dans les sources récentes comme **la couche de ciblage pré-événement pour les événements B2B** : liste des participants obtenue sous entente, enrichissement selon l’ICP, liste courte avec signaux et brouillons d’ouverture. Le commanditaire envoie les messages et conserve la relation. Le positionnement reste **provisoire** dans le corpus.

## Commencer ici

| Besoin | Document |
|---|---|
| Comprendre la stratégie et les priorités | [Synthèse](intelligence/00-synthese.md) |
| Comprendre l’entreprise et sa traction | [Entreprise](intelligence/01-entreprise.md) |
| Savoir ce qu’on vend et comment le présenter | [Positionnement](intelligence/02-positionnement.md), [offre et prix](intelligence/04-offre-pricing.md) |
| Qualifier un organisateur ou un commanditaire | [ICP](intelligence/03-icp.md), [motions GTM](intelligence/06-motions-gtm.md) |
| Rédiger un message | [Messaging](intelligence/05-messaging.md), [marque](intelligence/08-marque.md) |
| Travailler les événements | [Marchés](intelligence/07-evenements-marches.md), [HOP](campaigns/hop-2026/README.md), [ALL IN](campaigns/allin-2026/README.md) |
| Distinguer preuves, hypothèses et contradictions | [Registre éditorial](intelligence/09-preuves-decisions.md), [audit](docs/audit-du-corpus.md) |
| Retrouver une pièce originale | [Catalogue des 39 sources](sources/README.md) |
| Exploiter les CSV et les mettre à jour | [Données](data/README.md), [méthode](docs/methode.md) |
| Piloter les prochaines étapes | [Plan de travail](operations/plan-de-travail.md), [pipeline et mesure](operations/pipeline-et-mesure.md) |

## Structure

```text
intelligence/          synthèses éditoriales françaises, sourcées et datées
campaigns/             dossiers HOP et ALL IN, relus au calendrier actuel
operations/            plan de travail, pipeline, mesure et modèles
research/              index des recherches d’expansion et de marché
sources/originals/     les 39 pièces reçues, inchangées
sources/text/          textes consultables, dont extraction des 12 DOCX
sources/manifest.json  provenance, dates documentaires et SHA-256
data/config/           alias explicites et dates des campagnes
data/registers/        claims, décisions et conflits éditoriaux
data/derived/          tables reconstruites avec provenance par ligne
scripts/               reconstruction et validation, Python standard
```

## Données préparées

Les cinq CSV sources contiennent **261 lignes**, toutes conservées dans les tables correspondantes : 221 lignes ALL IN/HOP, 15 comptes CRM, neuf contacts organisateurs et 16 événements. Le catalogue dérivé contient **17 événements** après ajout de HOP. Le rapprochement prudent des comptes produit **230 identités normalisées** ; ce n’est pas un nombre de clients ni une déduplication exhaustive des entreprises.

ALL IN 2026 est passé **selon les dates fournies**. HOP est annoncé au 27 octobre, soit J-14 à la date d’analyse ; la clôture de vente du 29 septembre proposée dans les sources est dépassée. Aucun envoi ni lancement de campagne n’a été effectué.

## Utiliser le dépôt

Python 3.10+ suffit. Aucune clé API, base de données, installation npm ou service web n’est nécessaire pour consulter et reconstruire cette base documentaire.

```bash
cd /workspace/betalabs
python3 scripts/build_intelligence.py --as-of 2026-10-13
python3 scripts/validate_repo.py
```

Choisir une nouvelle date d’analyse explicitement lors d’un rafraîchissement. Le script recalcule les statuts calendaires des **données** ; il ne réécrit pas les synthèses, ne recherche pas de nouveaux contacts et ne vérifie pas les inscriptions. Utiliser `rg` pour chercher dans les synthèses et textes extraits.

Les originaux restent lisibles même lorsqu’ils se contredisent. Les identifiants S01–S39 permettent de remonter de chaque synthèse à sa source. La présence d’une affirmation dans un document, même marquée « validée » par son auteur, ne constitue pas une nouvelle vérification indépendante.

Le générateur JavaScript reçu est conservé comme archive. Il n’entre pas dans la reconstruction de cette base. Les contrôles effectués sont décrits dans le [rapport de validation](docs/validation.md).
