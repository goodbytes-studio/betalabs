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
