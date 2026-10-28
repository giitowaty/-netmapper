"""SQLite storage for observations: one row per network per scan."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .gps import Fix
from .wifi import Network

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id        INTEGER PRIMARY KEY,
    seen_at   TEXT NOT NULL,
    bssid     TEXT NOT NULL,
    ssid      TEXT NOT NULL,
    freq      INTEGER,
    channel   INTEGER,
    band      TEXT,
    signal    REAL,
    security  TEXT NOT NULL,
    lat       REAL NOT NULL,
    lon       REAL NOT NULL,
    alt       REAL
);
CREATE INDEX IF NOT EXISTS idx_observations_bssid ON observations (bssid);
"""


class Store:
    def __init__(self, path: str):
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        self._db.close()

    def add(self, networks: list[Network], fix: Fix) -> None:
        seen_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._db.executemany(
            "INSERT INTO observations "
            "(seen_at, bssid, ssid, freq, channel, band, signal, security, lat, lon, alt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    seen_at,
                    n.bssid,
                    n.ssid,
                    n.freq,
                    n.channel,
                    n.band,
                    n.signal,
                    n.security,
                    fix.lat,
                    fix.lon,
                    fix.alt,
                )
                for n in networks
            ],
        )
        self._db.commit()

    def networks(self) -> list[dict]:
        """One entry per BSSID, located at its strongest observation."""
        best: dict[str, dict] = {}
        counts: dict[str, int] = {}
        first_seen: dict[str, str] = {}
        last_seen: dict[str, str] = {}

        rows = self._db.execute("SELECT * FROM observations ORDER BY seen_at, id")
        for row in rows:
            bssid = row["bssid"]
            counts[bssid] = counts.get(bssid, 0) + 1
            first_seen.setdefault(bssid, row["seen_at"])
            last_seen[bssid] = row["seen_at"]

            current = best.get(bssid)
            if current is None or _stronger(row["signal"], current["signal"]):
                best[bssid] = dict(row)

        result = []
        for bssid, entry in best.items():
            result.append(
                {
                    "bssid": bssid,
                    "ssid": entry["ssid"],
                    "security": entry["security"],
                    "band": entry["band"],
                    "channel": entry["channel"],
                    "signal": entry["signal"],
                    "lat": entry["lat"],
                    "lon": entry["lon"],
                    "seen": counts[bssid],
                    "first_seen": first_seen[bssid],
                    "last_seen": last_seen[bssid],
                }
            )
        return result


def _stronger(a: float | None, b: float | None) -> bool:
    return a is not None and (b is None or a > b)
