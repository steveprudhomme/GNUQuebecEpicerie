import base64
import json

import pytest

from gnuquebecepicerie.analysis.iga_har import inspect_har, inspect_har_file


def capture(url=None, status=200, body='[{"id": 123}]', encoding=None):
    return {"log": {"entries": [{
        "request": {"method": "GET", "url": url or
                    "https://dam.flippenterprise.net/hosted/publications/test-merchant"
                    "?store_code=8270&access_token=SECRET_TOKEN",
                    "cookies": [{"value": "SECRET_COOKIE"}],
                    "headers": [{"value": "SECRET_HEADER"}]},
        "response": {"status": status, "content": {"text": body, "encoding": encoding}},
    }]}}


def test_report_omits_credentials_and_source_values():
    result = inspect_har(capture(body='[{"private": "SECRET_BODY"}]'))
    assert result["source_response_found"]
    assert "SECRET" not in json.dumps(result)
    assert result["candidates"][0]["top_level_list_count"] == 1
    assert not result["ready_for_archive"]


@pytest.mark.parametrize("changes", [
    {"status": 403}, {"body": "<html>Access denied</html>"}, {"body": None},
    {"body": '"string"'}, {"body": "bad", "encoding": "base64"},
    {"url": "https://dam.flippenterprise.net/hosted/publications/test?store_code=9999"},
    {"url": "https://dam.flippenterprise.net/hosted/publications/test?store_code=8270&store_code=9999"},
    {"url": "https://dam.flippenterprise.net.evil.test/hosted/publications/test?store_code=8270"},
])
def test_unusable_or_wrong_store_response_is_not_accepted(changes):
    assert not inspect_har(capture(**changes))["source_response_found"]


def test_base64_json_is_supported_without_copying_body():
    body = base64.b64encode(b'[{"id": 123}]').decode()
    assert inspect_har(capture(body=body, encoding="base64"))["source_response_found"]


def test_local_file_diagnostic_does_not_change_original(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "local/iga.har"
    path.parent.mkdir()
    raw = json.dumps(capture()).encode()
    path.write_bytes(raw)
    output, report = inspect_har_file(path)
    assert path.read_bytes() == raw
    assert json.loads(output.read_text()) == report
    assert "SECRET" not in output.read_text()


def test_har_outside_local_is_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="local"):
        inspect_har_file(tmp_path / "outside.har")
