# Enrichissement final dans Clay

Le CSV `clay-enrichment-import.csv` contient une ligne par entreprise à enrichir. Les colonnes déjà remplies viennent de la prévalidation ; les colonnes vides sont celles que Clay doit remplir. **Garder exactement les noms de colonnes** : `ingest_clay.py` les relit par leur nom.

## Dans Clay

1. Workspace **de la cliente** (vérifier en haut à gauche), **+ New → Table → Import CSV**, choisir `clay-enrichment-import.csv`. Type de table : *Companies*, colonne domaine : `domain`.
2. Ajouter les colonnes d'enrichissement ci-dessous, tester sur 5 lignes, vérifier le coût en crédits affiché par Clay, puis lancer sur toute la table.
3. Pour chaque résultat, **écrire la valeur dans la colonne cible** (bouton *Map to column* / formule `{{colonne}}`) : la machine ne lit pas les colonnes JSON de Clay.
4. Exporter : **Actions → Export → CSV** (toutes les colonnes) et donner le fichier à Claude.

## Colonnes à remplir

| Colonne cible | Source Clay conseillée | Format attendu |
|---|---|---|
| `revenue_raw` | Enrich Company (revenu) ou Claygent sur le rapport annuel | Nombre seul, sans `$` ni `M` : `45000000` |
| `revenue_currency` | même source | `CAD` ou `USD` |
| `revenue_year` | même source | `2025` |
| `revenue_source_url` | URL de la page source | `https://…` |
| `revenue_is_estimate` | `yes` si fourchette ou estimation d'un fournisseur de données | `yes` / `no` |
| `business_model` (si vide) | Claygent | `b2c`, `b2b` ou `b2b b2c` |
| `business_model_source_url` | Claygent | `https://…` |
| `<signal>` | voir ci-dessous | `yes` / `no` / vide |
| `<signal>_source_url` | page qui prouve | `https://…` |
| `<signal>_quote` | citation exacte ou élément technique observé | texte court |

Un CA estimé par un fournisseur de données (`revenue_is_estimate=yes`) reste brut : il sert au tri, pas à franchir un seuil ICP. Seul un CA en CAD, daté et sourcé, puis approuvé à la revue, est vérifié.

## Signaux connus et prompts Claygent

Adapter le prompt si un client définit un nouveau signal. Toujours demander l'URL et une citation.

| Signal | Question Claygent | Indice technique |
|---|---|---|
| `online_store` | « Le site {{website_url}} permet-il d'acheter en ligne (panier, paiement) ? Réponds yes/no, l'URL d'une page produit et une citation. » | Tech stack : Shopify, Magento, Salesforce Commerce Cloud, WooCommerce |
| `paid_ads_google_or_meta` | « {{name}} diffuse-t-il des publicités actives sur Meta ou Google ? Vérifie la Meta Ad Library et Google Ads Transparency. yes/no, URL, citation. » | Pixels Meta / Google Ads dans le tech stack |
| `supported_cms` | « Quel CMS / plateforme e-commerce utilise {{website_url}} ? Réponds yes si Shopify ou WordPress/WooCommerce, no sinon, avec l'outil détecté. » | Tech stack (BuiltWith / Wappalyzer) |
| `marketing_investment` | « {{name}} montre-t-il un investissement marketing récent (campagnes, embauches marketing, agence, rebranding) en 2025-2026 ? yes/no, URL, citation. » | Offres d'emploi marketing, actualités |
| `mobile_product_potential` | « {{name}} a-t-il une application mobile, un programme de fidélité ou un projet numérique annoncé ? yes/no, URL, citation. » | App Store / Google Play |
| `black_friday_readiness` | « {{name}} a-t-il mené une campagne Black Friday / Cyber Monday en 2025 ? yes/no, URL, citation. » | Pages promo archivées |
| `culture_challenge` | « Y a-t-il des signes publics d'enjeux de recrutement ou de culture chez {{name}} (embauches massives, avis employés, prix employeur) ? yes/no, URL, citation. » | Offres d'emploi, Glassdoor |

Les réponses Clay restent des propositions : `ingest_clay.py` les met en revue, et seules les lignes approuvées passent en confiance `high` dans les preuves.
