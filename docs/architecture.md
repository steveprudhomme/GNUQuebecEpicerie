# Architecture

GNUQuebecEpicerie sépare volontairement la collecte, la normalisation, la validation et l'archivage.

```text
source officielle
      |
      v
  Collector
      |
      v
observation brute
      |
      v
 Normalizer
      |
      v
 modèle commun
      |
      v
 Validator
    /     \
   v       v
 JSON     SQLite local
   |
   v
 Git
```

## Collecteurs

Chaque enseigne possède son propre collecteur sous `src/gnuquebecepicerie/collectors/`. Le collecteur est responsable de transformer une source spécifique en modèle commun, sans imposer sa structure aux autres enseignes.

## Normalisation

La normalisation conserve autant que possible le texte original (`raw_name`, `source_text`) et ajoute des champs structurés (`brand`, `quantity`, `sale_price`, etc.).

## Validation

Avant archivage, les données doivent :

- respecter le JSON Schema;
- avoir une période de validité cohérente;
- contenir un magasin et une enseigne connus;
- avoir des prix positifs lorsqu'un prix est présent;
- ne pas présenter une chute anormale du nombre d'offres sans avertissement.

## Stockage

Les JSON constituent l'archive maîtresse. SQLite est une représentation locale optimisée pour les requêtes et peut être régénérée.
