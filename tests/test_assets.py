import hashlib
import json

import httpx
import pytest

from gnuquebecepicerie.analysis.assets import capture_assets, image_urls

URL = "https://metrocommonapi.blob.core.windows.net/123/images/legal.jpg?version=abc"
IMAGE = b"\xff\xd8\xffexample-test-bytes"


def pages(url=URL):
    return [{"blocks": [{"images": [
        {"image": url.replace("legal.jpg", "small.jpg"), "resolution": 72},
        {"image": url, "resolution": 288},
    ]}]}]


def test_nested_mentions_and_basebars_are_discovered_once():
    data = pages()
    data[0]["basebars"] = {"desktop": [{"image": URL, "resolution": 288}]}
    data[0]["blocks"][0]["carouselBlocks"] = [{"images": [
        {"image": URL.replace("legal", "carousel"), "resolution": 144}]}]
    assert image_urls(data) == {URL, URL.replace("legal", "carousel")}


def test_saved_image_has_reproducible_hash_and_no_credentials(tmp_path):
    def handler(request):
        assert "ocp-apim-subscription-key" not in request.headers
        assert "authorization" not in request.headers
        return httpx.Response(200, content=IMAGE)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = capture_assets(client, pages(), "123", tmp_path, delay=0)
        with pytest.raises(FileExistsError):
            capture_assets(client, pages(), "123", tmp_path, delay=0)
    assert result["complete"] and not result["commercial_validation_complete"]
    item = result["items"][0]
    assert item["sha256"] == hashlib.sha256(IMAGE).hexdigest()
    assert (tmp_path / "assets/123" / item["file"]).read_bytes() == IMAGE
    assert json.loads((tmp_path / "assets/123/manifest.json").read_text()) == result


@pytest.mark.parametrize("url", [
    URL.replace("/123/", "/999/"), URL.replace("https:", "http:"),
    URL.replace("metrocommonapi.blob.core.windows.net", "example.com"),
    URL + "&token=secret", URL.replace("/images/", "/../"),
])
def test_unexpected_or_secret_urls_are_not_requested_or_saved(tmp_path, url):
    def handler(request):
        raise AssertionError("No network request allowed")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = capture_assets(client, pages(url), "123", tmp_path, delay=0)
    assert not result["complete"]
    assert result["items"][0]["reason"] == "unexpected_asset_url"
    assert "secret" not in (tmp_path / "assets/123/manifest.json").read_text()


@pytest.mark.parametrize("status", [302, 403, 404])
def test_failures_and_redirects_remain_incomplete_without_retry(tmp_path, status):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"Location": "https://example.com/"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = capture_assets(client, pages(), "123", tmp_path, delay=0)
    assert calls == [URL]
    assert result["saved"] == 0 and not result["complete"]
    assert result["items"][0]["reason"] == f"http_{status}"


def test_html_and_oversized_payloads_do_not_become_images(tmp_path, monkeypatch):
    from gnuquebecepicerie.analysis import assets
    for index, content in enumerate((b"<html>error</html>", IMAGE * 10)):
        monkeypatch.setattr(assets, "MAX_BYTES", 30)
        with httpx.Client(transport=httpx.MockTransport(
                lambda request, data=content: httpx.Response(200, content=data))) as client:
            result = capture_assets(client, pages(), "123", tmp_path / str(index), delay=0)
        assert not result["complete"]
        assert list((tmp_path / str(index) / "assets/123").iterdir())[0].name == "manifest.json"


def test_empty_source_is_not_complete(tmp_path):
    with httpx.Client() as client:
        result = capture_assets(client, [], "123", tmp_path, delay=0)
    assert result["requested"] == 0 and not result["complete"]
