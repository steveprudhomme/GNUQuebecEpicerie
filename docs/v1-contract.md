# Contrat de données V1

Version du format : `1.0`. Ce contrat est fixé avant la première collecte réelle.
La version du logiciel reste distincte (`0.1.0`). Le bootstrap n'avait aucune archive
de collecte : ses schémas provisoires sont remplacés sans migration de données.

## Promotions

`schema/flyer.schema.json` décrit une observation de circulaire pour un seul magasin.
Chaque offre suit `schema/offer.schema.json`. `examples/flyer.v1.json` contient sept
cas fictifs et ne doit jamais être ajouté aux archives réelles.

| Cas | Champs et signification |
| --- | --- |
| Prix simple | `sale_price`, prix annoncé pour `price_basis` |
| Multi-achat | `multi_buy_quantity` et `multi_buy_price`, prix total obligatoire du lot |
| Prix membre | `loyalty_required: true` et nom obligatoire dans `loyalty_program` |
| Points | `points`, nombre positif; seuil d'achat conservé dans `conditions` |
| Pourcentage | `discount_percent`, de plus de 0 à 100; prix inconnu laissé absent |
| Prix au poids | `price_basis: lb` ou `kg`; conversions dans `unit_prices` |
| Quantité limitée | `limit_quantity`; `price_after_limit` exige cette limite |

Une promotion doit comporter au moins un prix, un multi-achat, des points ou un
pourcentage. Les prix réguliers et après limite utilisent la même base que le prix
promotionnel. `package` désigne le format annoncé, `unit` une unité vendue.
Les autres bases admises sont `kg`, `lb`, `100g`, `l`, `100ml`.
Une donnée absente ou `null` signifie inconnue, jamais zéro.
Un multi-achat ne permet pas de présumer un prix à l'unité achetée séparément.

Les montants sont des nombres JSON en CAD. Les collecteurs devront calculer avec
`Decimal` à partir du texte source avant sérialisation : prix annoncés conservés à
leur précision d'origine, prix unitaires dérivés arrondis à 6 décimales au maximum
(arrondi commercial). La conversion d'une livre utilise exactement 0,45359237 kg.
Le prix publié est conservé tel quel; aucune taxe ni consigne n'est ajoutée ou retirée.
Les conditions originales précisent coupons, taxes et consignes lorsqu'elles sont affichées.

`quantity` exprime le contenu du produit en `g`, `kg`, `ml`, `l` ou `unit`.
Il ne désigne pas le nombre d'articles imposé par un multi-achat.
Pour un format ambigu ou un assortiment, laisser la quantité inconnue et préserver
le libellé original. Les offres « achetez X, obtenez Y » sans prix exploitable sont
conservées dans les observations brutes locales et signalées pour révision, sans
inventer de prix ni les publier comme promotions normalisées.

`raw_name` et `source_text` préservent le texte source. Les URL sont publiques et
ne contiennent ni jeton ni identifiant de session. Les horodatages portent un fuseau;
les dates de validité sont inclusives et locales au magasin (`America/Toronto`).
La date de début doit précéder la fin. Les `offer_id` sont uniques dans une circulaire.
Les identifiants de produits de l'enseigne sont des chaînes opaques; aucun
rapprochement automatique entre enseignes n'est imposé par V1.

## Identité et archives

Chemin définitif :

```text
data/<année>/<enseigne>/<store_id>/<valid_from>/<révision>/
  flyer.json
  manifest.json
```

`révision` est le SHA-256 complet du contenu métier normalisé (64 caractères hexadécimaux).
Normaliser d'abord le document avec `Flyer.model_validate(...).model_dump(mode="json")`
pour matérialiser les valeurs par défaut. Le document utilisé pour ce calcul contient
`schema_version`, `retailer_id`, `store_id`,
`valid_from`, `valid_to` et `offers`. Retirer `source.retrieved_at` des offres, trier
les offres par `offer_id`, trier les clés JSON et sérialiser en UTF-8 avec
`ensure_ascii=False`, `separators=(",", ":")`, `allow_nan=False`, sans saut de ligne.
Les autres tableaux conservent leur ordre. `flyer_id` vaut
`<store_id>:<valid_from>:<révision>`. Un `offer_id` provient de l'identifiant de l'offre
source, ou, à défaut, du SHA-256 du produit, de la promotion et de la source sans
horodatage, selon la même sérialisation canonique. Ce n'est pas un identifiant produit.

Le manifeste conserve `flyer_id`, `content_hash` (`sha256:<révision>`), `source_hash`
(SHA-256 des octets exacts de l'entrée du parseur), `collector_version`, les URL,
les dates, le magasin et le nombre d'offres. Pour plusieurs réponses, l'entrée du
parseur est leur concaténation ordonnée par URL, chaque réponse précédée de sa
longueur sur 8 octets non signés big-endian; conserver cette entrée localement.
Les données du manifeste doivent correspondre à `flyer.json`.

Même contenu = même révision, aucun écrasement et aucun commit supplémentaire.
Une correction crée une nouvelle révision, les anciennes restent disponibles.
Une nouvelle heure de consultation ne constitue pas un changement métier.
Une circulaire vide peut être représentée, mais sa publication automatique est
interdite; les futures collectes devront aussi contrôler les chutes de volume.

## Magasins de référence

Le registre versionné est `config/stores.yaml`, validé par `schema/stores.schema.json`.
Il contient les deux magasins choisis, leurs adresses, fuseau et langue.
Les identifiants internes sont stables, indépendants des plateformes des enseignes.
`source_store_id: null` signifie que le sélecteur technique n'a pas encore été vérifié.
`enabled: false` interdit l'activation avant cette vérification; cela ne remet pas
en question le choix du magasin. Ne jamais remplacer silencieusement un magasin.

Mise à jour du 20 septembre 2026 : l'identifiant du lecteur Super C est confirmé
à `447` (distinct de `653` dans le sélecteur du site). Voir
[l'analyse locale](superc-source-analysis.md). Super C reste désactivé tant que
la normalisation et les contrôles de collecte ne sont pas implémentés; IGA reste à analyser.

- Super C : 1000, boulevard des Laurentides, Laval, QC H7G 2W1.
  Source : [localisateur officiel](https://www.superc.ca/trouver-une-epicerie).
- IGA : 307, boulevard Cartier Ouest, Laval, QC H7N 2J1.
  Source : [fiche officielle IGA](https://emplois.iga.net/emplois/detail/133653).

Adresses consultées le 20 septembre 2026. Les sources attestent les adresses,
pas les identifiants techniques de collecte.

## Structure et évolution

`src/` contient le logiciel; `schema/` le contrat; `config/` les magasins et paramètres;
`examples/` des données fictives; `tests/` les contrôles; `docs/` les décisions;
`data/` les archives réelles. SQLite, réponses brutes, caches et secrets restent sous
`local/` ou dans les chemins ignorés. Aucun identifiant de connexion dans Git.

Les schémas V1 et les exemples sont vérifiés en CI. Toute modification incompatible
exige un nouveau numéro de format et un schéma distinct; ne pas réinterpréter les
archives existantes. JSON Schema vérifie les types et conditions structurelles;
la validation applicative vérifie les périodes et doublons. Le futur orchestrateur
devra vérifier les correspondances manifeste/circulaire/registre et la complétude
avant de publier. Les collecteurs réseau ne sont pas implémentés dans cette étape.
