# Archives de données

Ce dossier contient les observations versionnées.

## Chemin canonique

```text
data/<année>/<retailer_id>/<valid_from>/flyer.json
data/<année>/<retailer_id>/<valid_from>/manifest.json
```

Exemple :

```text
data/2026/superc/2026-09-24/flyer.json
data/2026/superc/2026-09-24/manifest.json
```

## Immutabilité

Une collecte publiée ne doit pas être réécrite pour intégrer silencieusement des données plus récentes. Une correction doit faire l'objet d'un commit explicite afin que l'historique reste auditable.

## Données dérivées

La base SQLite locale n'est pas versionnée. Elle doit pouvoir être reconstruite à partir des JSON du dépôt.
