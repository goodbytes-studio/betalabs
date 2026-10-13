# Validation du dépôt — 13 octobre 2026

Les vérifications portent sur la base documentaire construite dans cette instance cloud.

| Vérification | Résultat |
|---|---|
| Import | 39 fichiers, chacun vérifié contre son empreinte SHA-256 d’import |
| Lecture | 12 DOCX lisibles ; cinq CSV sans anomalie de largeur |
| Provenance | 261 lignes des cinq CSV couvertes dans les tables correspondantes |
| Valeurs sources | Champs des campagnes, CRM, contacts et événements conservés |
| Liaison | Références de comptes, événements, sources et registres valides |
| Navigation | Liens locaux des documents rédigés et du catalogue vérifiés |
| Calendrier | HOP J-14 et ALL IN historique au 13 octobre selon les dates fournies |
| Incertitude | Leads non inscrits, paiements non vérifiés et quantités ambiguës distingués |
| Reproduction | Deux constructions avec la même date ont produit les mêmes octets sur 47 fichiers générés |

Commandes exécutées avec succès dans `/workspace/betalabs` :

```bash
python3 scripts/build_intelligence.py --as-of 2026-10-13
python3 scripts/validate_repo.py
```

Le programme reçu `generate-report.js` n’a pas été exécuté. Aucun enrichissement externe, contact commercial, contrôle de coordonnées ou nouvelle vérification web n’a eu lieu. Les résultats de ventes, permissions de publication et capacités de livraison client restent ceux déclarés ou manquants dans les pièces.

La construction réussie ici ne prouve pas une publication de l’environnement ni une restauration dans une nouvelle tâche. Le dépôt est versionné avec Git ; la référence distante `main` permet de vérifier la synchronisation GitHub après un push. L’archive livrable permet aussi de transporter les fichiers.

## Exploration de marque et agents

Les deux agents disposent de prompts, de skills locaux et d’une mémoire structurée. Cela établit la présence de leurs instructions dans le dépôt, pas une exécution autonome ni une activation globale.

Le prototype local a été contrôlé en français et anglais, pour commanditaire et organisateur, à 1440, 390 et 320 px : 12 variantes de rendu, navigation clavier, changement de public/langue, génération de brief et traitement des champs comme texte. Les paires de contraste spécifiées et les hashes de la police sont vérifiés. Ces vérifications ne constituent pas un audit WCAG complet.

Les PNG sont des rendus de l’exploration, inspectés visuellement. La requête vers le vrai site a été bloquée : aucune capture live ou vérification actuelle du messaging de `betalabs.ca` n’est déclarée. Les détails sont dans [validation.json](../brand/prototypes/brand-direction-v1/validation.json).

## Brand guide v2

Le SVG utilisateur est préservé par hash. Le guide de 16 pages a été exporté en PDF et son nombre de pages contrôlé ; les planches logo, symbole, clearspace, imagerie, social et bannières ont été inspectées visuellement. Les 33 masters SVG et PNG sont contrôlés par hash et dimensions, et les logos transparents par canal alpha. Les fonts TTF/OFL et les sept bundles Open Design ont leur provenance et leurs empreintes.

Les nouvelles règles et le B dérivé sont des propositions de système. Les dates/formats sociaux sont des cibles d’export, pas une vérification live des specs de plateformes. Le PDF et ces assets ne démontrent ni métriques commerciales ni publication d’un site. [Validation détaillée](../brand/guide/validation.json).
