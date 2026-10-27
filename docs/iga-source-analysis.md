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


## Service public repéré et diagnostic de contexte

Le DOM du site référence le script public
`https://aq.flippenterprise.net/4592/iframe.js?ver=6.7`, téléchargé localement
avec HTTP 200. Ce script décrit une base `https://dam.flippenterprise.net/hosted`
et un chemin `/publications/{merchantNameIdentifier}`, avec notamment
`store_code`, `postal_code`, `locale`, `languages[]` et `access_token`.
Ces paramètres sont observés dans le code public générique; aucune réponse de
publications pour Cartier n'a encore été récupérée ni validée.

Le modèle d'URL de configuration exposé par ce script permet de lire
`https://aq.flippenterprise.net/4592/config.json` (HTTP 200). Cette réponse
contient les styles et options d'intégration, pas les paramètres complets du
flux. Le nombre 4592 est le chemin d'intégration observé, distinct du numéro de
magasin 8270 et de la publication 8193698. Un script Next.js référencé par IGA
retourne HTTP 403 en accès direct. Aucun cookie de navigateur n'a été exporté
et aucun contrôle d'accès n'a été contourné.

Une commande hors ligne permet maintenant de contrôler une capture accessible
complète du navigateur, enregistrée sous `local/` :

```powershell
gnuquebecepicerie inspect-iga-browser local/iga-discovery-20261027/cartier-current-ax.txt --publication 8193698 --valid-from 2026-10-22 --valid-to 2026-10-28
```

Elle produit `cartier-current-ax-context.json`, avec l'empreinte de la capture,
les paramètres attendus et les anomalies. Elle vérifie la page, le magasin dans
l'en-tête, l'unique onglet de publication sélectionné et ses jours/mois affichés.
Un décalage renvoie le code 2. Le code 0 signifie uniquement que ces contrôles
concordent : l'année fournie n'est pas attestée par l'onglet, la source n'est pas
complète et `ready_for_archive` reste faux. Ce parseur est limité au format AX
observé; une évolution de l'interface peut nécessiter son adaptation.

Vérification : capture réelle 8193698 conforme aux contrôles de contexte;
171 tests et Ruff réussis. Le téléchargement automatisé du flux structuré,
la validation de l'année et la normalisation des offres restent à réaliser.


## Étape nécessitant une capture réseau du navigateur

Le navigateur disponible permet de lire la page et ses éléments, mais n'expose
pas ses requêtes réseau à l'agent. Les attributs DOM du lecteur ne contiennent
pas les paramètres d'intégration manquants. Le flux exact n'est donc toujours
pas confirmé : ne pas inventer le nom marchand ni les paramètres d'accès.

Pour fournir la preuve manquante depuis le PC :

1. Ouvrir la circulaire IGA dans Chrome ou Edge, sélectionner explicitement
   IGA Extra des-Rapides (8270), puis vérifier la semaine souhaitée.
2. Ouvrir les outils de développement, onglet Réseau (Network), et démarrer
   l'enregistrement avant de recharger la circulaire.
3. Exporter le journal au format HAR avec le contenu des réponses, en utilisant
   l'export sans données sensibles proposé par le navigateur. Ne pas activer
   l'export des cookies ou des en-têtes d'authentification.
4. Enregistrer sous `local/iga-network.har` dans le projet. Ne pas ajouter ce
   fichier à Git et ne pas le téléverser dans la conversation.

La commande suivante travaille entièrement hors ligne :

```powershell
gnuquebecepicerie inspect-iga-har local/iga-network.har
```

Elle recherche exclusivement les requêtes GET HTTPS du chemin de publications
observé sur `dam.flippenterprise.net`, avec un unique `store_code=8270`.
Elle signale les réponses manquantes, non JSON, refusées ou d'un autre magasin.
Le rapport adjacent conserve l'empreinte du HAR, le chemin du service et les
résultats techniques; il exclut toutes les chaînes de requête, les en-têtes,
les cookies et les corps de réponse. Le HAR original reste intact et local.
Aucune requête n'est rejouée. Une réponse JSON reconnue n'est pas une validation
de son schéma, de ses publications, de l'année ou des prix : cette inspection
reste à faire après réception d'une capture réelle. Si le service observé
utilise un autre chemin, le diagnostic ne le devine pas et doit être adapté
sur preuve.

Validation : 183 tests réussis et Ruff réussi. Les nouveaux tests utilisent des
exports fictifs; aucun export réseau réel IGA n'a encore été fourni.
