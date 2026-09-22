# GNUQuebecEpicerie

GNUQuebecEpicerie est un projet libre visant à collecter, normaliser, archiver et comparer dans le temps les spéciaux des épiceries québécoises. Les données sont versionnées dans Git afin de conserver un historique vérifiable des prix et promotions.

## Objectifs

La première étape du projet cible **Super C** et **IGA**. L'architecture est conçue pour ajouter ensuite d'autres enseignes sans modifier le format de données commun.

Principes du projet :

- conserver les observations historiques plutôt que les écraser;
- distinguer la donnée publiée par l'enseigne de la donnée normalisée;
- associer chaque collecte à un magasin, une période de validité et une source;
- valider les données avant de les archiver;
- produire des fichiers JSON lisibles et versionnables;
- permettre la reconstruction d'une base SQLite locale à partir des archives;
- ne publier un commit de données que lorsqu'une nouvelle circulaire ou un changement réel est détecté.

## Architecture cible

```text
Sources Super C / IGA
        |
        v
   Collecteurs
        |
        v
  Normalisation
        |
        v
   Validation
      /   \
     v     v
  JSON    SQLite local
     |
     v
 Git commit + push
```

## Structure du dépôt

```text
GNUQuebecEpicerie/
├── config/                  # configuration des magasins et collecteurs
├── data/                    # archives JSON versionnées
├── docs/                    # architecture et documentation du modèle
├── schema/                  # JSON Schema
├── src/gnuquebecepicerie/   # application Python
├── tests/                   # tests automatisés
├── .github/workflows/       # intégration continue
├── pyproject.toml
└── README.md
```

## Convention d'archivage

Les données sont classées par année, enseigne et date de début de validité :

```text
data/2026/superc/superc-laval-des-laurentides-1000/2026-09-24/<révision>/
├── flyer.json
└── manifest.json
```

Une archive publiée est considérée comme immuable. Toute correction ultérieure doit être explicite et traçable dans Git.

## Développement local

Prérequis : Python 3.11 ou plus récent.

```powershell
git clone https://github.com/steveprudhomme/GNUQuebecEpicerie.git
cd GNUQuebecEpicerie
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
gnuquebecepicerie --help
```

## Commandes prévues

```powershell
gnuquebecepicerie status
gnuquebecepicerie validate examples/flyer.v1.json
gnuquebecepicerie update superc
gnuquebecepicerie update iga
```

Les collecteurs Super C et IGA sont des squelettes dans cette version initiale; leur implémentation réseau viendra dans la prochaine étape.

## État du projet

Les fondations V1 et la normalisation locale Super C sont en place. Les offres
restent en brouillon jusqu'à validation commerciale; les collecteurs complets
et la publication automatique restent à réaliser.

La [feuille de route](ROADMAP.md) détaille les prochaines étapes et leurs critères
de validation. Le [contrat V1.1](docs/v1.1-contract.md) et ses tests sont disponibles;
son intégration au normaliseur reste à réaliser.

## Licence

Le code est distribué sous licence **GNU General Public License v3.0 or later (GPL-3.0-or-later)**. Les données provenant de sources tierces demeurent soumises aux droits, conditions d'utilisation et licences de leurs sources respectives.

## Contrat V1

Le [contrat V1](docs/v1-contract.md) fixe les promotions, les magasins et les archives.
Le registre de référence est [config/stores.yaml](config/stores.yaml).
Les sept [exemples fictifs](examples/flyer.v1.json) sont validés en CI.

## Analyse locale des sources

L'[analyse Super C](docs/superc-source-analysis.md) confirme la source structurée
et l'identifiant du magasin de référence. Le diagnostic peut être relancé sur le PC :

```powershell
python -m gnuquebecepicerie.analysis.superc --date 2026-09-20
```

Ses réponses restent sous `local/`, hors Git. Il ne normalise ni ne publie encore les offres.

## Normalisation hors ligne

La [normalisation Super C](docs/superc-normalization.md) convertit une capture vérifiée
en brouillon V1 et signale les entrées ambiguës :

```powershell
python -m gnuquebecepicerie normalize-superc local/source-analysis/20260920T215125838198Z --publication 83817
```

Adapter le dossier et la publication au diagnostic local. Les résultats restent sous
`local/`; le code de sortie 2 indique des rejets à examiner. Aucune archive ni publication
Git n'est créée automatiquement par cette commande.
