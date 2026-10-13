# BETA Labs — Brand guide v2

Guide et système d’assets produits le 13 octobre 2026. Le logo SVG fourni est conservé intégralement. Le B dérivé, le clearspace, les règles et l’accent Newsreader sont des propositions de déclinaison.

## Livrables

- [Guide PDF — 16 pages](exports/BETA-Labs-Brand-Guide-v2.pdf)
- [Guide HTML](index.html)
- [Inventaire des masters](manifest.json)
- [Validation des exports](validation.json)

| Besoin | Master SVG |
|---|---|
| Logo original fourni | [primary-original.svg](assets/logos/primary-original.svg) |
| Logo sur fond clair | [primary-charcoal.svg](assets/logos/primary-charcoal.svg) |
| Logo sur fond sombre | [primary-cream.svg](assets/logos/primary-cream.svg) |
| Logomark | [logomark-charcoal.svg](assets/logos/logomark-charcoal.svg) |
| Avatar | [avatar-lime.svg](assets/logos/avatar-lime.svg) |
| Lockup secondaire | [stacked-lockup.svg](assets/logos/stacked-lockup.svg) |
| Clearspace | [wordmark](assets/rules/logo-clearspace.svg), [symbole](assets/rules/mark-clearspace.svg) |
| Pattern | [field](assets/patterns/signal-field.svg), [frame](assets/patterns/precision-frame.svg), [network](assets/patterns/signal-network.svg) |
| Infographies | [process](assets/diagrams/process-infographic.svg), [signal](assets/diagrams/signal-infographic.svg) |
| Schéma | [deux motions](assets/diagrams/dual-motion-schema.svg) |
| Social | [portrait](assets/social/statement-portrait.svg), [carré](assets/social/signal-square.svg), [story](assets/social/preparation-story.svg) |
| Carousel | [01](assets/social/carousel-01.svg), [02](assets/social/carousel-02.svg), [03](assets/social/carousel-03.svg), [04](assets/social/carousel-04.svg) |
| Bannières | [LinkedIn entreprise](assets/banners/linkedin-company.svg), [LinkedIn profil](assets/banners/linkedin-profile.svg), [Facebook](assets/banners/facebook-page.svg), [X](assets/banners/x-profile.svg), [YouTube](assets/banners/youtube-channel.svg) |
| Imagerie | [Étude éditoriale](assets/imagery/brand-study.png), [provenance](assets/imagery/provenance.json) |

Les 33 PNG correspondants sont dans `exports/png/`. Les logos transparents conservent leur alpha. Les SVG utilisent des contours de glyphes pour un rendu stable ; la copie, les mises en page et les données sources peuvent être modifiées dans le script de construction. Les fonts TTF et leurs OFL sont incluses dans `assets/fonts/`.

## Règles centrales

Palette crème/charbon/lime/blanc. Inter primaire ; Newsreader Italic pour un accent éditorial proposé. Une idée par composition, un signal visuel dominant, pas de données de participants ni de métriques inventées. Les exemples de profils sont fictifs.

Wordmark : zone libre x = H/2, où H est sa hauteur. Minimum numérique proposé 180 px ; symbole 16 px, 32 px+ recommandé. Les dimensions de bannières sont des cibles d’export, pas une nouvelle vérification des specs des plateformes.

## Reproduire

```bash
python3 scripts/build_brand_guide.py
python3 scripts/export_brand_guide.py
```

La construction demande FontTools et les fichiers de police, présents dans cette instance ; l’export utilise Playwright/Chromium et Pillow. Les fonts incluses sont utilisées lors des reconstructions suivantes. Le guide et ses exports ne nécessitent aucune clé API. L’imagerie générée est conservée comme asset ; sa régénération demanderait une nouvelle génération d’image.

Les méthodes du designer viennent des [skills Open Design](../../agents/learning/open-design/README.md) adaptés au contexte. BYQ et la lecture du site actuel restent en attente d’accès. Aucun push ou déploiement n’est impliqué par la création de ces fichiers.
