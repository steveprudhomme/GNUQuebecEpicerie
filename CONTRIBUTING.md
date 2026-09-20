# Contribuer à GNUQuebecEpicerie

Merci de contribuer au projet.

## Principes

1. Ne jamais écraser silencieusement une observation historique publiée.
2. Préserver les champs bruts provenant de la source lorsque ceux-ci sont disponibles.
3. Toute donnée normalisée doit pouvoir être reliée à sa source.
4. Les collecteurs doivent respecter les conditions d'utilisation applicables, les limites raisonnables de requêtes et les mécanismes publics des sites.
5. Ne jamais contourner un mécanisme d'authentification, un CAPTCHA ou une restriction technique.
6. Ajouter ou mettre à jour les tests lorsqu'un comportement change.

## Style des commits

Exemples :

```text
feat(superc): ajouter le collecteur de circulaire
fix(iga): corriger les promotions multi-achats
data(superc): circulaire 2026-09-24 au 2026-09-30
docs: préciser le modèle de données
```

## Données

Les nouveaux jeux de données doivent respecter les schémas JSON du dossier `schema/` avant d'être committés.
