# Modèle de données

## Flyer

Une circulaire (`Flyer`) représente une collecte pour un magasin et une période de validité.

Champs principaux :

- `schema_version`
- `flyer_id`
- `retailer_id`
- `store_id`
- `published_at`
- `valid_from`
- `valid_to`
- `retrieved_at`
- `source_urls`
- `offers`

## Offer

Une offre conserve trois couches conceptuelles.

### Produit

- `raw_name` : texte tel qu'observé;
- `name` : nom normalisé;
- `brand`, `variant`, `sku`, `upc`;
- `quantity` : quantité et unité;
- `category` : classification optionnelle.

### Promotion

- `sale_price`, `regular_price`;
- `multi_buy_quantity`, `multi_buy_price`;
- `loyalty_required`, `loyalty_program`;
- `points`;
- `limit_quantity`, `price_after_limit`;
- `unit_prices`;
- `conditions`.

### Source

- `url`;
- `source_text`;
- `retrieved_at`.

## Identité des produits

La première collecte ne doit pas tenter de fusionner agressivement les produits entre enseignes. Le rapprochement vers un futur `canonical_product_id` sera une étape distincte afin de préserver les observations originales.
