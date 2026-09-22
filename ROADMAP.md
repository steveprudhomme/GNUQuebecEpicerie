# Feuille de route

Mise à jour : 22 septembre 2026.

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

Le normaliseur 0.5.0 produit **346 offres en brouillon V1.1**; **2 entrées restent
rejetées et 8 entrées converties gardent des conditions incomplètes**. La validation V1.1 complète les 96 tests de la normalisation et du contrat V1. Ces résultats
ne constituent pas une validation commerciale exhaustive. L'archivage automatique
reste désactivé et les collecteurs réseau complets restent à implémenter.

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
- [ ] Confirmer les 300 points des caisses Bud Light/Coors Light et leurs conditions
  dans une source officielle (2 entrées).
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
- [ ] Enregistrer la couverture de validation et les anomalies non résolues.
- [ ] Autoriser l'archivage seulement lorsque les critères de qualité sont satisfaits;
  ne jamais présenter une collecte partielle comme complète.

## 4. Finaliser le collecteur Super C local

- [ ] Relier téléchargement, normalisation, validation et archivage dans un flux local.
- [ ] Gérer les erreurs réseau, changements de structure et captures incomplètes.
- [ ] Produire des archives immuables avec provenance, empreintes et révisions traçables.
- [ ] Tester plusieurs circulaires hebdomadaires successives et les changements
  apportés à une même circulaire.
- [ ] Vérifier qu'une exécution répétée sans changement ne crée pas de nouvelle archive.

Critère de fin : plusieurs semaines sont traitées de façon reproductible et les
anomalies empêchent la publication des données concernées.

## 5. Ajouter IGA Cartier et la comparaison

- [ ] Identifier et vérifier la source et l'identifiant du magasin IGA de référence.
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
