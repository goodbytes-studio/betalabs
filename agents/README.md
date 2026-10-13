# Les agents BETA Labs

Deux rôles réutilisables, fournis comme **skills locaux pour Codex** et comme prompts portables. Ils partagent la mémoire dans [brand/](../brand/README.md), les synthèses GTM et le registre de claims. Ils ne sont pas des services autonomes déployés ; ils s’exécutent dans une session d’assistant disposant du dépôt et des outils nécessaires.

| Agent | Définition | Skill local | Responsabilité |
|---|---|---|---|
| BETA Labs Designer | [Prompt](designer.md) | [SKILL.md](../.agents/skills/betalabs-designer/SKILL.md) | Direction artistique, systèmes, prototypes, composants et évolution de marque |
| BETA Labs Strategic Copywriter | [Prompt](copywriter.md) | [SKILL.md](../.agents/skills/betalabs-copywriter/SKILL.md) | Stratégie du message, offres, persuasion, architecture des pages et expérience de conversion |

Les skills sont placés dans `.agents/skills/` pour leur découverte par les sessions Codex qui chargent les skills du dépôt. Si la session ne les liste pas encore, rouvrir le dépôt ou demander explicitement de lire le SKILL.md indiqué. L’installation globale d’un agent ou l’activation d’un connecteur n’est pas revendiquée.

## Exemples d’appel

```text
$betalabs-designer
Crée un one-pager organisateur FR pour notre prochaine édition.
Pars de la marque documentée et propose une version de continuité,
puis une évolution qui rend le ciblage plus tangible.
Livre une maquette, les tokens utilisés et le passage de relais au copywriter.
```

```text
$betalabs-copywriter
Écris une landing page sponsor pour une firme B2B de 60 personnes
qui prépare un événement dans six semaines.
Le décideur pense que son équipe pourrait faire la préparation elle-même.
Livre l’angle recommandé, la page FR, la version EN et un plan de test.
Ne présume ni inscription d’un prospect réel ni tarif non confirmé.
```

Sans entrée précise, l’agent choisit un cas de travail explicite : commanditaire B2B de services à forte valeur, décideur direct, FR-CA, préparation d’un événement confirmé. Il avance avec des hypothèses marquées plutôt que bloquer le travail créatif. Une donnée nécessaire à la véracité d’une offre reste un champ à confirmer.

## Travail coordonné

Brief commercial → stratégie de message → structure et copy → concept visuel → relecture croisée → livrable. Le designer peut initier une exploration, puis demander au copywriter de justifier chaque section par une croyance ou une objection du lecteur.

Le [contrat de relais](handoff-template.md) rend les échanges concrets. Les deux agents partagent le même état de preuve ; un titre très convaincant ne change pas un claim en attente.

Une [démonstration coordonnée](../brand/prototypes/brand-direction-v1/brief.md) montre le processus sur une proposition sponsor/organisateur. Elle est fondée sur les documents ; elle ne prétend pas reproduire le site actuel.

Le designer v2 dispose d’une [bibliothèque Open Design](learning/open-design/README.md) et d’un [playbook d’adaptation](learning/designer-playbook.md). Le [brand guide](../brand/guide/README.md) applique ces méthodes au logo fourni et à une famille de supports. [BYQ](learning/BYQ.md) reste explicitement en attente.
