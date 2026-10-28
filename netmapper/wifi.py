"""Parse `iw dev <iface> scan` output and classify Wi-Fi security."""

from __future__ import annotations

import re
from dataclasses import dataclass

BSS_RE = re.compile(r"^BSS ([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})")


@dataclass(frozen=True)
class Network:
    bssid: str
    ssid: str
    freq: int
    channel: int | None
    band: str
    signal: float | None
    security: str


def channel_from_freq(freq: int) -> int | None:
    if freq == 2484:
        return 14
    if 2412 <= freq <= 2472:
        return (freq - 2407) // 5
    if 5000 <= freq <= 5900:
        return (freq - 5000) // 5
    if 5955 <= freq <= 7115:
        return (freq - 5950) // 5
    return None


def band_from_freq(freq: int) -> str:
    if 2400 <= freq < 2500:
        return "2.4 GHz"
    if 4900 <= freq < 5925:
        return "5 GHz"
    if 5925 <= freq <= 7125:
        return "6 GHz"
    return "unknown"


def classify(privacy: bool, rsn_akms: set[str] | None, wpa_akms: set[str] | None) -> str:
    """Return a short security label such as "WPA2" or "WPA3"."""
    if rsn_akms is not None:
        return _classify_rsn(rsn_akms)
    if wpa_akms is not None:
        return "WPA-Enterprise" if _has(wpa_akms, "802.1X") else "WPA"
    return "WEP" if privacy else "Open"


def _classify_rsn(akms: set[str]) -> str:
    if _has(akms, "OWE"):
        return "OWE"
    if _has(akms, "802.1X"):
        return "WPA3-Enterprise" if _has(akms, "SUITE-B") else "WPA2-Enterprise"
    has_sae = _has(akms, "SAE")
    has_psk = _has(akms, "PSK")
    if has_sae and has_psk:
        return "WPA2/WPA3"
    if has_sae:
        return "WPA3"
    if has_psk:
        return "WPA2"
    return "RSN"


def _has(akms: set[str], key: str) -> bool:
    return any(key in akm for akm in akms)


def parse_scan(output: str) -> list[Network]:
    networks: list[Network] = []
    bss: dict | None = None
    section: str | None = None

    for raw in output.splitlines():
        line = raw.strip()
        match = BSS_RE.match(line)
        if match:
            if bss is not None:
                networks.append(_finish(bss))
            bss = {
                "bssid": match.group(1).lower(),
                "ssid": "",
                "freq": 0,
                "signal": None,
                "privacy": False,
                "rsn": None,
                "wpa": None,
            }
            section = None
        elif bss is None or not line:
            continue
        elif line.startswith("freq:"):
            bss["freq"] = int(float(_value(line)))
        elif line.startswith("signal:"):
            bss["signal"] = float(_value(line).split()[0])
        elif line.startswith("SSID:"):
            bss["ssid"] = _value(line)
        elif line.startswith("capability:"):
            bss["privacy"] = "Privacy" in line
        elif line.startswith("RSN:"):
            section = "rsn"
            bss["rsn"] = set()
        elif line.startswith("WPA:"):
            section = "wpa"
            bss["wpa"] = set()

        if section and "Authentication suites:" in line:
            bss[section].update(line.split("Authentication suites:", 1)[1].split())

    if bss is not None:
        networks.append(_finish(bss))
    return networks


def _value(line: str) -> str:
    return line.split(":", 1)[1].strip()


def _finish(bss: dict) -> Network:
    freq = bss["freq"]
    return Network(
        bssid=bss["bssid"],
        ssid=bss["ssid"],
        freq=freq,
        channel=channel_from_freq(freq),
        band=band_from_freq(freq),
        signal=bss["signal"],
        security=classify(bss["privacy"], bss["rsn"], bss["wpa"]),
    )
