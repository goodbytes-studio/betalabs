# Écarts de la machine événements : cas Desjardins (HOP 2026)

Document de travail du 2026-10-20. Il ne contient aucun nom de prospect : le détail par entreprise reste hors Git, dans `.event-machine/`.

## Le test

Elizabeth avait repéré à la main, en travaillant sur les autres clients, 18 pistes pour Desjardins. 17 sont des entreprises retrouvées dans les inscrits ; 1 est introuvable (aucune entreprise du nom donné). La machine devait normalement les faire ressortir.

| Statut de la machine | Entreprises (17) |
|---|---|
| Fort | 0 |
| Possible | 1 |
| À confirmer | 14 |
| Exclu | 2 (contact non propriétaire) |

Aucune n'était exclue à tort pour son entreprise. Le problème est que la machine ne les a jamais mises en tête : 14 sur 17 sont restées noyées dans les 201 « à confirmer ».

## Simulation (sans toucher au moteur)

| Scénario | Fort | Possible |
|---|---|---|
| Aujourd'hui | 0 | 2 |
| Province déduite de la ville de l'inscrit | 3 | 12 |
| Province et estimations de CA Clay brutes aussi lues | 4 | 11 |

La lecture de la province est donc l'écart principal. Les CA bruts de Clay sont un levier secondaire et risqué : une estimation à 85 K$ a fait exclure une entreprise.

## Causes

| # | Écart | Preuve | Correctif proposé |
|---|---|---|---|
| E1 | **La province est inconnue** et l'ICP Desjardins l'exige (D31). Elle n'existe que pour environ 190 comptes sur 328 (champ `state` d'Apollo). | 14 des 17 restent « à confirmer » pour la province seulement. | Déduire la province de la **ville** de l'inscrit (confiance basse, signalée) et du pays. |
| E2 | **La colonne `city` a disparu** entre l'export du 19 et celui du 20 octobre, avec `estimated_num_employees`, `state` et `project_slugs`. Le moteur ne lit d'ailleurs pas `city`. | La ville existe pour 16 des 18 inscrits dans l'ancien export. | Redemander la colonne à l'organisateur, et faire lire `city` au moteur. Fusionner les anciens exports par courriel et domaine. |
| E3 | **Le CA des petites entreprises n'a jamais été relu.** Les ICP précédents avaient un plancher de 5 à 40 M$ ; la relecture Clay n'a gardé que ce qui servait ces clients. | Des estimations Clay brutes existent pour plusieurs comptes de 0,1 à 7 M$ sans avoir été approuvées. Un compte a deux chiffres en conflit. | Relire les estimations sous 5 M$ avec le même processus d'approbation (D21, D22), compte par compte. |
| E4 | **Le nombre d'employés manque** pour presque tous les comptes. L'ICP Desjardins vise 3 à 20 employés. | La plupart des comptes n'ont aucun effectif. | Ajouter l'effectif à la recherche ou à Clay ; afficher « effectif inconnu » comme un point à valider. |
| E5 | **Compte bon, mauvais contact.** La machine juge la personne, pas le compte. Un détaillant dont le seul inscrit est directeur des ventes ou des opérations est exclu sans qu'on propose de trouver le propriétaire. | 3 entreprises plausibles sur 17. | Ajouter une vue « compte conforme, contact à trouver ». |
| E6 | **« À confirmer » est un fourre-tout.** Un compte auquel il manque un seul élément est classé comme un compte auquel il manque tout. La liste courte ne montre que fort et possible. | 14 candidats corrects invisibles dans `shortlist-desjardins.csv`. | Ajouter une vue « presque fort » : un seul élément manquant, et lequel. |
| E7 | **Type inconnu quand le site est inaccessible** (erreurs 429 et 503, mauvais domaine). Les agents de recherche n'ont aucune autre source et la machine ne sait pas relancer. | 2 comptes sur 17 ; 16 comptes déjà tentés en vain. | Prévoir une recherche par le nom et la ville, puis une identification à la main. |
| E8 | **Le rattachement entreprise-personne est fragile** : un même inscrit peut se retrouver dans trois comptes (domaine personnel, nom seul, domaine de l'entreprise). Un cas a été corrigé le 2026-10-20 (courriels personnels). | Un compte « domaine personnel » regroupait 15 personnes d'entreprises différentes. | Fusionner les comptes par nom normalisé et domaine ; ne jamais clé sur un domaine de messagerie. |
| E9 | **Le titre « General Manager » compte comme décideur**, alors que Desjardins veut propriétaire ou actionnaire. | 3 comptes sur 17 ont ce titre. | Garder « à valider » pour les titres de direction salariée quand l'ICP demande un propriétaire. |
| E11 | **Un assouplissement a créé un trou de l'autre côté** : n'exclure jamais sur une estimation a laissé passer de grandes entreprises. | Touchette, MUST et d'autres, de 25 M$ à plus de 1 G$ (noms dans `.event-machine/`). | Asymétrie : jamais d'exclusion vers le bas sur estimation, limite ferme vers le haut ; contrôle de taille automatique du diagnostic. |
| E10 | **Une entreprise du client n'apparaît pas sous le nom donné** (nom commercial différent de celui du formulaire). | 1 piste sur 18 introuvable. | Rapprocher le nom par recherche floue et par domaine, et le dire à l'utilisatrice. |

## Du côté du processus

| Écart | Détail |
|---|---|
| Recherche web lancée par poste d'abord, pas par type d'entreprise | 56 entreprises cherchées, dont une grande partie de vendeurs de services. Un tri par le type d'abord aurait coûté moins de recherches. |
| Les comptes « dirigeant, déjà recherché, province inconnue » n'ont pas été examinés | Ils n'étaient pas à rechercher, donc je les ai laissés de côté, alors que leur blocage était la province. |
| Les chiffres du diagnostic n'étaient pas mis à jour après chaque étape | Il a fallu les recalculer (120 devenus 92). |

## Statut au 2026-10-20 (décision D36, source S61)

| Écart | État |
|---|---|
| E1, E2 province | **Corrigé** : le moteur lit la colonne `city` et déduit la province (`event_machine/geography.py`) ; l'hypothèse est signalée `[Déduit]` et n'exclut jamais. La colonne `city` reste à redemander à l'organisateur ; les villes de l'ancien export ont été fusionnées par courriel. |
| E3 CA | **Adapté** pour Desjardins : une estimation n'exclut jamais ; cœur 1 à 10 M$, zone élargie 0,5 à 20 M$ acceptée ; seul un CA vérifié hors zone exclut. Les estimations Clay brutes restent à approuver compte par compte. |
| E5 compte bon, contact à trouver | **Corrigé** : vue `contact-a-trouver-<client>.csv` du diagnostic. |
| E6 « à confirmer » fourre-tout | **Corrigé** : vue `near-miss-<client>.csv` (un seul élément manquant). |
| E9 General Manager | **Clos** : un directeur général convient (D37, S62). |
| E11 grandes entreprises dans les listes | **Corrigé** : la décision S61 (une estimation n'exclut jamais) a laissé passer des comptes de 25 M$ à plus de 1 G$. Limite ferme à 25 M$ vers le haut (D37), et section « Contrôle de taille » dans le diagnostic. |
| E12 estimation du CA des TPE | **Fait** (D43, S68) : estimation par calcul (`references/revenue-estimate-agent.md`, `scripts/revenue_estimate.py`) à partir d'indices sourcés et de références de Statistique Canada ; confiance basse ou moyenne ; une estimation de confiance basse plafonne le match à « possible » et n'exclut jamais ; revue humaine obligatoire. 11 comptes estimés, 2 sans estimation (indices insuffisants ou fourchette trop large). |
| E13 type d'organisation de la plateforme | **Ouvert** (réponse d'Elizabeth, 2026-10-20) : la plateforme de l'événement affiche une étiquette de type (par exemple « Détaillant.e ») sur chaque profil, mais elle **n'est pas exportable**. Elle ne sert qu'à la saisie manuelle des cas utiles (comme Statera, D41) ; à redemander à l'organisateur comme colonne de l'export. |
| E4 effectifs | **Partiellement corrigé** (D44, S69) : export Clay des effectifs par LinkedIn. À retenir : le compteur de Clay est souvent la borne basse de la fourchette (2 pour 2-10, 11 pour 11-50, 51 pour 51-200) ; plusieurs pages LinkedIn trouvées étaient de la mauvaise entreprise (Rachel : 85 personnes d'une autre page ; Bôsapin : page de Treasy Trees) ; le CA « IA » de Clay a été ignoré. |
| E7 sites inaccessibles, E8 comptes en double, E10 noms commerciaux | **Ouverts**. |

Après l'estimation du CA (D43) : 3 forts et 13 possibles pour Desjardins, les forts étant ceux dont l'estimation vient d'un fournisseur approuvé.

Résultat sur la même liste de pistes (état du 2026-10-20 en milieu de journée) : 0 fort et 2 possibles avant, 4 forts et 15 possibles après (dont un doublon de compte pour une même personne, E8).
