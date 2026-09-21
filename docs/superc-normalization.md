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
`normalized/superc-0.1.0/<publication>/` :

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

## Vérification sur la capture du 20 septembre 2026

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

La prochaine étape est de confirmer les conventions des coupons et des cents,
puis de décider du traitement des promotions sans prix final. Le normaliseur devra
ensuite être relié à la collecte réseau avec contrôle de volume historique et
publication d'archives complètes seulement.
