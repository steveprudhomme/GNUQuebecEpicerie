from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def archive_directory(data_root: Path, retailer_id: str, valid_from: str) -> Path:
    year = valid_from[:4]
    return data_root / year / retailer_id / valid_from


def write_json_atomic(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)
