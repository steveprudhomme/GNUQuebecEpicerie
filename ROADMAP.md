# Feuille de route

Mise à jour : 27 octobre 2026.

Le traitement s'exécute sur le PC local. GitHub reçoit le code, la documentation
et, une fois validées, les archives de données. Les captures brutes et les
brouillons restent sous `local/`, hors Git.

## État actuel

- [x] Initialiser le dépôt, les schémas V1, les tests et l'intégration continue.
- [x] Définir les magasins de référence : Super C, 1000 boulevard des Laurentides,
  Laval; IGA extra des-Rapides, 307 boulevard Cartier Ouest, Laval.
- [x] Identifier la source Super C et produire un diagnostic local reproductible.
- [x] Normaliser les captures Super C hors ligne avec rejets motivés et traçabilité.
- [x] Documenter les décisions sur les 22 entrées examinées de la circulaire 83817.

Pour la circulaire historique 83817, le normaliseur 0.5.2 produit **346 offres en brouillon V1.1**; **2 entrées restent
rejetées et 8 entrées converties gardent des conditions incomplètes**. La validation V1.1 complète les 96 tests de la normalisation et du contrat V1. Ces résultats
ne constituent pas une validation commerciale exhaustive. L'archivage automatique
reste désactivé et les collecteurs réseau complets restent à implémenter.

## Passage à IGA : ce qui reste et ce qui peut commencer

Le repérage de la source IGA commence maintenant; il n'exige pas de résoudre
chaque promotion historique Super C. Le numéro IGA 8270 et le lecteur Flipp sont confirmés; le flux structuré
et son association à la publication restent à vérifier. Voir [le diagnostic IGA](docs/iga-source-analysis.md).

Avant de finaliser puis d'activer le collecteur IGA, trois grands jalons Super C
et communs restent ouverts (ce ne sont pas trois interventions de durée fixe) :

1. **Validation commerciale** : examiner les entrées restantes, corriger les
   erreurs et isoler explicitement les cas ambigus. Une exclusion ne rend pas
   la circulaire complète; ne pas annoncer une couverture exhaustive.
2. **Flux local et archivage contrôlé** : relier capture, normalisation et
   validation, conserver les preuves et empêcher la publication des brouillons.
3. **Reproductibilité sur plusieurs semaines** : gérer les changements de source,
   les erreurs et les réexécutions sans produire de fausses nouvelles archives.

L'identification du magasin, l'inspection de la source et un diagnostic local IGA
peuvent avancer pendant ces travaux. Le normaliseur IGA sera développé une fois
son format source observé; l'activation attendra les contrôles communs et les
tests propres à IGA. Les anciennes ambiguïtés Super C resteront en quarantaine
si leurs preuves sont introuvables.

Le 27 octobre, une révision de la première page de 83986 a révélé deux prix de
poulet fusionnés dans une entrée : 4,87 $/lb ordinaire et 5,87 $/lb halal.
Cette entrée est désormais exclue : **362 offres, 340 entrées converties,
5 rejets et 2 entrées incomplètes**. Révision consignée pour 56/340 entrées
converties; 284 restent sans révision consignée. **162 tests réussis**.

## 1. Préparer le schéma V1.1 — contrat et tests réalisés

- [x] Définir les rabais conditionnels : montant ou pourcentage, quantité minimale,
  portée du rabais et conditions d'admissibilité.
- [x] Représenter séparément les rabais sur panier et les prix de vente des produits.
- [x] Ajouter les dates de validité propres à chaque promotion, distinctes de celles
  de la circulaire.
- [x] Préserver la distinction entre prix public, prix membre et récompense en points;
  ne jamais convertir un rabais en prix final sans preuve suffisante.
- [x] Documenter le contrat V1.1 et ajouter les schémas, modèles, exemples fictifs
  et tests correspondants avant d'adapter le normaliseur.
- [x] Maintenir la lecture et la validation des archives V1; versionner explicitement
  les nouveaux documents sans réécrire les archives existantes.

Le [contrat V1.1](docs/v1.1-contract.md), les schémas distincts, les exemples et
la lecture versionnée sont disponibles. Le normaliseur est adapté au V1.1;
les conditions et récompenses manquantes constituent la prochaine priorité.

Critère de fin : les nouveaux types de promotions sont représentables sans
ambiguïté et les tests de compatibilité V1/V1.1 passent.

## 2. Traiter les 12 entrées encore bloquées

- [x] Représenter le rabais de 2 $ à l'achat de 2 pains (2 entrées).
- [ ] Obtenir les conditions signalées par les astérisques du rabais de 15 $ sur
  le panier à l'achat de 2 caisses de bière, puis le représenter (5 entrées).
- [x] Confirmer les 300 points des caisses Bud Light/Coors Light dans la vue complète.
- [ ] Confirmer les conditions détaillées de ces points (2 entrées maintenues en révision).
- [x] Représenter les rabais public de 3 $ et membre de 6 $ du vinier sans les
  confondre avec des prix finaux (1 entrée).
- [x] Traiter explicitement la contradiction public/membre de la soupe Bâton Rouge :
  image à 11,99 $ public et 10,99 $ membre, contrairement aux champs JSON (1 entrée).
- [x] Représenter la validité jeudi et vendredi de la longe de porc, au lieu de la
  semaine entière annoncée dans le JSON (1 entrée).
- [ ] Associer chaque résolution à sa preuve, sa portée et ses tests; conserver
  en quarantaine les cas qui ne peuvent pas être résolus.

Critère de fin : chaque entrée est soit convertie avec preuve et conditions
complètes, soit explicitement exclue avec un motif documenté. Un schéma plus riche
ne remplace pas une information source manquante.

## 3. Valider les 346 offres en brouillon avant archivage

- [ ] Vérifier les prix, formats, quantités, conditions membre, points et limites
  par rapport aux sources officielles.
- [ ] Vérifier les dates commerciales, y compris les promotions de quelques jours.
- [ ] Contrôler la complétude, les doublons et les écarts entre la source et les offres.
- [x] Produire un bilan local de conversion et de couverture des révisions consignées
  (`quality.json` et `quality.txt`), avec motifs bloquant l'archivage.
- [ ] Enregistrer une validation commerciale exhaustive par offre; les révisions
  ponctuelles ne constituent pas cette validation.

- [ ] Autoriser l'archivage seulement lorsque les critères de qualité sont satisfaits;
  ne jamais présenter une collecte partielle comme complète.

Bilan du 10 octobre : pour 83986, 56 des 341 entrées converties ont une révision
consignée (285 restent sans révision); 4 entrées sont rejetées et 2 converties
ont des conditions incomplètes. Pour 83817, la couverture est de 20/317, avec
2 rejets et 8 entrées incomplètes. Ces compteurs portent sur les entrées source,
pas sur les 363 et 346 offres produites. Les tests de qualité font partie des
161 tests réussis.

## 4. Finaliser le collecteur Super C local

- [ ] Relier téléchargement, normalisation, validation et archivage dans un flux local.
- [ ] Gérer les erreurs réseau, changements de structure et captures incomplètes.
- [x] Ajouter la conservation locale des visuels référencés et de leurs empreintes,
  avec rejet des redirections et des chemins hors publication.
- [x] Vérifier la conservation sur une capture réelle : 277/277 visuels de 83986,
  empreintes concordantes et bloc des mentions générales lisible (6 octobre).
- [ ] Vérifier la couverture de tous les astérisques et conditions par offre.
- [x] Examiner les 50 indicateurs coupon de 83986 : 23 entrées converties avec
  preuves visuelles et 27 exclusions motivées; 309 offres en brouillon local.
- [x] Examiner les modalités des 25 entrées à points : 23 converties après lecture
  de la FAQ et des bandeaux; 2 Red Bull restent ambiguës. Bilan : 351 offres.
- [x] Représenter les 6 rabais en pourcentage et 4 rabais en dollars de 83986,
  avec preuves visuelles et points séparés : 363 offres en brouillon.
- [ ] Confirmer la base de calcul des 2 rabais de 50 % sur les pains : conditions
  marquées incomplètes, aucun prix final calculé.
- [ ] Résoudre les 4 rejets restants : portée des points de 2 Red Bull et
  2 avantages taxes/consigne.
- [ ] Produire des archives immuables avec provenance, empreintes et révisions traçables.
- [ ] Tester plusieurs circulaires hebdomadaires successives et les changements
  apportés à une même circulaire.
- [ ] Vérifier qu'une exécution répétée sans changement ne crée pas de nouvelle archive.

Critère de fin : plusieurs semaines sont traitées de façon reproductible et les
anomalies empêchent la publication des données concernées.

## 5. Ajouter IGA Cartier et la comparaison

- [x] Commencer le repérage des pages officielles : localisateur et circulaire
  sur `iga.ca`, après redirection de l'ancienne page `iga.net` (27 octobre).

- [x] Confirmer le magasin IGA 8270 sur la fiche officielle et sélectionner
  des-Rapides dans le lecteur Flipp; conserver les preuves localement.
- [ ] Identifier le flux structuré du lecteur et vérifier sa portée magasin/publication.
- [ ] Contrôler le magasin affiché et la semaine sélectionnée : l'URL seule ne
  remplace pas la sélection; le lecteur peut afficher un autre magasin ou un aperçu.
- [ ] Construire son diagnostic local, son normaliseur et son collecteur avec les
  mêmes exigences de provenance et de validation que Super C.
- [ ] Tester plusieurs circulaires IGA avant activation.
- [ ] Définir le rapprochement des produits entre enseignes : marque, format,
  quantité, variante et identifiants disponibles.
- [ ] Comparer les prix par unité compatible en distinguant les lots, prix membres
  et rabais conditionnels; signaler les produits non comparables.
- [ ] Exploiter l'historique pour suivre les prix et les cycles de promotions.

## 6. Automatiser sur le PC et publier par Git

- [ ] Préparer une commande locale complète et une planification sur le PC.
- [ ] Activer la planification seulement après validation des collecteurs sur
  plusieurs semaines.
- [ ] Conserver des journaux et un bilan d'exécution compréhensible en cas d'échec.
- [ ] Créer un commit de données uniquement pour une nouvelle circulaire ou un
  changement réel validé, puis pousser vers GitHub.
- [ ] Bloquer l'envoi des captures brutes, brouillons, secrets et données non validées.
- [ ] Gérer les erreurs d'authentification, les échecs de push et les changements
  distants sans écraser l'historique.

## Références

- [Contrat V1](docs/v1-contract.md)
- [Analyse de la source Super C](docs/superc-source-analysis.md)
- [Normalisation et bilan des révisions Super C](docs/superc-normalization.md)
- [Registre des observations](config/source-reviews/superc.json)
- [Magasins de référence](config/stores.yaml)
