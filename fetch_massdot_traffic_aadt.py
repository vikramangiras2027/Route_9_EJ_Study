#!/usr/bin/env python3
"""Pull MassDOT AADT for the Worcester/Shrewsbury study area and cache the raw layers.

Services (https://gis.massdot.state.ma.us/arcgis/rest/services/Roads, all FeatureServer):
    TrafficCountLocations/0      count-station points (worcester_traffic.geojson; no volumes)
    RoadInventoryLRS/57          Traffic_Segment: AADT, AADT_Year, F_Class, Statn_Num, Route_ID (polyline)
    RoadInventoryLRS/56          Traffic: AADT_P_Dir / AADT_O_Dir, truck AADT, Segment_ID (polyline)
    RoadInventoryLRS/2           Traffic_Station: StationID on the LRS (point)
    TrafficInventoryYearEnd/1    2024 year-end inventory: St_Name, Route_Number, AADT (polyline, fallback)

Raw pulls are written to cache/massdot/*.geojson and reused on re-run (pass --refresh to re-download).
Run on its own or imported by route9_deep_analysis.py, which calls ensure_massdot_cache().

Usage:  python fetch_massdot_traffic_aadt.py [--refresh]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MASSDOT_DIR = ROOT / "cache" / "massdot"
STATIONS_GEOJSON = ROOT / "worcester_traffic.geojson"

BASE = "https://gis.massdot.state.ma.us/arcgis/rest/services/Roads"
LAYERS = {
    "lrs_traffic_segment": f"{BASE}/RoadInventoryLRS/FeatureServer/57",
    "lrs_traffic": f"{BASE}/RoadInventoryLRS/FeatureServer/56",
    "lrs_traffic_station": f"{BASE}/RoadInventoryLRS/FeatureServer/2",
    "yearend_2024": f"{BASE}/TrafficInventoryYearEnd/FeatureServer/1",
}
STATIONS_URL = f"{BASE}/TrafficCountLocations/FeatureServer/0"

# WGS84 envelope around Worcester + Shrewsbury with room for the 5 km Route 9 buffer
BBOX_4326 = (-71.99, 42.14, -71.55, 42.42)
PAGE = 2000


def post_json(url: str, params: dict, retries: int = 4) -> dict:
    body = urllib.parse.urlencode(params).encode()
    for k in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=180) as r:
                payload = json.load(r)
            if "error" in payload:
                raise RuntimeError(payload["error"].get("message", payload["error"]))
            return payload
        except Exception as exc:
            if k == retries - 1:
                raise RuntimeError(f"MassDOT request failed: {url} ({exc})") from exc
            time.sleep(2 * (k + 1))


def service_meta(layer_url: str) -> dict:
    return post_json(layer_url, {"f": "pjson"})


def query_all(layer_url: str, bbox: tuple | None, where: str = "1=1", geometry: bool = True) -> list[dict]:
    params = {"where": where, "outFields": "*", "returnGeometry": str(geometry).lower(), "outSR": "4326",
              "returnZ": "false", "returnM": "false", "orderByFields": "OBJECTID", "f": "geojson",
              "resultRecordCount": str(PAGE)}
    if bbox:
        params.update(geometry=",".join(map(str, bbox)), geometryType="esriGeometryEnvelope", inSR="4326",
                      spatialRel="esriSpatialRelIntersects")
    feats, offset = [], 0
    while True:
        page = post_json(f"{layer_url}/query", {**params, "resultOffset": str(offset)})
        batch = page.get("features", [])
        feats.extend(batch)
        if not batch or not page.get("exceededTransferLimit"):
            return feats
        offset += len(batch)


def ensure_massdot_cache(refresh: bool = False, log=print) -> dict[str, Path]:
    MASSDOT_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for key, url in LAYERS.items():
        dest = MASSDOT_DIR / f"{key}.geojson"
        paths[key] = dest
        if dest.exists() and not refresh:
            continue
        log(f"  MassDOT {url.split('/rest/services/')[1]} -> {dest.name}")
        feats = query_all(url, BBOX_4326)
        dest.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
        log(f"    {len(feats):,} features")
    stations = MASSDOT_DIR / "traffic_count_locations.geojson"
    paths["stations"] = stations
    if not stations.exists() or refresh:
        if STATIONS_GEOJSON.exists() and not refresh:
            stations.write_bytes(STATIONS_GEOJSON.read_bytes())
        else:
            import get_worcester_traffic
            get_worcester_traffic.main()
            stations.write_bytes(get_worcester_traffic.OUT_PATH.read_bytes())
    (MASSDOT_DIR / "fetch_log.json").write_text(json.dumps(
        {"fetched": time.strftime("%Y-%m-%d %H:%M:%S"), "bbox_4326": BBOX_4326,
         "layers": {**LAYERS, "stations": STATIONS_URL}}, indent=2), encoding="utf-8")
    return paths


if __name__ == "__main__":
    ensure_massdot_cache(refresh="--refresh" in sys.argv)
    print("MassDOT cache ready:", MASSDOT_DIR)
