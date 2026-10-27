# Diagnostic IGA Cartier — repérage initial

Observation : 27 octobre 2026. Collecteur désactivé; aucune promotion IGA collectée.

## Magasin cible

IGA extra des-Rapides, 307 boulevard Cartier Ouest, Laval, H7N 2J1.
Identifiant interne : `iga-laval-cartier-ouest-307`. L'adresse déjà consignée
reste la cible choisie; l'identifiant de la plateforme de circulaires n'est pas
encore confirmé et `source_store_id` reste nul dans la configuration.

## Pages officielles observées

- L'ouverture de [l'ancienne page IGA](https://www.iga.net/validation-fr.html)
  aboutit à [iga.ca](https://www.iga.ca/validation-fr.html).
- Le menu mène au [localisateur](https://www.iga.ca/store-locator).
- Le menu mène à la [circulaire](https://www.iga.ca/flyer).

Dans la lecture web accessible, le localisateur expose une recherche et des
filtres, mais aucune fiche permettant de vérifier Cartier. La page circulaire
expose son cadre et un indicateur de chargement, sans les produits ni
l'association au magasin. Cela ne prouve ni l'absence de données ni une erreur
sur le site. Aucun identifiant n'est déduit d'un annuaire tiers ou d'un ancien
numéro de magasin. Ce repérage web n'est pas encore une capture reproductible
réalisée sur le PC.

## Prochaines actions

1. Sélectionner Cartier dans le site officiel et confirmer nom, adresse et
   identifiant réellement utilisé par la circulaire.
2. Observer la source publique chargée par cette page, sa langue, sa période,
   la portée magasin/région et les éventuelles conditions membre.
3. Construire le diagnostic local : réponses sources et visuels sous `local/`,
   URL, horodatage, empreintes et rapport des données manquantes.
4. Développer le normaliseur et ses tests à partir de captures réelles, puis
   vérifier plusieurs semaines avant toute activation.

Le repérage IGA peut avancer pendant la validation Super C. L'archivage et
l'automatisation IGA attendent les contrôles communs décrits dans ROADMAP.md.
