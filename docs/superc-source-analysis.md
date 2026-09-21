# Analyse locale de la source Super C

Analyse effectuée le 20 septembre 2026 depuis le poste Windows du propriétaire,
avec Python/httpx. Aucun travail distant GitHub Actions n'a été utilisé pour la
collecte exploratoire. Les réponses brutes restent sous `local/source-analysis/`,
ignoré par Git. Ce rapport décrit une observation ponctuelle, pas une API garantie.

## Conclusion

La circulaire possède des données JSON structurées : l'OCR n'est pas nécessaire
pour l'échantillon examiné. Le magasin de référence a été identifié sans connexion
à un compte. Son identifiant dans le lecteur est **447**. La normalisation complète
reste à implémenter et les collecteurs restent désactivés.

## Identité vérifiée

| Élément | Valeur observée |
| --- | --- |
| Magasin interne | `superc-laval-des-laurentides-1000` |
| Adresse | 1000, boulevard des Laurentides, Laval, QC H7G 2W1 |
| Nom dans le lecteur | `LAVAL DES LAURENTIDES` |
| Identifiant dans le sélecteur du site | `653` |
| Identifiant dans le lecteur de circulaires | `447` |
| Langue de l'API pour le français | `bil` |

Le [sélecteur officiel](https://www.superc.ca/trouver-magasin) fournit le nom,
l'adresse et les coordonnées de la succursale. Le service de magasins utilisé par
le lecteur associe ces mêmes adresse et code postal au numéro 447. Les métadonnées
de circulaire retournent ensuite le nom `LAVAL DES LAURENTIDES`.
Une requête avec 653 retourne 404 : les deux espaces d'identifiants sont distincts.
Le futur collecteur ne doit ni deviner un numéro ni se rabattre sur le magasin par défaut.

## Parcours observé

1. [Page officielle de circulaire](https://www.superc.ca/circulaire) : HTTP 200.
   Sans sélection explicite, elle désigne Ste-Thérèse, identifiant lecteur 465.
2. Le script `flyer.js`, lié par cette page, construit une iframe sur
   `https://circulaire.superc.ca/`, avec `storeId` et `language`.
3. Le lecteur charge `/config/app.json` et son application JavaScript publique.
   La configuration expose l'adresse API, sa version et les en-têtes utilisés
   normalement par le client. Les valeurs de clés ne sont pas versionnées.
4. L'API observée est `https://metrodigital-apim.azure-api.net/api/` (version 3.0).
   `GET flyers/447/bil?date=2026-09-20` retourne les publications de ce magasin.
   `GET pages/<title>/447/bil/` retourne les pages et leurs blocs produit.

Le localisateur `/trouver-une-epicerie` a renvoyé HTTP 403; il n'a pas été forcé.
Le sélecteur `/trouver-magasin`, directement lié par la page de circulaire, était
accessible normalement. Le lecteur renvoie du HTML pour `/robots.txt` : un statut
200 ne suffit donc pas à identifier un fichier robots valide.

Le [robots.txt du site](https://www.superc.ca/robots.txt) contient notamment des
restrictions de recherche, de pagination et de paramètres. Le diagnostic utilise
quelques lectures ciblées, sans balayage ni contournement de CAPTCHA. Les
[conditions publiées](https://www.superc.ca/conditions-utilisation) limitent l'usage
du contenu; cette analyse technique ne conclut pas à un droit de redistribuer une
circulaire entière. Aucun HTML, JavaScript tiers, image ou catalogue brut n'est publié.

## Échantillon du magasin de référence

Publication `83817`, valide du **17 au 23 septembre 2026** :

| Mesure | Observation |
| --- | ---: |
| Pages | 21 |
| Entrées dans les tableaux `products`, blocs imbriqués inclus | 331 |
| SKU distincts | 318 |
| Entrées avec `memberPriceFr` renseigné | 27 |
| Entrées avec `priceQuantity` renseigné | 10 |
| Types d'action | 319 `Product`, 9 `URL`, 3 `Inblock` |

Ces nombres ne sont **pas** un nombre de promotions normalisées : certains blocs
sont des liens ou du contenu embarqué; les répétitions doivent être examinées.
`productBlockId` n'est pas une clé unique (229 valeurs distinctes dans l'échantillon).
Les prix sont généralement des chaînes; `pts: 0` signifie absence de points ici,
et doit devenir `null` dans notre modèle plutôt qu'une promotion de zéro point.

## Correspondance à implémenter et tester

| Source | Destination V1 / traitement |
| --- | --- |
| `productFr`, `bodyFr` | Nom original et texte source; nettoyer le HTML sans perdre les conditions |
| `sku`, `upc` | Chaînes opaques; ne pas dédupliquer uniquement sur le SKU |
| `productBrands`, `brandDescriptionFr` | Marque éventuelle; `brand` est un booléen, pas un nom |
| `salePriceFr`, `regularPriceFr` | Prix décimaux; prévoir le repli explicite vers les champs non suffixés |
| `priceQuantity` | Examiner le prix du lot et ses conditions avant de créer un multi-achat |
| `promoUnitFr`, `alternatePriceFr` | Distinguer `/lb`, contenu approximatif et prix à la caisse |
| `memberPriceFr`, `memberPriceQuantity` | Conserver séparément prix public et prix membre |
| `pts`, `loyalty*` | Points et programme, sans convertir les points en argent |
| `limitQty`, `afterLimitPrice` | Limite et prix après limite; non présents dans cet échantillon |
| `validFrom`, `validTo`, `validFromROW`, `validToROW` | Détecter les exceptions de période par offre |

Les métadonnées globales utilisent minuit UTC pour le début, tandis que les entrées
produit utilisent 04:00 UTC. Il faut traiter les dates commerciales de la circulaire
comme des dates, sans convertir aveuglément minuit UTC en date de la veille à Laval.
Dans cet échantillon, toutes les périodes produit couvrent les mêmes journées;
les champs `ROW` sont nuls. Toute exception future doit être mise en révision plutôt
que silencieusement forcée dans une période globale.

V1 ne contient qu'un prix par objet `Promotion` : produire deux offres liées au même
produit pour les prix public et membre, avec des identifiants d'offre distincts.
Les cas ambigus sont conservés localement et signalés; ne jamais les transformer
en prix simple par défaut. Aucun mapping de prix n'est déclaré validé par ce diagnostic.

## Reproduire sur le PC

Depuis la racine du dépôt, après installation de `.[dev]` :

```powershell
python -m gnuquebecepicerie.analysis.superc --date 2026-09-20
```

Le diagnostic charge la configuration publique en mémoire, vérifie le nom du magasin,
espace les requêtes de deux secondes et écrit les métadonnées, pages et un résumé
dans un nouveau sous-dossier local horodaté. Il n'effectue aucun commit ni push.
Il s'arrête sur erreur HTTP, magasin inattendu ou changement de l'adresse API;
aucune nouvelle clé n'est enregistrée. Les tests utilisent des réponses fictives.

## Prochaine étape

Implémenter le normaliseur Super C sur des fixtures fictives couvrant prix public,
prix membre, lots et poids; effectuer ensuite une collecte locale complète avec
rapport des rejets et vérification manuelle. L'activation et la publication de données
réelles exigent des contrôles de complétude, de magasin et de période. Ce commit publie
le rapport, le diagnostic et les tests, pas un collecteur de promotions terminé.

Étape suivante réalisée : [normaliseur hors ligne et bilan des rejets](superc-normalization.md).
