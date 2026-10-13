# BETA Labs — GTM, skills et brand guide

Base de travail interne pour GoodBytes Studio et BETA Labs : intelligence GTM, skills designer et copywriter, mémoire de marque et brand guide v2. **Analyse du corpus au 13 octobre 2026**, sans nouvelle confirmation auprès des clients. La [lecture du site actuel reste bloquée](brand/audit-2026-10-13.md) par l’accès réseau.

BETA Labs est décrit dans les sources récentes comme **la couche de ciblage pré-événement pour les événements B2B** : liste des participants obtenue sous entente, enrichissement selon l’ICP, liste courte avec signaux et brouillons d’ouverture. Le commanditaire envoie les messages et conserve la relation. Le positionnement reste **provisoire** dans le corpus.

## Brand guide et assets

Le [brand guide v2](brand/guide/README.md) comprend **16 pages et 33 masters SVG avec leurs exports PNG** : logos, symbole B, clearspace, typographie, palette, imagerie, patterns, infographies, social et bannières.

| Livrable | Accès |
|---|---|
| Guide PDF | [Consulter ou télécharger le PDF](brand/guide/exports/BETA-Labs-Brand-Guide-v2.pdf) |
| Guide HTML | [Fichier HTML](brand/guide/index.html) — à ouvrir localement |
| Masters SVG et polices | [Assets](brand/guide/assets/) |
| Exports PNG | [33 fichiers PNG](brand/guide/exports/png/) |
| Logo original fourni | [SVG original](brand/assets/logos/betalabs-original.svg) |
| Inventaire et provenance | [Manifeste](brand/guide/manifest.json), [validation](brand/guide/validation.json) |

Le logo original est préservé. Les déclinaisons et les nouvelles règles sont des propositions v2. Inter et Newsreader sont fournis avec leurs licences OFL ; l’imagerie générée conserve sa provenance.

## Skills Codex

| Skill | Usage | Instructions |
|---|---|---|
| `$betalabs-designer` | Direction artistique, supports visuels, prototypes et système de marque | [SKILL.md](.agents/skills/betalabs-designer/SKILL.md), [prompt designer](agents/designer.md) |
| `$betalabs-copywriter` | Stratégie du message, offres, pages et rédaction FR/EN | [SKILL.md](.agents/skills/betalabs-copywriter/SKILL.md), [prompt copywriter](agents/copywriter.md) |

Ouvrir le dépôt dans Codex et invoquer le skill avec un brief. Si le skill n’apparaît pas dans la session, demander de lire son `SKILL.md` directement. Les [exemples d’appel et instructions d’usage](agents/README.md) détaillent le travail coordonné. Les deux rôles partagent la [mémoire de marque](brand/README.md) et le registre de claims.

## Intelligence GTM — commencer ici

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
| Faire travailler le designer ou le copywriter | [Agents BETA Labs](agents/README.md), [mémoire de marque](brand/README.md) |
| Voir une évolution concrète de la marque | [Prototype interactif](brand/prototypes/brand-direction-v1/index.html), [stratégie et copy](brand/prototypes/brand-direction-v1/copy-pack.md) |
| Utiliser le brand guide et ses assets | [Brand guide v2](brand/guide/README.md), [PDF](brand/guide/exports/BETA-Labs-Brand-Guide-v2.pdf) |

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
brand/                 mémoire, tokens, propositions et prototype de marque
agents/                rôles designer/copywriter et contrat de relais
.agents/skills/        skills locaux Codex pour les deux agents
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

## Designer et copywriter

Utiliser `$betalabs-designer` pour direction artistique, systèmes et supports visuels, ou `$betalabs-copywriter` pour stratégie du message et rédaction. Les [instructions d’usage](agents/README.md) expliquent leur découverte locale et le chargement manuel si nécessaire. Ces rôles partagent les mêmes sources et claims ; aucune activation globale ou déploiement autonome n’est annoncé.

Le prototype est une exploration FR/EN commanditaire/organisateur, fondée sur les documents, avec profils fictifs. Sa vérification optionnelle utilise Playwright et Chromium, disponibles dans cette instance : `python3 scripts/verify_brand_prototype.py`. Elle ne fait pas partie des dépendances nécessaires à la lecture et à la reconstruction du corpus.

Le designer v2 utilise sept [bundles Open Design](agents/learning/open-design/README.md) et dix références de craft. [BYQ](agents/learning/BYQ.md) reste non ingéré, son accès étant bloqué. Le [DESIGN.md](brand/DESIGN.md) et le [contrat](brand/design-contract.md) relient ces méthodes à BETA Labs.

Le logo SVG fourni est conservé dans `brand/assets/logos/betalabs-original.svg`. Le guide de 16 pages et ses 33 masters SVG/PNG couvrent logo, B dérivé, clearspace, typographie, palette, imagery, patterns, infographies, schémas, social et bannières. Fonts OFL et imagerie générée ont leur provenance ; les règles nouvelles sont des propositions v2.
