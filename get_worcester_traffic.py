#!/usr/bin/env python3
"""Download MassDOT traffic-count locations in Worcester County.

The Roads/TrafficCountLocations feature service has a town field and no
county field, so Worcester County is selected as its 60 municipalities.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

QUERY_URL = (
    "https://gis.massdot.state.ma.us/arcgis/rest/services/"
    "Roads/TrafficCountLocations/FeatureServer/0/query"
)

# The 60 cities and towns of Worcester County, Massachusetts.
WORCESTER_COUNTY_TOWNS = (
    "Ashburnham", "Athol", "Auburn", "Barre", "Berlin", "Blackstone",
    "Bolton", "Boylston", "Brookfield", "Charlton", "Clinton", "Douglas",
    "Dudley", "East Brookfield", "Fitchburg", "Gardner", "Grafton",
    "Hardwick", "Harvard", "Holden", "Hopedale", "Hubbardston", "Lancaster",
    "Leicester", "Leominster", "Lunenburg", "Mendon", "Milford", "Millbury",
    "Millville", "New Braintree", "North Brookfield", "Northborough",
    "Northbridge", "Oakham", "Oxford", "Paxton", "Petersham", "Phillipston",
    "Princeton", "Royalston", "Rutland", "Shrewsbury", "Southborough",
    "Southbridge", "Spencer", "Sterling", "Sturbridge", "Sutton",
    "Templeton", "Upton", "Uxbridge", "Warren", "Webster", "West Boylston",
    "West Brookfield", "Westborough", "Westminster", "Winchendon", "Worcester",
)

OUT_PATH = Path(__file__).with_name("worcester_traffic.geojson")
PAGE_SIZE = 2000


def fetch_page(offset: int) -> dict:
    towns = ", ".join(f"'{name}'" for name in WORCESTER_COUNTY_TOWNS)
    params = {
        "where": f"TOWN IN ({towns})",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "orderByFields": "OBJECTID",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE_SIZE),
    }
    body = urllib.parse.urlencode(params).encode()
    request = urllib.request.Request(QUERY_URL, data=body)
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    if "error" in payload:
        message = payload["error"].get("message", payload["error"])
        raise RuntimeError(f"MassDOT query failed: {message}")
    return payload


def main() -> None:
    features = []
    offset = 0
    while True:
        page = fetch_page(offset)
        batch = page.get("features", [])
        features.extend(batch)
        if not batch or not page.get("exceededTransferLimit"):
            break
        offset += len(batch)

    collection = {"type": "FeatureCollection", "features": features}
    OUT_PATH.write_text(json.dumps(collection), encoding="utf-8")
    print(f"Wrote {len(features)} features to {OUT_PATH.name}")


if __name__ == "__main__":
    main()
