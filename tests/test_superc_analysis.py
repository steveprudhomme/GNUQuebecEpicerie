import json
from datetime import date

import httpx
import pytest

from gnuquebecepicerie.analysis.superc import audit, summarize_pages


def mock_client(store_name="LAVAL DES LAURENTIDES", pages_status=200, extra_flyers=()):
    def handle(request):
        if request.url.path.endswith("app.json"):
            return httpx.Response(200, json={
                "api": "https://metrodigital-apim.azure-api.net/api/",
                "apikey": "synthetic-key-do-not-publish", "banner_id": "test", "api_version": "3.0",
            })
        assert request.headers["Ocp-Apim-Subscription-Key"] == "synthetic-key-do-not-publish"
        if "/flyers/" in request.url.path:
            assert "/447/bil" in request.url.path
            return httpx.Response(200, json={"flyers": [{
                "title": "123", "storeName": store_name,
                "startDate": "2026-09-17T00:00:00Z", "endDate": "2026-09-23T23:59:00Z",
            }, *extra_flyers]})
        assert request.url.path == "/api/pages/123/447/bil/"
        return httpx.Response(pages_status, json=[{"blocks": [{"products": [
            {"sku": "fictif", "salePriceFr": "4.99", "memberPriceFr": None}
        ]}]}])
    return httpx.Client(transport=httpx.MockTransport(handle))


def test_nested_blocks_and_duplicate_skus_are_not_lost():
    product = {"sku": "example", "salePriceFr": "3.99", "memberPriceFr": "2.99"}
    pages = [{"blocks": [{"products": [product], "carouselBlocks": [{"products": [product]}]}]}]
    result = summarize_pages(pages)
    assert result["product_entries_count"] == 2
    assert result["distinct_skus_count"] == 1
    assert result["member_price_entries_count"] == 2


def test_audit_never_writes_public_client_key(tmp_path):
    with mock_client() as client:
        result = audit(client, date(2026, 9, 20), tmp_path / "audit", delay=0)
    assert result["flyers"][0]["product_entries_count"] == 1
    for path in (tmp_path / "audit").iterdir():
        assert "synthetic-key-do-not-publish" not in path.read_text()
    assert json.loads((tmp_path / "audit/summary.json").read_text())["source_store_id"] == "447"


def test_unexpected_store_stops_without_output(tmp_path):
    with mock_client(store_name="STE-THERESE") as client, pytest.raises(ValueError):
        audit(client, date(2026, 9, 20), tmp_path / "audit", delay=0)
    assert not (tmp_path / "audit").exists()


def test_blocked_pages_do_not_produce_success_summary(tmp_path):
    with mock_client(pages_status=403) as client, pytest.raises(httpx.HTTPStatusError):
        audit(client, date(2026, 9, 20), tmp_path / "audit", delay=0)
    assert not (tmp_path / "audit/summary.json").exists()



def test_audit_reports_incomplete_visual_capture_separately(tmp_path):
    def assets_handler(request):
        raise AssertionError("No image URLs in this synthetic source")
    with (mock_client() as client,
          httpx.Client(transport=httpx.MockTransport(assets_handler)) as images):
        result = audit(client, date(2026, 9, 20), tmp_path / "audit", delay=0,
                       asset_client=images)
    assert result["flyers"][0]["assets"]["complete"] is False
    assert (tmp_path / "audit/pages-123.json").exists()
    assert (tmp_path / "audit/assets/123/manifest.json").exists()
    assert result["flyers"][0]["assets"]["requested"] == 0


@pytest.mark.parametrize("day", [date(2026, 9, 17), date(2026, 9, 23)])
def test_only_flyers_covering_requested_day_are_downloaded(tmp_path, day):
    other_periods = [
        {"title": "124m", "storeName": "LAVAL DES LAURENTIDES",
         "startDate": "2026-09-24T00:00:00Z", "endDate": "2026-09-30T23:59:00Z"},
        {"title": "122", "storeName": "LAVAL DES LAURENTIDES",
         "startDate": "2026-09-10T00:00:00Z", "endDate": "2026-09-16T23:59:00Z"},
    ]
    with mock_client(extra_flyers=other_periods) as client:
        result = audit(client, day, tmp_path / "audit", delay=0)
    assert [f["flyer_id"] for f in result["flyers"]] == ["123"]
    metadata = json.loads((tmp_path / "audit/metadata.json").read_text())
    assert len(metadata["flyers"]) == 3


def test_no_flyer_covering_date_stops_without_output(tmp_path):
    with mock_client() as client, pytest.raises(ValueError, match="date demandée"):
        audit(client, date(2026, 9, 24), tmp_path / "audit", delay=0)
    assert not (tmp_path / "audit").exists()
