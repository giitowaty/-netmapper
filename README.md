# netmapper

Passive Wi-Fi wardriving logger. It records every network your wireless card
hears, tags it with the GPS position, classifies its security (Open, WEP, WPA,
WPA2, WPA3, WPA2/WPA3, OWE, Enterprise variants), and draws everything on an
interactive map.

Standard library only (Python 3.10+). No packages to install.

## Requirements

- Linux with the `iw` tool (`sudo apt install iw`)
- A Wi-Fi adapter in managed mode (any normal card; scanning does not connect)
- Root or `CAP_NET_ADMIN` to run `iw dev <iface> scan`
- Optional: `gpsd` with a GPS receiver (`sudo apt install gpsd gpsd-clients`).
  Without it, use `--fixed LAT,LON` for testing.

## Usage

Scan and log, using gpsd for position:

```bash
sudo python3 -m netmapper scan -i wlan0 --db drive.db --interval 5
```

Scan with a fixed position (indoor test):

```bash
sudo python3 -m netmapper scan -i wlan0 --db test.db --fixed 52.2297,21.0122 --count 3
```

Render the map (open the HTML file in a browser; tiles and Leaflet load from the internet):

```bash
python3 -m netmapper map --db drive.db -o drive.html
```

Each marker is colored by security type. The layer control on the map toggles
each type on or off. Popups show SSID, BSSID, band and channel, best signal,
how many times it was seen, and first/last seen times.

## How it works

- `netmapper/wifi.py` parses `iw dev <iface> scan` output and classifies the
  RSN/WPA information elements (AKM suites: PSK, SAE, 802.1X, OWE).
- `netmapper/gps.py` is a small gpsd JSON client (TCP port 2947).
- `netmapper/store.py` keeps one SQLite row per network per scan. The map uses
  each BSSID's strongest observation as its location.
- `netmapper/mapper.py` writes a single self-contained HTML file with Leaflet.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Scope and responsibility

This tool only listens to beacons and probe responses. It does not connect to,
probe, deauthenticate or attempt to crack any network. Keep the databases and
maps private: BSSIDs at home addresses are personal data in many countries, and
the legality of wardriving varies by location. Use it on your own equipment or
where you are allowed to.
