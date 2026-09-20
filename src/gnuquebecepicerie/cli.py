from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from gnuquebecepicerie import __version__
from gnuquebecepicerie.collectors import IGACollector, SuperCCollector
from gnuquebecepicerie.validators.schema import validate_json

app = typer.Typer(help="Collecte et archive les promotions d'épiceries québécoises.")


@app.command()
def status() -> None:
    """Affiche l'état du projet."""
    typer.echo(f"GNUQuebecEpicerie {__version__}")
    typer.echo("Collecteurs configurés : superc, iga")


@app.command()
def validate(
    file: Annotated[Path, typer.Argument(exists=True, readable=True)],
    schema: Annotated[Path, typer.Option("--schema")] = Path("schema/flyer.schema.json"),
) -> None:
    """Valide un fichier JSON archivé."""
    document = json.loads(file.read_text(encoding="utf-8"))
    validate_json(document, schema)
    typer.echo(f"OK : {file}")


@app.command()
def update(
    retailer: Annotated[str, typer.Argument(help="superc ou iga")],
    store_id: Annotated[
        str, typer.Option(help="Identifiant du magasin de référence")
    ] = "TO_DEFINE",
) -> None:
    """Lance un collecteur. Les collecteurs réseau arrivent à la phase 1."""
    collectors = {"superc": SuperCCollector, "iga": IGACollector}
    collector_type = collectors.get(retailer.lower())
    if collector_type is None:
        raise typer.BadParameter("Enseigne inconnue. Valeurs permises : superc, iga")
    try:
        collector_type().collect(store_id)
    except NotImplementedError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
