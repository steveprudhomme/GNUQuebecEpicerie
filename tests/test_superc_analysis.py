import json
from datetime import date

import httpx
import pytest

from gnuquebecepicerie.analysis.superc import audit, summarize_pages


def mock_client(store_name="LAVAL DES LAURENTIDES", pages_status=200):
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
            }]})
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
