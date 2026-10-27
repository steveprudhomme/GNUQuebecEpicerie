# Diagnostic IGA Cartier

Observation : 27 octobre 2026. Collecteur désactivé; aucune archive IGA produite.

## Magasin et lecteur confirmés dans le navigateur

La [fiche officielle](https://www.iga.ca/fr/magasins/8270-iga-extra-des-rapides)
associe IGA Extra des-Rapides au 307 boulevard Cartier Ouest, Laval, H7N2J1.
Son lien « Consulter la Circulaire » utilise
[le numéro 8270](https://www.iga.ca/flyer?set_preferred_store_number=8270).
Ce numéro est enregistré comme `source_store_id`; l'identifiant interne reste
`iga-laval-cartier-ouest-307`. Il s'agit du numéro de magasin IGA, pas d'un
identifiant de publication Flipp.

Le lecteur de circulaires intégré porte la mention « Généré par Flipp ».
Après sélection explicite du magasin, l'en-tête et la zone circulaire affichent
IGA Extra des-Rapides. La semaine du 22 au 28 octobre a été sélectionnée : son
onglet expose `filmstrip-8193698`. L'aperçu du 29 octobre au 4 novembre expose
`filmstrip-8208962`. Ces identifiants sont observés dans l'interface; ils ne
constituent pas encore un contrat d'API ni une preuve de portée exclusive au magasin.

## Deux contrôles indispensables

1. **Magasin réellement affiché** : ouvrir le lien contenant 8270 conservait
   initialement IGA Atwater. Il a fallu utiliser « Sélectionnez ce magasin » sur
   la fiche Cartier, confirmer le changement, puis rouvrir la circulaire.
   Le paramètre de l'URL seul ne suffit donc pas à attribuer les offres à Cartier.
2. **Période réellement sélectionnée** : le lecteur affichait d'abord l'aperçu
   du 29 octobre au 4 novembre. La semaine courante du 22 au 28 octobre doit être
   choisie explicitement pour une collecte au 27 octobre.

L'interface montre des doublons de produits, des prix Scène+, des quantités par
lot et des conditions distinctes. Dans la semaine courante, la fiche de fondue
surgelée affiche une condition valable du 22 au 24 octobre 2026 et la mention
« Expiré ». Ne pas étendre ces dates à toute la circulaire. Le lecteur précise
également que le visuel de la circulaire prévaut en cas de désaccord avec la fiche.

## Preuves locales et accès

Le diagnostic est conservé sous `local/iga-discovery-20261027/` :

- `cartier-current-ax.txt` : état accessible complet du navigateur après sélection;
- `cartier-current.png` : capture montrant le magasin et la fiche produit;
- `store-locator.html` : réponse de refus HTTP 403 à la tentative directe;
- `manifest.json` : URL, numéro de magasin, publication observée, empreintes et limites.

Ces fichiers restent hors Git. Il ne s'agit pas d'une capture complète des
réponses sources ou des visuels. Le téléchargement HTTP direct du localisateur
retourne 403, tandis que la navigation ordinaire fonctionne. Aucun contournement
ni transfert de cookies n'a été effectué. Les cadres du lecteur n'exposent pas
d'URL `src` utilisable dans le DOM observé; le flux structuré reste à identifier.

## Prochaines actions

- Observer le flux public utilisé par le lecteur officiel et vérifier le lien
  entre magasin, publication, langue, période et données produits.
- Préparer une capture locale reproductible avec arrêt sur mauvais magasin,
  mauvaise semaine, refus réseau ou source incomplète.
- Développer le normaliseur à partir des données réellement capturées : dates
  par offre, prix public/membre, lots, points conditionnels et doublons.
- Valider les visuels et plusieurs semaines avant toute activation ou publication.

Le repérage IGA avance pendant la validation Super C. L'archivage et
l'automatisation attendent les contrôles communs décrits dans ROADMAP.md.
