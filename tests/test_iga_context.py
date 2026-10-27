from datetime import date

import pytest
from typer.testing import CliRunner

from gnuquebecepicerie.analysis.iga import inspect_capture, inspect_context
from gnuquebecepicerie.cli import app

TEXT = """Browser tab: 2, URL: "https://www.iga.ca/fr/circulaire?set_preferred_store_number=8270".
5 pop up button (collapsed) Description: IGA Extra des-Rapides Ouvert aujourd'hui
6 tab (selected, settable, boolean) Québec Valide du 22 oct. au 28 oct., ID: filmstrip-8193698
7 tab (selectable, settable, boolean) Aperçu Valide du 29 oct. au 04 nov., ID: filmstrip-8208962
"""
START, END = date(2026, 10, 22), date(2026, 10, 28)


def test_visible_context_is_not_commercial_approval():
    result = inspect_context(TEXT, "8193698", START, END)
    assert result["context_checks_passed"]
    assert not result["year_verified"]
    assert not result["complete_source_capture"]
    assert not result["ready_for_archive"]


@pytest.mark.parametrize("text,reason", [
    (TEXT.replace("des-Rapides", "Atwater"), "displayed_store_not_confirmed"),
    (TEXT.replace("=8270", "=9999"), "unexpected_page_or_store_parameter"),
    (TEXT.replace("filmstrip-8193698", "filmstrip-8208962"), "selected_publication_mismatch"),
    (TEXT.replace("22 oct.", "21 oct."), "displayed_period_mismatch"),
    (TEXT.replace("tab (selected,", "tab (selectable,"), "selected_publication_mismatch"),
    ("", "displayed_store_not_confirmed"),
])
def test_incorrect_context_is_blocked(text, reason):
    result = inspect_context(text, "8193698", START, END)
    assert not result["context_checks_passed"]
    assert reason in result["context_issues"]


def test_capture_outside_local_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    capture = tmp_path / "capture.txt"
    capture.write_text(TEXT, encoding="utf-8")
    with pytest.raises(ValueError, match="local"):
        inspect_capture(capture, "8193698", START, END)


def test_cli_mismatch_writes_diagnostic_and_returns_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    capture = tmp_path / "local/capture.txt"
    capture.parent.mkdir()
    capture.write_text(TEXT.replace("des-Rapides", "Atwater"), encoding="utf-8")
    result = CliRunner().invoke(app, ["inspect-iga-browser", str(capture),
        "--publication", "8193698", "--valid-from", "2026-10-22",
        "--valid-to", "2026-10-28"])
    assert result.exit_code == 2
    assert (capture.parent / "capture-context.json").exists()
    assert "displayed_store_not_confirmed" in result.output
