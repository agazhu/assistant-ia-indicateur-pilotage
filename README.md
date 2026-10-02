# Indicateur de pilotage de la diffusion de l'Assistant IA

Prototype réalisé dans le cadre d'une candidature au poste de cheffe de projet IA et transformation numérique (Direction du numérique pour l'éducation). **Il ne s'agit pas d'un outil officiel du ministère.**

- **Note de deux pages** (fiche indicateur et recommandations) : [NOTE.md](NOTE.md)
- **Tableau de bord** : https://agazhu.github.io/assistant-ia-indicateur-pilotage/

## Ce que fait le prototype

Chaque jour, une tâche automatisée :

1. télécharge les deux jeux de données ouverts de data.education.gouv.fr :
   - `fr-en-assistant_ia_deploiement_menjs` : compteurs quotidiens cumulés d'utilisateurs et de messages par domaine de messagerie ;
   - `assistant-ia-dinum-deploiement-au-ministere-de-leducation-nationale-en-academie` : utilisateurs par académie et par profil ;
2. historise le second jeu, publié sans date, dans `data/historique_production/` ;
3. calcule l'indicateur (pénétration, vitalité, atteinte de la cible) et applique les seuils ;
4. écrit `docs/data/indicateur.json`, lu par la page de tableau de bord, et ajoute une ligne à `data/historique_national.csv`.

## Utilisation de l'API

La collecte interroge l'API Explore v2.1 de data.education.gouv.fr :

```
https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/{identifiant}/exports/csv?delimiter=;&use_labels=true&lang=fr
```

Le point d'accès `/exports` renvoie le jeu complet en un seul appel. Le point d'accès `/records` est limité à 100 lignes par appel ; or la série quotidienne en compte déjà 94 et en gagne une par jour, ce qui imposerait une pagination sans bénéfice. En cas d'échec de l'API (trois essais), la tâche s'arrête en erreur plutôt que d'afficher des données périmées. Le journal de chaque exécution, dans l'onglet *Actions*, indique le nombre de lignes reçues de l'API.

## Structure du dépôt

| Chemin | Rôle |
|---|---|
| `pipeline/run.py` | Collecte, historisation, calculs et seuils (version de référence) |
| `.github/workflows/mise-a-jour-quotidienne.yml` | Exécution quotidienne à 5h30 UTC et lancement manuel |
| `docs/index.html` | Page de tableau de bord (GitHub Pages) |
| `docs/data/indicateur.json` | Résultats du dernier calcul |
| `referentiel/config.json` | Effectif national, cible, vacances scolaires neutralisées |
| `referentiel/effectifs_academies.csv` | Effectifs par académie (à renseigner, voir limites) |
| `n8n/workflow-indicateur.json` | Workflow n8n équivalent, version simplifiée |
| `data/` | Copies des sources, instantanés historisés, historique national |

## Méthode

- **Flux.** Les compteurs publiés étant cumulés, les nouveaux utilisateurs et les messages d'une période se calculent par différence entre deux relevés. Les jours sans relevé sont interpolés linéairement et signalés sur la page.
- **Fenêtre de 28 jours.** Elle couvre quatre semaines complètes, ce qui neutralise l'effet des week-ends.
- **Rattachement.** Les colonnes sont identifiées par leur libellé normalisé (sans accents ni ponctuation), ce qui rend le script indépendant du format des en-têtes de l'API.
- **Seuils.**
  - Alerte : pénétration inférieure à 50 % de la médiane nationale.
  - Vigilance : vitalité inférieure à 50 % de la médiane, suspendue si plus de la moitié de la fenêtre tombe en vacances scolaires.
  - Contrôle de qualité : messages inchangés pendant sept jours observés hors vacances.
- **Cohérence.** Les deux versions (Python et n8n) donnent les mêmes valeurs nationales sur les données du 1er octobre 2026 : 17 524 utilisateurs, médiane de vitalité 4,77, seuil 2,38.

## Choix techniques

- **GitHub Actions pour l'exécution.** Aucun serveur à maintenir, historique des exécutions consultable, résultats versionnés dans le dépôt.
- **n8n comme voie d'industrialisation.** Le workflow fourni reproduit le calcul national et la vitalité par académie (sans interpolation des jours manquants) et publie le résultat dans le dépôt. Il n'a pas été exécuté dans une instance n8n : il nécessite un jeton GitHub à configurer.
- **Pas de Système de design de l'État.** Son usage est réservé aux sites de l'État ; une version en production l'adopterait. La page suit néanmoins les bonnes pratiques d'accessibilité : contrastes suffisants, navigation au clavier, alternative textuelle et tableau pour chaque graphique.
- **Aucune bibliothèque JavaScript externe.** Les graphiques sont dessinés en SVG.

## Déploiement

1. Déposer le contenu de l'archive à la racine du dépôt.
2. Dans *Settings > Pages*, choisir la branche `main` et le dossier `/docs`.
3. Dans *Settings > Actions > General*, autoriser les workflows en lecture et écriture.
4. Dans l'onglet *Actions*, lancer manuellement « Mise à jour quotidienne de l'indicateur » et vérifier qu'il se termine sans erreur.

Exécution locale : `pip install -r requirements.txt`, puis `python pipeline/run.py` (ou `--offline` pour utiliser les copies de `data/sources/`, réservé aux tests).

## Limites et points à vérifier

- **Effectifs par académie non renseignés.** La pénétration par académie et le seuil d'alerte s'activeront dès que `referentiel/effectifs_academies.csv` sera complété (au moins 15 académies). Source prévue : DEPP, Panorama statistique des personnels 2024-2025.
- **Dates de vacances à vérifier.** Les dates de `referentiel/config.json` sont à confirmer sur le calendrier scolaire officiel. Seules les vacances communes aux trois zones sont neutralisées.
- **Utilisateurs cumulés.** Les données publiées ne permettent pas de compter les utilisateurs réguliers.
- **Le jeu par profil** n'est pas daté et sa population n'est pas documentée.

## Usage de l'IA générative

Claude (Anthropic) a été utilisé pour la synthèse des documents, l'exploration des données (scripts Python exécutés et résultats contrôlés), ainsi que l'aide à la rédaction et au code. Seules des données publiques ont été traitées, conformément au cadre d'usage de l'IA en éducation.
