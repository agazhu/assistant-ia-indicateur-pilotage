# Piloter la diffusion de l'Assistant IA au ministère de l'Éducation nationale

*Cas pratique, candidature au poste de cheffe de projet IA et transformation numérique (DNE). Octobre 2026.*

## Contexte et constat

L'Assistant, chatbot interministériel souverain, a été généralisé à tous les agents de l'État en juin 2026. La feuille de route IA 2026-2027 en fait un pilier de la transformation de l'administration, avec une cible de 100 000 personnels administratifs. Le pilotage repose aujourd'hui sur le tableau de suivi trimestriel de la stratégie du numérique pour l'éducation (objectif 36, avancement déclaré de 15 %). Or le ministère publie chaque jour, en données ouvertes, le nombre d'utilisateurs et de messages par domaine de messagerie : au 1er octobre 2026, 18 859 agents ont utilisé l'Assistant et envoyé 415 798 messages. La proposition consiste à transformer cette donnée quotidienne en un indicateur de pilotage territorial, calculé automatiquement.

## Fiche indicateur

**Intitulé.** Taux de pénétration de l'Assistant IA dans les académies.

**Définition.** Part des personnels d'une académie ayant utilisé au moins une fois l'Assistant avec leur adresse académique. Deux lectures complètent l'indicateur : la vitalité de l'usage et l'atteinte de la cible ministérielle.

**Formules.**
- Pénétration (a, t) = utilisateurs cumulés de l'académie a au jour t / effectif des personnels en activité de l'académie a.
- Vitalité (a, t) = messages envoyés sur 28 jours / utilisateurs cumulés de l'académie.
- Atteinte de la cible (t) = utilisateurs du périmètre ministériel (académies, régions académiques, administration centrale, IGÉSR) / 100 000.

**Valeurs au 1er octobre 2026.**

| Mesure | Valeur |
|---|---|
| Pénétration nationale | 1,44 % (17 524 / 1 218 110) |
| Atteinte de la cible | 17,5 %, en ordre de grandeur |
| Vitalité, médiane des 30 académies | 4,8 messages par utilisateur sur 28 jours |
| Vitalité, étendue | de 0,65 (Toulouse) à 7,8 (La Réunion) |
| Croissance des utilisateurs sur 28 jours | de +6 % à +93 %, médiane +47 % |

[À COMPLÉTER : pénétration par académie, dès intégration de la table des effectifs de la DEPP.]

**Sources.**
- data.education.gouv.fr : jeu « Déploiement de l'Assistant » (compteurs quotidiens) et jeu « Déploiement en académie » (ventilation par profil).
- DEPP, Panorama statistique des personnels 2024-2025 (effectifs au 30 novembre 2024).
- Feuille de route IA 2026-2027, pour la cible.

**Fréquence.** Calcul quotidien automatisé, revue mensuelle au comité des ambassadeurs de l'IA, synthèse trimestrielle au comité ministériel de l'IA.

**Seuils.**
- **Alerte** : pénétration inférieure à 50 % de la médiane nationale. Ce seuil est relatif, faute de cible académique publiée.
- **Vigilance** : vitalité inférieure à 50 % de la médiane (2,4 au 1er octobre), hors vacances scolaires. Une académie est concernée : Toulouse.
- **Contrôle de qualité** : compteurs inchangés pendant sept jours hors vacances, signe d'une anomalie de collecte probable. Exemple : Toulouse, du 3 au 18 septembre.
- **Pas de seuil haut sur le volume de messages**, conformément au principe de frugalité du cadre d'usage de l'IA en éducation.

**Limites.**
1. L'indicateur mesure la diffusion, pas la fidélisation. Environ la moitié des messages proviennent d'agents déjà inscrits, mais cette estimation statistique est fragile.
2. La cible porte sur les personnels administratifs, alors que la généralisation et les données couvrent tous les profils (35 % d'enseignants dans le jeu par profil).
3. Le dénominateur date de 2024 et inclut les AED et AESH, dont l'accès effectif n'est pas vérifié.
4. Le rattachement se fait par domaine de messagerie ; 320 utilisateurs ne sont pas identifiés.
5. La saisonnalité est forte : environ 150 nouveaux utilisateurs par semaine à la mi-août, de 1 150 à 1 450 depuis septembre.
6. Le jeu par profil n'est pas daté et sa population n'est pas documentée.

## Trois recommandations de mise en œuvre

**1. Cibler la formation sur les académies en alerte.**
*Lien stratégique : plan de formation de la feuille de route, objectif 18 de la stratégie (formations à l'IA pour tous les agents d'ici 2027, avancement de 5 %).*
Orienter en priorité le Lab IA et les agents-relais vers les académies sous les seuils. Faire revoir chaque mois les écarts par le comité des ambassadeurs, qui en apporte l'explication de terrain. Suivre l'évolution de la pénétration de l'académie concernée dans les huit semaines suivant les actions engagées.

**2. Fiabiliser et enrichir la donnée avec la DINUM.**
*Lien stratégique : action 2 de la stratégie, « Partager des indicateurs à des fins de pilotage et d'évaluation ».*
Demander la publication, par domaine de messagerie, des utilisateurs actifs sur 7 et 30 jours (données agrégées, sans enjeu au regard du RGPD), la datation du jeu par profil et la documentation des règles de rattachement. Le prototype est prêt à calculer un taux de fidélisation dès la publication de ces données. Faire arbitrer par le comité ministériel la population de référence : personnels administratifs ou ensemble des agents.

**3. Intégrer l'indicateur au pilotage existant.**
*Lien stratégique : objectifs 3 et 4 de la stratégie, tableau de suivi et tableau de bord du numérique éducatif.*
Alimenter automatiquement le tableau de suivi trimestriel de la stratégie (objectif 36). Proposer l'indicateur au tableau de bord du numérique éducatif, à la maille académique. Publier la chaîne d'alimentation sur la Forge des communs numériques éducatifs, pour qu'elle puisse être réutilisée pour d'autres services, comme les fonctions IA de la messagerie.

## Prototype

Une tâche GitHub Actions interroge chaque jour l'API de data.education.gouv.fr, historise le jeu par profil (publié sans date), calcule l'indicateur et les seuils, puis met à jour une page de tableau de bord publiée sur GitHub Pages. Un workflow n8n équivalent est fourni comme voie d'industrialisation. La page n'utilise pas le Système de design de l'État, réservé aux sites de l'État ; une version en production l'adopterait. Le détail figure dans le fichier README du dépôt.

## Usage de l'IA générative

**Outil.** Claude (Anthropic). L'Assistant souverain, prioritaire au titre du cadre d'usage, n'est pas accessible à une candidate extérieure au ministère.
**Étapes concernées.** Synthèse des documents stratégiques ; exploration des données au moyen de scripts Python exécutés et dont les résultats ont été contrôlés ; aide à la rédaction et au code.
**Conformité au cadre d'usage.** Seules des données publiques ont été traitées. Les chiffres ont été recalculés et les sources recoupées. Les choix méthodologiques et les recommandations relèvent de mon analyse.
