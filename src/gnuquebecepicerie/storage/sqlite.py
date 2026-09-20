from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS flyers (
    flyer_id TEXT PRIMARY KEY,
    retailer_id TEXT NOT NULL,
    store_id TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    json_path TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS offers (
    offer_id TEXT NOT NULL,
    flyer_id TEXT NOT NULL,
    raw_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    brand TEXT,
    sale_price REAL,
    regular_price REAL,
    currency TEXT NOT NULL DEFAULT 'CAD',
    PRIMARY KEY (offer_id, flyer_id),
    FOREIGN KEY (flyer_id) REFERENCES flyers(flyer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_offers_name ON offers(normalized_name);
CREATE INDEX IF NOT EXISTS idx_flyers_period ON flyers(valid_from, valid_to);
"""


def initialize_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
