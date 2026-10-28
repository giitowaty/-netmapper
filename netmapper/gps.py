"""Minimal gpsd client (JSON protocol over TCP, default port 2947)."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class Fix:
    lat: float
    lon: float
    alt: float | None = None


def parse_tpv(line: str) -> Fix | None:
    """Return a Fix from a gpsd TPV message, or None if there is no 2D+ fix."""
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        return None
    if msg.get("class") != "TPV" or msg.get("mode", 0) < 2:
        return None
    if "lat" not in msg or "lon" not in msg:
        return None
    return Fix(lat=float(msg["lat"]), lon=float(msg["lon"]), alt=msg.get("alt"))


class GpsdClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 2947):
        self._sock = socket.create_connection((host, port), timeout=5)
        self._sock.sendall(b'?WATCH={"enable":true,"json":true}\n')
        self._sock.setblocking(False)
        self._buf = b""
        self.fix: Fix | None = None

    def poll(self) -> Fix | None:
        """Consume pending gpsd output without blocking and return the latest fix."""
        while True:
            try:
                chunk = self._sock.recv(4096)
            except BlockingIOError:
                break
            if not chunk:
                raise ConnectionError("gpsd closed the connection")
            self._buf += chunk

        *lines, self._buf = self._buf.split(b"\n")
        for raw in lines:
            fix = parse_tpv(raw.decode(errors="replace"))
            if fix is not None:
                self.fix = fix
        return self.fix

    def close(self) -> None:
        self._sock.close()
