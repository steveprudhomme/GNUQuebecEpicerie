from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from gnuquebecepicerie import __version__
from gnuquebecepicerie.collectors import IGACollector, SuperCCollector
from gnuquebecepicerie.normalizers.superc_snapshot import normalize_snapshot
from gnuquebecepicerie.validators.schema import validate_json

app = typer.Typer(help="Collecte et archive les promotions d'épiceries québécoises.")


@app.command("normalize-superc")
def normalize_superc(
    snapshot: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    publication: Annotated[str, typer.Option(help="Identifiant de publication du diagnostic")],
    schemas: Annotated[Path, typer.Option()] = Path("schema"),
) -> None:
    """Normalise une capture locale; signale les rejets et ne publie aucune archive."""
    try:
        output, report = normalize_snapshot(snapshot, publication, schemas)
    except (ValueError, KeyError, OSError) as exc:
        typer.echo(f"Normalisation arrêtée : {exc}", err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"Brouillon local : {output}")
    typer.echo(
        f"{report['offers_count']} offres; {report['rejected_entries']} entrées à revoir; "
        f"{report['skipped_entries']} blocs non commerciaux ignorés."
    )
    typer.echo(f"{report['incomplete_entries']} entrées aux conditions incomplètes.")
    if report["rejected_entries"] or report["incomplete_entries"]:
        raise typer.Exit(code=2)


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
