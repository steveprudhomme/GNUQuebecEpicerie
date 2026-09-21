# Normalisation locale Super C

La commande `normalize-superc` convertit hors ligne une capture du diagnostic
en brouillon JSON V1. Elle n'effectue aucune requête réseau, aucun commit et aucun
push. Elle ne remplace pas encore la commande `update superc`.

## Utilisation

Depuis la racine du dépôt et dans l'environnement Python du projet :

```powershell
python -m gnuquebecepicerie normalize-superc local/source-analysis/20260920T215125838198Z --publication 83817
```

Pour une nouvelle capture, commencer par le diagnostic décrit dans
[l'analyse de source](superc-source-analysis.md), puis utiliser son dossier horodaté
et l'identifiant de publication retourné.

Le résultat se trouve sous le dossier de capture, dans
`normalized/superc-0.2.0/<publication>/` :

- `flyer.json` : offres acceptées, conformes au schéma V1;
- `manifest.json` : période, magasin, compte des offres et empreintes;
- `report.json` : décompte des entrées, rejets motivés et enregistrements originaux;
- `source-input.bin` : octets d'entrée encadrés selon le contrat V1, permettant de
  reproduire l'empreinte du manifeste.

Tous ces fichiers restent sous `local/`, ignoré par Git. Une nouvelle exécution
sur la même capture remplace ces brouillons locaux avec le même contenu; elle ne
modifie aucune archive publiée. Le code de sortie est **2** si des entrées sont
rejetées ou si les contrôles d'entrée échouent. Un code 0 signifie conversion sans
rejet, pas autorisation de publication : `ready_for_archive` reste faux tant que
les vérifications manuelles et les contrôles de complétude ne sont pas terminés.

## Règles implémentées

- Contrôle du magasin 447, du nom, de la langue `bil`, de la publication et de
  l'empreinte SHA-256 des pages par rapport au diagnostic enregistré.
- Prix simples lus avec `Decimal`, sans extraire arbitrairement un nombre d'une plage.
- Lots : quantité et prix total; aucun prix d'achat individuel inventé.
- Prix au poids : base conservée et conversion livre/kilogramme à six décimales.
- Prix membre : offre séparée du prix public, avec programme `moi`.
- Points : offre membre séparée; zéro point devient absence de récompense.
- Limites : quantité et prix après limite soumis aux règles du modèle V1.
- Format produit exact uniquement lorsqu'il est isolé; formats variables laissés inconnus.
- Prix normal ambigu conservé dans le texte source, sans prix structuré supposé.
- Conditions et champs source originaux conservés dans chaque offre.
- Seuls les doublons strictement identiques sont supprimés; deux prix différents
  pour le même SKU restent deux offres.
- Identité stable indépendamment de l'ordre des entrées et de l'heure de consultation.
- Une différence de période par offre entraîne une révision, pas un changement silencieux.

La conversion d'une entrée est atomique : si une variante membre est ambiguë,
l'entrée entière est signalée, même si son prix public paraît interprétable.
Les blocs `URL` et `Inblock` sont recensés séparément, sans être considérés comme des produits.

## Premier bilan (normaliseur 0.1.0)

Circulaire 83817, du 17 au 23 septembre, magasin Laval Des Laurentides :

| Résultat | Nombre |
| --- | ---: |
| Entrées source | 331 |
| Entrées produit acceptées | 240 |
| Blocs non commerciaux écartés | 12 |
| Entrées produit à revoir | 79 |
| Offres après séparation et déduplication | 240 |
| Doublons d'offres exacts supprimés | 2 |

Les offres retenues incluent 34 prix à la livre, 3 multi-achats et 2 récompenses
en points distinctes du prix public. Les prix membres sont couverts par les tests
fictifs; les cas réels associés à un indicateur de coupon restent en révision.
Des exemples réels de prix simple, de lot, de poids et de points ont été comparés
aux champs source; il ne s'agit pas d'une validation manuelle exhaustive.

| Motif de révision (premier motif par entrée) | Nombre |
| --- | ---: |
| Indicateur de coupon dont les conditions restent à confirmer | 41 |
| Symbole de cents dont la convention de stockage reste ambiguë | 31 |
| Base de prix non reconnue | 2 |
| Prix ou récompense exploitable absent | 5 |

Une conversion de toutes les entrées en prix simples serait incorrecte. Ces 79
entrées sont préservées dans le rapport local. Aucune collecte partielle n'a été
ajoutée à `data/`, et le collecteur reste désactivé.

## Vérifications et suite

La suite de tests inclut des cas fictifs : prix public/membre, points, lots, poids,
limites, dates, encodage UTF-8, doublons, changements de prix, stabilité des
identifiants, capture modifiée et résultat incomplet de la CLI. Les tests fonctionnent
hors ligne, sans dépendre des offres courantes.

Les améliorations et les limites découvertes lors de la vérification visuelle sont
détaillées ci-dessous. La collecte réseau avec publication automatique reste désactivée.

## Vérification visuelle du 21 septembre — normaliseur 0.2.0

Le lecteur officiel a été consulté dans le navigateur local à l'adresse
`https://circulaire.superc.ca/flyer/83817?storeId=447&language=fr`, avec les images
de circulaire et les résultats de recherche. Les observations ne proviennent pas
d'une interprétation des seuls textes alternatifs : ceux-ci affichent parfois
`0,99¢`, alors que l'image indique 99 ¢.

Conclusions appliquées :

- `priceSign: ¢` avec `salePriceFr: 0.99` représente **0,99 CAD**, pas 0,0099 CAD.
  Le code du lecteur formate lui aussi cette valeur décimale en dollars. Les cas
  à 1 ou plus avec ce symbole et les valeurs françaises/génériques contradictoires
  restent rejetés. La même règle s'applique au champ de prix membre.
- Le prix membre à 99 ¢ du jus de tomate est explicitement affiché avec son prix
  public à 1,25 $. L'indicateur `coupon: true` ne suffit donc pas à identifier un
  coupon à activer. Le normaliseur accepte maintenant les entrées ayant un prix
  membre numérique et le libellé explicite `prix membre`; il conserve les deux prix
  séparément et préserve l'indicateur original. Les autres cas ne sont pas extrapolés.
- Le melon entier à 5,99 $ est vendu au format approximatif d'environ 11 lb,
  et non à 5,99 $/lb. Aucune masse exacte ni conversion unitaire n'est inventée.
- Les figues à 9,99 $ sont vendues par demi-caisse : `package` désigne ici ce format,
  préservé dans les conditions et le texte source; aucun poids n'est déduit.

### Contradiction de période découverte

Sur la première page, l'image de l'offre de longe de porc (SKU 15122301) affiche
une validité limitée au jeudi et au vendredi. Ses champs JSON `validFrom` et `validTo`
couvrent pourtant les sept jours. Les champs `ROW`, les tags et les métadonnées
du bloc ne fournissent pas la correction. Cette offre est maintenant mise en
quarantaine par `config/source-reviews/superc.json`.

Le registre est limité à la publication, au magasin, au SKU et à la période concernés.
Une nouvelle publication n'hérite pas automatiquement de cette observation.
La conversion d'une capture exige le registre; s'il manque, elle s'arrête. Son empreinte
est enregistrée dans le rapport local pour tracer les décisions appliquées.
Ces observations de contenu public sont versionnées; aucune clé ni image tierce
n'est incluse dans le registre.

Cet écart démontre qu'une validation JSON seule ne garantit pas la justesse commerciale
des dates. Les brouillons restent non publiables automatiquement, y compris lorsque
leur conversion syntaxique n'a aucun rejet. Les autres offres n'ont pas été vérifiées
visuellement de manière exhaustive.

### Nouveau bilan sur la même capture

| Résultat | Nombre |
| --- | ---: |
| Entrées source | 331 |
| Entrées produit acceptées | 298 |
| Blocs non commerciaux écartés | 12 |
| Entrées à revoir | 21 |
| Offres après séparation public/membre/points et déduplication | 324 |
| Doublons d'offres supprimés | 2 |

Les 21 entrées restantes comprennent 15 indicateurs de coupon non élucidés,
5 entrées sans prix ni récompense structurée, et la contradiction de période ci-dessus.
Le nombre d'offres ne doit pas être comparé directement au nombre d'entrées : un
produit peut générer plusieurs offres de conditions différentes.

Les tests couvrent désormais la convention des cents, les divergences de montant,
les prix membres associés à l'indicateur de coupon, les formats de vente vérifiés,
les rabais membres qui ne sont pas un prix final et le périmètre exact du registre
de quarantaine. Les résultats 0.1.0 restent dans leur ancien dossier local; les
résultats 0.2.0 sont générés dans un dossier distinct.

La suite exige une source fiable pour les conditions et dates absentes du JSON,
ainsi qu'un traitement explicite des rabais sans prix final. La désactivation de
la publication automatique est conservée jusqu'à résolution de ces points.
