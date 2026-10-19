---
name: event-prospect-research
description: Recherche d'actualités d'entreprise pour personnaliser les fiches de prospects d'un événement BETA Labs (HOP, ALL IN, etc.). Pour une liste d'entreprises, trouve les faits récents et sourcés (rachats, ouvertures, nouveaux concepts, lancements, expansions, prix, partenariats) qui nourrissent les angles de conversation et les brouillons d'ouverture. À utiliser avant ou pendant la rédaction des fiches (skill event-match-cards), dès qu'on parle de rechercher des nouvelles, de l'actualité ou des faits récents sur des prospects ou des entreprises, même si l'utilisateur ne nomme pas le skill. Peut tourner sur un modèle plus léger (Sonnet) ou dans une autre session.
---

# Recherche d'actualités sur les entreprises prospects

But : donner à la rédaction des fiches des faits **précis, datés et sourcés** sur chaque entreprise, pour que les angles de conversation et les brouillons soient personnalisés au lieu de génériques. Une seule bonne nouvelle (un rachat, une ouverture, un lancement) vaut mieux que dix faits génériques tirés du site.

Communiquer avec Elizabeth en français, sans jargon.

## Entrée

Une liste d'entreprises, une par ligne : `nom | site web | personne inscrite et poste (contexte seulement) | client(s)`. Elle peut être collée dans la conversation ou fournie en CSV. Demander la date de l'événement si elle n'est pas donnée.

## Ce qu'on cherche, par entreprise

1. **Actualités récentes** (viser les 24 derniers mois) : rachats ou ventes, changements de propriétaires, ouvertures et fermetures de magasins, nouveaux concepts ou formats, déménagements, entrée dans une nouvelle province ou aux États-Unis, lancements de produits, de marques ou de services, refonte de site ou d'application, programme de fidélité, rebranding, financement, prix et classements (ex. étude WOW de Léger), partenariats, campagnes caritatives, anniversaires marquants.
2. **Un ou deux faits distinctifs durables** : histoire, modèle d'affaires, signature, positionnement.
3. **Sujets sensibles à signaler** (sans les proposer comme angle) : difficultés financières, protection contre les créanciers, mises à pied, recul dans un classement, conflits avec fournisseurs, poursuites.

## Règles

- **Uniquement l'entreprise.** Rien sur la carrière personnelle, l'historique LinkedIn ou la vie privée des personnes. Un rachat par des dirigeants est un fait d'entreprise ; leur parcours ne l'est pas.
- **Chaque fait** : date (mois et année si possible), citation courte ou paraphrase fidèle, URL.
- **Statut obligatoire** : « Confirmé » (page lue en entier) ou « Résumé de recherche seulement » (vu dans un extrait de moteur, page bloquée ou payante). Ne jamais présenter un résumé comme confirmé.
- **Ne rien inventer.** Si rien de récent n'est trouvé, l'écrire.
- **Chiffres d'affaires** : seulement s'ils sont publiés par une source fiable (entreprise cotée, société d'État, média reconnu), et les marquer comme tels. Jamais d'estimations de répertoires (RocketReach, Apollo, ZoomInfo).
- **Contenu commandité** (ex. La Presse XTRA) : l'indiquer.
- **Contradictions entre sources** (nombre de magasins, dates) : les noter toutes.
- **Publicité en ligne du prospect** : ne pas la rechercher ni la décrire ici ; ce critère se vérifie ailleurs (Clay) et ne doit jamais apparaître dans les textes destinés au prospect.

## Outils

- WebSearch pour trouver ; lancer plusieurs recherches en parallèle (nom de l'entreprise + « 2026 », « ouverture », « acquisition », « nouveau concept », nom + média régional).
- Pour lire une page : si WebFetch est bloqué, utiliser `curl -sL --max-time 25 -A "Mozilla/5.0" URL` et extraire le texte avec Python (`re` + `html.unescape`). Retail Insider, LinkedIn et certains médias bloquent la lecture : statut « résumé ».
- Pour un gros lot, répartir les entreprises entre plusieurs agents (5 à 8 entreprises chacun). Un modèle plus léger (Sonnet) suffit pour ce travail si les règles ci-dessus sont dans la consigne.

## Sortie

Un fichier Markdown par lot, nommé `recherche-<événement>-<lot>.md` (dans `livrables-<événement>/recherche/` si le dépôt est disponible, jamais commité ; sinon dans le dossier de travail de la session, à envoyer à Elizabeth).

```markdown
# Recherche d'actualités : <événement>, lot <n> (date)

Légende : Confirmé = page lue ; Résumé = extrait de moteur seulement.

## <Entreprise>

**Faits récents**
- **<Mois année> : <titre court>.** <Citation ou paraphrase>. Statut. <URL>

**Faits distinctifs durables**
- ...

**Sujets sensibles** (ne pas utiliser comme angle)
- ...

**Rien trouvé sur** : <ce qui manque>
```

Terminer par un résumé de deux lignes par entreprise dans la conversation, puis la liste de ce qui reste à confirmer.

## Remise

Si la recherche est faite dans une autre session que la rédaction des fiches, les fichiers ne passent pas d'une session à l'autre : les envoyer à Elizabeth, qui les téléverse dans la session de rédaction. Les données de prospects restent hors du dépôt Git.
