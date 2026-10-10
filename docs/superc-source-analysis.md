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
sélectionne uniquement les circulaires couvrant la date demandée (bornes incluses),
espace les requêtes API de deux secondes et écrit les métadonnées, pages et un résumé
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


## Conservation des visuels lors des prochains diagnostics

Le diagnostic conserve désormais par défaut les images de blocs (y compris
les mentions et les carrousels) et les bandeaux référencés dans les pages JSON.
Pour chaque groupe, il choisit la résolution maximale et déduplique les URL.
Les images de produits isolées et un éventuel PDF non référencé ne sont pas
inclus : la complétude du manifeste porte uniquement sur ces visuels référencés.

```powershell
python -m gnuquebecepicerie.analysis.superc --date YYYY-MM-DD
```

Les fichiers restent sous `local/source-analysis/<capture>/assets/<publication>/`.
Le manifeste local enregistre l'URL, l'heure de consultation, le fichier, sa taille
et son empreinte SHA-256. Il indique aussi les échecs. Le nom de fichier est dérivé
de l'URL, sans utiliser de chemin fourni par le serveur. Le diagnostic peut prendre
plusieurs minutes : les images sont téléchargées en série avec une pause de
0,2 seconde entre les requêtes. Les métadonnées brutes conservent aussi les
aperçus retournés par le lecteur, mais leurs pages et images ne sont pas téléchargées.

Seules les URL HTTPS du stockage connu, dans le chemin de la publication demandée,
sont admises. Les redirections ne sont pas suivies; les réponses 403/404 sont des
échecs consignés, sans tentative de contournement. Aucun en-tête de clé API n'est
transmis par le client dédié aux images. Les réponses HTML et les fichiers de plus
de 20 Mio sont rejetés. La signature JPEG/PNG est contrôlée; cela ne remplace pas
une vérification visuelle de lisibilité ni de complétude commerciale.

Une capture vide ou comportant des fichiers manquants n'est pas déclarée complète.
La commande termine avec le code **2** si les visuels sont incomplets, tout en
conservant le diagnostic JSON et le manifeste des échecs. Une erreur des requêtes
API reste bloquante. `--no-assets` permet explicitement un diagnostic JSON seul;
le résumé porte alors `assets.status: not_requested`.

Les anciens diagnostics ne sont pas complétés automatiquement. Cette évolution
ne récupère pas les mentions historiques bloquées de 83817. La validation
commerciale et la publication automatique restent désactivées. Le normaliseur
continue d'utiliser ses entrées JSON vérifiées; il n'interprète pas encore ces
images et ne considère jamais leur téléchargement comme une validation.

Validation de cette évolution : tests hors ligne avec serveur simulé, incluant
les doublons, les mentions imbriquées, les redirections, les erreurs, les URL hors
publication, les contenus non-images et les limites de taille. Les tests de période
couvrent les bornes incluses, les aperçus futurs, les publications expirées et
l’absence de circulaire applicable.


## Vérification réelle du 6 octobre 2026

Capture locale `20261006T045222888814Z`, publication **83986**, du **1er au 7 octobre** :

- 20 pages JSON, 356 entrées source et 341 SKU distincts.
- **277 visuels référencés sur 277 conservés**, sans échec; toutes les empreintes
  SHA-256 ont été recalculées et correspondent au manifeste.
- Le bloc `288_NB-9_Ad_Metro_p23_LEGAL_FR_NAT.jpg` a été ouvert : les mentions
  générales et la période sont lisibles. Ce contrôle ne couvre pas encore chaque
  astérisque de chaque offre ni les conditions externes du programme de fidélité.
- Les aperçus 83987 et 83987m du 8 au 14 octobre sont exclus de la collecte du 6.

Le normaliseur 0.5.1 produit **286 offres** à partir de 285 entrées acceptées;
**60 entrées sont rejetées** et 11 blocs non commerciaux sont ignorés. Motifs :
50 `coupon_requires_review`, 6 `missing_price_or_supported_reward` et
4 `discount_amount_requires_review`. Aucune correction historique de 83817
n'a été appliquée. `ready_for_archive` reste faux.

Examen des 50 indicateurs coupon réalisé : 23 entrées converties, 27 maintenues
en révision. Voir le [bilan 0.5.2](superc-normalization.md) : 309 offres et 37 rejets.
Prochaine analyse : modalités des points, avantages taxes/consigne, prix absents
et rabais ambigus. La disponibilité des mentions d'octobre
ne résout pas les conditions historiques de septembre. Les fichiers bruts, visuels
et brouillons restent locaux; seuls le code et ce bilan sont versionnés.


Complément fidélité : après examen de la FAQ et du bandeau de points doublés,
le bilan est de **351 offres et 14 rejets**. Voir le complément dans le
[bilan de normalisation](superc-normalization.md). La publication des données
reste désactivée.


Examen local du 10 octobre des rabais : **363 offres, 4 rejets et 2 entrées aux
conditions incomplètes**. Les rabais en pourcentage et en dollars sont représentés
sans prix final calculé. Voir le [bilan détaillé](superc-normalization.md).
