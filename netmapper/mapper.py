"""Render scanned networks as a standalone Leaflet HTML map."""

from __future__ import annotations

import html
import json
from pathlib import Path

SECURITY_COLORS = {
    "Open": "#e53935",
    "WEP": "#fb8c00",
    "WPA": "#fdd835",
    "WPA2": "#7cb342",
    "WPA2/WPA3": "#26a69a",
    "WPA3": "#1e88e5",
    "WPA-Enterprise": "#ab47bc",
    "WPA2-Enterprise": "#8e24aa",
    "WPA3-Enterprise": "#5e35b1",
    "OWE": "#78909c",
    "RSN": "#9e9e9e",
}

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  html, body, #map { height: 100%; margin: 0; }
  body { font-family: system-ui, sans-serif; }
  .popup td { padding: 2px 6px; vertical-align: top; }
  .popup th { padding: 2px 6px; text-align: left; font-weight: normal; color: #555; }
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const COLORS = __COLORS__;
const NETWORKS = __DATA__;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => (
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]
  ));
}

const map = L.map("map");
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

const layers = {};
const points = [];
for (const n of NETWORKS) {
  const label = n.security;
  if (!layers[label]) layers[label] = L.layerGroup().addTo(map);

  const marker = L.circleMarker([n.lat, n.lon], {
    radius: 6,
    color: "#222",
    weight: 1,
    fillColor: COLORS[label] || "#9e9e9e",
    fillOpacity: 0.85
  });
  const rows = [
    ["SSID", n.ssid || "<hidden>"],
    ["BSSID", n.bssid],
    ["Security", n.security],
    ["Band / channel", `${n.band} / ${n.channel ?? "?"}`],
    ["Signal", n.signal == null ? "?" : `${n.signal} dBm`],
    ["Seen", `${n.seen}x`],
    ["First seen", n.first_seen],
    ["Last seen", n.last_seen]
  ];
  marker.bindPopup(
    `<table class="popup">${rows.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join("")}</table>`
  );
  marker.addTo(layers[label]);
  points.push([n.lat, n.lon]);
}

L.control.layers(null, layers, {collapsed: false}).addTo(map);
if (points.length) {
  map.fitBounds(points, {padding: [30, 30], maxZoom: 17});
} else {
  map.setView([0, 0], 2);
}
</script>
</body>
</html>
"""


def render_map(networks: list[dict], title: str = "netmapper") -> str:
    # "<" is escaped so no SSID can close the script tag or start a comment.
    data = json.dumps(networks).replace("<", "\\u003c")
    colors = json.dumps(SECURITY_COLORS)
    return (
        TEMPLATE.replace("__TITLE__", html.escape(title))
        .replace("__COLORS__", colors)
        .replace("__DATA__", data)
    )


def write_map(networks: list[dict], path: str, title: str = "netmapper") -> Path:
    out = Path(path)
    out.write_text(render_map(networks, title), encoding="utf-8")
    return out
