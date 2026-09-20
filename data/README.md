# Archives de données

Ce dossier contient les observations versionnées.

## Chemin canonique

```text
data/<année>/<retailer_id>/<store_id>/<valid_from>/<révision>/flyer.json
data/<année>/<retailer_id>/<store_id>/<valid_from>/<révision>/manifest.json
```

Exemple :

```text
data/2026/superc/superc-laval-des-laurentides-1000/2026-09-24/<révision>/flyer.json
data/2026/superc/superc-laval-des-laurentides-1000/2026-09-24/<révision>/manifest.json
```

## Immutabilité

Une collecte publiée ne doit pas être réécrite pour intégrer silencieusement des données plus récentes. Une correction crée un nouveau dossier de révision et un commit explicite. La révision est le SHA-256 du contenu métier défini dans [le contrat V1](../docs/v1-contract.md).

## Données dérivées

La base SQLite locale n'est pas versionnée. Elle doit pouvoir être reconstruite à partir des JSON du dépôt.
