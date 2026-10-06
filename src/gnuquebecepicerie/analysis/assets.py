"""Conservation locale des visuels référencés par une nouvelle capture."""

import hashlib
import json
import time
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import httpx

MAX_BYTES = 20 * 1024 * 1024
HOST = "metrocommonapi.blob.core.windows.net"


def image_urls(value):
    """Une résolution maximale par groupe; inclut blocs, carrousels et mentions."""
    found = set()
    if isinstance(value, list):
        if value and all(isinstance(v, dict) and isinstance(v.get("image"), str)
                         and isinstance(v.get("resolution"), (int, float)) for v in value):
            found.add(max(value, key=lambda v: v["resolution"])["image"])
        else:
            for child in value:
                found.update(image_urls(child))
    elif isinstance(value, dict):
        for child in value.values():
            found.update(image_urls(child))
    return found


def permitted(url, publication):
    parsed = urlsplit(url)
    return (parsed.scheme == "https" and parsed.netloc == HOST
            and parsed.path.startswith(f"/{publication}/")
            and ".." not in parsed.path and "%" not in parsed.path
            and not parsed.fragment
            and set(parse_qs(parsed.query, keep_blank_values=True)) <= {"version"})


def capture_assets(client, pages, publication, output, delay=0.2):
    """Le client est dédié aux images, sans en-têtes d'authentification API."""
    folder = output / "assets" / publication
    folder.mkdir(parents=True, exist_ok=False)
    items = []
    for url in sorted(image_urls(pages)):
        # Ne pas conserver une URL inattendue pouvant contenir des secrets.
        item = {"url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                "observed_at": datetime.now(UTC).isoformat()}
        if not permitted(url, publication):
            item.update(status="rejected", reason="unexpected_asset_url")
            items.append(item)
            continue
        item["url"] = url
        time.sleep(delay)
        try:
            with client.stream("GET", url, follow_redirects=False) as response:
                if response.status_code != 200:
                    item.update(status="failed", reason=f"http_{response.status_code}")
                else:
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_BYTES:
                            raise ValueError("asset_too_large")
                    if content.startswith(b"\xff\xd8\xff"):
                        suffix = ".jpg"
                    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
                        suffix = ".png"
                    else:
                        raise ValueError("unsupported_image_content")
                    filename = item["url_sha256"] + suffix
                    (folder / filename).write_bytes(content)
                    item.update(status="saved", file=filename, size=len(content),
                                sha256=hashlib.sha256(content).hexdigest())
        except httpx.HTTPError:
            item.update(status="failed", reason="network_error")
        except ValueError as exc:
            item.update(status="failed", reason=str(exc))
        items.append(item)
    result = {
        "publication": publication, "requested": len(items),
        "saved": sum(i["status"] == "saved" for i in items),
        "complete": bool(items) and all(i["status"] == "saved" for i in items),
        "scope": "referenced_block_images_and_basebars_highest_resolution",
        "commercial_validation_complete": False, "items": items,
    }
    (folder / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
