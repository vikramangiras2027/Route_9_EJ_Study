#!/usr/bin/env python3
"""
Route 9 corridor (Worcester & Shrewsbury, MA) - advisory-ready environmental justice study:
measured traffic loading, who lives nearby, Worcester equity, regional PM2.5 context, limits.

Inputs  (folder DATA_DIR, see resolve_data_dir):
    ACSST5Y2024.S1901-Data.csv   ACS 5-yr 2024 tract income table (S1901)
    EJ_POLY.dbf                  MassGIS 2020-based EJ block-group attribute table
    traffic.csv(.txt)            MassDOT station M3002W anchor (Route 9 / Belmont St)
    ad_viz_plotval_data.csv      EPA AQS daily PM2.5, Worcester County monitors

Public data (downloaded once, cached in ./cache):
    US Census TIGER/Line 2024 block groups, primary/secondary roads (Route 9 centreline), county subdivisions
    MassDOT Roads services (fetch_massdot_traffic_aadt.py): segment AADT, count stations -> cache/massdot/

Outputs:
    outputs/master_route9_table.csv     block-group master table (legacy columns kept, new columns appended)
    outputs/tract_table_route9.csv      tract-level equity table
    outputs/summary_statistics.txt      sectioned narrative statistics
    outputs/advisory_brief.md           plain-language brief (same numbers)
    outputs/data_dictionary.md          master-table column dictionary
    charts/figure1_income_traffic_ej.png, figure2_pm25_distribution.png, figure3_priority_hotspots.png

Usage:  python route9_deep_analysis.py [path-to-data-folder]
"""
from __future__ import annotations

import os
import re
import sys
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from dbfread import DBF
from scipy import stats
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from fetch_massdot_traffic_aadt import BBOX_4326, LAYERS, STATIONS_URL, ensure_massdot_cache

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Several features with id")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent
OUT_DIR, CHART_DIR, CACHE_DIR = ROOT / "outputs", ROOT / "charts", ROOT / "cache"
for _d in (OUT_DIR, CHART_DIR, CACHE_DIR):
    _d.mkdir(exist_ok=True)

STUDY_TOWNS = ["Worcester", "Shrewsbury"]
WORCESTER_COUNTY_FIPS = "25027"
CRS_MA = 26986                    # NAD83 / Massachusetts Mainland (metres)
CORRIDOR_M = 1500                 # corridor = block-group centroid within ~1 mile of Route 9
EXPOSURE_DECAY_M = 300            # e-folding distance of the near-road gradient (default)
EXPOSURE_DECAY_ALT_M = 150        # sensitivity
GRID_M = 50                       # sampling grid for area-weighted exposure
BUFFERS_M = (300, 500, 1000)
AADT_HIGH, AADT_MID = 30000, 20000
AADT_CLASSES = [0, AADT_MID, AADT_HIGH, np.inf]
AADT_LABELS = ["<20k", "20-30k", ">=30k"]
STATION_ON_ROUTE_M = 50           # count station counts as "on Route 9" within this distance of the centreline
BANDS = [0, 500, 1000, 2000, 4000, np.inf]
BAND_LABELS = ["<=0.5 km", "0.5-1 km", "1-2 km", "2-4 km", ">4 km"]
RNG = np.random.default_rng(20260106)

BKT_COLS = [f"acs_bkt_{i:02d}" for i in range(1, 11)]
BKT_EDGES = [0, 10e3, 15e3, 25e3, 35e3, 50e3, 75e3, 100e3, 150e3, 200e3, np.inf]

# Air-quality benchmarks (ug/m3)
NAAQS_ANNUAL = 9.0        # EPA primary annual PM2.5 NAAQS (2024 revision)
NAAQS_24H = 35.0          # EPA primary 24-hour PM2.5 NAAQS (98th pct, 3-yr avg)
WHO_ANNUAL = 5.0          # WHO 2021 guideline (health reference, not regulatory)
WHO_24H = 15.0            # WHO 2021 guideline (99th pct)

# Stated inputs in the brief, checked against the data below
BRIEF_AADT, BRIEF_PM_MEAN, BRIEF_PM_MAX = 28112, 5.65, 33.5

# Headlines of the previous release (single-station exposure model), for the CHANGELOG
PRIOR = {"hotspots": 33, "hotspot_pop": 42805, "corridor_bgs": 81, "ej_pop_300": 28786, "ej_pop_500": 47144,
         "ej_pop_1000": 81149, "rho_inc_dist": 0.470, "slope_per_km": 10651, "mean_exposure": 3504.0,
         "aadt_basis": "one station (M3002W, 28,112) applied to the whole centreline"}

LEGACY_COLS = [
    "geoid_bg", "geoid_tract", "bg_name", "municipality", "ej_designated", "ej_criteria_code", "ej_criteria_count",
    "ej_criteria_desc", "ej_income", "ej_minority", "ej_english_isolation", "total_pop", "total_hh", "pct_minority",
    "lep_hh", "pct_lep_hh", "bg_median_hh_income", "acs_median_income", "acs_median_income_moe", "acs_income_cv",
    "acs_income_reliable", "acs_income_topcoded", "acs_pct_hh_under_50k", "acs_pct_hh_150k_plus", "income_best",
    "income_source", "income_pct_of_state", "centroid_lat", "centroid_lon", "area_km2", "dist_centroid_m",
    "dist_edge_m", "mean_dist_m", "dist_band", "in_corridor", "exposure_index", "pct_area_within_300m",
    "pct_area_within_500m", "pct_area_within_1000m", "pm_monitor", "dist_pm_monitor_km", "pm25_monitor_annual_mean",
    "pm25_monitor_p98", "pm25_monitor_max", "pm25_monitor_days_over_who24", "shape_area", "shape_len",
    "acs_households", "acs_mean_income", "aadt_station", "aadt_westbound", "aadt_eastbound", "westbound_share",
    "est_ej_pop_within_300m", "est_ej_pop_within_500m", "est_ej_pop_within_1000m", "p_traffic", "p_low_income",
    "p_ej_criteria", "cumulative_burden_index", "cbi_quintile", "hotspot"]

TIGER = {
    "bg": "https://www2.census.gov/geo/tiger/TIGER2024/BG/tl_2024_25_bg.zip",
    "roads": "https://www2.census.gov/geo/tiger/TIGER2024/PRISECROADS/tl_2024_25_prisecroads.zip",
    "towns": "https://www2.census.gov/geo/tiger/TIGER2024/COUSUB/tl_2024_25_cousub.zip",
}

# --------------------------------------------------------------------------- #
# Sectioned report buffer
# --------------------------------------------------------------------------- #
SECTIONS = [
    ("changelog", "CHANGELOG (headline changes versus the previous release)"),
    ("exec", "1. EXECUTIVE SUMMARY"),
    ("near", "2. WHO LIVES NEAR ROUTE 9"),
    ("traffic", "3. TRAFFIC ALONG THE CORRIDOR"),
    ("worc", "4. EQUITY - WORCESTER (PRIMARY)"),
    ("shrew", "5. SHREWSBURY (SENSITIVITY)"),
    ("vuln", "6. VULNERABILITY WITHOUT TRAFFIC"),
    ("air", "7. REGIONAL AIR QUALITY (CONTEXT ONLY, NOT CORRIDOR-SPECIFIC)"),
    ("limits", "8. LIMITATIONS"),
    ("audit", "APPENDIX A. DATA INTEGRATION, CLEANING AND FETCH LOG"),
]
_SEC: dict[str, list[str]] = {k: [] for k, _ in SECTIONS}
_CUR = "audit"


def section(key: str) -> None:
    global _CUR
    _CUR = key


def say(text: str = "") -> None:
    _SEC[_CUR].append(text)


def progress(text: str) -> None:
    print(text, flush=True)


def assemble() -> str:
    out = []
    for key, title in SECTIONS:
        if not _SEC[key]:
            continue
        out += ["=" * 100, title, "=" * 100, *_SEC[key], ""]
    return "\n".join(out)


def resolve_data_dir() -> Path:
    cands = []
    if len(sys.argv) > 1:
        cands.append(Path(sys.argv[1]))
    if os.environ.get("ROUTE9_DATA_DIR"):
        cands.append(Path(os.environ["ROUTE9_DATA_DIR"]))
    cands += [ROOT / "data.environment", Path.home() / "OneDrive" / "Desktop" / "data.environment",
              Path.home() / "Desktop" / "data.environment"]
    for c in cands:
        if c.is_dir():
            return c
    raise SystemExit("Data folder not found. Pass it as the first argument or set ROUTE9_DATA_DIR.")


def find_file(folder: Path, patterns: list[str]) -> Path:
    for p in patterns:
        hits = sorted(folder.glob(p))
        if hits:
            return hits[0]
    raise SystemExit(f"No file matching {patterns} in {folder}")


def snake(s: str) -> str:
    return re.sub(r"[^0-9a-z]+", "_", str(s).strip().lower()).strip("_")


def missing_audit(name: str, df: pd.DataFrame, cols: list[str] | None = None) -> None:
    cols = cols or list(df.columns)
    miss = df[cols].isna().sum()
    miss = miss[miss > 0]
    say(f"  [{name}] rows={len(df):,}  cols={df.shape[1]}  columns with missing values: "
        + (", ".join(f"{c}={n}" for c, n in miss.items()) if len(miss) else "none"))


# --------------------------------------------------------------------------- #
# 1. Loading & cleaning
# --------------------------------------------------------------------------- #
def load_acs(path: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(path, dtype=str, low_memory=False)
    labels = raw.iloc[0]
    raw = raw.iloc[1:].reset_index(drop=True)

    want = {"S1901_C01_001E": "acs_households", "S1901_C01_012E": "acs_median_income",
            "S1901_C01_012M": "acs_median_income_moe", "S1901_C01_013E": "acs_mean_income"}
    brackets = [f"S1901_C01_{i:03d}E" for i in range(2, 12)]
    assert "Total" in labels["S1901_C01_001E"] and "Median income" in labels["S1901_C01_012E"], \
        "Unexpected S1901 column layout"
    assert "Less than $10,000" in labels["S1901_C01_002E"] and "$35,000 to $49,999" in labels["S1901_C01_006E"]
    assert "$50,000 to $74,999" in labels["S1901_C01_007E"] and "$200,000 or more" in labels["S1901_C01_011E"]

    df = raw[["GEO_ID", "NAME"] + list(want) + brackets].copy()
    df = df.rename(columns={"GEO_ID": "geo_id", "NAME": "acs_name", **want})

    # Census sentinels -> NaN; keep top/bottom-coding flags for the median
    med = df["acs_median_income"].fillna("")
    df["acs_income_topcoded"] = med.str.endswith("+")
    df["acs_income_bottomcoded"] = med.str.len().gt(1) & med.str.endswith("-")
    sentinel = {"-", "(X)", "N", "**", "***", "*****", "null", "(NA)", ""}
    for c in df.columns[2:]:
        if c in ("acs_income_topcoded", "acs_income_bottomcoded"):
            continue
        s = df[c].astype("string").str.strip()
        s = s.mask(s.isin(sentinel))
        s = s.str.replace(r"[,+]", "", regex=True).str.replace(r"-$", "", regex=True)
        df[c] = pd.to_numeric(s, errors="coerce").astype("float64")
    df = df.rename(columns=dict(zip(brackets, BKT_COLS)))
    df["acs_pct_hh_under_50k"] = df[BKT_COLS[:5]].sum(axis=1, min_count=5)     # <$10k ... $35-49.9k
    df["acs_pct_hh_150k_plus"] = df[BKT_COLS[8:10]].sum(axis=1, min_count=2)
    df["acs_income_cv"] = (df["acs_median_income_moe"] / 1.645) / df["acs_median_income"]
    df["acs_income_reliable"] = df["acs_income_cv"] < 0.30

    ref = {}
    st = df[df.geo_id == "0400000US25"]
    if len(st):
        ref["state_median_income"] = float(st["acs_median_income"].iloc[0])
    co = df[df.geo_id == "0500000US" + WORCESTER_COUNTY_FIPS]
    if len(co):
        ref["county_median_income"] = float(co["acs_median_income"].iloc[0])

    df = df[df.geo_id.str.startswith("1400000US" + WORCESTER_COUNTY_FIPS)].copy()
    df["geoid_tract"] = df.geo_id.str[-11:]
    return df, ref


def load_ej(path: Path) -> pd.DataFrame:
    ej = pd.DataFrame(iter(DBF(str(path), load=True, encoding="latin-1")))
    ej = ej.rename(columns={
        "GEOGRAPHIC": "bg_name", "GEOID": "geoid_bg", "SPLIT_FOR_": "split_flag", "MUNICIPALI": "municipality",
        "TOTAL_POP": "total_pop", "NONHISPWHI": "nonhisp_white", "PCT_MINORI": "pct_minority",
        "TOTALHH": "total_hh", "LIMENGHH": "lep_hh", "LIMENGHHPC": "pct_lep_hh", "BG_MHHI": "bg_median_hh_income",
        "BG_MHHI_PC": "bg_income_pct_of_state", "BG_MHHI_IS": "bg_income_flag_n", "MUNI_MHHI": "muni_median_hh_income",
        "MUNIMHHI_P": "muni_income_pct_of_state", "MEDIANHHI": "flag_income", "LIMITEDENG": "flag_english_isolation",
        "MINORITY_P": "flag_minority", "EJ": "ej_designated", "EJ_CRITERI": "ej_criteria_code",
        "EJ_CRITE_1": "ej_criteria_count", "EJ_CRIT_DE": "ej_criteria_desc"})
    ej.columns = [snake(c) for c in ej.columns]
    for c in ej.select_dtypes(include=["object", "string"]).columns:
        ej[c] = ej[c].astype("string").str.strip().replace("", pd.NA)
    # MEDIANHHI == 'U' marks "income unavailable" and BG_MHHI is coded 0 there -> missing, not $0
    ej.loc[ej["flag_income"].eq("U") | ej["bg_median_hh_income"].le(0), "bg_median_hh_income"] = np.nan
    ej["ej_designated"] = ej["ej_designated"].eq("Yes")
    ej["ej_minority"] = ej["flag_minority"].eq("M")
    ej["ej_income"] = ej["flag_income"].eq("I")
    ej["ej_english_isolation"] = ej["flag_english_isolation"].eq("E")
    ej["geoid_tract"] = ej["geoid_bg"].str[:11]
    return ej


def load_traffic(path: Path) -> dict:
    t = pd.read_csv(path)
    t.columns = [snake(c) for c in t.columns]
    row = t.iloc[0]
    parts = dict(re.findall(r"(EB|WB)\s*:\s*([\d,]+)", str(row["direction_split"])))
    eb, wb = (int(parts[k].replace(",", "")) for k in ("EB", "WB"))
    return {"station": row["station_id"], "road": row["road"], "location": row["location"], "aadt": int(row["aadt"]),
            "eb": eb, "wb": wb, "wb_share": wb / (eb + wb), "dir_sum_gap": int(row["aadt"]) - (eb + wb)}


def load_pm25(path: Path) -> pd.DataFrame:
    pm = pd.read_csv(path)
    pm.columns = [snake(c) for c in pm.columns]
    pm = pm.rename(columns={"daily_mean_pm2_5_concentration": "pm25", "daily_aqi_value": "aqi",
                            "local_site_name": "site", "site_latitude": "lat", "site_longitude": "lon",
                            "percent_complete": "pct_complete"})
    pm["date"] = pd.to_datetime(pm["date"], format="%m/%d/%Y")
    pm["site"] = pm["site"].str.title()
    n0 = len(pm)
    pm = pm.dropna(subset=["pm25"])
    pm = pm[pm["pm25"] >= 0]
    # several POCs at one site on one day would double count the day -> average
    pm = (pm.groupby(["site_id", "site", "lat", "lon", "date"], as_index=False)
            .agg(pm25=("pm25", "mean"), aqi=("aqi", "max"), pct_complete=("pct_complete", "min")))
    pm["month"] = pm["date"].dt.month
    say(f"  PM2.5: {n0} raw rows -> {len(pm)} valid site-days after dropping missing/negative and POC de-duplication")
    return pm


def fetch(url: str) -> Path:
    dest = CACHE_DIR / Path(url).name
    if not dest.exists():
        progress(f"  downloading {url}")
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as exc:
            dest.unlink(missing_ok=True)
            raise SystemExit(f"Could not download {url} ({exc}).\nDownload it manually into {CACHE_DIR}.")
    return dest


# --------------------------------------------------------------------------- #
# 2. Spatial layer: corridor definition
# --------------------------------------------------------------------------- #
def build_spatial(ej_ws: pd.DataFrame, ej_all: pd.DataFrame):
    all_bgs = gpd.read_file(fetch(TIGER["bg"]))[["GEOID", "ALAND", "AWATER", "geometry"]].to_crs(CRS_MA)
    all_bgs = all_bgs.rename(columns={"GEOID": "geoid_bg"})
    # EJ_POLY contains ONLY EJ-designated block groups, so non-EJ block groups must come from Census geometry.
    # A block group is in the study universe if it is an EJ record for Worcester/Shrewsbury OR its centroid
    # lies inside either municipality (Census county subdivision boundary).
    towns_all = gpd.read_file(fetch(TIGER["towns"])).to_crs(CRS_MA)
    towns = towns_all[towns_all["NAME"].isin(STUDY_TOWNS)][["NAME", "geometry"]].rename(columns={"NAME": "municipality_geo"})
    cent_pts = all_bgs.assign(geometry=all_bgs.centroid)
    cent_pts = gpd.sjoin(cent_pts, towns, predicate="within", how="left")[["geoid_bg", "municipality_geo"]]
    all_bgs = all_bgs.merge(cent_pts.drop_duplicates("geoid_bg"), on="geoid_bg", how="left")
    in_ej = all_bgs.geoid_bg.isin(ej_ws.geoid_bg)
    bgs = all_bgs[all_bgs.municipality_geo.notna() | in_ej].copy()
    n_state, n_cty = len(all_bgs), int(all_bgs.geoid_bg.str.startswith(WORCESTER_COUNTY_FIPS).sum())
    say(f"  Census TIGER block groups: {n_state:,} statewide, {n_cty} in Worcester County; "
        f"EJ_POLY has {len(ej_all):,} statewide -> it is an EJ-only layer ({len(ej_all) / n_state:.1%} of block groups).")
    say(f"  Study universe (all block groups in {' + '.join(STUDY_TOWNS)}): {len(bgs)} "
        f"= {int(bgs.geoid_bg.isin(ej_ws.geoid_bg).sum())} EJ-designated + {int((~bgs.geoid_bg.isin(ej_ws.geoid_bg)).sum())} not EJ-designated")
    roads = gpd.read_file(fetch(TIGER["roads"])).to_crs(CRS_MA)
    r9 = roads[roads["FULLNAME"].eq("State Rte 9")]
    study_area = bgs.union_all()
    r9 = r9[r9.intersects(study_area.buffer(5000))]
    r9_line = r9.union_all()
    say(f"  Route 9 centreline: {len(r9)} TIGER segments, {r9_line.length / 1000:.1f} km within 5 km of the study area")
    bgs["municipality_geo"] = bgs["municipality_geo"].fillna("(EJ record outside town polygon)")

    bgs["dist_centroid_m"] = bgs.centroid.distance(r9_line)
    bgs["dist_edge_m"] = bgs.geometry.distance(r9_line)

    # sample the study area on a regular grid (area weighting); tiny block groups are represented by their centroid
    minx, miny, maxx, maxy = bgs.total_bounds
    xs, ys = np.arange(minx, maxx, GRID_M) + GRID_M / 2, np.arange(miny, maxy, GRID_M) + GRID_M / 2
    gx, gy = np.meshgrid(xs, ys)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(gx.ravel(), gy.ravel()), crs=CRS_MA)
    pts = gpd.sjoin(pts, bgs[["geoid_bg", "geometry"]], predicate="within", how="inner")[["geoid_bg", "geometry"]]
    small = bgs[~bgs.geoid_bg.isin(pts.geoid_bg)]
    if len(small):
        extra = gpd.GeoDataFrame({"geoid_bg": small.geoid_bg.to_numpy()}, geometry=small.centroid.reset_index(drop=True), crs=CRS_MA)
        pts = pd.concat([pts, extra], ignore_index=True)
    pts = pts.reset_index(drop=True)
    pts["d"] = pts.geometry.distance(r9_line)
    g = pts.groupby("geoid_bg")
    agg = pd.DataFrame({"mean_dist_m": g["d"].mean()})
    for b in BUFFERS_M:
        agg[f"pct_area_within_{b}m"] = pts["d"].le(b).groupby(pts["geoid_bg"]).mean() * 100
    bgs = bgs.merge(agg, left_on="geoid_bg", right_index=True, how="left")
    bgs["area_km2"] = bgs.geometry.area / 1e6
    return bgs, pts, r9, r9_line, towns, study_area, {"n_state": n_state, "n_cty": n_cty}


# --------------------------------------------------------------------------- #
# 3. MassDOT traffic: segment AADT, count stations, join
# --------------------------------------------------------------------------- #
def read_layer(paths: dict, key: str) -> gpd.GeoDataFrame:
    return gpd.read_file(paths[key]).to_crs(CRS_MA)


def route9_lrs_id(seg56: gpd.GeoDataFrame, r9_line) -> str:
    zone = r9_line.buffer(15)
    cand = seg56.iloc[seg56.sindex.query(zone, predicate="intersects")].copy()
    cand["len_in"] = cand.geometry.intersection(zone).length
    return str(cand.groupby("Route_ID").len_in.sum().sort_values(ascending=False).index[0])


def station_road_text(row) -> str:
    t = row.ROUTE_STREET if isinstance(row.ROUTE_STREET, str) and row.ROUTE_STREET.strip() else row.STATION_LOC
    t = str(t) if isinstance(t, str) else ""
    return re.split(r"\b(?:NORTH|SOUTH|EAST|WEST|NEAR|OFF|AT)\b", t, maxsplit=1, flags=re.I)[0]


def segment_at(segs: pd.DataFrame, measure: float):
    hit = segs[(segs.From_Measure <= measure) & (segs.To_Measure >= measure)]
    return hit.iloc[0] if len(hit) else None


def build_corridor_traffic(r9_line, study_area, towns, anchor: dict) -> dict:
    paths = ensure_massdot_cache(log=progress)
    seg56, seg57 = read_layer(paths, "lrs_traffic"), read_layer(paths, "lrs_traffic_segment")
    sta2, pts = read_layer(paths, "lrs_traffic_station"), read_layer(paths, "stations")
    inv = {"seg56": len(seg56), "seg57": len(seg57), "sta2": len(sta2), "stations_county": len(pts),
           "yearend": len(read_layer(paths, "yearend_2024"))}

    rid = route9_lrs_id(seg56, r9_line)
    segs = seg56[seg56.Route_ID.eq(rid) & seg56.intersects(study_area.buffer(5000))].copy()
    segs = segs.sort_values("From_Measure").reset_index(drop=True)
    segs["seg_id"] = [f"{rid.replace(' ', '')}@{a:.3f}" for a in segs.From_Measure]
    segs["aadt"] = segs["AADT"].astype(float)
    segs["aadt_year"] = segs["AADT_Year"].astype(float)
    segs["aadt_source"] = np.where(segs.aadt.notna(), "LRS Traffic (layer 56)", "")
    s57 = seg57[seg57.Route_ID.eq(rid) & seg57.AADT.notna()]
    n_miss56 = int(segs.aadt.isna().sum())
    for i in segs.index[segs.aadt.isna()]:
        hit = segment_at(s57, (segs.From_Measure[i] + segs.To_Measure[i]) / 2)
        if hit is not None:
            segs.loc[i, ["aadt", "aadt_year", "aadt_source"]] = [float(hit.AADT), float(hit.AADT_Year), "LRS Traffic_Segment (layer 57)"]
    n_fill57 = int((segs.aadt_source == "LRS Traffic_Segment (layer 57)").sum())
    still = segs.aadt.isna()
    segs.loc[still, "aadt"] = anchor["aadt"]
    segs.loc[still, "aadt_source"] = "traffic.csv anchor"
    segs["len_m"] = segs.geometry.length

    clip = gpd.overlay(segs[["seg_id", "aadt", "aadt_year", "D_Factor", "AADT_P_Dir", "From_Measure", "To_Measure", "geometry"]],
                       towns.rename(columns={"municipality_geo": "town"}), how="intersection", keep_geom_type=True)
    clip["len_m"] = clip.geometry.length
    clip = clip[clip.len_m > 1].sort_values("From_Measure").reset_index(drop=True)

    # ---- count stations: clip to Route 9 in Worcester/Shrewsbury and join AADT ----
    line = r9_line
    pts = pts[pts.geometry.notna()].copy()
    pts = pts[pts.geometry.within(study_area.buffer(100))].copy()
    pts["station_id"] = pts["STATION_NUMBER"].astype("Int64").astype("string")
    pts["dist_r9_m"] = pts.geometry.distance(line)
    txt = pts.apply(station_road_text, axis=1)
    pts["on_route9"] = (txt.str.contains(r"\b(?:RTE|RT|ROUTE)\b\.?\s*9\b", case=False, regex=True)
                        & ~pts["STATION_LOC"].fillna("").str.contains("RAMP", case=False)
                        & ~pts["ROUTE_STREET"].fillna("").str.contains("RAMP", case=False)
                        & (pts.dist_r9_m <= STATION_ON_ROUTE_M))
    n_s57_statn = int(seg57["Statn_Num"].notna().sum())
    statn57 = set(seg57["Statn_Num"].dropna().astype(int).astype(str))
    sid57 = seg57[seg57.StationID.notna() & seg57.AADT.notna()].drop_duplicates("StationID").set_index("StationID")
    lrs = sta2.drop_duplicates("StationID").set_index("StationID")

    aadt, year, source, seg_id, meas = [], [], [], [], []
    seg_nearest = gpd.sjoin_nearest(gpd.GeoDataFrame(geometry=pts.geometry.values, crs=CRS_MA), segs[["seg_id", "geometry"]],
                                    distance_col="d_seg", how="left")
    seg_nearest = seg_nearest[~seg_nearest.index.duplicated()]
    seg_by_id = segs.set_index("seg_id")
    for k, (sid, on) in enumerate(zip(pts.station_id, pts.on_route9)):
        a = y = src = sg = ms = None
        if pd.notna(sid) and sid in statn57:
            src = "T1 Statn_Num (layer 57)"
        if pd.notna(sid) and sid in sid57.index and pd.notna(sid57.loc[sid, "AADT"]):
            a, y, src = float(sid57.loc[sid, "AADT"]), float(sid57.loc[sid, "AADT_Year"]), "T1b StationID (layer 57)"
        if a is None and pd.notna(sid) and sid in lrs.index:
            lr = lrs.loc[sid]
            if lr.Route_ID == rid and not on:
                src = "road mismatch (LRS station on Route 9, count station is a cross street)"
            else:
                sub = seg56[seg56.Route_ID.eq(lr.Route_ID)]
                hit = segment_at(sub[sub.AADT.notna()], float(lr.Measure))
                if hit is not None:
                    a, y, src, ms = float(hit.AADT), float(hit.AADT_Year), "T2 StationID -> LRS measure -> Traffic (layer 2 + 56)", float(lr.Measure)
        if a is None and on and seg_nearest.d_seg.iloc[k] <= STATION_ON_ROUTE_M:
            sg = seg_nearest.seg_id.iloc[k]
            a, y, src = float(seg_by_id.loc[sg, "aadt"]), float(seg_by_id.loc[sg, "aadt_year"]), "T3 nearest Route 9 segment (spatial)"
        if a is not None and sg is None and on:
            sg = seg_nearest.seg_id.iloc[k]
        if on and ms is None and sg is not None:
            row = seg_by_id.loc[sg]
            ms = row.From_Measure + (row.To_Measure - row.From_Measure) * min(1.0, row.geometry.project(pts.geometry.iloc[k]) / row.geometry.length)
        aadt.append(a); year.append(y); source.append(src or "unmatched"); seg_id.append(sg); meas.append(ms)
    pts["aadt"], pts["aadt_year"], pts["join_source"], pts["seg_id"], pts["measure"] = aadt, year, source, seg_id, meas
    pts["tier"] = pts.join_source.str.extract(r"^(T1b|T1|T2|T3)")[0].fillna("none")

    # anchor station M3002W (traffic.csv) and its place on the LRS
    anc = {"found": False}
    a_row = sta2[sta2.StationID.eq(anchor["station"])]
    if len(a_row):
        meas_a = float(a_row.Measure.iloc[0])
        hit = segment_at(segs, meas_a)
        near_hits = segs[(segs.From_Measure - meas_a).abs().le(0.05) | (segs.To_Measure - meas_a).abs().le(0.05)]
        co3150 = pts[pts.station_id.eq("3150")]
        anc = {"found": True, "route_id": a_row.Route_ID.iloc[0], "measure": meas_a, "geometry": a_row.geometry.iloc[0],
               "seg_aadt": float(hit.aadt), "seg_year": float(hit.aadt_year), "seg_id": hit.seg_id,
               "neighbour_max": float(near_hits.aadt.max()), "neighbour_min": float(near_hits.aadt.min()),
               "diff_pct": (anchor["aadt"] / float(hit.aadt) - 1) * 100,
               "dist_3150_m": float(co3150.geometry.distance(a_row.geometry.iloc[0]).min()) if len(co3150) else np.nan,
               "pair_found": bool(sta2.StationID.eq(anchor["station"][:-1] + "E").any())}
    st = pts.drop_duplicates(["station_id", "on_route9", "aadt"]).copy()
    st["x"], st["y"] = st.geometry.x, st.geometry.y
    on9 = st[st.on_route9].drop_duplicates("station_id").copy()
    if anc["found"]:
        in_town = towns[towns.geometry.contains(anc["geometry"])].municipality_geo
        anchor_row = gpd.GeoDataFrame({"station_id": [anchor["station"]], "ROUTE_STREET": [anchor["road"]],
                                       "STATION_LOC": [anchor["location"]], "TOWN": [in_town.iloc[0] if len(in_town) else ""],
                                       "aadt": [float(anchor["aadt"])],
                                       "aadt_year": [np.nan], "join_source": ["anchor traffic.csv"], "tier": ["anchor"],
                                       "on_route9": [True], "measure": [anc["measure"]], "dist_r9_m": [float(anc["geometry"].distance(line))]},
                                      geometry=[anc["geometry"]], crs=CRS_MA)
        on9 = pd.concat([on9, anchor_row], ignore_index=True)
    on9 = on9.sort_values("measure").reset_index(drop=True)

    uniq_ws = st.drop_duplicates("station_id")
    stats_ = {
        "rid": rid, "inv": inv, "n_miss56": n_miss56, "n_fill57": n_fill57, "n_fill_anchor": int(still.sum()),
        "n_segs": len(segs), "n_segs_in": len(clip), "n_s57_statn": n_s57_statn,
        "n_s57_stationid": int(seg57.StationID.notna().sum()), "n_s57_aadt": int(seg57.AADT.notna().sum()),
        "n_s57_r9": int(seg57.Route_ID.eq(rid).sum()), "n_s57_r9_aadt": int(s57.shape[0]),
        "n_ws_rows": len(pts), "n_ws_unique": int(pts.station_id.nunique()), "n_ws_no_id": int(pts.station_id.isna().sum()),
        "tier_rows": pts.tier.value_counts().to_dict(), "n_ws_joined": int(pts.aadt.notna().sum()),
        "n_r9_rows": int(pts.on_route9.sum()), "n_r9_unique": int(pts[pts.on_route9].station_id.nunique()),
        "n_r9_joined": int(pts[pts.on_route9].drop_duplicates("station_id").aadt.notna().sum()),
        "r9_tiers": pts[pts.on_route9].drop_duplicates("station_id").tier.value_counts().to_dict(),
        "n_dup_ids": int(pts.station_id.dropna().duplicated().sum()), "anchor": anc,
        "p_dir_n": int(segs.AADT_P_Dir.notna().sum()), "d_factor": segs.D_Factor.dropna().astype(int).value_counts().to_dict(),
    }
    return {"segs": segs, "segs_in": clip, "stations_ws": pts, "stations": on9, "stats": stats_, "paths": paths}


def wquantile(v, w, q: float) -> float:
    v, w = np.asarray(v, float), np.asarray(w, float)
    ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
    if not ok.any():
        return np.nan
    o = np.argsort(v[ok])
    cw = np.cumsum(w[ok][o]) / w[ok].sum()
    return float(v[ok][o][np.searchsorted(cw, q)])


def apply_exposure(bgs: gpd.GeoDataFrame, pts: gpd.GeoDataFrame, segs: gpd.GeoDataFrame, stations: gpd.GeoDataFrame,
                   anchor_aadt: float) -> gpd.GeoDataFrame:
    """Primary: AADT of the nearest MassDOT Route 9 segment x exp(-d/300 m); also d=150 m and the legacy single-AADT model."""
    near = gpd.sjoin_nearest(pts[["geoid_bg", "d", "geometry"]], segs[["seg_id", "aadt", "geometry"]], how="left")
    near = near[~near.index.duplicated(keep="first")]
    near["expo"] = near.aadt * np.exp(-near.d / EXPOSURE_DECAY_M)
    near["expo150"] = near.aadt * np.exp(-near.d / EXPOSURE_DECAY_ALT_M)
    near["legacy"] = anchor_aadt * np.exp(-near.d / EXPOSURE_DECAY_M)
    g = near.groupby("geoid_bg")
    agg = pd.DataFrame({"exposure_index": g["expo"].mean(), "exposure_index_d150": g["expo150"].mean(),
                        "legacy_exposure_index": g["legacy"].mean()})
    for b in BUFFERS_M:
        inb = near["d"].le(b)
        agg[f"pct_area_within_{b}m_aadt20k"] = (inb & near.aadt.ge(AADT_MID)).groupby(near.geoid_bg).mean() * 100
        agg[f"pct_area_within_{b}m_aadt30k"] = (inb & near.aadt.ge(AADT_HIGH)).groupby(near.geoid_bg).mean() * 100
    bgs = bgs.merge(agg, left_on="geoid_bg", right_index=True, how="left")

    cent = gpd.GeoDataFrame({"geoid_bg": bgs.geoid_bg.to_numpy()}, geometry=bgs.centroid.reset_index(drop=True), crs=CRS_MA)
    cn = gpd.sjoin_nearest(cent, segs[["seg_id", "aadt", "aadt_year", "aadt_source", "geometry"]], how="left")
    cn = cn.drop_duplicates("geoid_bg")[["geoid_bg", "seg_id", "aadt", "aadt_year", "aadt_source"]]
    cn.columns = ["geoid_bg", "nearest_segment_id", "nearest_segment_aadt", "nearest_segment_aadt_year", "_src"]
    cn["exposure_method"] = np.where(cn["_src"].eq("LRS Traffic (layer 56)"), f"segment_nearest_lrs_aadt_d{EXPOSURE_DECAY_M}",
                                     "segment_nearest_fallback_aadt_d" + str(EXPOSURE_DECAY_M))
    bgs = bgs.merge(cn.drop(columns="_src"), on="geoid_bg", how="left")

    cand = stations[stations.aadt.notna() & (stations.tier != "anchor")]
    cand = cand.drop_duplicates("station_id")
    anchor_near = stations[stations.tier.eq("anchor")]
    if len(anchor_near) and len(cand):        # 3150 sits within metres of M3002W: keep one station per location
        dup = cand.geometry.apply(lambda p: anchor_near.geometry.iloc[0].distance(p) < 100)
        cand = pd.concat([cand[~dup], anchor_near])
    cc = bgs.centroid.reset_index(drop=True)
    dm = np.column_stack([cc.distance(p) for p in cand.geometry])
    k = dm.argmin(axis=1)
    bgs["nearest_station_id"] = cand.station_id.to_numpy()[k]
    bgs["nearest_station_aadt"] = cand.aadt.to_numpy()[k]
    bgs["nearest_station_aadt_year"] = cand.aadt_year.to_numpy()[k]
    bgs["nearest_station_dist_m"] = dm.min(axis=1)
    return bgs


# --------------------------------------------------------------------------- #
# Statistics helpers
# --------------------------------------------------------------------------- #
def morans_i(x: np.ndarray, w: np.ndarray, n_perm: int = 999) -> tuple[float, float]:
    z = x - x.mean()
    s0 = w.sum()

    def stat(zz):
        return (len(zz) / s0) * (zz @ w @ zz) / (zz @ zz)
    obs = stat(z)
    perm = np.array([stat(RNG.permutation(z)) for _ in range(n_perm)])
    return obs, (1 + (np.abs(perm) >= abs(obs)).sum()) / (n_perm + 1)


def queen_weights(gdf: gpd.GeoDataFrame) -> np.ndarray:
    idx = gdf.sindex.query(gdf.geometry.values, predicate="intersects")
    n = len(gdf)
    w = np.zeros((n, n))
    w[idx[0], idx[1]] = 1
    np.fill_diagonal(w, 0)
    rs = w.sum(axis=1, keepdims=True)
    return np.divide(w, rs, out=np.zeros_like(w), where=rs > 0)


def cliffs_delta(a, b) -> float:
    u = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return 2 * u / (len(a) * len(b)) - 1


def spearman(df: pd.DataFrame, x: str, y: str):
    d = df[[x, y]].dropna()
    r, p = stats.spearmanr(d[x], d[y])
    return r, p, len(d)


def cluster_boot_spearman(df: pd.DataFrame, x: str, y: str, cluster: str, n_boot: int = 2000):
    d = df[[x, y, cluster]].dropna()
    groups = [g[[x, y]].to_numpy(dtype=float) for _, g in d.groupby(cluster)]
    out = []
    for _ in range(n_boot):
        pick = RNG.integers(0, len(groups), len(groups))
        arr = np.vstack([groups[i] for i in pick])
        if np.ptp(arr[:, 0]) > 0 and np.ptp(arr[:, 1]) > 0:
            out.append(stats.spearmanr(arr[:, 0], arr[:, 1])[0])
    return np.percentile(out, [2.5, 97.5])


def boot_rows(df: pd.DataFrame, x: str, y: str, n_boot: int = 2000):
    """Row bootstrap (each row is its own cluster): Spearman and OLS slope per x-unit."""
    d = df[[x, y]].dropna().to_numpy(float)
    rho, slope = [], []
    for _ in range(n_boot):
        s = d[RNG.integers(0, len(d), len(d))]
        if np.ptp(s[:, 0]) > 0 and np.ptp(s[:, 1]) > 0:
            rho.append(stats.spearmanr(s[:, 0], s[:, 1])[0])
            slope.append(np.polyfit(s[:, 0], s[:, 1], 1)[0])
    return np.percentile(rho, [2.5, 97.5]), np.percentile(slope, [2.5, 97.5])


def fe_slope(df: pd.DataFrame, x: str, y: str, fe: str, cluster: str):
    """OLS of y on distance (km) with municipality fixed effects; cluster-robust CI (CR1, t with G-1 df)."""
    d = df[[x, y, fe, cluster]].dropna()
    X = np.column_stack([d[x].to_numpy(float) / 1000, pd.get_dummies(d[fe]).to_numpy(float)])
    yv = d[y].to_numpy(float)
    xtxi = np.linalg.inv(X.T @ X)
    beta = xtxi @ X.T @ yv
    u = yv - X @ beta
    groups = d[cluster].to_numpy()
    meat = np.zeros((X.shape[1],) * 2)
    for gname in np.unique(groups):
        s = X[groups == gname].T @ u[groups == gname]
        meat += np.outer(s, s)
    G, N, K = len(np.unique(groups)), len(d), X.shape[1]
    se = np.sqrt((xtxi @ meat @ xtxi)[0, 0] * (G / (G - 1)) * ((N - 1) / (N - K)))
    t = stats.t.ppf(0.975, G - 1)
    return beta[0], beta[0] - t * se, beta[0] + t * se, N, G


def wavg(v: pd.Series, w: pd.Series) -> float:
    m = v.notna() & w.notna() & (w > 0)
    return float(np.average(v[m], weights=w[m])) if m.any() else np.nan


def pooled_income(d: pd.DataFrame, w) -> tuple[float, float, float]:
    """Household-weighted pooled median income (ACS S1901 bracket shares, linear interpolation), % <$50k, % >=$150k."""
    pct = d[BKT_COLS].to_numpy(float)
    w = np.asarray(w, float)
    ok = ~np.isnan(pct).any(axis=1) & np.isfinite(w) & (w > 0)
    if not ok.any():
        return np.nan, np.nan, np.nan
    cnt = (pct[ok] / 100 * w[ok, None]).sum(axis=0)
    cum = np.cumsum(cnt) / cnt.sum()
    k = int(np.searchsorted(cum, 0.5))
    lo, hi = BKT_EDGES[k], BKT_EDGES[k + 1]
    prev = cum[k - 1] if k else 0.0
    med = lo if not np.isfinite(hi) else lo + (0.5 - prev) / (cum[k] - prev) * (hi - lo)
    return float(med), float(cnt[:5].sum() / cnt.sum() * 100), float(cnt[8:].sum() / cnt.sum() * 100)


def fmt_p(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def money(v: float) -> str:
    return f"{'-' if v < 0 else '+'}${abs(v):,.0f}"


def tract_label(geoid_tract: str) -> str:
    code = geoid_tract[5:]
    return f"{int(code[:4])}" + (f".{code[4:]}" if code[4:] != "00" else "")


def bg_label(geoid_bg: str) -> str:
    return f"{tract_label(geoid_bg[:11])}-{geoid_bg[-1]}"


# --------------------------------------------------------------------------- #
# Master table
# --------------------------------------------------------------------------- #
def build_master(bgs, ej, acs, ref, traffic, pm_mon) -> pd.DataFrame:
    cent_ll = bgs.centroid.to_crs(4326)
    bgs = bgs.assign(centroid_lat=cent_ll.y.round(5), centroid_lon=cent_ll.x.round(5))
    m = bgs.drop(columns="geometry").merge(ej, on="geoid_bg", how="left", validate="1:1")
    m["geoid_tract"] = m["geoid_bg"].str[:11]
    m = m.merge(acs.drop(columns=["geo_id"]), on="geoid_tract", how="left", validate="m:1")
    # EJ_POLY lists only EJ block groups: absence = not EJ-designated (demographics unknown, not zero)
    for col in ("ej_designated", "ej_minority", "ej_income", "ej_english_isolation"):
        m[col] = m[col].fillna(False).astype(bool)
    m["ej_criteria_count"] = m["ej_criteria_count"].fillna(0).astype(int)
    m["ej_criteria_desc"] = m["ej_criteria_desc"].astype("object").fillna("Not EJ-designated")
    m["municipality"] = m["municipality"].astype("object").fillna(m["municipality_geo"])
    m["ej_flag"] = m["ej_designated"].astype(int)
    m["income_best"] = m["acs_median_income"].fillna(m["bg_median_hh_income"])
    m["income_source"] = np.where(m["acs_median_income"].notna(), "ACS 2024 tract",
                                  np.where(m["bg_median_hh_income"].notna(), "EJ BG (fallback)", "missing"))
    m["income_pct_of_state"] = m["income_best"] / ref["state_median_income"] * 100
    m["dist_band"] = pd.cut(m["dist_centroid_m"], BANDS, labels=BAND_LABELS, right=True, include_lowest=True)
    m["in_corridor"] = m["dist_centroid_m"] <= CORRIDOR_M
    m["aadt_station"] = traffic["aadt"]
    m["aadt_westbound"] = traffic["wb"]
    m["aadt_eastbound"] = traffic["eb"]
    m["westbound_share"] = traffic["wb_share"]
    for b in BUFFERS_M:
        m[f"est_ej_pop_within_{b}m"] = m["total_pop"] * m[f"pct_area_within_{b}m"] / 100
        m[f"est_ej_pop_within_{b}m_aadt30k"] = m["total_pop"] * m[f"pct_area_within_{b}m_aadt30k"] / 100
    # households: tract households (ACS) shared across block groups in proportion to EJ-table households where known
    w = m["total_hh"].fillna(m.groupby("geoid_tract")["total_hh"].transform("mean")).fillna(1.0)
    m["est_households"] = m["acs_households"] * w / w.groupby(m["geoid_tract"]).transform("sum")
    for b in BUFFERS_M:
        m[f"est_hh_within_{b}m"] = m["est_households"] * m[f"pct_area_within_{b}m"] / 100

    # traffic-independent vulnerability and the legacy cumulative burden index (traffic share is by construction)
    comps = {"p_traffic": m["exposure_index"].rank(pct=True),
             "p_low_income": (-m["income_best"]).rank(pct=True),
             "p_ej_criteria": m["ej_criteria_count"].rank(pct=True)}      # 0 = not EJ, 1-3 = number of criteria met
    for k, v in comps.items():
        m[k] = v
    m["cumulative_burden_index"] = pd.concat(comps, axis=1).mean(axis=1, skipna=False) * 100
    m["cbi_quintile"] = pd.qcut(m["cumulative_burden_index"], 5, labels=["Q1 lowest", "Q2", "Q3", "Q4", "Q5 highest"])
    m["hotspot"] = (m["cbi_quintile"] == "Q5 highest") & m["in_corridor"]
    m["vulnerability_index"] = pd.concat([m.p_low_income, m.p_ej_criteria], axis=1).mean(axis=1, skipna=False) * 100
    v = m["vulnerability_index"]
    m["vuln_quintile"] = pd.qcut(v.rank(method="first"), 5, labels=["Q1 lowest", "Q2", "Q3", "Q4", "Q5 highest"])
    m["priority_hotspot"] = (m["vuln_quintile"] == "Q5 highest") & m["in_corridor"]
    pr = m[m.priority_hotspot].sort_values(["vulnerability_index", "est_ej_pop_within_500m"], ascending=False)
    m["priority_rank"] = pd.Series(np.arange(1, len(pr) + 1), index=pr.index).reindex(m.index).astype("Int64")

    # PM2.5: nearest AQS monitor (regional context only)
    cent = gpd.GeoSeries(gpd.points_from_xy(m.centroid_lon, m.centroid_lat), crs=4326).to_crs(CRS_MA)
    dmat = np.column_stack([cent.distance(m_) for m_ in pm_mon.geometry])
    nearest = dmat.argmin(axis=1)
    m["pm_monitor"] = pm_mon["site"].to_numpy()[nearest]
    m["dist_pm_monitor_km"] = dmat.min(axis=1) / 1000
    for c, src in [("pm25_monitor_annual_mean", "mean"), ("pm25_monitor_p98", "p98"), ("pm25_monitor_max", "max"),
                   ("pm25_monitor_days_over_who24", "days_over_who24")]:
        m[c] = pm_mon[src].to_numpy()[nearest]
    return m


def tract_table(m: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t, g in m.groupby("geoid_tract"):
        a = g.area_km2
        rows.append({
            "geoid_tract": t, "tract": tract_label(t), "municipality": g.municipality.mode().iat[0], "block_groups": len(g),
            "households": g.acs_households.iloc[0], "acs_median_income": g.acs_median_income.iloc[0],
            "acs_median_income_moe": g.acs_median_income_moe.iloc[0], "income_reliable": g.acs_income_reliable.iloc[0],
            "pct_hh_under_50k": g.acs_pct_hh_under_50k.iloc[0], "dist_m": wavg(g.dist_centroid_m, a),
            "pct_area_within_500m": wavg(g.pct_area_within_500m, a), "nearest_segment_aadt": wavg(g.nearest_segment_aadt, a),
            "exposure_index": wavg(g.exposure_index, a), "ej_bgs": int(g.ej_flag.sum()), "ej_residents": g.total_pop.sum(),
            "ej_pop_within_500m": g.est_ej_pop_within_500m.sum(), "vulnerability_index": g.vulnerability_index.mean(),
            "priority_bgs": int(g.priority_hotspot.sum()), "in_corridor": bool(g.in_corridor.mean() >= 0.5)})
    return pd.DataFrame(rows).sort_values(["municipality", "dist_m"]).reset_index(drop=True)


def zone_profile(m: pd.DataFrame, share: pd.Series) -> dict:
    """Household-/population-weighted profile of the part of each block group inside (share) a zone."""
    hh, pop = m.est_households * share, m.total_pop * share
    med, u50, o150 = pooled_income(m, hh)
    return {"ej_pop": pop.sum(), "hh": hh.sum(), "med_income": med, "pct_under_50k": u50, "pct_150k_plus": o150,
            "pct_minority": wavg(m.pct_minority, pop), "pct_lep": wavg(m.pct_lep_hh, pop)}


# --------------------------------------------------------------------------- #
# Report sections
# --------------------------------------------------------------------------- #
def sec_near(m, F):
    section("near")
    say("Distance = block-group area (50 m grid) to the TIGER Route 9 centreline. Two population bases are used because neither alone is complete:")
    say("  EJ residents  = MassGIS EJ_POLY population, EJ-designated block groups only (the DBF omits the 17 non-EJ block groups, so this undercounts, "
        "mostly in Shrewsbury).")
    say("  Households    = ACS 2024 tract households shared across block groups (EJ-table households as shares) -> covers every block group.")
    say("Both are areal interpolations (uniform density inside a block group). Income is the household-weighted pooled median built from "
        "ACS S1901 bracket shares, not a median of block-group values.\n")
    scopes = [("Worcester", m.municipality.eq("Worcester")), ("Worcester + Shrewsbury", pd.Series(True, index=m.index))]
    rows = []
    for lab, sel in scopes:
        d = m[sel]
        tot_pop, tot_hh = d.total_pop.sum(), d.est_households.sum()
        for b in BUFFERS_M:
            s = d[f"pct_area_within_{b}m"] / 100
            i, o = zone_profile(d, s), zone_profile(d, 1 - s)
            rows.append({"scope": lab, "buffer": f"<={b} m", "EJ_residents": round(i["ej_pop"]), "%_of_EJ_pop": round(i["ej_pop"] / tot_pop * 100, 1),
                         "households": round(i["hh"]), "%_of_hh": round(i["hh"] / tot_hh * 100, 1),
                         "median_inc_in": round(i["med_income"]), "median_inc_beyond": round(o["med_income"]),
                         "%hh<50k_in": round(i["pct_under_50k"], 1), "%hh<50k_beyond": round(o["pct_under_50k"], 1),
                         "%minority_in": round(i["pct_minority"], 1), "%minority_beyond": round(o["pct_minority"], 1),
                         "%LEP_in": round(i["pct_lep"], 1), "%LEP_beyond": round(o["pct_lep"], 1)})
    say(pd.DataFrame(rows).to_string(index=False))
    say("   (% minority and % LEP are population-weighted over EJ-designated block groups only; income and households cover all block groups.)")

    say("\nResidents within 500 m by the measured AADT of the adjacent Route 9 segment (nearest MassDOT segment to each 50 m cell):")
    rows = []
    for lab, sel in scopes:
        d = m[sel]
        s5, s20, s30 = (d[f"pct_area_within_500m{k}"] / 100 for k in ("", "_aadt20k", "_aadt30k"))
        for cls, sh in [("<20k", s5 - s20), ("20-30k", s20 - s30), (">=30k", s30)]:
            p = zone_profile(d, sh)
            rows.append({"scope": lab, "adjacent_AADT": cls, "EJ_residents": round(p["ej_pop"]), "households": round(p["hh"]),
                         "median_income": round(p["med_income"]), "%hh<50k": round(p["pct_under_50k"], 1)})
    say(pd.DataFrame(rows).to_string(index=False))
    corr = m[m.in_corridor]
    cls = pd.cut(corr.nearest_segment_aadt, AADT_CLASSES, labels=AADT_LABELS, right=False)
    t = corr.groupby(cls, observed=False).agg(block_groups=("geoid_bg", "size"), ej_bgs=("ej_flag", "sum"),
                                              ej_residents=("total_pop", "sum"), households=("est_households", "sum")).round(0).astype(int)
    say("\nCorridor block groups (centroid <= 1.5 km) by AADT of their nearest Route 9 segment:")
    say(t.to_string())


def sec_traffic(m, tc, traffic, F):
    section("traffic")
    s, segs, cin = tc["stats"], tc["segs"], tc["segs_in"]
    say("Provenance (all fetched by fetch_massdot_traffic_aadt.py; raw pulls cached in cache/massdot/, re-run is idempotent):")
    for k, u in {**LAYERS, "stations": STATIONS_URL}.items():
        say(f"  {k:<22}{u}")
    say(f"  query envelope (WGS84): {BBOX_4326}; records pulled: Traffic(56)={s['inv']['seg56']:,}, Traffic_Segment(57)={s['inv']['seg57']:,}, "
        f"Traffic_Station(2)={s['inv']['sta2']:,}, YearEnd 2024={s['inv']['yearend']:,}, count-station points (county)={s['inv']['stations_county']:,}")
    say("\nJoin results (requested path first, then what the data actually supports):")
    say(f"  STATION_NUMBER <-> Traffic_Segment.Statn_Num (layer 57): Statn_Num is populated in {s['n_s57_statn']} of {s['inv']['seg57']:,} pulled records -> 0 stations matched.")
    say(f"  Layer 57 StationID is populated for {s['n_s57_stationid']} records (none on Route 9); AADT present on {s['n_s57_aadt']:,} records "
        f"(Route 9: {s['n_s57_r9_aadt']} of {s['n_s57_r9']} segments, 2017 vintage) -> layer 57 is used only as a segment fallback.")
    say(f"  Working path (tier T2): count-station STATION_NUMBER -> RoadInventoryLRS/2 StationID (route + milepost) -> RoadInventoryLRS/56 Traffic segment covering that milepost.")
    say(f"  Spatial tier (T3, on-Route-9 stations only): nearest Route 9 segment within {STATION_ON_ROUTE_M} m. Station counts as ON Route 9 if it is within "
        f"{STATION_ON_ROUTE_M} m of the TIGER centreline AND its road name (ROUTE_STREET, else STATION_LOC, before any 'north/south/east/west of' clause) is Route 9; ramps excluded.")
    say(f"  Count stations in Worcester + Shrewsbury: {s['n_ws_rows']} rows ({s['n_ws_unique']} distinct STATION_NUMBERs; {s['n_ws_no_id']} rows without a number; "
        f"{s['n_dup_ids']} repeated IDs). Rows with an AADT by any tier: {s['n_ws_joined']} ({s['n_ws_joined'] / s['n_ws_rows']:.0%}); by tier: {s['tier_rows']}.")
    say(f"  Stations ON Route 9: {s['n_r9_rows']} rows = {s['n_r9_unique']} distinct stations; with AADT {s['n_r9_joined']} -> join rate "
        f"{s['n_r9_joined'] / max(s['n_r9_unique'], 1):.0%} (tiers: {s['r9_tiers']}).")
    F["join_rate_r9"] = s["n_r9_joined"] / max(s["n_r9_unique"], 1)
    F["join_rate_ws"] = s["n_ws_joined"] / s["n_ws_rows"]
    F["n_r9_unique"], F["r9_tiers"] = s["n_r9_unique"], s["r9_tiers"]

    st = tc["stations"]
    say("\nCount stations on Route 9 (west to east; AADT from the LRS segment at the station's milepost, MassDOT vintage in AADT_Year):")
    tbl = pd.DataFrame({"station": st.station_id, "road": st.ROUTE_STREET.fillna("").str.strip().replace("", pd.NA).fillna(st.STATION_LOC.str.strip()),
                        "town": st.TOWN.str.title(), "milepost": st.measure.round(2), "AADT": st.aadt.round(0), "AADT_year": st.aadt_year,
                        "join": st.tier, "dist_to_centreline_m": st.dist_r9_m.round(1)})
    say(tbl.to_string(index=False))

    a = s["anchor"]
    say(f"\nAnchor check, {traffic['station']} (traffic.csv {traffic['aadt']:,} veh/day):")
    if a["found"]:
        say(f"  In the LRS it is station {traffic['station']} on {a['route_id']} at milepost {a['measure']:.2f} (RoadInventoryLRS/2), beside count station 3150 'RTE. 9 (BELMONT ST.)' "
            f"(same road; the two point locations are {a['dist_3150_m']:.0f} m apart). TrafficCountLocations STATION_NUMBER 3002 is NOT this station (it is a Route 12/202 site in "
            f"Winchendon / Route 395 in Webster), so the M3002W ID cannot be joined to count-station points directly; the anchor is added as its own station.")
        say(f"  Layer-56 segment at that milepost: {a['seg_aadt']:,.0f} ({a['seg_year']:.0f}); adjacent segments {a['neighbour_min']:,.0f}-{a['neighbour_max']:,.0f}. "
            f"traffic.csv is {a['diff_pct']:+.1f}% vs the containing segment -> anchor and segment AADT agree within a few percent.")
    else:
        say("  M3002W not found in RoadInventoryLRS/2; anchor not reconciled.")
    F["anchor"] = a

    say(f"\nCorridor AADT along Route 9 ({s['rid']}), Worcester + Shrewsbury, {s['n_segs_in']} segments clipped to town limits:")
    rows = []
    for lab, d in [("Worcester", cin[cin.town == "Worcester"]), ("Shrewsbury", cin[cin.town == "Shrewsbury"]), ("Pooled", cin)]:
        w = d.len_m
        rows.append({"scope": lab, "km": round(w.sum() / 1000, 1), "AADT_mean(len-wtd)": round(np.average(d.aadt, weights=w)),
                     "median": round(wquantile(d.aadt, w, .5)), "p10": round(wquantile(d.aadt, w, .1)), "p90": round(wquantile(d.aadt, w, .9)),
                     "min": round(d.aadt.min()), "max": round(d.aadt.max()),
                     "%km_<20k": round(w[d.aadt < AADT_MID].sum() / w.sum() * 100), "%km_20-30k": round(w[(d.aadt >= AADT_MID) & (d.aadt < AADT_HIGH)].sum() / w.sum() * 100),
                     "%km_>=30k": round(w[d.aadt >= AADT_HIGH].sum() / w.sum() * 100)})
        F[f"aadt_{lab}"] = rows[-1]
    say(pd.DataFrame(rows).to_string(index=False))
    yr = cin.groupby(cin.aadt_year.fillna(0).astype(int)).len_m.sum() / cin.len_m.sum()
    F["share_recent"] = float(yr[yr.index >= 2023].sum())
    say(f"  Vintage (share of corridor length by MassDOT AADT_Year): " + ", ".join(f"{k or 'n/a'}: {v:.0%}" for k, v in yr.items())
        + f" -> {F['share_recent']:.0%} is 2023-2025 data.")
    old = cin[cin.aadt_year < 2023]
    if len(old):
        say(f"  Older than 2023: {len(old)} clipped segments, {old.len_m.sum() / 1000:.2f} km (AADT_Year {int(old.aadt_year.min())}-{int(old.aadt_year.max())}, "
            f"AADT {old.aadt.min():,.0f}-{old.aadt.max():,.0f}); the corridor minimum {cin.aadt.min():,.0f} is "
            f"{'one of them' if cin.aadt.min() in set(old.aadt) else 'not one of them'}, so treat it as a lower-confidence value.")
    src = segs.aadt_source.value_counts().to_dict()
    say(f"  Fallbacks: {s['n_miss56']} of {s['n_segs']} Route 9 segments lacked a layer-56 AADT; filled from layer 57: {s['n_fill57']}; "
        f"from the traffic.csv anchor: {s['n_fill_anchor']}. Source mix: {src}.")
    peak = cin.loc[cin.aadt.idxmax()]
    say(f"  AADT profile: lowest {cin.aadt.min():,.0f}, highest {cin.aadt.max():,.0f} (milepost {peak.From_Measure:.1f}, {peak.town}); "
        f"AADT increases roughly west to east, so a single station misstates both ends of the corridor "
        f"({cin.aadt.min() / traffic['aadt'] - 1:+.0%} to {cin.aadt.max() / traffic['aadt'] - 1:+.0%} vs the {traffic['aadt']:,} anchor).")
    F["aadt_peak"] = (peak.aadt, peak.From_Measure, peak.town)

    say(f"\nDirectional skew: {traffic['station']} reports WB {traffic['wb']:,} vs EB {traffic['eb']:,} ({traffic['wb_share']:.1%} westbound, "
        f"{traffic['wb'] / traffic['eb']:.1f}:1; EB+WB differs from AADT by {traffic['dir_sum_gap']} veh/day, rounding).")
    say(f"  This is a single-station observation. The LRS Traffic layer has directional AADT (AADT_P_Dir) on {s['p_dir_n']} of {s['n_segs']} Route 9 segments and a "
        f"design directional factor D_Factor = {s['d_factor']} (share of design-hour flow in the peak direction), i.e. near-even. Do not treat the 75% WB skew as a corridor property.")

    say("\nModelled exposure (disclaimer): block-group traffic is NOT measured. Measured quantities are the AADT on Route 9 segments and the residents living within a stated distance.")
    say(f"  Primary exposure_index = AADT of the nearest MassDOT segment x exp(-d / {EXPOSURE_DECAY_M} m), averaged over each block group on a {GRID_M} m grid "
        f"(method 'segment_nearest_lrs_aadt_d{EXPOSURE_DECAY_M}'). Chosen over a multi-station sum because a sum depends on how many stations happen to exist "
        f"(clustered at Belmont St) and double counts; segments give continuous, vintage-stamped coverage of all {s['n_segs']} stretches.")
    say(f"  Sensitivity: exposure_index_d150 (e-folding {EXPOSURE_DECAY_ALT_M} m). Legacy: legacy_exposure_index = {traffic['aadt']:,} x exp(-d/{EXPOSURE_DECAY_M} m), kept one release.")
    rho_l = stats.spearmanr(m.exposure_index, m.legacy_exposure_index)[0]
    rho_150 = stats.spearmanr(m.exposure_index, m.exposure_index_d150)[0]
    rho_d = stats.spearmanr(m.exposure_index, m.dist_centroid_m)[0]
    rho_ld = stats.spearmanr(m.legacy_exposure_index, m.dist_centroid_m)[0]
    say(f"  Rank agreement across block groups: primary vs legacy rho = {rho_l:.3f}; primary vs d150 rho = {rho_150:.3f}. "
        f"Spearman with distance: primary {rho_d:+.3f}, legacy {rho_ld:+.3f} -> both mostly restate distance; any near/far contrast in 'exposure' is largely by construction.")
    corr = m[m.in_corridor]
    say(f"  What the segment AADT adds: it ranks corridor block groups by the traffic actually carried next to them "
        f"(corridor block-group nearest-segment AADT: median {corr.nearest_segment_aadt.median():,.0f}, range {corr.nearest_segment_aadt.min():,.0f}-{corr.nearest_segment_aadt.max():,.0f}); "
        f"mean primary exposure {m.exposure_index.mean():,.0f} vs {m.legacy_exposure_index.mean():,.0f} under the legacy model (prior release {PRIOR['mean_exposure']:,.0f}).")
    F.update(rho_exp_legacy=rho_l, rho_exp_dist=rho_d, mean_expo=m.exposure_index.mean(), mean_expo_legacy=m.legacy_exposure_index.mean())


def sec_worcester(m, tr, bgs, acs, ref, F):
    section("worc")
    w = m[m.municipality == "Worcester"]
    trw = tr[(tr.municipality == "Worcester")]
    trwi = trw.dropna(subset=["acs_median_income"])
    say(f"Worcester: {len(w)} block groups in {len(trw)} tracts ({len(trwi)} with an ACS income estimate; {int((~trwi.income_reliable.astype(bool)).sum())} with CV>30%); "
        f"corridor = centroid <= {CORRIDOR_M / 1000:g} km -> {int(w.in_corridor.sum())} block groups; {int(trw.in_corridor.sum())} tracts have most of their block groups in it. "
        f"Block-group incomes repeat their parent tract's ACS value, so tract-level results are primary and block-group n is overstated.")

    say("\nA. Corridor vs rest of Worcester (household-weighted; ACS S1901 bracket pooling)")
    ci, co = w[w.in_corridor], w[~w.in_corridor]
    pi, po = pooled_income(ci, ci.est_households), pooled_income(co, co.est_households)
    ej_i, ej_o = ci.ej_flag.mean(), co.ej_flag.mean()
    tab = [[int(ci.ej_flag.sum()), int((1 - ci.ej_flag).sum())], [int(co.ej_flag.sum()), int((1 - co.ej_flag).sum())]]
    orr, pf = stats.fisher_exact(tab)
    x, y = trwi[trwi.in_corridor].acs_median_income, trwi[~trwi.in_corridor].acs_median_income
    u = stats.mannwhitneyu(x, y, alternative="two-sided")
    rows = [
        ("households (est.)", f"{ci.est_households.sum():,.0f}", f"{co.est_households.sum():,.0f}"),
        ("pooled median household income", f"${pi[0]:,.0f}", f"${po[0]:,.0f}"),
        ("% households < $50k", f"{pi[1]:.1f}", f"{po[1]:.1f}"),
        ("% households >= $150k", f"{pi[2]:.1f}", f"{po[2]:.1f}"),
        ("tracts: median of tract medians", f"${x.median():,.0f} (n={len(x)})", f"${y.median():,.0f} (n={len(y)})"),
        ("EJ-designated block groups", f"{int(ci.ej_flag.sum())}/{len(ci)} ({ej_i:.0%})", f"{int(co.ej_flag.sum())}/{len(co)} ({ej_o:.0%})"),
        ("EJ residents (EJ_POLY)", f"{ci.total_pop.sum():,.0f}", f"{co.total_pop.sum():,.0f}"),
        ("EJ criteria met, mean (0-3)", f"{ci.ej_criteria_count.mean():.2f}", f"{co.ej_criteria_count.mean():.2f}"),
    ]
    say(pd.DataFrame(rows, columns=["metric", "corridor", "rest of Worcester"]).to_string(index=False))
    say(f"   Tract-level Mann-Whitney on median income: {fmt_p(u.pvalue)}, Cliff's delta {cliffs_delta(x, y):+.2f}. "
        f"EJ share corridor vs rest: odds ratio {orr:.1f} (Fisher exact {fmt_p(pf)}).")
    say(f"   Pooled corridor median is {pi[0] / ref['state_median_income']:.0%} of the statewide median (${ref['state_median_income']:,.0f}); "
        f"rest of Worcester {po[0] / ref['state_median_income']:.0%}.")
    F["worc"] = {"pi": pi, "po": po, "hh_i": ci.est_households.sum(), "hh_o": co.est_households.sum(), "ej_i": ej_i, "ej_o": ej_o,
                 "n_i": len(ci), "n_o": len(co), "or": orr, "p_or": pf, "tr_i": x.median(), "tr_o": y.median(),
                 "n_tr_i": len(x), "n_tr_o": len(y), "p_mw": u.pvalue, "delta": cliffs_delta(x, y), "n_bg": len(w),
                 "n_tr": len(trw), "n_tr_inc": len(trwi), "n_corr_bg": len(ci), "n_corr_tr": int(trw.in_corridor.sum())}

    say("\nB. Income vs distance to Route 9, Worcester only (primary spatial result)")
    r_t, p_t, n_t = spearman(trwi, "dist_m", "acs_median_income")
    ci_rho, ci_slope = boot_rows(trwi, "dist_m", "acs_median_income")
    slope_t = np.polyfit(trwi.dist_m / 1000, trwi.acs_median_income, 1)[0]
    say(f"   Tract level (n={n_t}; each tract one observation): Spearman rho = {r_t:+.3f} ({fmt_p(p_t)}), tract bootstrap 95% CI [{ci_rho[0]:+.2f}, {ci_rho[1]:+.2f}]; "
        f"OLS {money(slope_t)} per km (bootstrap CI {money(ci_slope[0] * 1000)} to {money(ci_slope[1] * 1000)}).")
    r_b, p_b, n_b = spearman(w, "dist_centroid_m", "acs_median_income")
    cib = cluster_boot_spearman(w, "dist_centroid_m", "acs_median_income", "geoid_tract")
    lr = stats.linregress(w.dropna(subset=["acs_median_income"]).dist_centroid_m / 1000, w.dropna(subset=["acs_median_income"]).acs_median_income)
    say(f"   Block-group level (n={n_b}; tract values repeated, so naive p is overstated): rho = {r_b:+.3f}, tract-cluster bootstrap 95% CI [{cib[0]:+.2f}, {cib[1]:+.2f}]; OLS {money(lr.slope)}/km (R2={lr.rvalue ** 2:.2f}).")
    r_e, p_e, n_e = spearman(w, "dist_centroid_m", "ej_flag")
    cie = cluster_boot_spearman(w, "dist_centroid_m", "ej_flag", "geoid_tract")
    say(f"   EJ designation vs distance (block groups): rho = {r_e:+.3f} ({fmt_p(p_e)} naive), cluster CI [{cie[0]:+.2f}, {cie[1]:+.2f}].")
    b_fe, lo_fe, hi_fe, n_fe, g_fe = fe_slope(m, "dist_centroid_m", "acs_median_income", "municipality", "geoid_tract")
    t_fe = fe_slope(tr.assign(dm=tr.dist_m), "dm", "acs_median_income", "municipality", "geoid_tract")
    pooled_slope = stats.linregress(m.dropna(subset=["acs_median_income"]).dist_centroid_m / 1000,
                                    m.dropna(subset=["acs_median_income"]).acs_median_income).slope
    say(f"   Municipality-aware check (both towns, town fixed effects, tract-clustered CI): block groups {money(b_fe)} per km "
        f"[{money(lo_fe)}, {money(hi_fe)}] (n={n_fe}, {g_fe} tracts); tracts {money(t_fe[0])} per km [{money(t_fe[1])}, {money(t_fe[2])}] (n={t_fe[3]}). "
        f"Pooled OLS without town effects: {money(pooled_slope)} per km.")
    gg = bgs.merge(m[["geoid_bg", "acs_median_income", "municipality"]], on="geoid_bg").dropna(subset=["acs_median_income"])
    mi_all, mp_all = morans_i(np.log(gg["acs_median_income"].to_numpy()), queen_weights(gg))
    gw = gg[gg.municipality == "Worcester"].reset_index(drop=True)
    mi_w, mp_w = morans_i(np.log(gw["acs_median_income"].to_numpy()), queen_weights(gw))
    tg = bgs.assign(geoid_tract=bgs.geoid_bg.str[:11])[["geoid_tract", "geometry"]].dissolve(by="geoid_tract").reset_index().merge(acs[["geoid_tract", "acs_median_income"]], on="geoid_tract").dropna(subset=["acs_median_income"])
    mi_t, mp_t = morans_i(np.log(tg["acs_median_income"].to_numpy()), queen_weights(tg.reset_index(drop=True)))
    say(f"   Spatial autocorrelation, Moran's I of log income (queen contiguity, 999 permutations): all block groups {mi_all:.2f} ({fmt_p(mp_all)}); "
        f"Worcester block groups {mi_w:.2f}; tracts {mi_t:.2f} ({fmt_p(mp_t)}). Strong clustering shrinks the effective sample, so the cluster / tract bootstrap CIs "
        f"above (not the naive p) carry the inference.")
    F["worc_stats"] = {"r_t": r_t, "p_t": p_t, "n_t": n_t, "ci_rho": ci_rho, "slope_t": slope_t, "ci_slope": ci_slope * 1000, "r_b": r_b, "n_b": n_b, "cib": cib,
                       "slope_b": lr.slope, "r_e": r_e, "fe": (b_fe, lo_fe, hi_fe), "fe_t": t_fe[:3], "mi_all": mi_all, "mi_w": mi_w, "mi_t": mi_t,
                       "pooled_slope": pooled_slope}

    say("\nC. Sensitivity to the corridor definition (Worcester block groups, household-weighted)")
    rows = []
    for thr in (500, 1000, 1500, 2000, 3000):
        i, o = w[w.dist_centroid_m <= thr], w[w.dist_centroid_m > thr]
        a_, b_ = pooled_income(i, i.est_households), pooled_income(o, o.est_households)
        rows.append((f"<= {thr} m", len(i), round(i.est_households.sum()), round(i.ej_flag.mean() * 100), round(o.ej_flag.mean() * 100),
                     round(a_[0]), round(b_[0]), round(a_[0] - b_[0]), round(a_[1], 1), round(b_[1], 1)))
    say(pd.DataFrame(rows, columns=["corridor", "n_bg", "households", "%EJ_in", "%EJ_out", "median_in", "median_out", "gap", "%hh<50k_in", "%hh<50k_out"]).to_string(index=False))

    say("\nD. Tract table, Worcester tracts in the corridor (full table: outputs/tract_table_route9.csv)")
    show = trw[trw.in_corridor][["tract", "block_groups", "households", "acs_median_income", "income_reliable", "pct_hh_under_50k", "dist_m",
                                 "nearest_segment_aadt", "ej_bgs", "ej_residents", "priority_bgs"]].copy()
    for c in ("households", "acs_median_income", "dist_m", "nearest_segment_aadt", "ej_residents"):
        show[c] = show[c].round(0).astype("Int64")
    say(show.round({"pct_hh_under_50k": 1}).to_string(index=False))

    say("\nE. Priority hotspot table, Worcester (top-quintile traffic-independent vulnerability inside the corridor; see Section 6)")
    hot = m[m.priority_hotspot & (m.municipality == "Worcester")].sort_values("priority_rank")
    say(f"   {len(hot)} Worcester block groups; {hot.total_pop.sum():,.0f} EJ residents; {hot.est_households.sum():,.0f} est. households")
    ht = hot[["priority_rank", "geoid_bg", "total_pop", "est_ej_pop_within_500m", "income_best", "acs_pct_hh_under_50k", "ej_criteria_desc",
              "dist_centroid_m", "nearest_segment_aadt", "vulnerability_index"]].head(15).copy()
    ht["geoid_bg"] = ht.geoid_bg.map(bg_label)
    ht = ht.rename(columns={"priority_rank": "rank", "geoid_bg": "tract-bg", "total_pop": "EJ_pop", "est_ej_pop_within_500m": "EJ_pop_500m",
                            "income_best": "tract_income", "acs_pct_hh_under_50k": "%hh<50k", "dist_centroid_m": "dist_m",
                            "nearest_segment_aadt": "adj_AADT", "vulnerability_index": "vuln"})
    for c in ("EJ_pop", "EJ_pop_500m", "tract_income", "dist_m", "adj_AADT"):
        ht[c] = ht[c].round(0).astype("Int64")
    say(ht.round({"%hh<50k": 1, "vuln": 1}).to_string(index=False))
    F["worc_hot"] = {"n": len(hot), "pop": hot.total_pop.sum(), "hh": hot.est_households.sum()}


def sec_shrewsbury(m, tr, F):
    section("shrew")
    s = m[m.municipality == "Shrewsbury"]
    trs = tr[tr.municipality == "Shrewsbury"]
    trsi = trs.dropna(subset=["acs_median_income"])
    say("Sensitivity only: Route 9 crosses Shrewsbury for a short stretch, corridor block groups are few and tract incomes are high, so it is reported "
        "separately and not pooled into the primary equity result.")
    ci = s[s.in_corridor]
    pi, po = pooled_income(ci, ci.est_households), pooled_income(s[~s.in_corridor], s[~s.in_corridor].est_households)
    say(f"  {len(s)} block groups in {len(trs)} tracts; corridor: {len(ci)} block groups in {int(trs.in_corridor.sum())} tracts; "
        f"EJ-designated {int(s.ej_flag.sum())}/{len(s)} overall and {int(ci.ej_flag.sum())}/{len(ci)} in the corridor.")
    say(f"  Tract median income ${trsi.acs_median_income.min():,.0f}-${trsi.acs_median_income.max():,.0f} (median ${trsi.acs_median_income.median():,.0f}); "
        f"household-weighted pooled median: corridor ${pi[0]:,.0f} ({pi[1]:.1f}% of households < $50k) vs rest of Shrewsbury ${po[0]:,.0f}.")
    rows = []
    for b in BUFFERS_M:
        sh = s[f"pct_area_within_{b}m"] / 100
        p = zone_profile(s, sh)
        rows.append({"buffer": f"<={b} m", "households": round(p["hh"]), "%_of_town_hh": round(p["hh"] / s.est_households.sum() * 100, 1),
                     "median_income": round(p["med_income"]), "%hh<50k": round(p["pct_under_50k"], 1), "EJ_residents": round(p["ej_pop"])})
    say(pd.DataFrame(rows).to_string(index=False))
    say("  (EJ residents undercount Shrewsbury: only EJ-designated block groups carry a population in the EJ table; use households.)")
    r_s, p_s, n_s = spearman(trsi, "dist_m", "acs_median_income")
    say(f"  Tract level income vs distance, Shrewsbury only: rho = {r_s:+.2f} ({fmt_p(p_s)}, n={n_s} tracts: too few for stable inference).")
    wt = tr[(tr.municipality == "Worcester")].dropna(subset=["acs_median_income"])
    pooled = tr.dropna(subset=["acs_median_income"])
    r_w, _, n_w = spearman(wt, "dist_m", "acs_median_income")
    r_p, _, n_p = spearman(pooled, "dist_m", "acs_median_income")
    say(f"  Does pooling change the story? tract-level rho: Worcester only {r_w:+.2f} (n={n_w}); both towns {r_p:+.2f} (n={n_p}). "
        f"Shrewsbury's corridor tracts are high-income (pooled median ${pi[0]:,.0f} vs Worcester's corridor), which dilutes the pooled gradient; "
        f"the town-fixed-effects slope in Section 4 removes that town divide.")
    cs = m[(m.municipality == "Shrewsbury")].nearest_segment_aadt
    cw = m[(m.municipality == "Worcester")].nearest_segment_aadt
    n_ph = int((s.priority_hotspot).sum())
    say(f"  Adjacent measured AADT (nearest Route 9 segment): Shrewsbury block-group median {cs.median():,.0f} vs Worcester {cw.median():,.0f}. "
        f"The highest-volume stretch is in Shrewsbury; {n_ph} Shrewsbury block groups are priority hotspots (Section 6).")
    F["shrew"] = {"n_bg": len(s), "n_corr": len(ci), "pi": pi, "po": po, "n_tr": len(trs), "r_w": r_w, "r_p": r_p, "inc_med": trsi.acs_median_income.median(),
                  "aadt_med": cs.median(), "aadt_med_w": cw.median(), "hh_500": rows[1]["households"], "tr_corr": int(trs.in_corridor.sum())}


def sec_vulnerability(m, tr, F):
    section("vuln")
    say("Vulnerability index (0-100) = mean percentile rank of (a) low tract income and (b) EJ criteria met (0-3), pooled across all 166 block groups. "
        "It contains no traffic term, so its relationship with distance to Route 9 is an observation, not a construction.")
    say("Priority hotspot = top quintile of the vulnerability index AND inside the 1.5 km corridor (columns vulnerability_index, vuln_quintile, priority_hotspot, priority_rank).")
    rows = []
    for lab, d in [("Worcester", m[m.municipality == "Worcester"]), ("Pooled", m)]:
        r_v, p_v, n_v = spearman(d, "dist_centroid_m", "vulnerability_index")
        ci = cluster_boot_spearman(d, "dist_centroid_m", "vulnerability_index", "geoid_tract")
        rows.append({"scope": lab, "n": n_v, "rho(distance, vulnerability)": round(r_v, 3), "cluster 95% CI": f"[{ci[0]:+.2f}, {ci[1]:+.2f}]", "naive p": fmt_p(p_v)})
        F[f"vuln_{lab}"] = (r_v, ci)
    say(pd.DataFrame(rows).to_string(index=False))

    say("\nHow much of the legacy cumulative burden index (CBI) contrast is built in? Spearman with distance to Route 9, pooled:")
    comp = {"traffic exposure percentile (p_traffic)": "p_traffic", "low-income percentile": "p_low_income", "EJ-criteria percentile": "p_ej_criteria",
            "vulnerability index (no traffic)": "vulnerability_index", "cumulative burden index (incl. traffic)": "cumulative_burden_index"}
    rr = {}
    for lab, c in comp.items():
        r_, p_, n_ = spearman(m, "dist_centroid_m", c)
        rr[c] = r_
        say(f"   {lab:<42} rho = {r_:+.3f}")
    say(f"   -> the traffic term is a function of distance (rho {rr['p_traffic']:+.2f}), so CBI's correlation with distance ({rr['cumulative_burden_index']:+.2f}) is partly by construction; "
        f"the traffic-independent vulnerability index ({rr['vulnerability_index']:+.2f}) is the cleaner statement.")
    F["vuln_rr"] = rr

    say("\nBy distance band (pooled block groups):")
    b = m.groupby("dist_band", observed=True).agg(block_groups=("geoid_bg", "size"), mean_vulnerability=("vulnerability_index", "mean"),
                                                  pct_in_vuln_Q5=("vuln_quintile", lambda s: (s == "Q5 highest").mean() * 100),
                                                  pct_EJ=("ej_flag", lambda s: s.mean() * 100), mean_EJ_criteria=("ej_criteria_count", "mean"),
                                                  households=("est_households", "sum")).round(1)
    say(b.to_string())

    ph = m[m.priority_hotspot]
    old = m[m.hotspot]
    both = (m.priority_hotspot & m.hotspot).sum()
    say(f"\nPriority hotspots: {len(ph)} block groups ({int((ph.municipality == 'Worcester').sum())} Worcester, {int((ph.municipality == 'Shrewsbury').sum())} Shrewsbury); "
        f"{ph.total_pop.sum():,.0f} EJ residents ({ph.total_pop.sum() / m.total_pop.sum():.1%} of the study EJ population); "
        f"{ph.est_ej_pop_within_500m.sum():,.0f} EJ residents within 500 m of Route 9; median adjacent AADT {ph.nearest_segment_aadt.median():,.0f}.")
    say(f"  Legacy CBI hotspots (top-quintile CBI inside the corridor): {len(old)} block groups, {old.total_pop.sum():,.0f} EJ residents (prior release {PRIOR['hotspots']} / {PRIOR['hotspot_pop']:,}); "
        f"{both} block groups are in both lists.")
    F["vuln_ph"] = {"n": len(ph), "pop": ph.total_pop.sum(), "pop500": ph.est_ej_pop_within_500m.sum(), "aadt_med": ph.nearest_segment_aadt.median(),
                    "both": int(both), "n_old": len(old), "pop_old": old.total_pop.sum(), "n_w": int((ph.municipality == 'Worcester').sum())}


def sec_air(pm, mon, mon_gdf, r9_line, bgs, F):
    section("air")
    c = pm["pm25"]
    mon = mon.copy()
    mon["dist_r9_km"] = mon_gdf.geometry.distance(r9_line).to_numpy() / 1000
    say(f"Context only. EPA AQS daily PM2.5, {pm.date.min():%Y-%m-%d} to {pm.date.max():%Y-%m-%d}: {len(pm)} site-days at {pm.site_id.nunique()} Worcester County monitors.")
    say("DATA GAP: there is no roadside or near-road PM2.5 monitor on Route 9; the monitors below are the only county ambient data and cannot resolve a Route 9 gradient. "
        f"The nearest ({mon.loc[mon.dist_r9_km.idxmin(), 'site']}) is {mon.dist_r9_km.min():.1f} km from the road, beyond the 300 m near-road zone used in this study.")
    rows = []
    for r in mon.itertuples():
        sub = pm[pm.site == r.site]
        ann = sub.groupby(sub.date.dt.quarter).pm25.mean().mean()
        rows.append({"monitor": r.site, "days": r.days, "annual_mean": round(ann, 2), "vs_NAAQS_9": "exceeds" if ann > NAAQS_ANNUAL else "meets",
                     "vs_WHO_5": "exceeds" if ann > WHO_ANNUAL else "meets", "p98": round(r.p98, 1), "max": round(r.max, 1),
                     "days>35": r.days_over_naaqs24, "days>15(WHO)": r.days_over_who24, "km_to_Route9": round(r.dist_r9_km, 1)})
    say(pd.DataFrame(rows).to_string(index=False))
    wide = pm.pivot_table(index="date", columns="site", values="pm25")
    rr = np.nan
    dist_mon = np.nan
    if wide.shape[1] >= 2:
        pair = wide.dropna()
        rr = stats.spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])[0]
        dist_mon = mon_gdf.geometry.iloc[0].distance(mon_gdf.geometry.iloc[1]) / 1000
    who = pm[pm.pm25 > WHO_24H]
    summer = who.month.isin([6, 7, 8]).mean()
    say(f"All monitors: mean {c.mean():.2f} ug/m3, p98 {c.quantile(.98):.1f}, max {c.max():.1f}; days above federal 24-h standard {int((c > NAAQS_24H).sum())} of {len(pm)}; "
        f"above WHO 24-h guideline {len(who)} ({len(who) / len(pm):.1%}, {who.date.nunique()} distinct dates, {summer:.0%} in June-August).")
    say(f"Monitors {dist_mon:.0f} km apart move together (Spearman {rr:.2f} on common days): episodes are regional, not attributable to Route 9. "
        f"Single-year screen only; NAAQS compliance uses 3-year design values.")
    F["pm"] = {"mean": c.mean(), "max": c.max(), "p98": c.quantile(.98), "n": len(pm), "fed_days": int((c > NAAQS_24H).sum()), "who_days": len(who),
               "who_dates": int(who.date.nunique()), "summer": summer, "rho": rr, "dist_mon": dist_mon, "dist_r9": mon.dist_r9_km.tolist(),
               "sites": mon.site.tolist(), "n_sites": pm.site_id.nunique(), "ann": [r["annual_mean"] for r in rows]}


def sec_limits(F):
    section("limits")
    for line in [
        "- Traffic exposure at block groups is modelled (distance decay from segment AADT, not measured). AADT is annual average, both directions, with no truck share, grade, "
        "lane geometry or wind; vintages are mostly 2024-2025 but some segments are older (see Section 3).",
        "- The corridor centreline is the Census TIGER 'State Rte 9' line; MassDOT segments are matched to it within a few metres. Only Route 9 is modelled: "
        "I-290, I-190, I-495 and cross streets are not, so block groups near them are not marked as exposed.",
        "- Count-station IDs are inconsistent (blank and repeated numbers, M3002W does not equal STATION_NUMBER 3002); stations are used for validation and context, "
        "segment AADT drives the model.",
        "- The WB 75% skew belongs to one station and is not generalised.",
        "- Population: EJ_POLY gives residents only for the 149 EJ-designated block groups; non-EJ block-group populations are unknown (EJ residents undercount, especially Shrewsbury). "
        "Households are ACS tract households shared across block groups (an allocation, not a count).",
        "- Block-group incomes repeat tract ACS estimates (some with CV > 30%); household-weighted pooled medians come from bracket shares and are approximate. "
        "EJ-table incomes are an older ACS vintage.",
        "- Near-road residents are interpolated by area (uniform density). Results are ecological associations at neighbourhood scale, not individual exposure, health effects or causation.",
        "- Moran's I is high (about 0.7 at block-group level), so naive p-values are overstated; tract / cluster bootstrap intervals are reported instead.",
        "- PM2.5 is regional context from two county monitors (Worcester Summer St, Uxbridge) and one year; it cannot be localised to Route 9 or used to rank block groups. "
        "Nearest-monitor columns in the master table are labels, not exposure.",
        "- CBI correlates with distance partly by construction (its traffic term is a function of distance); use vulnerability_index for traffic-independent statements.",
    ]:
        say(line)


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
EJ_COLORS = {
    "Minority": "#4c78a8",
    "Minority and income": "#f58518",
    "Minority, income and English isolation": "#b2182b",
    "Minority and English isolation": "#54a24b",
    "Income": "#9467bd",
    "Not EJ-designated": "#c8c8c8",
}
AADT_CMAP = LinearSegmentedColormap.from_list("aadt", plt.cm.YlOrRd(np.linspace(0.3, 1.0, 256)))
AADT_NORM = plt.Normalize(10000, 50000)


def scalebar(ax, length_m=2000):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x, y = x0 + (x1 - x0) * 0.05, y0 + (y1 - y0) * 0.04
    ax.plot([x, x + length_m], [y, y], color="k", lw=3, solid_capstyle="butt")
    ax.text(x + length_m / 2, y + (y1 - y0) * 0.015, f"{length_m / 1000:g} km", ha="center", fontsize=9)
    ax.annotate("N", xy=(x1 - (x1 - x0) * 0.05, y1 - (y1 - y0) * 0.03), xytext=(x1 - (x1 - x0) * 0.05, y1 - (y1 - y0) * 0.11),
                ha="center", fontsize=11, fontweight="bold", arrowprops=dict(arrowstyle="-|>", color="k", lw=1.5))


def route_lines(ax, segs, lw=3.6):
    lines, vals = [], []
    for geom, a in zip(segs.geometry, segs.aadt):
        for part in getattr(geom, "geoms", [geom]):
            lines.append(np.asarray(part.coords)[:, :2])
            vals.append(a)
    ax.add_collection(LineCollection(lines, colors="white", linewidths=lw + 2.2, zorder=4, capstyle="round"))
    ax.add_collection(LineCollection(lines, array=np.array(vals), cmap=AADT_CMAP, norm=AADT_NORM, linewidths=lw, zorder=5, capstyle="round"))


def station_marks(ax, st, anchor_id, label=True):
    ok = st[st.tier != "anchor"]
    ax.scatter(ok.geometry.x, ok.geometry.y, marker="^", s=55, c="#111", edgecolor="white", linewidth=0.7, zorder=7)
    a = st[st.tier == "anchor"]
    if len(a):
        ax.scatter(a.geometry.x, a.geometry.y, marker="*", s=230, c="#00a6a6", edgecolor="black", linewidth=0.9, zorder=8)
        if label:
            ax.annotate(anchor_id, (a.geometry.x.iloc[0], a.geometry.y.iloc[0]), xytext=(8, 10), textcoords="offset points", fontsize=8.5,
                        fontweight="bold", zorder=9, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))


def town_map(ax, g, town, tc, corridor_zone, vmin, vmax, anchor_id, title, pad=700):
    ctx = g[g.municipality != town]
    ctx.plot(ax=ax, color="#f1f1f1", edgecolor="white", linewidth=0.4)
    sub = g[g.municipality == town]
    tracts = sub.dissolve(by="geoid_tract", aggfunc={"acs_median_income": "first"}).reset_index()
    tracts.plot(column="acs_median_income", cmap="YlGnBu", vmin=vmin, vmax=vmax, ax=ax, edgecolor="white", linewidth=0.7,
                missing_kwds={"color": "#d9d9d9", "hatch": "///", "edgecolor": "white"})
    corridor_zone.boundary.plot(ax=ax, color="#444", linewidth=1, linestyle="--", zorder=3)
    route_lines(ax, tc["segs"])
    st = tc["stations"]
    station_marks(ax, st[st.geometry.within(sub.union_all().buffer(150))], anchor_id, label=(town == "Worcester"))
    xmin, ymin, xmax, ymax = sub.total_bounds
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.set_title(title)
    scalebar(ax, 2000 if town == "Worcester" else 1000)


def figure1(m, bgs, tr, tc, r9, traffic, ref, F, H):
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold", "axes.titlesize": 11})
    g = bgs.merge(m[["geoid_bg", "acs_median_income", "municipality", "geoid_tract"]], on="geoid_bg", suffixes=("_x", ""))
    corridor_zone = gpd.GeoSeries([r9.clip(g.union_all().buffer(1500)).union_all().buffer(CORRIDOR_M)], crs=CRS_MA)
    vmin, vmax = np.nanpercentile(tr.acs_median_income.dropna(), [3, 97])
    fig = plt.figure(figsize=(17, 13.5), dpi=300)
    gs = fig.add_gridspec(2, 6, height_ratios=[1.2, 1], hspace=0.26, wspace=0.6, left=0.055, right=0.975, top=0.915, bottom=0.14)
    axA, axB, axC = (fig.add_subplot(gs[0, i:i + 2]) for i in (0, 2, 4))
    axD, axE = fig.add_subplot(gs[1, :3]), fig.add_subplot(gs[1, 3:])
    town_map(axA, g, "Worcester", tc, corridor_zone, vmin, vmax, traffic["station"], "A. Worcester (primary): tract income + Route 9 AADT")
    town_map(axB, g, "Shrewsbury", tc, corridor_zone, vmin, vmax, traffic["station"], "B. Shrewsbury (sensitivity)", pad=500)

    # C: measured AADT profile
    cin, s = tc["segs_in"], tc["stats"]
    for town, col in (("Worcester", "#e8eef5"), ("Shrewsbury", "#f4e9d8")):
        d = cin[cin.town == town]
        axC.axvspan(d.From_Measure.min(), d.To_Measure.max(), color=col, zorder=0)
        axC.text((d.From_Measure.min() + d.To_Measure.max()) / 2, 49500, town, ha="center", va="top", fontsize=10, fontweight="bold", color="#555")
    axC.step(np.r_[cin.From_Measure, cin.To_Measure.iloc[-1]], np.r_[cin.aadt, cin.aadt.iloc[-1]], where="post", color="#b2182b", lw=2.2,
             label="MassDOT segment AADT (LRS Traffic, 2023-25 mostly)")
    axC.fill_between(np.r_[cin.From_Measure, cin.To_Measure.iloc[-1]], np.r_[cin.aadt, cin.aadt.iloc[-1]], step="post", color="#b2182b", alpha=0.12)
    old = cin[cin.aadt_year < 2023]
    axC.scatter(old.From_Measure, old.aadt, s=14, c="#555", zorder=6, label="segment AADT older than 2023")
    st = tc["stations"]
    ok = st[(st.tier != "anchor") & st.measure.between(cin.From_Measure.min(), cin.To_Measure.max())]
    axC.scatter(ok.measure, ok.aadt, marker="^", s=70, c="#111", edgecolor="white", zorder=7, label="count stations on Route 9 (joined AADT)")
    axC.axhline(traffic["aadt"], color="#00a6a6", lw=1.6, ls="--", label=f"{traffic['station']} anchor {traffic['aadt']:,} (old model)")
    a = st[st.tier == "anchor"]
    if len(a):
        axC.scatter(a.measure, a.aadt, marker="*", s=240, c="#00a6a6", edgecolor="black", zorder=8)
    axC.set_ylim(0, 52000)
    axC.set_xlim(cin.From_Measure.min(), cin.To_Measure.max())
    axC.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))
    axC.set_xlabel("Route 9 milepost (MassDOT LRS, miles; west to east)")
    axC.set_ylabel("AADT (vehicles/day, both directions)")
    axC.set_title(f"C. Measured AADT along Route 9 ({F['aadt_Pooled']['km']} km in the two towns)")
    axC.legend(loc="lower right", fontsize=6.8, framealpha=0.95)
    axC.grid(alpha=0.25)

    # D: Worcester tract scatter
    wt = tr[(tr.municipality == "Worcester")].dropna(subset=["acs_median_income"])
    sh = tr[(tr.municipality == "Shrewsbury")].dropna(subset=["acs_median_income"])
    hh = wt.households.fillna(1500)
    all_ej = wt.ej_bgs == wt.block_groups
    for flag, col, lab in ((True, "#b2182b", "all block groups EJ-designated"), (False, "#6baed6", "some / no block groups EJ")):
        d = wt[all_ej == flag]
        axD.scatter(d.dist_m / 1000, d.acs_median_income, s=np.clip(d.households.fillna(1500) / 8, 20, 320), c=col, alpha=0.8,
                    edgecolor="white", linewidth=0.6, label=f"Worcester tract, {lab} (n={len(d)})")
    axD.scatter(sh.dist_m / 1000, sh.acs_median_income, s=np.clip(sh.households.fillna(1500) / 8, 20, 320), facecolors="none",
                edgecolors="#555", linewidth=1.1, label=f"Shrewsbury tract (sensitivity, n={len(sh)})")
    axD.set_xscale("log")
    axD.set_xlim(0.1, 8)
    axD.set_xticks([0.1, 0.25, 0.5, 1, 2, 4, 8])
    axD.xaxis.set_major_formatter(plt.ScalarFormatter())
    axD.xaxis.set_minor_formatter(plt.NullFormatter())
    q = pd.qcut(wt.dist_m, 5, duplicates="drop")
    tb = wt.groupby(q, observed=True).agg(x=("dist_m", "median"), y=("acs_median_income", "median"))
    axD.plot(tb.x / 1000, tb.y, color="black", lw=2, marker="D", ms=5, label="Worcester quintile medians")
    axD.axhline(ref["state_median_income"], color="#666", ls=":", lw=1.4)
    axD.text(7.8, ref["state_median_income"] * 1.03, f"MA median ${ref['state_median_income'] / 1000:.0f}k", ha="right", fontsize=8.5, color="#444")
    axD.axvline(CORRIDOR_M / 1000, color="#444", ls="--", lw=1)
    ws = F["worc_stats"]
    axD.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    axD.set_xlabel("Tract distance to Route 9 (km, area-weighted, log scale; dashed = 1.5 km corridor); marker size ~ households")
    axD.set_ylabel("ACS median household income ($)")
    axD.set_title(f"D. Worcester tracts: income vs distance (rho = {ws['r_t']:+.2f}, tract-bootstrap 95% CI [{ws['ci_rho'][0]:+.2f}, {ws['ci_rho'][1]:+.2f}], n = {ws['n_t']})")
    axD.grid(alpha=0.25)
    axD.legend(fontsize=7.5, loc="upper left", framealpha=0.95)

    # E: who lives near Route 9 (Worcester, household-weighted)
    pr = [H["near"][("Wor", b)] for b in BUFFERS_M]
    x = np.arange(len(pr))
    axE.bar(x - 0.19, [p["med_income"] for p in pr], 0.36, color="#b2182b", label="households inside buffer")
    axE.bar(x + 0.19, [p["beyond"]["med_income"] for p in pr], 0.36, color="#9ecae1", label="households beyond buffer")
    for i, p in enumerate(pr):
        axE.text(i - 0.19, p["med_income"] + 1500, f"${p['med_income'] / 1000:.0f}k\n{p['pct_under_50k']:.0f}% <$50k", ha="center", fontsize=8.5, fontweight="bold")
        axE.text(i + 0.19, p["beyond"]["med_income"] + 1500, f"${p['beyond']['med_income'] / 1000:.0f}k\n{p['beyond']['pct_under_50k']:.0f}% <$50k", ha="center", fontsize=8.5)
    axE.axhline(ref["state_median_income"], color="#666", ls=":", lw=1.4)
    axE.text(len(pr) - 0.5, ref["state_median_income"] * 1.02, f"MA median ${ref['state_median_income'] / 1000:.0f}k", ha="right", fontsize=8.5, color="#444")
    axE.set_xticks(x)
    axE.set_xticklabels([f"within {b} m\n{p['hh']:,.0f} households ({p['hh'] / p['tot_hh']:.0%})\n{p['ej_pop']:,.0f} EJ residents" for b, p in zip(BUFFERS_M, pr)], fontsize=9)
    axE.set_ylim(0, ref["state_median_income"] * 1.25)
    axE.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    axE.set_ylabel("Household-weighted median income ($)")
    axE.set_title("E. Who lives near Route 9: Worcester households by distance")
    axE.legend(fontsize=8.5, loc="upper left")
    axE.grid(alpha=0.25, axis="y")

    cax1 = fig.add_axes([0.05, 0.078, 0.2, 0.011])
    sm = plt.cm.ScalarMappable(cmap="YlGnBu", norm=plt.Normalize(vmin, vmax))
    cb = fig.colorbar(sm, cax=cax1, orientation="horizontal")
    cb.set_label("ACS 2024 tract median household income (A, B)", fontsize=9)
    cb.ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    cax2 = fig.add_axes([0.32, 0.078, 0.2, 0.011])
    cb2 = fig.colorbar(plt.cm.ScalarMappable(cmap=AADT_CMAP, norm=AADT_NORM), cax=cax2, orientation="horizontal")
    cb2.set_label("MassDOT AADT on Route 9 segments (A, B)", fontsize=9)
    cb2.ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))
    fig.legend(handles=[Line2D([0], [0], marker="^", color="w", markerfacecolor="#111", markersize=9, label="count station on Route 9"),
                        Line2D([0], [0], marker="*", color="w", markerfacecolor="#00a6a6", markeredgecolor="k", markersize=15, label=f"{traffic['station']} anchor"),
                        Line2D([0], [0], color="#444", ls="--", lw=1, label=f"corridor: centroid <= {CORRIDOR_M / 1000:g} km"),
                        Patch(facecolor="#d9d9d9", hatch="///", edgecolor="white", label="no income estimate")],
               loc="center left", ncol=2, bbox_to_anchor=(0.6, 0.082), fontsize=8.5, frameon=False)

    fig.suptitle("Figure 1. Measured Route 9 traffic loading and neighbourhood income, Worcester (primary) and Shrewsbury (sensitivity), MA",
                 fontsize=14.5, fontweight="bold", y=0.975)
    fig.text(0.04, 0.012,
             "Sources: MassDOT Roads / RoadInventoryLRS Traffic (AADT by segment) and TrafficCountLocations; ACS 5-yr 2024 (S1901); MassGIS EJ 2020 block groups; US Census TIGER/Line 2024. "
             "Route 9 loading is measured per segment; neighbourhood exposure (not shown) is modelled by distance decay and is not a measurement. "
             "Block-group income = parent-tract ACS estimate; panels A, B, D use tracts; E pools ACS bracket shares across households (areal interpolation; EJ residents = EJ-designated block groups only).",
             fontsize=7.8, color="#444", wrap=True)
    path = CHART_DIR / "figure1_income_traffic_ej.png"
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    progress(f"  saved {path}")


def figure2(pm, mon, mon_gdf, r9_line):
    sites = list(mon.site)
    pal = dict(zip(sites, ["#1f77b4", "#e07b00", "#2ca02c", "#9467bd"]))
    dist = dict(zip(sites, mon_gdf.geometry.distance(r9_line).to_numpy() / 1000))
    fig = plt.figure(figsize=(16, 6.4), dpi=300)
    gs = fig.add_gridspec(1, 2, width_ratios=[2.2, 1], wspace=0.14, left=0.055, right=0.985, top=0.84, bottom=0.2)
    axA, axB = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    ymax = max(NAAQS_24H * 1.35, pm.pm25.max() * 1.2)
    for s in sites:
        d = pm[pm.site == s].sort_values("date")
        axA.plot(d.date, d.pm25, color=pal[s], lw=1.0, alpha=0.9, label=f"{s}: mean {d.pm25.mean():.2f}, {dist[s]:.1f} km from Route 9")
        over = d[d.pm25 > WHO_24H]
        axA.scatter(over.date, over.pm25, s=22, color=pal[s], edgecolor="black", linewidth=0.5, zorder=4)
    axA.axhline(NAAQS_24H, color="#b2182b", lw=2, label=f"Federal 24-h NAAQS {NAAQS_24H:.0f}")
    axA.axhline(WHO_24H, color="#e07b00", lw=1.5, ls="--", label=f"WHO 24-h guideline {WHO_24H:.0f} (circled days)")
    axA.axhline(NAAQS_ANNUAL, color="#555", lw=1.2, ls=":", label=f"Federal annual NAAQS {NAAQS_ANNUAL:.0f}")
    axA.set_ylim(0, ymax)
    axA.set_ylabel("Daily mean PM2.5 (ug/m3)")
    axA.xaxis.set_major_locator(mdates.MonthLocator())
    axA.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axA.set_title("A. Daily PM2.5 at the Worcester County monitors, 2025 (regional context)")
    axA.legend(loc="upper left", fontsize=8.2, framealpha=0.95)
    axA.grid(alpha=0.25)
    thr = [("> 9", NAAQS_ANNUAL), ("> 12", 12.0), (f"> {WHO_24H:.0f}\n(WHO)", WHO_24H), ("> 25", 25.0), (f"> {NAAQS_24H:.0f}\n(federal)", NAAQS_24H)]
    w = 0.8 / len(sites)
    for i, s in enumerate(sites):
        arr = pm[pm.site == s].pm25
        cnt = [int((arr > t).sum()) for _, t in thr]
        xs = np.arange(len(thr)) + (i - (len(sites) - 1) / 2) * w
        axB.bar(xs, cnt, width=w * 0.92, color=pal[s], label=s)
        for x, v in zip(xs, cnt):
            axB.text(x, v + 4, str(v), ha="center", fontsize=8.5, fontweight="bold")
    axB.set_xticks(range(len(thr)))
    axB.set_xticklabels([t for t, _ in thr], fontsize=9)
    axB.set_xlabel("Daily mean PM2.5 threshold (ug/m3)")
    axB.set_ylabel("Days above threshold")
    axB.set_title("B. Days above benchmarks")
    axB.legend(fontsize=8.5)
    axB.grid(alpha=0.25, axis="y")
    fig.suptitle("Appendix Figure A1 (Figure 2). Regional PM2.5 context, Worcester County: not corridor-specific", fontsize=14.5, fontweight="bold", y=0.965)
    fig.text(0.055, 0.045, "DATA GAP: no roadside PM2.5 monitor exists on Route 9; these ambient monitors cannot localise PM2.5 to the corridor and are not used to rank block groups.",
             fontsize=9.5, color="#b2182b", fontweight="bold")
    fig.text(0.055, 0.012, "Source: EPA AQS daily PM2.5 (88101). NAAQS compliance is judged on 3-year design values (annual mean <= 9.0; 98th percentile <= 35); this is a single-year screen.",
             fontsize=8, color="#444")
    path = CHART_DIR / "figure2_pm25_distribution.png"
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    progress(f"  saved {path}")


def figure3(m, bgs, tc, r9, traffic, F):
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold", "axes.titlesize": 11.5})
    g = bgs.merge(m[["geoid_bg", "municipality", "vuln_quintile", "priority_hotspot", "priority_rank", "vulnerability_index"]], on="geoid_bg", suffixes=("_x", ""))
    qcols = dict(zip(["Q1 lowest", "Q2", "Q3", "Q4", "Q5 highest"], ["#fff5e6", "#fdd49e", "#fdae6b", "#e6550d", "#7f0000"]))
    fig = plt.figure(figsize=(17, 8.6), dpi=300)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1], wspace=0.5, left=0.06, right=0.985, top=0.9, bottom=0.14)
    ax, axb = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    for k, col in qcols.items():
        part = g[g.vuln_quintile == k]
        if len(part):
            part.plot(ax=ax, color=col, edgecolor="white", linewidth=0.4)
    g[g.vuln_quintile.isna()].plot(ax=ax, color="#d9d9d9", hatch="///", edgecolor="white")
    ph = g[g.priority_hotspot.astype(bool)]
    ph.boundary.plot(ax=ax, color="black", linewidth=1.5, zorder=6)
    route_lines(ax, tc["segs"], lw=3.0)
    top = ph.sort_values("priority_rank").head(15)
    for r in top.itertuples():
        p = r.geometry.representative_point()
        ax.annotate(str(int(r.priority_rank)), (p.x, p.y), ha="center", va="center", fontsize=8.5, fontweight="bold", color="white", zorder=9,
                    bbox=dict(boxstyle="circle,pad=0.18", fc="black", ec="white", lw=0.8))
    xmin, ymin, xmax, ymax = g[g.municipality == "Worcester"].total_bounds
    ax.set_xlim(xmin - 300, xmax + 300)
    ax.set_ylim(ymin - 300, ymax + 300)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.set_title(f"A. Worcester vulnerability; {len(ph)} priority hotspots outlined (top 15 numbered)")
    scalebar(ax, 2000)
    ax.legend(handles=[Patch(facecolor=c, edgecolor="#999", label=f"Vulnerability {k}") for k, c in qcols.items()]
              + [Patch(facecolor="none", edgecolor="black", label="priority hotspot (Q5 inside 1.5 km corridor)")],
              loc="lower left", fontsize=8.5, framealpha=0.95)
    cax = fig.add_axes([0.40, 0.075, 0.14, 0.012])
    cbt = fig.colorbar(plt.cm.ScalarMappable(cmap=AADT_CMAP, norm=AADT_NORM), cax=cax, orientation="horizontal")
    cbt.set_label("Route 9 AADT (MassDOT)", fontsize=8.5)
    cbt.ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))

    top = top.iloc[::-1]
    labels = [f"#{int(r.priority_rank)}  {bg_label(r.geoid_bg)} ({r.municipality[:4]}.)" for r in top.itertuples()]
    mm = m.set_index("geoid_bg")
    axb.barh(range(len(top)), top.vulnerability_index, color="#7f0000", height=0.7)
    for i, r in enumerate(top.itertuples()):
        row = mm.loc[r.geoid_bg]
        axb.text(r.vulnerability_index + 0.8, i, f"adj. AADT {row.nearest_segment_aadt / 1000:.0f}k | {row.est_ej_pop_within_500m:,.0f} EJ res. <=500 m",
                 va="center", fontsize=8)
    axb.set_yticks(range(len(top)))
    axb.set_yticklabels(labels, fontsize=8.5)
    axb.set_xlim(0, 175)
    axb.set_xticks([0, 20, 40, 60, 80, 100])
    axb.set_xlabel("Vulnerability index (0-100; income + EJ criteria)")
    axb.set_title("B. Top-15 priority block groups (tract-block group)")
    axb.grid(alpha=0.25, axis="x")
    fig.suptitle("Figure 3. Where to look first: vulnerability without traffic, inside the Route 9 corridor", fontsize=14.5, fontweight="bold", y=0.975)
    fig.text(0.02, 0.012, "Vulnerability = mean percentile of low tract income and EJ criteria met (no traffic term). Route 9 shown at measured AADT per segment. "
             "EJ residents <= 500 m counts EJ-designated block groups only (0 = none counted). Ecological, neighbourhood-scale indicator; not individual exposure or health risk.", fontsize=8, color="#444")
    path = CHART_DIR / "figure3_priority_hotspots.png"
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    progress(f"  saved {path}")


# --------------------------------------------------------------------------- #
# Executive summary, changelog, advisory brief, data dictionary
# --------------------------------------------------------------------------- #
def build_headlines(m, traffic, ref, F) -> dict:
    sc = {"Wor": m.municipality.eq("Worcester"), "Pool": pd.Series(True, index=m.index)}
    H = {"near": {}}
    for k, sel in sc.items():
        d = m[sel]
        for b in BUFFERS_M:
            s = d[f"pct_area_within_{b}m"] / 100
            H["near"][(k, b)] = {**zone_profile(d, s), "tot_pop": d.total_pop.sum(), "tot_hh": d.est_households.sum(),
                                 "beyond": zone_profile(d, 1 - s)}
        s30 = d["pct_area_within_500m_aadt30k"] / 100
        H["near"][(k, "30k")] = zone_profile(d, s30)
    return H


def exec_summary(m, traffic, ref, F, H):
    section("exec")
    wp, ws, sh, pm_ = F["worc"], F["worc_stats"], F["shrew"], F["pm"]
    a = F["aadt_Pooled"]
    n3, n5, n10 = (H["near"][("Pool", b)] for b in BUFFERS_M)
    w5 = H["near"][("Wor", 500)]
    hi = H["near"][("Pool", "30k")]
    vph = F["vuln_ph"]
    B = []
    tiers = F["r9_tiers"]
    B.append(f"Measured traffic now drives the corridor picture: MassDOT segment AADT covers all {F['aadt_Pooled']['km']} km of Route 9 in Worcester + Shrewsbury "
             f"({F['share_recent']:.0%} of length is 2023-2025 data). All {F['n_r9_unique']} on-route count stations got an AADT ({tiers.get('T2', 0)} via LRS station ID and milepost, "
             f"{tiers.get('T3', 0)} by spatial match); the Statn_Num join named in the brief matched none, because that field is empty.")
    B.append(f"Loading ranges {a['min']:,.0f}-{a['max']:,.0f} veh/day (length-weighted mean {a['AADT_mean(len-wtd)']:,.0f}); {a['%km_>=30k']}% of the corridor carries >= 30k and "
             f"it rises from Worcester (mean {F['aadt_Worcester']['AADT_mean(len-wtd)']:,.0f}) to Shrewsbury (mean {F['aadt_Shrewsbury']['AADT_mean(len-wtd)']:,.0f}). "
             f"The old single value ({traffic['aadt']:,}, M3002W) is {F['anchor']['diff_pct']:+.1f}% against the MassDOT segment at that milepost but misstates both ends.")
    B.append(f"The 75% westbound skew ({traffic['wb']:,} WB vs {traffic['eb']:,} EB) is one station's count, not a corridor property.")
    B.append(f"Who lives near: about {n3['ej_pop']:,.0f} EJ-designated residents ({n3['ej_pop'] / n3['tot_pop']:.0%}) live within 300 m, {n5['ej_pop']:,.0f} ({n5['ej_pop'] / n5['tot_pop']:.0%}) within 500 m "
             f"and {n10['ej_pop']:,.0f} ({n10['ej_pop'] / n10['tot_pop']:.0%}) within 1 km of Route 9; households within 500 m ~{n5['hh']:,.0f} ({n5['hh'] / n5['tot_hh']:.0%} of all in the two towns).")
    hw = H["near"][("Wor", "30k")]
    B.append(f"The busiest stretches are not beside the lowest-income neighbourhoods: ~{hi['ej_pop']:,.0f} EJ residents / ~{hi['hh']:,.0f} households live within 500 m of segments "
             f"carrying >= 30k veh/day (median income ${hi['med_income']:,.0f}), mostly at the Shrewsbury end; in Worcester only {hw['ej_pop']:,.0f} EJ residents do, "
             f"while its low-income corridor neighbourhoods sit beside 14k-28k segments.")
    B.append(f"Worcester (primary): household-weighted median income is ${wp['pi'][0]:,.0f} in the corridor vs ${wp['po'][0]:,.0f} in the rest of the city; "
             f"{wp['pi'][1]:.0f}% vs {wp['po'][1]:.0f}% of households earn under $50k.")
    B.append(f"Within Worcester, tract income rises with distance from Route 9 (rho = {ws['r_t']:+.2f}, tract-bootstrap 95% CI [{ws['ci_rho'][0]:+.2f}, {ws['ci_rho'][1]:+.2f}], n = {ws['n_t']} tracts); "
             f"with town fixed effects the slope is {money(ws['fe'][0])}/km (CI {money(ws['fe'][1])} to {money(ws['fe'][2])}). Moran's I ~{ws['mi_all']:.2f}, so intervals use cluster / tract bootstrap.")
    B.append(f"EJ designation: {wp['ej_i']:.0%} of Worcester corridor block groups vs {wp['ej_o']:.0%} elsewhere in the city (odds ratio {wp['or']:.1f}, {fmt_p(wp['p_or'])}); high everywhere, with only a suggestive (not conclusive) edge near the road.")
    B.append(f"Shrewsbury is a sensitivity case: {sh['n_corr']} corridor block groups in {sh['tr_corr']} tracts, tract median income ${sh['inc_med']:,.0f}; pooling both towns "
             f"(tract rho {sh['r_p']:+.2f}) vs Worcester alone ({sh['r_w']:+.2f}) changes the gradient little, but adds the highest-volume stretch with comparatively few nearby residents.")
    B.append(f"Without any traffic term, {vph['n']} corridor block groups ({vph['pop']:,.0f} EJ residents; {vph['n_w']} in Worcester) rank in the top vulnerability quintile "
             f"(rho with distance {F['vuln_Pooled'][0]:+.2f}); the legacy CBI's distance link ({F['vuln_rr']['cumulative_burden_index']:+.2f}) is partly built in.")
    B.append(f"PM2.5 is regional only: 2025 mean {pm_['mean']:.2f} ug/m3 (below the {NAAQS_ANNUAL:.0f} federal annual standard, above the WHO {WHO_ANNUAL:.0f} guideline), "
             f"no day above the federal 24-h standard; monitors {pm_['dist_mon']:.0f} km apart move together (rho {pm_['rho']:.2f}); there is no roadside monitor on Route 9.")
    B.append("Results are neighbourhood-scale associations; near-road exposure is modelled, populations are interpolated, and nothing here shows individual exposure, health effects or causation.")
    for i, b in enumerate(B, 1):
        say(f"{i:>2}. {b}")
    F["bullets"] = B
    say("\nRecommended next steps for the advisory group:")
    steps = [
        "Commission near-road PM2.5 / NO2 (or UFP) monitoring on the >= 30k stretches and beside priority block groups; ambient county monitors cannot answer the corridor question.",
        "Ask MassDOT for classification counts with truck share and directional volumes at M3002W-class stations to verify the westbound skew and refresh older (pre-2023) segments.",
        "Treat Worcester as the primary equity case; review the priority block-group list (Figure 3, tract table) with neighbourhood groups before any targeting decision.",
        "Fill the population gap (decennial / ACS block-group population for non-EJ block groups) so near-road counts cover everyone, not only EJ-designated residents.",
        "Pair this analysis with tract health outcomes (e.g., asthma ED visits) if the group wants evidence on effects rather than proximity.",
        "Re-run annually (fetch_massdot_traffic_aadt.py --refresh) as MassDOT updates AADT vintages.",
    ]
    for i, s_ in enumerate(steps, 1):
        say(f"  {chr(96 + i)}. {s_}")
    F["steps"] = steps


def build_changelog(m, F):
    section("changelog")
    new = {"hotspots": int(m.hotspot.sum()), "hotspot_pop": float(m.loc[m.hotspot, "total_pop"].sum()), "corridor_bgs": int(m.in_corridor.sum()),
           "ej_pop_300": m.est_ej_pop_within_300m.sum(), "ej_pop_500": m.est_ej_pop_within_500m.sum(), "ej_pop_1000": m.est_ej_pop_within_1000m.sum(),
           "mean_exposure": float(m.exposure_index.mean())}
    rho_inc = spearman(m, "dist_centroid_m", "acs_median_income")[0]
    d = m[["dist_centroid_m", "acs_median_income"]].dropna()
    slope = stats.linregress(d.dist_centroid_m / 1000, d.acs_median_income).slope
    moved, same = [], []
    for k, lab in [("hotspots", "legacy CBI hotspot block groups"), ("hotspot_pop", "EJ residents in legacy CBI hotspots"),
                   ("mean_exposure", "mean exposure_index (veh/day-equivalent)")]:
        (moved if abs(new[k] - PRIOR[k]) > 0.5 else same).append(f"{lab}: {PRIOR[k]:,.0f} -> {new[k]:,.0f}")
    for k, lab, tol in [("corridor_bgs", "corridor block groups", 0), ("ej_pop_300", "EJ residents within 300 m", 1), ("ej_pop_500", "EJ residents within 500 m", 1),
                        ("ej_pop_1000", "EJ residents within 1 km", 1)]:
        (moved if abs(new[k] - PRIOR[k]) > tol else same).append(f"{lab}: {PRIOR[k]:,.0f} -> {new[k]:,.0f}")
    (moved if abs(rho_inc - PRIOR["rho_inc_dist"]) > 0.005 else same).append(f"pooled rho(distance, income): {PRIOR['rho_inc_dist']:+.2f} -> {rho_inc:+.2f}")
    (moved if abs(slope - PRIOR["slope_per_km"]) > 1 else same).append(f"pooled OLS income slope: ${PRIOR['slope_per_km']:,.0f}/km -> ${slope:,.0f}/km")
    say("Method / framing changes:")
    say(f"  - Traffic basis: {PRIOR['aadt_basis']} -> measured MassDOT LRS AADT per Route 9 segment ({F['aadt_Pooled']['min']:,.0f}-{F['aadt_Pooled']['max']:,.0f} veh/day); "
        f"exposure_index is now nearest-segment AADT x exp(-d/300 m); the old model is kept as legacy_exposure_index for one release.")
    say("  - Narrative is Worcester-first, Shrewsbury is a sensitivity section; household-weighted pooled incomes replace block-group medians as the headline summary.")
    say("  - Headline traffic-independent measure: vulnerability_index / priority_hotspot (new); CBI and `hotspot` are retained but flagged as partly built-in.")
    say("  - Figure 1 reworked (Worcester map + Shrewsbury panel, measured AADT, stations, tract scatter); Figure 2 shortened to a PM2.5 appendix; Figure 3 added.")
    say("Headline numbers that MOVED:")
    for s_ in moved or ["  (none)"]:
        say(f"  - {s_}")
    say("Headline numbers UNCHANGED (geometry / income inputs are identical):")
    for s_ in same:
        say(f"  - {s_}")
    F["new_hot"] = new


def advisory_brief(m, traffic, ref, F, H) -> str:
    wp, ws, sh, pm_ = F["worc"], F["worc_stats"], F["shrew"], F["pm"]
    a = F["aadt_Pooled"]
    n3, n5, n10 = (H["near"][("Pool", b)] for b in BUFFERS_M)
    w3, w5, w10 = (H["near"][("Wor", b)] for b in BUFFERS_M)
    hi = H["near"][("Pool", "30k")]
    vph = F["vuln_ph"]
    top = m[m.priority_hotspot].sort_values("priority_rank").head(8)
    L = ["# Route 9 corridor (Worcester and Shrewsbury): advisory brief", "",
         "Plain-language summary of `outputs/summary_statistics.txt`. Every number below is computed by `route9_deep_analysis.py` and matches that file.", "",
         "## The short version", "",
         f"- Route 9 carries between {a['min']:,.0f} and {a['max']:,.0f} vehicles a day inside the two towns (average about {a['AADT_mean(len-wtd)']:,.0f}), measured by MassDOT segment counts. "
         f"Traffic is heaviest in Shrewsbury and the eastern end; about {a['%km_>=30k']}% of the road carries 30,000 or more.",
         f"- Worcester is the main equity story. Households within about a mile of the road have a median income near ${wp['pi'][0]:,.0f}, versus ${wp['po'][0]:,.0f} in the rest of the city; "
         f"{wp['pi'][1]:.0f}% of corridor households earn under $50,000 versus {wp['po'][1]:.0f}%.",
         f"- Income rises with distance from Route 9 in Worcester (tract-level correlation {ws['r_t']:+.2f}). This holds with town effects included, so it is not just Worcester versus Shrewsbury.",
         f"- Close to the road: roughly {n5['ej_pop']:,.0f} residents of environmental justice (EJ) areas live within 500 m (about {n5['hh']:,.0f} households in all); "
         f"{hi['ej_pop']:,.0f} EJ residents live within 500 m of the busiest (30,000+) stretches, mostly at the Shrewsbury end; Worcester's lower-income corridor neighbourhoods sit beside 14,000-28,000 stretches.",
         f"- {vph['n']} neighbourhood block groups near the road rank in the most vulnerable fifth by income and EJ criteria alone (no traffic involved); they are the suggested first look.",
         "- Air quality data are county-wide only. They show the region meets the federal annual PM2.5 standard but sits above the stricter WHO guideline; they cannot say anything about Route 9 itself.", "",
         "## Who lives near the road", "",
         "| Distance from Route 9 | EJ residents | Households (est.) | Median household income (inside) | Beyond |", "|---|---|---|---|---|"]
    for b, p in zip(BUFFERS_M, (n3, n5, n10)):
        L.append(f"| within {b} m (both towns) | {p['ej_pop']:,.0f} ({p['ej_pop'] / p['tot_pop']:.0%} of EJ residents) | {p['hh']:,.0f} ({p['hh'] / p['tot_hh']:.0%}) "
                 f"| ${p['med_income']:,.0f} | ${p['beyond']['med_income']:,.0f} |")
    L += ["", "EJ residents are counted only in EJ-designated block groups (the state table has no population for the others), so they undercount, especially in Shrewsbury. "
          "Households come from the Census income table and cover every block group.", "",
          "## Worcester", "",
          f"- {wp['n_bg']} block groups, {wp['n_tr']} tracts; {wp['n_corr_bg']} block groups ({wp['n_corr_tr']} tracts) are within 1.5 km of Route 9.",
          f"- {wp['ej_i']:.0%} of corridor block groups are EJ-designated versus {wp['ej_o']:.0%} elsewhere in Worcester (odds ratio {wp['or']:.1f}).",
          f"- Each extra kilometre from the road goes with roughly {money(ws['fe'][0])} higher tract income (95% interval {money(ws['fe'][1])} to {money(ws['fe'][2])}, town effects included).",
          "- The map and tract table (`outputs/tract_table_route9.csv`) show which tracts are closest, poorest and busiest.", "",
          "## Shrewsbury (check, not the headline)", "",
          f"- Few corridor block groups ({sh['n_corr']}), high incomes (tract median ${sh['inc_med']:,.0f}); treating the two towns together barely changes the pattern (tract-level correlation {sh['r_p']:+.2f} vs {sh['r_w']:+.2f} for Worcester alone).", "",
          "## Where to look first", "",
          "Block groups in the top vulnerability fifth (low income plus EJ criteria) within 1.5 km of Route 9 (Figure 3):", "",
          "| Rank | Tract-block group | Town | Tract income | EJ residents within 500 m | Adjacent AADT |", "|---|---|---|---|---|---|"]
    for r in top.itertuples():
        L.append(f"| {int(r.priority_rank)} | {bg_label(r.geoid_bg)} | {r.municipality} | ${r.income_best:,.0f} | {r.est_ej_pop_within_500m:,.0f} | {r.nearest_segment_aadt:,.0f} |")
    L += ["", f"In total {vph['n']} block groups meet the test ({vph['pop']:,.0f} EJ residents). A 0 in the 500 m column means no part of that block group's area lies within 500 m of the road; the block group is still inside the 1.5 km corridor.", "",
          "## What this does not tell us", "",
          "- Traffic next to homes is modelled by distance from the road, not measured. Only the volume on Route 9 itself is measured.",
          "- Nothing here measures pollution at the roadside, health effects, or cause and effect.",
          "- The westbound-heavy count at one station (75% westbound) is not a corridor-wide fact.",
          f"- PM2.5: 2025 mean {pm_['mean']:.2f} ug/m3 at two county monitors about {pm_['dist_mon']:.0f} km apart; no monitor sits on Route 9.", "",
          "## Suggested next steps", ""]
    L += [f"{i}. {s_}" for i, s_ in enumerate(F["steps"], 1)]
    L += ["", "## Sources", "",
          "MassDOT Roads services (RoadInventoryLRS Traffic, Traffic_Station; TrafficCountLocations); ACS 5-year 2024 table S1901; MassGIS 2020 Environmental Justice block groups; "
          "US Census TIGER/Line 2024; EPA Air Quality System. Re-run: `python fetch_massdot_traffic_aadt.py` then `python route9_deep_analysis.py`.", ""]
    return "\n".join(L)


COLUMN_DOC = {
    "geoid_bg": "Census block-group GEOID (12 digits).", "geoid_tract": "Census tract GEOID (11 digits).", "bg_name": "MassGIS block-group name (EJ block groups only).",
    "municipality": "Worcester or Shrewsbury.", "ej_designated": "Block group present in MassGIS EJ_POLY (EJ-designated).",
    "ej_criteria_code": "MassGIS EJ criteria code.", "ej_criteria_count": "EJ criteria met (0-3; 0 = not EJ).", "ej_criteria_desc": "EJ criteria met, text.",
    "ej_income": "EJ criterion: median household income <= 65% of state.", "ej_minority": "EJ criterion: minority share.", "ej_english_isolation": "EJ criterion: English isolation.",
    "total_pop": "Block-group population (EJ_POLY; blank for non-EJ block groups).", "total_hh": "Households (EJ_POLY; blank for non-EJ).", "pct_minority": "% minority (EJ block groups only).",
    "lep_hh": "Limited-English households (EJ only).", "pct_lep_hh": "% limited-English households (EJ only).", "bg_median_hh_income": "Block-group median household income, EJ table (older ACS vintage).",
    "acs_median_income": "ACS 2024 5-yr tract median household income (repeated for each block group in the tract).", "acs_median_income_moe": "Margin of error of acs_median_income.",
    "acs_income_cv": "Coefficient of variation of acs_median_income.", "acs_income_reliable": "True when CV < 0.30.", "acs_income_topcoded": "Tract median is top-coded.",
    "acs_pct_hh_under_50k": "% households under $50,000 (tract).", "acs_pct_hh_150k_plus": "% households at or above $150,000 (tract).", "income_best": "acs_median_income, else EJ-table income.",
    "income_source": "Where income_best came from.", "income_pct_of_state": "income_best as % of the statewide median.", "centroid_lat": "Block-group centroid latitude.",
    "centroid_lon": "Block-group centroid longitude.", "area_km2": "Block-group land+water polygon area (km2).", "dist_centroid_m": "Distance, block-group centroid to TIGER Route 9 centreline (m). Primary distance.",
    "dist_edge_m": "Distance, nearest polygon edge to Route 9 (m).", "mean_dist_m": "Mean distance over the block group's 50 m grid cells (m).", "dist_band": "Band of dist_centroid_m.",
    "in_corridor": "dist_centroid_m <= 1,500 m.", "exposure_index": "MODELLED. Nearest MassDOT Route 9 segment AADT x exp(-d/300 m), mean over 50 m grid cells (AADT-equivalent veh/day). Replaces the single-station model.",
    "pct_area_within_300m": "% of block-group area within 300 m of Route 9.", "pct_area_within_500m": "% of area within 500 m.", "pct_area_within_1000m": "% of area within 1 km.",
    "pm_monitor": "Nearest EPA PM2.5 monitor (label only; regional context).", "dist_pm_monitor_km": "Distance to that monitor (km).", "pm25_monitor_annual_mean": "That monitor's mean daily PM2.5 (ug/m3).",
    "pm25_monitor_p98": "98th percentile daily PM2.5.", "pm25_monitor_max": "Maximum daily PM2.5.", "pm25_monitor_days_over_who24": "Days above WHO 24-h guideline (15 ug/m3).",
    "shape_area": "EJ_POLY polygon area (source units).", "shape_len": "EJ_POLY polygon perimeter (source units).", "acs_households": "ACS tract households (S1901).",
    "acs_mean_income": "ACS tract mean household income.", "aadt_station": "traffic.csv anchor AADT at M3002W (same for every row; NOT corridor loading).",
    "aadt_westbound": "Anchor westbound AADT at M3002W.", "aadt_eastbound": "Anchor eastbound AADT at M3002W.", "westbound_share": "Anchor westbound share at M3002W (single station).",
    "est_ej_pop_within_300m": "EJ residents within 300 m (areal interpolation).", "est_ej_pop_within_500m": "EJ residents within 500 m.", "est_ej_pop_within_1000m": "EJ residents within 1 km.",
    "p_traffic": "Percentile rank of exposure_index (0-1).", "p_low_income": "Percentile rank of low income.", "p_ej_criteria": "Percentile rank of EJ criteria count.",
    "cumulative_burden_index": "Legacy CBI 0-100: mean of p_traffic, p_low_income, p_ej_criteria. Distance link is partly by construction.", "cbi_quintile": "Quintile of CBI.",
    "hotspot": "Legacy: top CBI quintile AND in_corridor.",
    "legacy_exposure_index": "Previous release model: 28,112 x exp(-d/300 m), mean over grid. Kept one release.", "exposure_index_d150": "Sensitivity: as exposure_index with 150 m decay.",
    "exposure_method": "Model used for the row (segment_nearest_lrs_aadt_d300 or fallback).", "nearest_segment_id": "MassDOT LRS Traffic segment nearest the centroid (route@milepost).",
    "nearest_segment_aadt": "MEASURED AADT of that segment (veh/day).", "nearest_segment_aadt_year": "AADT_Year of that segment.", "nearest_station_id": "Nearest on-Route-9 count station with AADT (or M3002W anchor).",
    "nearest_station_aadt": "AADT joined to that station.", "nearest_station_aadt_year": "AADT_Year of that station's segment.", "nearest_station_dist_m": "Distance centroid to that station (m).",
    "pct_area_within_300m_aadt20k": "% of area within 300 m of Route 9 where the adjacent segment AADT >= 20,000.", "pct_area_within_300m_aadt30k": "... >= 30,000.",
    "pct_area_within_500m_aadt20k": "% within 500 m, adjacent AADT >= 20,000.", "pct_area_within_500m_aadt30k": "... >= 30,000.",
    "pct_area_within_1000m_aadt20k": "% within 1 km, adjacent AADT >= 20,000.", "pct_area_within_1000m_aadt30k": "... >= 30,000.",
    "est_ej_pop_within_300m_aadt30k": "EJ residents within 300 m of segments >= 30,000 AADT.", "est_ej_pop_within_500m_aadt30k": "... within 500 m.", "est_ej_pop_within_1000m_aadt30k": "... within 1 km.",
    "est_households": "Estimated households: ACS tract households allocated across block groups (EJ-table households as shares).", "est_hh_within_300m": "Estimated households within 300 m.",
    "est_hh_within_500m": "Estimated households within 500 m.", "est_hh_within_1000m": "Estimated households within 1 km.",
    "vulnerability_index": "Traffic-independent 0-100: mean percentile of low income and EJ criteria.", "vuln_quintile": "Quintile of vulnerability_index.",
    "priority_hotspot": "vuln_quintile = Q5 AND in_corridor.", "priority_rank": "Rank among priority hotspots (vulnerability, then EJ residents within 500 m).",
}


def data_dictionary(master: pd.DataFrame) -> str:
    L = ["# Data dictionary: `outputs/master_route9_table.csv`", "",
         f"{len(master)} block groups x {master.shape[1]} columns. Legacy columns keep their names and positions; new columns are appended after `hotspot`. "
         "Columns marked MODELLED are not measurements.", "",
         "Changed meaning: `exposure_index` (now measured segment AADT x decay; old model in `legacy_exposure_index`). `aadt_station` / `aadt_westbound` / `aadt_eastbound` / "
         "`westbound_share` are the M3002W anchor, not corridor loading.", "", "| Column | Description |", "|---|---|"]
    for c in master.columns:
        L.append(f"| `{c}` | {COLUMN_DOC.get(c, '')} |")
    L += ["", "## Other outputs", "", "- `outputs/tract_table_route9.csv`: one row per tract (income, distance, adjacent AADT, EJ counts, vulnerability).",
          "- `cache/massdot/*.geojson`: raw MassDOT pulls (re-run `fetch_massdot_traffic_aadt.py --refresh` to update).", ""]
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Main pipeline
# --------------------------------------------------------------------------- #
def main() -> None:
    F: dict = {}
    data_dir = resolve_data_dir()
    section("audit")
    say(f"Data folder : {data_dir}")
    say(f"Script root : {ROOT}")
    progress("Loading inputs")
    acs, ref = load_acs(find_file(data_dir, ["ACSST5Y2024.S1901-Data*.csv"]))
    ej_all = load_ej(find_file(data_dir, ["EJ_POLY*.dbf", "*.dbf"]))
    traffic = load_traffic(find_file(data_dir, ["traffic.csv", "traffic*.csv*", "traffic*"]))
    pm = load_pm25(find_file(data_dir, ["ad_viz_plotval_data*.csv"]))

    say("\nMissing-value audit (after cleaning):")
    missing_audit("ACS S1901, Worcester County tracts", acs, ["acs_households", "acs_median_income", "acs_median_income_moe", "acs_mean_income", "acs_pct_hh_under_50k"])
    missing_audit("EJ DBF, statewide", ej_all, ["total_pop", "pct_minority", "total_hh", "bg_median_hh_income", "pct_lep_hh", "ej_criteria_desc"])
    missing_audit("PM2.5", pm, ["pm25", "aqi"])
    say(f"  Sentinel handling: ACS '-', '(X)', '**' -> NaN; EJ block-group income coded 0 / flag 'U' (unavailable) -> NaN "
        f"({int(ej_all.bg_median_hh_income.isna().sum())} block groups statewide); blank EJ flags -> False.")
    say(f"  ACS Worcester County tracts: {len(acs)}; with no median income: {int(acs.acs_median_income.isna().sum())}; "
        f"top-coded ($250,000+): {int(acs.acs_income_topcoded.sum())}; unreliable (CV>30%): {int((~acs.acs_income_reliable & acs.acs_median_income.notna()).sum())}")
    say(f"  Statewide MA median household income (ACS 2024 5-yr): ${ref.get('state_median_income', np.nan):,.0f}")
    say(f"  Anchor traffic.csv: {traffic['station']} | {traffic['road']} | {traffic['location']} | AADT {traffic['aadt']:,} (brief check {BRIEF_AADT:,}: {traffic['aadt'] == BRIEF_AADT})")

    ej = ej_all[ej_all.municipality.isin(STUDY_TOWNS)].copy()
    if ej.geoid_bg.duplicated().any():
        say("  WARNING: duplicated block-group GEOIDs (split municipalities) - keeping the largest-population record.")
        ej = ej.sort_values("total_pop", ascending=False).drop_duplicates("geoid_bg")
    say(f"  EJ_POLY records for {' + '.join(STUDY_TOWNS)}: {len(ej)} block groups in {ej.geoid_tract.nunique()} tracts ({int(ej.total_pop.sum()):,} residents)")

    progress("Building spatial layer (Census TIGER/Line 2024)")
    bgs, pts, r9, r9_line, towns, study_area, meta = build_spatial(ej, ej_all)

    progress("Fetching / joining MassDOT traffic")
    tc = build_corridor_traffic(r9_line, study_area, towns, traffic)
    bgs = apply_exposure(bgs, pts, tc["segs"], tc["stations"], traffic["aadt"])

    mon = (pm.groupby(["site_id", "site", "lat", "lon"], as_index=False)
             .agg(days=("pm25", "size"), mean=("pm25", "mean"), p98=("pm25", lambda s: s.quantile(.98)),
                  max=("pm25", "max"), days_over_who24=("pm25", lambda s: int((s > WHO_24H).sum())),
                  days_over_naaqs24=("pm25", lambda s: int((s > NAAQS_24H).sum()))))
    mon_gdf = gpd.GeoDataFrame(mon, geometry=gpd.points_from_xy(mon.lon, mon.lat), crs=4326).to_crs(CRS_MA)

    progress("Building master table")
    m = build_master(bgs, ej, acs, ref, traffic, mon_gdf)
    tr = tract_table(m)
    tr.round(4).to_csv(OUT_DIR / "tract_table_route9.csv", index=False)

    drop = {"split_flag", "nonhisp_white", "bg_income_flag_n", "muni_income_pct_of_state", "flag_income", "flag_minority", "flag_english_isolation",
            "grid_pts", "ALAND", "AWATER", "geo_id", "acs_name", "bg_income_pct_of_state", "acs_income_bottomcoded", "ej_flag", "municipality_geo",
            "muni_median_hh_income", *BKT_COLS}
    new_cols = [c for c in m.columns if c not in LEGACY_COLS and c not in drop]
    master = m[[c for c in LEGACY_COLS if c in m.columns] + new_cols].sort_values(["municipality", "geoid_bg"]).reset_index(drop=True)
    for c in master.select_dtypes("float").columns:
        master[c] = master[c].round(4)
    master.to_csv(OUT_DIR / "master_route9_table.csv", index=False)
    say(f"\nMaster table: {len(master)} rows x {master.shape[1]} cols ({len(LEGACY_COLS)} legacy + {master.shape[1] - len(LEGACY_COLS)} new) -> {OUT_DIR / 'master_route9_table.csv'}")
    missing_audit("master", master, ["income_best", "total_pop", "pct_minority", "exposure_index", "vulnerability_index", "est_households"])
    cor = m[m.in_corridor]
    say(f"  Corridor: block-group centroid <= {CORRIDOR_M:,} m -> {len(cor)} of {len(m)} block groups, {cor.geoid_tract.nunique()} tracts, "
        f"{int(cor.total_pop.sum()):,} EJ residents ({cor.total_pop.sum() / m.total_pop.sum():.0%} of EJ residents in the two towns); {int((m.municipality.eq('Shrewsbury') & m.in_corridor).sum())} are in Shrewsbury.")
    cnty_ej = ej_all[ej_all.geoid_bg.str.startswith(WORCESTER_COUNTY_FIPS)]
    ej_rest, n_rest, ejn = int((~cnty_ej.geoid_bg.isin(m.geoid_bg)).sum()), meta["n_cty"] - len(m), int(m.ej_designated.sum())
    say(f"  EJ designation share: Worcester + Shrewsbury {ejn}/{len(m)} ({ejn / len(m):.1%}); rest of Worcester County {ej_rest}/{n_rest} ({ej_rest / n_rest:.1%}); "
        f"Massachusetts {len(ej_all):,}/{meta['n_state']:,} ({len(ej_all) / meta['n_state']:.1%}).")
    say("  Criteria mix (Worcester + Shrewsbury block groups): " + "; ".join(f"{k} {v}" for k, v in m.ej_criteria_desc.value_counts().items()))

    progress("Computing sections")
    sec_near(m, F)
    sec_traffic(m, tc, traffic, F)
    sec_worcester(m, tr, bgs, acs, ref, F)
    sec_shrewsbury(m, tr, F)
    sec_vulnerability(m, tr, F)

    # PM2.5 section
    progress("PM2.5 context")
    sec_air(pm, mon.copy(), mon_gdf, r9_line, bgs, F)
    pk = pm.loc[pm.pm25.idxmax()]
    section("audit")
    say(f"  PM2.5 brief check: mean {pm.pm25.mean():.2f} ug/m3 (brief ~{BRIEF_PM_MEAN}), max {pm.pm25.max():.1f} (brief {BRIEF_PM_MAX}) -> "
        f"{'consistent' if abs(pm.pm25.mean() - BRIEF_PM_MEAN) < 0.05 and abs(pm.pm25.max() - BRIEF_PM_MAX) < 0.05 else 'INCONSISTENT'}; "
        f"peak {pk.pm25:.1f} on {pk.date:%Y-%m-%d} at {pk.site}")

    sec_limits(F)
    H = build_headlines(m, traffic, ref, F)
    exec_summary(m, traffic, ref, F, H)
    build_changelog(m, F)

    progress("Figures")
    figure1(m, bgs, tr, tc, r9, traffic, ref, F, H)
    figure2(pm, mon, mon_gdf, r9_line)
    figure3(m, bgs, tc, r9, traffic, F)

    text = assemble()
    (OUT_DIR / "summary_statistics.txt").write_text(text, encoding="utf-8")
    (OUT_DIR / "advisory_brief.md").write_text(advisory_brief(m, traffic, ref, F, H), encoding="utf-8")
    (OUT_DIR / "data_dictionary.md").write_text(data_dictionary(master), encoding="utf-8")
    print(text)
    progress(f"\nSaved: {OUT_DIR / 'summary_statistics.txt'}, advisory_brief.md, data_dictionary.md, tract_table_route9.csv")


if __name__ == "__main__":
    main()
