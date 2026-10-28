"""Command line interface: `netmapper scan` and `netmapper map`."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from .gps import Fix, GpsdClient
from .mapper import write_map
from .store import Store
from .wifi import Network, parse_scan


class FixedPosition:
    """Stand-in for gpsd when testing indoors."""

    def __init__(self, lat: float, lon: float):
        self._fix = Fix(lat=lat, lon=lon)

    def poll(self) -> Fix:
        return self._fix

    def close(self) -> None:
        pass


def run_iw_scan(iface: str) -> list[Network] | None:
    """Passive scan via iw. Returns None if the scan itself failed."""
    proc = subprocess.run(
        ["iw", "dev", iface, "scan"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        print(f"iw scan failed: {proc.stderr.strip()}", file=sys.stderr)
        return None
    return parse_scan(proc.stdout)


def cmd_scan(args: argparse.Namespace) -> int:
    if args.fixed:
        lat, lon = (float(v) for v in args.fixed.split(","))
        gps: FixedPosition | GpsdClient = FixedPosition(lat, lon)
    else:
        gps = GpsdClient(args.gpsd_host, args.gpsd_port)

    store = Store(args.db)
    scans = 0
    try:
        while args.count is None or scans < args.count:
            fix = gps.poll()
            if fix is None:
                print("waiting for GPS fix...", flush=True)
                time.sleep(1)
                continue

            networks = run_iw_scan(args.iface)
            if networks is not None:
                store.add(networks, fix)
                scans += 1
                print(
                    f"scan {scans}: {len(networks)} networks at "
                    f"{fix.lat:.6f},{fix.lon:.6f}",
                    flush=True,
                )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("stopped")
    except FileNotFoundError:
        print("error: 'iw' not found; install the iw package", file=sys.stderr)
        return 1
    finally:
        store.close()
        gps.close()
    return 0


def cmd_map(args: argparse.Namespace) -> int:
    store = Store(args.db)
    try:
        networks = store.networks()
    finally:
        store.close()
    out = write_map(networks, args.out, args.title)
    print(f"wrote {len(networks)} networks to {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netmapper",
        description="Passively log Wi-Fi networks with GPS position and map them.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="scan and log networks with the current GPS fix")
    scan.add_argument("-i", "--iface", required=True, help="wireless interface, e.g. wlan0")
    scan.add_argument("--db", default="netmapper.db", help="SQLite database file")
    scan.add_argument("--interval", type=float, default=5.0, help="seconds between scans")
    scan.add_argument("--count", type=int, help="stop after N successful scans")
    scan.add_argument("--fixed", metavar="LAT,LON", help="use a fixed position instead of gpsd")
    scan.add_argument("--gpsd-host", default="127.0.0.1")
    scan.add_argument("--gpsd-port", type=int, default=2947)
    scan.set_defaults(func=cmd_scan)

    mapp = sub.add_parser("map", help="render the database as an HTML map")
    mapp.add_argument("--db", default="netmapper.db", help="SQLite database file")
    mapp.add_argument("-o", "--out", default="netmapper.html", help="output HTML file")
    mapp.add_argument("--title", default="netmapper")
    mapp.set_defaults(func=cmd_map)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
