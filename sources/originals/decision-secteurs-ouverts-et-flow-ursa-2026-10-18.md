# Décision — Secteurs ouverts, fourchettes de CA et règles de sélection HOP 2026

- Date : 2026-10-18 (America/Toronto)
- Décideuse : Elizabeth (BETA Labs)
- Contexte : machine événements, HOP 2026 ; réévaluation des entreprises classées « autre » ou exclues pour un secteur flou.
- Forme : décisions données en conversation de travail avec l'assistant, retranscrites sans modification de sens.

## Décisions

1. Mirego accepte les secteurs « autre » (Mirego n'exclut que cpg, pharmacy et insurance).
2. Créneaux rattachés à un secteur existant : piscines et spas, sapins de Noël, tissus → maison (`furniture_home`) ; passe-temps → sport et plein air. De nouveaux secteurs peuvent être créés (`footwear`, `jewelry`, `pets`, `optical`, `cannabis`, `convenience`). « Si une entreprise est un bon fit sur les autres critères, et que le secteur seul n'est pas évident, je peux valider. Mais elle ne devrait pas être exclue direct. » Les listes de secteurs d'Ursa et de Studio Réverbère deviennent ouvertes (`sectors_allow_strict: false`) : un secteur hors liste est « à valider », pas exclu. Les exclusions explicites restent.
3. Studio Réverbère : « pour l'instant, pas de ready-to-wear » (`fashion` exclu). À revoir avec le client au besoin.
4. Les marques qui vendent en direct sur leur site comptent comme détaillants.
5. Une fourchette de CA estimée ne doit pas être une exclusion absolue (exemple : Mondou, estimé à environ 100 M$ par une première recherche d'Elizabeth). Elle n'exclut que si elle est à plus de 3 fois le seuil (`revenue_estimate_hard_factor: 3`) ; sinon le match est « à valider » et l'entreprise passe par Clay.
6. « Un prospect peut aller à plus d'un client. Lorsque possible, on essaie d'éviter de donner un prospect à trop de clients, mais si c'est un top match, on le donne à plusieurs. »
7. Ursa : trois contacts (Oberson, Joelle Collection, Club Tissus) confirmés par Elizabeth comme dirigeants de ces entreprises. Altitude Sports, Buro Pro Citation, Signé Sarah et Rachel entrent dans le flow d'analyse d'Ursa. Cible : 20 prospects pour Ursa, 15 pour Mirego et Studio Réverbère.

## Correction associée

Les titres « Chief Executive Officer », « Présidente », « Cofounder », « Fondatrice » sont reconnus comme direction générale ; auparavant ils restaient « fonction du poste à confirmer ».
