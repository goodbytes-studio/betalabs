# Registre des titres de décideur

Décision D32 (source S57). Le moteur (`event_machine/core.py`, constantes `OWNER_TERMS`, `LEAD_TERMS`, `NOT_PRINCIPAL_TERMS`) compare les titres après normalisation : accents, majuscules, traits d'union et ponctuation disparaissent. « Co-propriétaire », « co propriétaire » et « Copropriétaire » sont donc équivalents, tout comme « P.-D.G. » et « PDG ».

## Reconnus comme décideur (niveau `executive`)

| Famille | Variantes reconnues |
|---|---|
| Propriété | propriétaire, propriétaire-exploitant, co-propriétaire, copropriétaire, chef propriétaire, owner, co-owner, coowner, joint owner, proprietor |
| Actionnariat | actionnaire, actionnaire principal, co-actionnaire, shareholder |
| Fondation | fondateur, fondatrice, fondateur·trice, co-fondateur, co-fondatrice, cofondateur, cofondatrice, founder, co-founder, cofounder |
| Présidence | président, présidente, président(e), co-président, copresident, président du conseil, chairman, chairwoman |
| Direction générale | PDG, P.-D.G., président-directeur général, présidente-directrice générale, CEO, co-CEO, chief executive officer, chef de la direction, directeur général, directrice générale, DG, general manager, managing director |
| Associés et dirigeants | associé, associée, managing partner, dirigeant, dirigeante, chef d'entreprise, entrepreneur, entrepreneure, entrepreneuse |

## Règles

| Règle | Exemple |
|---|---|
| Une propriété l'emporte sur un titre de vice-président. | « Vice président – Propriétaire » est un décideur. |
| Un titre de présidence ou de direction générale ne compte pas si le titre est aussi celui d'un vice-président. | « Vice-président marketing » reste `vp_clevel`. |
| Adjoint, assistant, deputy, ancien, former, past, ex : pas un décideur final. | « Directrice générale adjointe », « Assistant du président », « Ancien président ». |
| « Product Owner » est un rôle produit. | Pas un propriétaire. |

## Ambigus : jamais classés décideur sans validation

| Titre | Pourquoi |
|---|---|
| gérant, gérante, gestionnaire de magasin | Souvent un employé, pas le propriétaire. |
| franchisé | Peut être propriétaire de sa franchise ; à valider avec la règle des franchises (D31). |
| Partner, partenaire (seul) | Peut être un associé comme un partenaire d'affaires ; « Business Partner » est un rôle RH. |
| président d'une association, d'une division, d'une fondation | Pas le propriétaire de l'entreprise ; à valider selon le cas. |
| membre du CA, administrateur | Pas un propriétaire par défaut. |
| entrepreneur dans un titre de conseil (« accompagnateur et entrepreneur ») | Peut décrire un consultant ; le type d'organisation tranche. |

## Titre vide ou non reconnu

Un titre vide ou non reconnu reste `unknown` : le match devient « à confirmer », jamais « fort ». Ajouter une variante manquante se fait dans les constantes ci-dessus avec un test dans `tests/test_event_machine.py`, puis ici.
