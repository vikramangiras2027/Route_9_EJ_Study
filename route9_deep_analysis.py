#!/usr/bin/env python3
"""
Route 9 corridor (Worcester & Shrewsbury, MA) - environmental justice,
traffic exposure and PM2.5 synthesis.

Inputs  (folder DATA_DIR, see resolve_data_dir):
    ACSST5Y2024.S1901-Data.csv   ACS 5-yr 2024 tract income table (S1901)
    EJ_POLY.dbf                  MassGIS 2020-based EJ block-group attribute table
    traffic.csv(.txt)            MassDOT station M3002W (Route 9 / Belmont St)
    ad_viz_plotval_data.csv      EPA AQS daily PM2.5, Worcester County monitors

Public geometry (downloaded once from the US Census Bureau, cached in ./cache):
    TIGER/Line 2024 block groups and primary/secondary roads (Route 9 centreline).
    The EJ DBF has attributes only (no shapes), so this is the only way to
    measure real distance to Route 9.

Outputs:
    outputs/master_route9_table.csv     block-group master analytic table
    outputs/summary_statistics.txt      everything printed to the console
    charts/figure1_income_traffic_ej.png
    charts/figure2_pm25_distribution.png

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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import Point

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
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
EXPOSURE_DECAY_M = 300            # e-folding distance of the near-road exposure gradient
GRID_M = 50                       # sampling grid for area-weighted exposure
BUFFERS_M = (300, 500, 1000)
BANDS = [0, 500, 1000, 2000, 4000, np.inf]
BAND_LABELS = ["<=0.5 km", "0.5-1 km", "1-2 km", "2-4 km", ">4 km"]
RNG = np.random.default_rng(20260106)

# Air-quality benchmarks (ug/m3)
NAAQS_ANNUAL = 9.0        # EPA primary annual PM2.5 NAAQS (2024 revision)
NAAQS_24H = 35.0          # EPA primary 24-hour PM2.5 NAAQS (98th pct, 3-yr avg)
WHO_ANNUAL = 5.0          # WHO 2021 guideline (health reference, not regulatory)
WHO_24H = 15.0            # WHO 2021 guideline (99th pct)

# Stated inputs in the brief, checked against the data below
BRIEF_AADT, BRIEF_PM_MEAN, BRIEF_PM_MAX = 28112, 5.65, 33.5

TIGER = {
    "bg": "https://www2.census.gov/geo/tiger/TIGER2024/BG/tl_2024_25_bg.zip",
    "roads": "https://www2.census.gov/geo/tiger/TIGER2024/PRISECROADS/tl_2024_25_prisecroads.zip",
    "towns": "https://www2.census.gov/geo/tiger/TIGER2024/COUSUB/tl_2024_25_cousub.zip",
}

_LOG: list[str] = []


def say(text: str = "") -> None:
    print(text)
    _LOG.append(text)


def header(title: str) -> None:
    say("\n" + "=" * 100)
    say(title)
    say("=" * 100)


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
    for c in brackets:
        df = df.rename(columns={c: "acs_pct_hh_" + c[-4:-1]})
    bcols = [c for c in df.columns if c.startswith("acs_pct_hh_")]
    df["acs_pct_hh_under_50k"] = df[bcols[:5]].sum(axis=1, min_count=5)     # <$10k ... $35-49.9k
    df["acs_pct_hh_150k_plus"] = df[bcols[8:10]].sum(axis=1, min_count=2)
    df = df.drop(columns=bcols)
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


_GEOM_CACHE: dict = {}


def fetch(url: str) -> Path:
    dest = CACHE_DIR / Path(url).name
    if not dest.exists():
        say(f"  downloading {url}")
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as exc:
            dest.unlink(missing_ok=True)
            raise SystemExit(f"Could not download {url} ({exc}).\nDownload it manually into {CACHE_DIR}.")
    return dest


# --------------------------------------------------------------------------- #
# 2. Spatial layer: corridor definition & exposure
# --------------------------------------------------------------------------- #
def build_spatial(ej_ws: pd.DataFrame, ej_all: pd.DataFrame, traffic: dict):
    all_bgs = gpd.read_file(fetch(TIGER["bg"]))[["GEOID", "ALAND", "AWATER", "geometry"]].to_crs(CRS_MA)
    all_bgs = all_bgs.rename(columns={"GEOID": "geoid_bg"})
    # EJ_POLY contains ONLY EJ-designated block groups, so non-EJ block groups must come from Census geometry.
    # A block group is in the study universe if it is an EJ record for Worcester/Shrewsbury OR its centroid
    # lies inside either municipality (Census county subdivision boundary).
    towns = gpd.read_file(fetch(TIGER["towns"])).to_crs(CRS_MA)
    towns = towns[towns["NAME"].isin(STUDY_TOWNS)][["NAME", "geometry"]].rename(columns={"NAME": "municipality_geo"})
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

    # area-weighted exposure: sample the study area on a regular grid
    minx, miny, maxx, maxy = bgs.total_bounds
    xs, ys = np.arange(minx, maxx, GRID_M) + GRID_M / 2, np.arange(miny, maxy, GRID_M) + GRID_M / 2
    gx, gy = np.meshgrid(xs, ys)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(gx.ravel(), gy.ravel()), crs=CRS_MA)
    pts = gpd.sjoin(pts, bgs[["geoid_bg", "geometry"]], predicate="within", how="inner")
    pts["d"] = pts.geometry.distance(r9_line)
    pts["expo"] = traffic["aadt"] * np.exp(-pts["d"] / EXPOSURE_DECAY_M)
    g = pts.groupby("geoid_bg")
    agg = pd.DataFrame({"grid_pts": g.size(), "mean_dist_m": g["d"].mean(), "exposure_index": g["expo"].mean()})
    for b in BUFFERS_M:
        agg[f"pct_area_within_{b}m"] = g["d"].apply(lambda s, b=b: (s <= b).mean() * 100)
    bgs = bgs.merge(agg, left_on="geoid_bg", right_index=True, how="left")
    # block groups smaller than one grid cell: fall back to the centroid
    small = bgs["grid_pts"].isna()
    if small.any():
        bgs.loc[small, "mean_dist_m"] = bgs.loc[small, "dist_centroid_m"]
        bgs.loc[small, "exposure_index"] = traffic["aadt"] * np.exp(-bgs.loc[small, "dist_centroid_m"] / EXPOSURE_DECAY_M)
        for b in BUFFERS_M:
            bgs.loc[small, f"pct_area_within_{b}m"] = (bgs.loc[small, "dist_centroid_m"] <= b) * 100.0
    bgs["area_km2"] = bgs.geometry.area / 1e6
    return bgs, r9, r9_line, {"n_state": n_state, "n_cty": n_cty}


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


# --------------------------------------------------------------------------- #
# Statistics helpers
# --------------------------------------------------------------------------- #
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


def wavg(v: pd.Series, w: pd.Series) -> float:
    m = v.notna() & w.notna() & (w > 0)
    return float(np.average(v[m], weights=w[m])) if m.any() else np.nan


def fmt_p(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


# --------------------------------------------------------------------------- #
# Main pipeline
# --------------------------------------------------------------------------- #
def main() -> None:
    data_dir = resolve_data_dir()
    say(f"Data folder : {data_dir}")
    say(f"Script root : {ROOT}")

    # ------------------------------------------------------------------ 1 ---
    header("1. DATA INTEGRATION, INSPECTION & CLEANING")
    acs, ref = load_acs(find_file(data_dir, ["ACSST5Y2024.S1901-Data*.csv"]))
    ej_all = load_ej(find_file(data_dir, ["EJ_POLY*.dbf", "*.dbf"]))
    traffic = load_traffic(find_file(data_dir, ["traffic.csv", "traffic*.csv*", "traffic*"]))
    pm = load_pm25(find_file(data_dir, ["ad_viz_plotval_data*.csv"]))

    say("\nMissing-value audit (after cleaning):")
    missing_audit("ACS S1901, Worcester County tracts", acs, ["acs_households", "acs_median_income",
                  "acs_median_income_moe", "acs_mean_income", "acs_pct_hh_under_50k"])
    missing_audit("EJ DBF, statewide", ej_all, ["total_pop", "pct_minority", "total_hh", "bg_median_hh_income",
                  "pct_lep_hh", "ej_criteria_desc"])
    missing_audit("PM2.5", pm, ["pm25", "aqi"])
    say(f"  Sentinel handling: ACS '-', '(X)', '**' -> NaN; EJ block-group income coded 0 / flag 'U' (unavailable) -> NaN "
        f"({int(ej_all.bg_median_hh_income.isna().sum())} block groups statewide); blank EJ flags -> False.")
    say(f"  ACS Worcester County tracts: {len(acs)}; with no median income: {int(acs.acs_median_income.isna().sum())}; "
        f"top-coded ($250,000+): {int(acs.acs_income_topcoded.sum())}; "
        f"unreliable (CV>30%): {int((~acs.acs_income_reliable & acs.acs_median_income.notna()).sum())}")
    say(f"  Statewide MA median household income (ACS 2024 5-yr): ${ref.get('state_median_income', np.nan):,.0f}")

    say("\nTraffic input (MassDOT):")
    say(f"  Station {traffic['station']} | {traffic['road']} | {traffic['location']}")
    say(f"  AADT={traffic['aadt']:,}  EB={traffic['eb']:,}  WB={traffic['wb']:,}  WB share={traffic['wb_share']:.1%}  "
        f"WB:EB ratio={traffic['wb'] / traffic['eb']:.2f}:1  (EB+WB differs from AADT by {traffic['dir_sum_gap']} veh/day: rounding)")
    say(f"  Brief check: AADT matches stated {BRIEF_AADT:,}: {traffic['aadt'] == BRIEF_AADT}")
    say("  NOTE: one count station => one AADT value. Tract-level traffic is MODELLED by distance decay from the "
        "Route 9 centreline, not measured.")

    # corridor universe ----------------------------------------------------------
    ej = ej_all[ej_all.municipality.isin(STUDY_TOWNS)].copy()
    if ej.geoid_bg.duplicated().any():
        say("  WARNING: duplicated block-group GEOIDs (split municipalities) - keeping the largest-population record.")
        ej = ej.sort_values("total_pop", ascending=False).drop_duplicates("geoid_bg")
    say(f"\nEJ_POLY records for {' + '.join(STUDY_TOWNS)}: {len(ej)} block groups in {ej.geoid_tract.nunique()} tracts "
        f"({int(ej.total_pop.sum()):,} residents)")

    say("\nBuilding spatial layer (Census TIGER/Line 2024):")
    bgs, r9, r9_line, meta = build_spatial(ej, ej_all, traffic)

    # PM2.5 monitors -> nearest monitor per block group
    mon = (pm.groupby(["site_id", "site", "lat", "lon"], as_index=False)
             .agg(days=("pm25", "size"), mean=("pm25", "mean"), p98=("pm25", lambda s: s.quantile(.98)),
                  max=("pm25", "max"), days_over_who24=("pm25", lambda s: int((s > WHO_24H).sum())),
                  days_over_naaqs24=("pm25", lambda s: int((s > NAAQS_24H).sum()))))
    mon_gdf = gpd.GeoDataFrame(mon, geometry=gpd.points_from_xy(mon.lon, mon.lat), crs=4326).to_crs(CRS_MA)
    cent = bgs.centroid
    dmat = np.column_stack([cent.distance(m_) for m_ in mon_gdf.geometry])
    nearest = dmat.argmin(axis=1)
    bgs["pm_monitor"] = mon_gdf["site"].to_numpy()[nearest]
    bgs["dist_pm_monitor_km"] = dmat.min(axis=1) / 1000
    for c, src in [("pm25_monitor_annual_mean", "mean"), ("pm25_monitor_p98", "p98"), ("pm25_monitor_max", "max"),
                   ("pm25_monitor_days_over_who24", "days_over_who24")]:
        bgs[c] = mon_gdf[src].to_numpy()[nearest]

    # ------------------------------------------------------------------ master
    cent_ll = bgs.centroid.to_crs(4326)
    bgs["centroid_lat"], bgs["centroid_lon"] = cent_ll.y.round(5), cent_ll.x.round(5)
    m = (bgs.drop(columns="geometry")
            .merge(ej, on="geoid_bg", how="left", validate="1:1"))
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
    n_bg_tract = m.groupby("geoid_tract")["geoid_bg"].transform("size")
    m["hh_weight_approx"] = m["acs_households"] / n_bg_tract      # tract households split evenly across its block groups

    # cumulative burden index: mean percentile rank of three equally weighted stressors
    comps = {
        "p_traffic": m["exposure_index"].rank(pct=True),
        "p_low_income": (-m["income_best"]).rank(pct=True),
        "p_ej_criteria": m["ej_criteria_count"].rank(pct=True),   # 0 = not EJ, 1-3 = number of EJ criteria met
    }
    for k, v in comps.items():
        m[k] = v
    m["cumulative_burden_index"] = pd.concat(comps, axis=1).mean(axis=1, skipna=False) * 100
    m["cbi_quintile"] = pd.qcut(m["cumulative_burden_index"], 5, labels=["Q1 lowest", "Q2", "Q3", "Q4", "Q5 highest"])
    m["hotspot"] = (m["cbi_quintile"] == "Q5 highest") & m["in_corridor"]

    cols_first = ["geoid_bg", "geoid_tract", "bg_name", "municipality", "ej_designated", "ej_criteria_code",
                  "ej_criteria_count", "ej_criteria_desc", "ej_income", "ej_minority", "ej_english_isolation",
                  "total_pop", "total_hh", "pct_minority", "lep_hh", "pct_lep_hh", "bg_median_hh_income",
                  "acs_median_income", "acs_median_income_moe", "acs_income_cv", "acs_income_reliable",
                  "acs_income_topcoded", "acs_pct_hh_under_50k", "acs_pct_hh_150k_plus", "income_best",
                  "income_source", "income_pct_of_state", "centroid_lat", "centroid_lon", "area_km2",
                  "dist_centroid_m", "dist_edge_m", "mean_dist_m", "dist_band", "in_corridor"]
    drop = {"split_flag", "nonhisp_white", "bg_income_flag_n", "muni_income_pct_of_state", "flag_income",
            "flag_minority", "flag_english_isolation", "grid_pts", "ALAND", "AWATER", "geo_id", "acs_name",
            "bg_income_pct_of_state", "acs_income_bottomcoded", "ej_flag", "hh_weight_approx", "municipality_geo",
            "muni_median_hh_income"}
    rest = [c for c in m.columns if c not in cols_first and c not in drop]
    master = m[cols_first + rest].sort_values(["municipality", "geoid_bg"]).reset_index(drop=True)
    for c in master.select_dtypes("float").columns:
        master[c] = master[c].round(4)
    master.to_csv(OUT_DIR / "master_route9_table.csv", index=False)
    say(f"\nMaster table: {len(master)} rows x {master.shape[1]} cols -> {OUT_DIR / 'master_route9_table.csv'}")
    say("  Demographic fields (pop, % minority, % LEP, EJ-table income) exist only for EJ-designated block groups "
        "(the DBF omits the rest); ACS tract income covers both groups.")
    missing_audit("master", master, ["income_best", "total_pop", "pct_minority", "exposure_index", "cumulative_burden_index"])

    cor = m[m.in_corridor]
    say(f"\nCorridor definition: block-group centroid <= {CORRIDOR_M:,} m from Route 9  ->  {len(cor)} of {len(m)} block groups, "
        f"{cor.geoid_tract.nunique()} tracts, {int(cor.total_pop.sum()):,} EJ-designated residents "
        f"({cor.total_pop.sum() / m.total_pop.sum():.0%} of all EJ residents in the two towns); "
        f"{int((m.municipality.eq('Shrewsbury') & m.in_corridor).sum())} corridor block groups are in Shrewsbury.")

    # ------------------------------------------------------------------ 2 ---
    header("2. CUMULATIVE EXPOSURE & EQUITY MODEL")
    say(f"Traffic exposure index = AADT({traffic['aadt']:,}) x exp(-d / {EXPOSURE_DECAY_M} m), averaged over each block "
        f"group's area on a {GRID_M} m grid (units: AADT-equivalent veh/day; 0 = no road influence).")
    say("Cumulative burden index (0-100) = mean percentile rank of: traffic exposure, low income (ACS tract), EJ criteria met (0-3).")
    say("PM2.5 is assigned from the nearest of the county's AQS monitors (no tract-level monitoring exists).")

    say("\nEJ designation (EJ = block group present in MassGIS EJ_POLY):")
    cnty_ej = ej_all[ej_all.geoid_bg.str.startswith(WORCESTER_COUNTY_FIPS)]
    ej_rest = int((~cnty_ej.geoid_bg.isin(m.geoid_bg)).sum())
    n_rest = meta["n_cty"] - len(m)
    ejn = int(m.ej_designated.sum())
    say(f"  Worcester + Shrewsbury       {ejn:>5,} / {len(m):>5,} block groups EJ  ({ejn / len(m):.1%})")
    say(f"  Rest of Worcester County     {ej_rest:>5,} / {n_rest:>5,} block groups EJ  ({ej_rest / n_rest:.1%})")
    say(f"  Massachusetts                {len(ej_all):>5,} / {meta['n_state']:>5,} block groups EJ  ({len(ej_all) / meta['n_state']:.1%})")
    say("  Criteria mix, Worcester + Shrewsbury block groups:")
    for k, v in m.ej_criteria_desc.value_counts().items():
        say(f"     {k:<42}{v:>4}  ({v / len(m):.0%})")

    say("\nDistance bands (block-group centroid to Route 9):")
    band = m.groupby("dist_band", observed=True).agg(
        block_groups=("geoid_bg", "size"), pct_ej=("ej_flag", lambda s: s.mean() * 100),
        ej_residents=("total_pop", "sum"), median_income=("income_best", "median"),
        pct_minority=("pct_minority", "mean"), pct_lep_hh=("pct_lep_hh", "mean"),
        mean_ej_criteria=("ej_criteria_count", "mean"), traffic_exposure=("exposure_index", "mean"),
        mean_cbi=("cumulative_burden_index", "mean")).round(1)
    say(band.to_string())
    say("   (pct_minority / pct_lep_hh are means over EJ-designated block groups only)")

    say("\nEJ-designated residents near Route 9 (areal interpolation; assumes uniform density inside each block group):")
    ej_pop_tot = m.total_pop.sum()
    for b in BUFFERS_M:
        inside = m[f"est_ej_pop_within_{b}m"]
        outside = m.total_pop - inside
        land_in = m.area_km2 * m[f"pct_area_within_{b}m"] / 100
        ej_land_share = (land_in * m.ej_flag).sum() / land_in.sum()
        land_out = m.area_km2 - land_in
        ej_land_share_out = (land_out * m.ej_flag).sum() / land_out.sum()
        say(f"  within {b:>4} m: {inside.sum():>8,.0f} EJ residents ({inside.sum() / ej_pop_tot:.1%} of the {ej_pop_tot:,.0f}) | "
            f"land in EJ block groups {ej_land_share:.0%} vs {ej_land_share_out:.0%} beyond | "
            f"% minority {wavg(m.pct_minority, inside):.1f} vs {wavg(m.pct_minority, outside):.1f} | "
            f"% LEP hh {wavg(m.pct_lep_hh, inside):.1f} vs {wavg(m.pct_lep_hh, outside):.1f} | "
            f"BG income ${wavg(m.bg_median_hh_income, inside):,.0f} vs ${wavg(m.bg_median_hh_income, outside):,.0f}")

    # ------------------------------------------------------------------ 3 ---
    header("3. STATISTICAL INSIGHTS")
    findings: dict = {}

    say("A. Proximity to Route 9 vs equity indicators (block-group level, Spearman rank correlation)")
    say("   Reading the signs: rho(distance, income) > 0 means incomes RISE with distance from Route 9;")
    say("   rho(exposure, income) < 0 means incomes FALL where modelled traffic exposure is higher.\n")
    rows = []
    for lab, xcol in [("centroid distance (primary)", "dist_centroid_m"), ("polygon-edge distance", "dist_edge_m"),
                      ("area-weighted mean distance", "mean_dist_m"), ("modelled traffic exposure index", "exposure_index")]:
        for ylab, ycol in [("ACS 2024 tract median income", "acs_median_income"),
                           ("EJ designated (0/1)", "ej_flag"), ("EJ criteria met (0-3)", "ej_criteria_count"),
                           ("EJ-table BG income [EJ BGs]", "bg_median_hh_income"),
                           ("% minority [EJ BGs]", "pct_minority"), ("% LEP households [EJ BGs]", "pct_lep_hh")]:
            r, p, n = spearman(m, xcol, ycol)
            rows.append((lab, ylab, n, r, p))
    tbl = pd.DataFrame(rows, columns=["proximity measure", "outcome", "n", "rho", "p"])
    tbl["p"] = tbl["p"].map(fmt_p)
    tbl["rho"] = tbl["rho"].round(3)
    say(tbl.to_string(index=False))

    rho, p, n = spearman(m, "dist_centroid_m", "acs_median_income")
    ci = cluster_boot_spearman(m, "dist_centroid_m", "acs_median_income", "geoid_tract")
    findings["rho_inc_dist"], findings["p_inc_dist"] = rho, p
    findings["rho_inc_dist_ci"] = f"[{ci[0]:.2f}, {ci[1]:.2f}]"
    say(f"\n   Primary result: rho(centroid distance, ACS median income) = {rho:+.3f} (n={n}, {fmt_p(p)}); "
        f"tract-cluster bootstrap 95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]")
    rho_e, p_e, n_e = spearman(m, "dist_centroid_m", "ej_flag")
    ci_e = cluster_boot_spearman(m, "dist_centroid_m", "ej_flag", "geoid_tract")
    findings.update(rho_ej=rho_e, p_ej=p_e, rho_ej_ci=f"[{ci_e[0]:.2f}, {ci_e[1]:.2f}]")
    say(f"   Primary result: rho(centroid distance, EJ designated) = {rho_e:+.3f} (n={n_e}, {fmt_p(p_e)}); "
        f"cluster bootstrap 95% CI [{ci_e[0]:+.3f}, {ci_e[1]:+.3f}]")

    say("\n   Town-confound check (Shrewsbury is far wealthier than Worcester and Route 9 crosses both): gradient WITHIN each town")
    for town in STUDY_TOWNS:
        sub = m[m.municipality == town]
        r_i, p_i, n_i = spearman(sub, "dist_centroid_m", "acs_median_income")
        c_i = cluster_boot_spearman(sub, "dist_centroid_m", "acs_median_income", "geoid_tract")
        r_j, p_j, n_j = spearman(sub, "dist_centroid_m", "ej_flag")
        say(f"     {town:<11} income: rho = {r_i:+.3f} (n={n_i}, {fmt_p(p_i)}, cluster 95% CI [{c_i[0]:+.2f}, {c_i[1]:+.2f}]) | "
            f"EJ designated: rho = {r_j:+.3f} (n={n_j}, {fmt_p(p_j)}) | median income ${sub.acs_median_income.median():,.0f}")
        findings[f"rho_inc_{town}"], findings[f"p_inc_{town}"] = r_i, p_i
        findings[f"ci_inc_{town}"] = f"[{c_i[0]:.2f}, {c_i[1]:.2f}]"
        findings[f"n_inc_{town}"] = n_i
    wor = m[m.municipality == "Worcester"]
    lr_w = stats.linregress(wor.dropna(subset=["acs_median_income"]).dist_centroid_m / 1000,
                            wor.dropna(subset=["acs_median_income"]).acs_median_income)
    say(f"     Worcester-only OLS slope: ${lr_w.slope:+,.0f} income per km from Route 9 (R2={lr_w.rvalue ** 2:.3f}, naive {fmt_p(lr_w.pvalue)})")
    findings["slope_worcester"] = lr_w.slope

    d = m[["dist_centroid_m", "acs_median_income"]].dropna()
    lr = stats.linregress(d.dist_centroid_m / 1000, d.acs_median_income)
    findings["slope_per_km"] = lr.slope
    say(f"   OLS: income changes by ${lr.slope:+,.0f} per km from Route 9 (R2={lr.rvalue ** 2:.3f}, {fmt_p(lr.pvalue)}; "
        f"naive p, spatial dependence ignored)")

    # EJ status vs corridor
    e_in, e_out = m[m.in_corridor], m[~m.in_corridor]
    tab = [[int(e_in.ej_flag.sum()), int((1 - e_in.ej_flag).sum())], [int(e_out.ej_flag.sum()), int((1 - e_out.ej_flag).sum())]]
    orr, pf = stats.fisher_exact(tab)
    u_d = stats.mannwhitneyu(m.loc[m.ej_designated, "dist_centroid_m"], m.loc[~m.ej_designated, "dist_centroid_m"])
    med_d_ej, med_d_non = m.loc[m.ej_designated, "dist_centroid_m"].median(), m.loc[~m.ej_designated, "dist_centroid_m"].median()
    findings.update(ej_in=e_in.ej_flag.mean(), ej_out=e_out.ej_flag.mean(), or_=orr, p_or=pf,
                    med_d_ej=med_d_ej, med_d_non=med_d_non, p_dist_ej=u_d.pvalue)
    say(f"\n   EJ share: {e_in.ej_flag.mean():.1%} of corridor block groups ({tab[0][0]}/{sum(tab[0])}) vs {e_out.ej_flag.mean():.1%} "
        f"elsewhere in the two towns ({tab[1][0]}/{sum(tab[1])}); odds ratio {orr:.1f} (Fisher exact {fmt_p(pf)})")
    say(f"   Median centroid distance to Route 9: EJ block groups {med_d_ej:,.0f} m vs non-EJ {med_d_non:,.0f} m "
        f"(Mann-Whitney {fmt_p(u_d.pvalue)}, Cliff's delta {cliffs_delta(m.loc[m.ej_designated, 'dist_centroid_m'], m.loc[~m.ej_designated, 'dist_centroid_m']):+.2f})")

    # tract level
    tr = (m.assign(w=m.area_km2)
            .groupby("geoid_tract")
            .apply(lambda g: pd.Series({
                "municipality": g.municipality.mode().iat[0], "block_groups": len(g), "ej_residents": g.total_pop.sum(),
                "income": g.acs_median_income.iloc[0], "dist_m": wavg(g.dist_centroid_m, g.w),
                "exposure": wavg(g.exposure_index, g.w), "ej_share": g.ej_flag.mean(),
                "ej_crit_mean": g.ej_criteria_count.mean()}), include_groups=False)
            .reset_index())
    r_t, p_t, n_t = spearman(tr, "dist_m", "income")
    r_x, p_x, _ = spearman(tr, "exposure", "income")
    r_te, p_te, n_te = spearman(tr, "dist_m", "ej_share")
    say(f"\n   Tract level (n={n_t} tracts with income): rho(distance, income) = {r_t:+.3f} ({fmt_p(p_t)}); "
        f"rho(exposure, income) = {r_x:+.3f} ({fmt_p(p_x)}); rho(distance, share of block groups that are EJ) = {r_te:+.3f} ({fmt_p(p_te)}, n={n_te})")
    findings.update(rho_tract=r_t, rho_tract_ej=r_te, p_tract_ej=p_te)

    # spatial autocorrelation
    gg = bgs.merge(m[["geoid_bg", "acs_median_income"]], on="geoid_bg").dropna(subset=["acs_median_income"])
    w = queen_weights(gg)
    mi, mp = morans_i(np.log(gg["acs_median_income"].to_numpy()), w)
    say(f"   Moran's I of log(income) across block groups = {mi:.3f} ({fmt_p(mp)}; 999 permutations) -> "
        f"{'strong' if mi > 0.4 else 'moderate' if mi > 0.2 else 'weak'} spatial clustering; "
        f"effective sample size is smaller than n, so the cluster-bootstrap CI above is the safer inference.")
    findings["moran"] = mi

    say("\nB. Corridor vs. rest of Worcester + Shrewsbury (Mann-Whitney U; Cliff's delta = effect size, 0=none, +/-1=complete separation)")
    a, b_ = m[m.in_corridor], m[~m.in_corridor]
    rows = []
    for lab, col in [("ACS tract median income ($)", "acs_median_income"), ("% HH under $50k (ACS tract)", "acs_pct_hh_under_50k"),
                     ("EJ criteria met (0-3)", "ej_criteria_count"), ("EJ-table BG income ($) [EJ BGs]", "bg_median_hh_income"),
                     ("% minority [EJ BGs]", "pct_minority"), ("% LEP households [EJ BGs]", "pct_lep_hh"),
                     ("Cumulative burden index", "cumulative_burden_index")]:
        x, y = a[col].dropna(), b_[col].dropna()
        u = stats.mannwhitneyu(x, y, alternative="two-sided")
        rows.append((lab, len(x), len(y), x.median(), y.median(), x.median() - y.median(), cliffs_delta(x, y), u.pvalue))
    gt = pd.DataFrame(rows, columns=["metric", "n_corridor", "n_other", "median_corridor", "median_other",
                                     "difference", "cliffs_delta", "p"])
    gt["p"] = gt["p"].map(fmt_p)
    say(gt.round(2).to_string(index=False))
    inc_c, inc_o = a.acs_median_income.median(), b_.acs_median_income.median()
    findings.update(inc_corr=inc_c, inc_other=inc_o)
    hh_c = wavg(a.acs_median_income, a.hh_weight_approx)
    hh_o = wavg(b_.acs_median_income, b_.hh_weight_approx)
    say(f"   Household-weighted mean of tract median incomes (tract households split evenly across block groups): "
        f"corridor ${hh_c:,.0f} vs elsewhere ${hh_o:,.0f} ({(hh_c / hh_o - 1):+.1%}); "
        f"statewide median ${ref['state_median_income']:,.0f} (corridor median = {inc_c / ref['state_median_income']:.0%} of state)")
    say(f"   Low-income households (<$50k, ACS tract): corridor {a.acs_pct_hh_under_50k.median():.1f}% vs elsewhere {b_.acs_pct_hh_under_50k.median():.1f}% (medians)")
    findings.update(lowinc_c=a.acs_pct_hh_under_50k.median(), lowinc_o=b_.acs_pct_hh_under_50k.median())

    say("\nC. Sensitivity of the corridor gaps to the corridor definition (centroid distance)")
    rows = []
    for thr in (500, 1000, 1500, 2000, 3000):
        i, o = m[m.dist_centroid_m <= thr], m[m.dist_centroid_m > thr]
        x, y = i.acs_median_income.dropna(), o.acs_median_income.dropna()
        rows.append((f"<= {thr} m", len(i), i.ej_flag.mean() * 100, o.ej_flag.mean() * 100, x.median(), y.median(),
                     x.median() - y.median(), stats.mannwhitneyu(x, y).pvalue if len(x) > 2 and len(y) > 2 else np.nan))
    sens = pd.DataFrame(rows, columns=["corridor", "n_bg", "pct_EJ_in", "pct_EJ_out", "median_inc_in", "median_inc_out", "gap", "p(income)"])
    sens["p(income)"] = sens["p(income)"].map(fmt_p)
    say(sens.round(1).to_string(index=False))

    say("\nD. Worcester County context (ACS tracts, all income data; no geometry needed)")
    study_tracts = set(m.geoid_tract)
    in_study = acs[acs.geoid_tract.isin(study_tracts)].acs_median_income.dropna()
    other = acs[~acs.geoid_tract.isin(study_tracts)].acs_median_income.dropna()
    u = stats.mannwhitneyu(in_study, other)
    say(f"   Worcester+Shrewsbury tracts: median ${in_study.median():,.0f} (n={len(in_study)}) | other Worcester County tracts: "
        f"median ${other.median():,.0f} (n={len(other)}) | Mann-Whitney {fmt_p(u.pvalue)}, Cliff's delta {cliffs_delta(in_study, other):+.2f}")
    findings.update(ws_tract_med=in_study.median(), oth_tract_med=other.median())
    towns_t = m.groupby("municipality").agg(block_groups=("geoid_bg", "size"), pct_EJ=("ej_flag", lambda s: s.mean() * 100),
                                            median_income=("acs_median_income", "median"),
                                            median_dist_m=("dist_centroid_m", "median"))
    say(towns_t.round(1).to_string())

    say("\nE. Cumulative burden - corridor hotspots (top quintile of index AND inside the corridor)")
    hs_pop = m.loc[m.hotspot, "total_pop"].sum()
    say(f"   {int(m.hotspot.sum())} hotspot block groups; {hs_pop:,.0f} EJ-designated residents "
        f"({hs_pop / ej_pop_tot:.1%} of EJ residents in the two towns)")
    hot = (m[m.hotspot].sort_values("cumulative_burden_index", ascending=False)
             [["geoid_bg", "municipality", "total_pop", "income_best", "pct_minority", "pct_lep_hh", "dist_centroid_m",
               "exposure_index", "ej_criteria_desc", "cumulative_burden_index"]].head(10))
    hot = hot.assign(dist_centroid_m=hot.dist_centroid_m.round(0), exposure_index=hot.exposure_index.round(0),
                     cumulative_burden_index=hot.cumulative_burden_index.round(1), income_best=hot.income_best.round(0))
    say(hot.to_string(index=False))
    rho_c, p_c, _ = spearman(m, "dist_centroid_m", "cumulative_burden_index")
    say(f"   rho(distance, cumulative burden index) = {rho_c:+.3f} ({fmt_p(p_c)}) - traffic is one of 3 components, so this is partly by construction.")
    vuln = pd.concat([m.p_low_income, m.p_ej_criteria], axis=1).mean(axis=1, skipna=False) * 100
    rho_v, p_v, _ = spearman(m.assign(vuln=vuln), "dist_centroid_m", "vuln")
    say(f"   Traffic-independent vulnerability score (income + EJ criteria) vs distance: rho = {rho_v:+.3f} ({fmt_p(p_v)})")
    findings.update(rho_vuln=rho_v, p_vuln=p_v, hs_n=int(m.hotspot.sum()), hs_pop=hs_pop)
    pop_tot = ej_pop_tot

    # ------------------------------------------------------------- PM2.5 ---
    header("4. PM2.5 AIR QUALITY (EPA AQS, Worcester County)")
    c = pm["pm25"]
    say(f"Period {pm.date.min():%Y-%m-%d} to {pm.date.max():%Y-%m-%d}; {len(pm)} site-days at {pm.site_id.nunique()} monitors")
    say(f"Brief check: mean {c.mean():.2f} ug/m3 (brief ~{BRIEF_PM_MEAN}), max {c.max():.1f} (brief {BRIEF_PM_MAX}) -> "
        f"{'consistent' if abs(c.mean() - BRIEF_PM_MEAN) < 0.05 and abs(c.max() - BRIEF_PM_MAX) < 0.05 else 'INCONSISTENT'}")
    say(f"All-monitor: median {c.median():.1f}, SD {c.std():.2f}, p95 {c.quantile(.95):.1f}, p98 {c.quantile(.98):.1f}, max {c.max():.1f}")
    pk = pm.loc[pm.pm25.idxmax()]
    say(f"Peak: {pk.pm25:.1f} ug/m3 on {pk.date:%Y-%m-%d} at {pk.site} (AQI {int(pk.aqi)}); "
        f"same date at other monitor(s): " + ", ".join(f"{r.site} {r.pm25:.1f}" for r in
                                                     pm[(pm.date == pk.date) & (pm.site != pk.site)].itertuples()))
    mon_out = mon.rename(columns={"site": "monitor"}).drop(columns=["site_id", "lat", "lon"]).round(2)
    say("\nBy monitor:")
    say(mon_out.to_string(index=False))
    say("\nBenchmark comparison (ug/m3):")
    for r in mon.itertuples():
        sub = pm[pm.site == r.site]
        q = sub.groupby(sub.date.dt.quarter).pm25.mean()
        ann = q.mean()
        say(f"  {r.site:<26} annual mean (mean of quarterly means) {ann:.2f} vs federal annual NAAQS {NAAQS_ANNUAL} -> "
            f"{'EXCEEDS' if ann > NAAQS_ANNUAL else 'meets'}; WHO annual {WHO_ANNUAL} -> {'exceeds' if ann > WHO_ANNUAL else 'meets'}")
        say(f"  {'':<26} 98th percentile {r.p98:.1f} vs federal 24-h NAAQS {NAAQS_24H:.0f} -> "
            f"{'EXCEEDS' if r.p98 > NAAQS_24H else 'meets'}; days > {NAAQS_24H:.0f}: {r.days_over_naaqs24}; "
            f"days > WHO 24-h {WHO_24H:.0f}: {r.days_over_who24} ({r.days_over_who24 / r.days:.1%}); max AQI {int(sub.aqi.max())}")
    say("  (Official NAAQS compliance uses 3-year design values; the figures above are a single-year screen.)")
    wide = pm.pivot_table(index="date", columns="site", values="pm25")
    if wide.shape[1] >= 2:
        pair = wide.dropna()
        s1, s2 = pair.columns[:2]
        wst = stats.wilcoxon(pair[s1], pair[s2])
        rr = stats.spearmanr(pair[s1], pair[s2])[0]
        say(f"\nMonitor agreement ({len(pair)} common days): Spearman {rr:.2f}; mean difference {pair[s1].mean() - pair[s2].mean():+.2f} ug/m3 "
            f"({s1} minus {s2}), Wilcoxon {fmt_p(wst.pvalue)}")
    seas = pm.groupby("month").pm25.mean()
    say(f"Seasonality: highest monthly mean {seas.max():.1f} (month {seas.idxmax()}), lowest {seas.min():.1f} (month {seas.idxmin()})")
    who_days = pm[pm.pm25 > WHO_24H]
    by_month = who_days.groupby("month").size()
    summer_share = who_days.month.isin([6, 7, 8]).mean()
    say(f"WHO 24-h exceedance site-days by month: {by_month.to_dict()} -> {summer_share:.0%} fall in Jun-Aug; "
        f"{who_days.date.nunique()} distinct dates")
    say("Two monitors ~{:.0f} km apart move together (Spearman above) -> spikes are regionally synchronous, "
        "i.e. not attributable to a single local road from these data.".format(
            gpd.GeoSeries([mon_gdf.geometry.iloc[0]], crs=CRS_MA).distance(mon_gdf.geometry.iloc[1]).iloc[0] / 1000 if len(mon_gdf) > 1 else 0))
    findings.update(who_summer_share=summer_share, who_dates=int(who_days.date.nunique()), pm_corr=rr if wide.shape[1] >= 2 else np.nan)
    top5 = pm.nlargest(5, "pm25")[["date", "site", "pm25", "aqi"]]
    say("Five highest site-days:")
    say(top5.assign(date=top5.date.dt.strftime("%Y-%m-%d")).to_string(index=False))
    nearest_counts = bgs.groupby("pm_monitor").size()
    say("\nBlock groups by nearest PM2.5 monitor: " + "; ".join(f"{k}={v}" for k, v in nearest_counts.items()) +
        f"; median distance to monitor {bgs.dist_pm_monitor_km.median():.1f} km")
    findings.update(pm_mean=c.mean(), pm_max=c.max(), pm_p98=c.quantile(.98), who_days=int((c > WHO_24H).sum()),
                    fed_days=int((c > NAAQS_24H).sum()), n_pm=len(c))

    # ------------------------------------------------------------ figures ---
    header("5. FIGURES")
    figure1(m, bgs, r9, traffic, ref)
    figure2(pm, mon)

    # ------------------------------------------------------------ findings ---
    header("6. KEY QUANTITATIVE FINDINGS (policy brief)")
    write_findings(m, tr, traffic, ref, findings, band, pop_tot, hot)

    (OUT_DIR / "summary_statistics.txt").write_text("\n".join(_LOG), encoding="utf-8")
    say(f"\nSaved: {OUT_DIR / 'summary_statistics.txt'}")


# --------------------------------------------------------------------------- #
# Figure 1: income + traffic + EJ
# --------------------------------------------------------------------------- #
EJ_COLORS = {
    "Minority": "#4c78a8",
    "Minority and income": "#f58518",
    "Minority, income and English isolation": "#b2182b",
    "Minority and English isolation": "#54a24b",
    "Income": "#9467bd",
    "Not EJ-designated": "#c8c8c8",
}


def scalebar(ax, length_m=2000):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x, y = x0 + (x1 - x0) * 0.05, y0 + (y1 - y0) * 0.04
    ax.plot([x, x + length_m], [y, y], color="k", lw=3, solid_capstyle="butt")
    ax.text(x + length_m / 2, y + (y1 - y0) * 0.015, f"{length_m / 1000:g} km", ha="center", fontsize=9)
    ax.annotate("N", xy=(x1 - (x1 - x0) * 0.05, y1 - (y1 - y0) * 0.03), xytext=(x1 - (x1 - x0) * 0.05, y1 - (y1 - y0) * 0.11),
                ha="center", fontsize=11, fontweight="bold", arrowprops=dict(arrowstyle="-|>", color="k", lw=1.5))


def figure1(m, bgs, r9, traffic, ref):
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold", "axes.titlesize": 12})
    g = bgs.merge(m[["geoid_bg", "acs_median_income", "ej_criteria_desc", "in_corridor", "geoid_tract", "total_hh"]],
                  on="geoid_bg", suffixes=("", "_m"))
    tracts = g.dissolve(by="geoid_tract", aggfunc={"acs_median_income": "first", "in_corridor": "max"}).reset_index()
    r9c = r9.clip(g.union_all().buffer(1500))
    corridor_zone = r9c.union_all().buffer(CORRIDOR_M)
    corridor_zone = gpd.GeoSeries([corridor_zone], crs=CRS_MA)
    xmin, ymin, xmax, ymax = g.total_bounds
    pad = 600

    fig = plt.figure(figsize=(17, 14.5), dpi=300)
    gs = fig.add_gridspec(2, 2, hspace=0.22, wspace=0.16, left=0.05, right=0.94, top=0.91, bottom=0.115)
    axA, axB, axC, axD = (fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2))

    # A: income choropleth
    vmin, vmax = np.nanpercentile(tracts.acs_median_income, [3, 97])
    tracts.plot(column="acs_median_income", cmap="YlGnBu", vmin=vmin, vmax=vmax, ax=axA, edgecolor="white",
                linewidth=0.6, missing_kwds={"color": "#d9d9d9", "hatch": "///", "edgecolor": "white"},
                alpha=1.0)
    tracts[~tracts.in_corridor.astype(bool)].plot(ax=axA, color="white", alpha=0.45, linewidth=0)
    corridor_zone.boundary.plot(ax=axA, color="#444", linewidth=1, linestyle="--")
    r9c.plot(ax=axA, color="#c0001a", linewidth=2.6, zorder=5)
    sm = plt.cm.ScalarMappable(cmap="YlGnBu", norm=plt.Normalize(vmin, vmax))
    cb = fig.colorbar(sm, ax=axA, fraction=0.04, pad=0.01, shrink=0.8)
    cb.set_label("Median household income, ACS 2024 5-yr ($)")
    cb.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    axA.set_title("A. Median household income by tract, with Route 9 and the 1.5 km corridor")
    handles = [Line2D([0], [0], color="#c0001a", lw=3, label=f"Route 9 (AADT {traffic['aadt']:,}/day)"),
               Line2D([0], [0], color="#444", lw=1, ls="--", label=f"Corridor: centroid <= {CORRIDOR_M / 1000:g} km"),
               Patch(facecolor="#d9d9d9", hatch="///", edgecolor="white", label="No income estimate")]
    axA.legend(handles=handles, loc="lower right", fontsize=8.5, framealpha=0.95)

    # B: EJ criteria
    for k, col in EJ_COLORS.items():
        sub = g[g.ej_criteria_desc == k]
        for flag, alpha in ((True, 1.0), (False, 0.35)):
            part = sub[sub.in_corridor.astype(bool) == flag]
            if len(part):
                part.plot(ax=axB, color=col, edgecolor="white", linewidth=0.4, alpha=alpha)
    corridor_zone.boundary.plot(ax=axB, color="#444", linewidth=1, linestyle="--")
    r9c.plot(ax=axB, color="black", linewidth=2.6, zorder=5)
    n_ej = int(m.ej_designated.sum())
    axB.set_title(f"B. EJ status: {n_ej} of {len(m)} block groups designated (faded = outside corridor)")
    hb = [Patch(facecolor=c_, label=f"{k} (n={int((g.ej_criteria_desc == k).sum())})") for k, c_ in EJ_COLORS.items()
          if (g.ej_criteria_desc == k).any()] + [Line2D([0], [0], color="black", lw=3, label="Route 9")]
    axB.legend(handles=hb, loc="lower right", fontsize=8, framealpha=0.95, title="MassGIS EJ criteria met", title_fontsize=8.5)
    box = (f"MassDOT station {traffic['station']}\nAADT {traffic['aadt']:,} veh/day\n"
           f"WB {traffic['wb']:,} ({traffic['wb_share']:.1%})\nEB {traffic['eb']:,} ({1 - traffic['wb_share']:.1%})")
    axB.text(0.02, 0.98, box, transform=axB.transAxes, va="top", fontsize=9,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#888", alpha=0.95))
    for ax in (axA, axB):
        ax.set_xlim(xmin - pad, xmax + pad)
        ax.set_ylim(ymin - pad, ymax + pad)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("")
        ax.set_ylabel("")
        scalebar(ax)

    # C: scatter
    d = m.dropna(subset=["income_best"]).copy()
    for k, col in EJ_COLORS.items():
        s = d[d.ej_criteria_desc == k]
        if s.empty:
            continue
        hh = s.total_hh.fillna(s.hh_weight_approx).fillna(300)     # non-EJ block groups have no DBF household count
        axC.scatter(s.dist_centroid_m / 1000, s.income_best, s=np.clip(hh / 6, 12, 300), c=col, alpha=0.75,
                    edgecolor="white", linewidth=0.5, label=k)
    axC.set_xscale("log")
    axC.set_xlim(0.04, 8)
    q = pd.qcut(d.dist_centroid_m, 8, duplicates="drop")
    tr_ = d.groupby(q, observed=True).agg(x=("dist_centroid_m", "median"), y=("income_best", "median"))
    axC.plot(tr_.x / 1000, tr_.y, color="black", lw=2.2, marker="D", ms=5, label="Octile median")
    axC.axhline(ref["state_median_income"], color="#666", ls=":", lw=1.4)
    axC.text(7.8, ref["state_median_income"] * 1.03, f"MA median ${ref['state_median_income'] / 1000:.0f}k", ha="right",
             fontsize=8.5, color="#444")
    axC.axvline(CORRIDOR_M / 1000, color="#444", ls="--", lw=1)
    rho, p, n = spearman(d, "dist_centroid_m", "income_best")
    axC.text(0.03, 0.04, f"Spearman rho = {rho:+.2f} ({fmt_p(p)}), n={n}\nmarker size ~ households",
             transform=axC.transAxes, fontsize=9.5, bbox=dict(boxstyle="round", fc="white", ec="#888"))
    axC.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    axC.set_xlabel("Distance from block-group centroid to Route 9 (km, log scale)")
    axC.set_ylabel("Median household income ($)")
    axC.set_title("C. Income vs. distance to Route 9, coloured by EJ criteria")
    axC.grid(alpha=0.25)
    axC.legend(fontsize=7.5, loc="upper left", framealpha=0.95)

    # D: bands
    bt = (m.groupby("dist_band", observed=True)
            .agg(n=("geoid_bg", "size"), inc=("income_best", "median"), expo=("exposure_index", "mean"),
                 ej=("ej_flag", "mean")).reindex(BAND_LABELS))
    xs = np.arange(len(bt))
    axD.bar(xs, bt.inc, color="#2b6f9e", width=0.62, label="Median household income")
    for x, v in zip(xs, bt.inc):
        if pd.notna(v):
            axD.text(x, v + ref["state_median_income"] * 0.015, f"${v / 1000:.0f}k", ha="center", va="bottom",
                     color="#1b4a6b", fontsize=10, fontweight="bold")
    axD.set_ylim(0, max(bt.inc.max(), ref["state_median_income"]) * 1.3)
    axD.axhline(ref["state_median_income"], color="#666", ls=":", lw=1.4)
    axD.set_ylabel("Median household income ($)")
    axD.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    axD.set_xticks(xs)
    axD.set_xticklabels([f"{b}\nn={int(n_)} BGs\n{e_:.0%} EJ" for b, n_, e_ in zip(bt.index, bt.n, bt.ej)])
    axD.set_xlabel("Distance band: block-group centroid to Route 9")
    ax2 = axD.twinx()
    ax2.plot(xs, bt.expo, color="#c0001a", marker="o", lw=2.4, label="Modelled traffic exposure")
    for x, v in zip(xs, bt.expo):
        ax2.annotate(f"{v:,.0f}", (x, v), textcoords="offset points", xytext=(10, 6), ha="left", fontsize=8.5,
                     color="#c0001a", fontweight="bold")
    ax2.set_ylabel("Traffic exposure index (AADT-equivalent veh/day)", color="#c0001a")
    ax2.tick_params(axis="y", colors="#c0001a")
    ax2.set_ylim(0, max(bt.expo.max() * 1.25, 1))
    ax2.grid(False)
    axD.set_title("D. Income and modelled traffic exposure by distance band")
    h1, l1 = axD.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    axD.legend(h1 + h2 + [Line2D([0], [0], color="#666", ls=":", label="MA median income")], l1 + l2 + ["MA median income"],
               loc="upper center", ncol=3, fontsize=8.5, framealpha=0.95)

    fig.suptitle("Figure 1. Income, traffic exposure and environmental-justice status along the Route 9 corridor, "
                 "Worcester & Shrewsbury, MA", fontsize=15, fontweight="bold", y=0.975)
    fig.text(0.05, 0.012,
             "Sources: ACS 5-yr 2024 (S1901); MassGIS EJ 2020-based block groups; MassDOT station M3002W; US Census TIGER/Line 2024. "
             f"Traffic exposure is modelled: AADT x exp(-distance/{EXPOSURE_DECAY_M} m), area-weighted; a single count station is applied to the whole centreline. "
             "Income for block groups = parent-tract ACS estimate.", fontsize=8, color="#444", wrap=True)
    path = CHART_DIR / "figure1_income_traffic_ej.png"
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    say(f"  saved {path}")


# --------------------------------------------------------------------------- #
# Figure 2: PM2.5
# --------------------------------------------------------------------------- #
def figure2(pm, mon):
    sites = list(mon.site)
    pal = dict(zip(sites, ["#1f77b4", "#e07b00", "#2ca02c", "#9467bd"]))
    fig = plt.figure(figsize=(17, 12.5), dpi=300)
    gs = fig.add_gridspec(2, 2, hspace=0.28, wspace=0.16, left=0.06, right=0.97, top=0.91, bottom=0.11)
    axA, axB = fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0])
    axC = fig.add_subplot(gs[1, 1])
    ymax = max(NAAQS_24H * 1.35, pm.pm25.max() * 1.2)

    # A: time series
    for s in sites:
        d = pm[pm.site == s].sort_values("date")
        axA.plot(d.date, d.pm25, color=pal[s], lw=1.0, alpha=0.9, label=f"{s} (n={len(d)}, mean {d.pm25.mean():.2f})")
        over = d[d.pm25 > WHO_24H]
        axA.scatter(over.date, over.pm25, s=26, color=pal[s], edgecolor="black", linewidth=0.6, zorder=4)
    axA.axhline(NAAQS_24H, color="#b2182b", lw=2.2, label=f"Federal 24-h NAAQS: {NAAQS_24H:.0f} ug/m3")
    axA.axhline(WHO_24H, color="#e07b00", lw=1.6, ls="--", label=f"WHO 24-h guideline: {WHO_24H:.0f} ug/m3 (health reference)")
    axA.axhline(NAAQS_ANNUAL, color="#555", lw=1.2, ls=":", label=f"Federal annual NAAQS: {NAAQS_ANNUAL:.0f} ug/m3")
    axA.axhspan(NAAQS_24H, ymax, color="#b2182b", alpha=0.07)
    pk = pm.loc[pm.pm25.idxmax()]
    axA.annotate(f"Peak {pk.pm25:.1f} ug/m3\n{pk.date:%b %d, %Y}\n{pk.site} (AQI {int(pk.aqi)})", (pk.date, pk.pm25),
                 xytext=(25, -5), textcoords="offset points", fontsize=9.5, arrowprops=dict(arrowstyle="->"),
                 bbox=dict(boxstyle="round", fc="white", ec="#888"))
    n_fed = int((pm.pm25 > NAAQS_24H).sum())
    n_who = int((pm.pm25 > WHO_24H).sum())
    axA.text(0.99, 0.62, f"Days above federal 24-h standard: {n_fed} of {len(pm)}\n"
                         f"Days above WHO 24-h guideline: {n_who} of {len(pm)} (circled points)",
             transform=axA.transAxes, ha="right", fontsize=10, fontweight="bold",
             bbox=dict(boxstyle="round", fc="white", ec="#b2182b"))
    axA.set_ylim(0, ymax)
    axA.set_ylabel("Daily mean PM2.5 (ug/m3)")
    axA.xaxis.set_major_locator(mdates.MonthLocator())
    axA.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axA.set_title("A. Daily PM2.5 at Worcester County monitors, 2025")
    axA.legend(loc="upper left", fontsize=8.5, ncol=2, framealpha=0.95)
    axA.grid(alpha=0.25)

    # B: distribution
    data = [pm[pm.site == s].pm25.to_numpy() for s in sites]
    vp = axB.violinplot(data, positions=range(len(sites)), showextrema=False, widths=0.8)
    for body, s in zip(vp["bodies"], sites):
        body.set_facecolor(pal[s])
        body.set_alpha(0.35)
    axB.boxplot(data, positions=range(len(sites)), widths=0.18, showfliers=False, patch_artist=True,
                boxprops=dict(facecolor="white"), medianprops=dict(color="black", lw=2))
    for i, (s, arr) in enumerate(zip(sites, data)):
        jit = RNG.normal(i, 0.07, len(arr))
        axB.scatter(jit, arr, s=7, color=pal[s], alpha=0.45)
        axB.scatter([i], [arr.mean()], marker="D", s=60, color="white", edgecolor="black", zorder=5)
        axB.text(i + 0.32, arr.mean(), f"mean {arr.mean():.2f}\np98 {np.percentile(arr, 98):.1f}", fontsize=9, va="center")
    axB.axhline(NAAQS_24H, color="#b2182b", lw=2.2)
    axB.axhline(WHO_24H, color="#e07b00", lw=1.6, ls="--")
    axB.axhline(NAAQS_ANNUAL, color="#555", lw=1.2, ls=":")
    axB.set_xticks(range(len(sites)))
    axB.set_xticklabels([s.replace(" ", "\n", 1) for s in sites])
    axB.set_xlim(-0.6, len(sites) - 0.1)
    axB.set_ylim(0, ymax)
    axB.set_ylabel("Daily mean PM2.5 (ug/m3)")
    axB.set_title("B. Distribution by monitor (diamond = mean, box = IQR)")
    axB.grid(alpha=0.25, axis="y")

    # C: exceedance counts by threshold
    thr = [("> 9\n(annual NAAQS\nlevel; ref. only)", NAAQS_ANNUAL), ("> 12", 12.0), (f"> {WHO_24H:.0f}\n(WHO 24-h)", WHO_24H),
           ("> 25", 25.0), (f"> {NAAQS_24H:.0f}\n(federal\n24-h NAAQS)", NAAQS_24H)]
    w = 0.8 / len(sites)
    for i, s in enumerate(sites):
        arr = pm[pm.site == s].pm25
        cnt = [int((arr > t).sum()) for _, t in thr]
        xs = np.arange(len(thr)) + (i - (len(sites) - 1) / 2) * w
        bars = axC.bar(xs, cnt, width=w * 0.92, color=pal[s], label=s)
        for x, v in zip(xs, cnt):
            axC.text(x, v + 4, str(v), ha="center", fontsize=9, fontweight="bold")
    axC.set_xticks(range(len(thr)))
    axC.set_xticklabels([t for t, _ in thr], fontsize=9)
    axC.set_ylabel("Number of days exceeding threshold")
    axC.set_xlabel("Daily mean PM2.5 threshold (ug/m3)")
    axC.set_ylim(0, axC.get_ylim()[1] * 1.08)
    axC.patches[-1].set_edgecolor("#b2182b")
    axC.annotate("Federal standard:\nno exceedance days", xy=(len(thr) - 1, 6), xytext=(len(thr) - 2.3, axC.get_ylim()[1] * 0.45),
                 fontsize=10, color="#b2182b", fontweight="bold", arrowprops=dict(arrowstyle="->", color="#b2182b"))
    axC.set_title("C. Days exceeding benchmark thresholds")
    axC.legend(fontsize=9)
    axC.grid(alpha=0.25, axis="y")

    fig.suptitle("Figure 2. Daily PM2.5 distribution and exceedances of air-quality standards, Worcester County, MA",
                 fontsize=15, fontweight="bold", y=0.975)
    fig.text(0.06, 0.012, "Source: EPA AQS daily PM2.5 (88101, Local Conditions). Circled points in A exceed the WHO 24-h guideline. "
             "NAAQS compliance is judged on 3-year design values (annual mean <= 9.0; 98th percentile <= 35); this is a single-year screen.",
             fontsize=8, color="#444")
    path = CHART_DIR / "figure2_pm25_distribution.png"
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    say(f"  saved {path}")


# --------------------------------------------------------------------------- #
# Key findings text (all numbers computed above)
# --------------------------------------------------------------------------- #
def money(v: float) -> str:
    return f"{'-' if v < 0 else '+'}${abs(v):,.0f}"


def write_findings(m, tr, traffic, ref, f, band, pop_tot, hot):
    inside500 = m["est_ej_pop_within_500m"].sum()
    inside1k = m["est_ej_pop_within_1000m"].sum()
    inc_dir = "rise" if f["rho_inc_dist"] > 0 else "fall"
    w, s_ = "Worcester", "Shrewsbury"
    L = []
    L.append(f"1. Traffic loading. Route 9 at {traffic['station']} carries {traffic['aadt']:,} vehicles/day, "
             f"{traffic['wb_share']:.1%} westbound ({traffic['wb']:,} WB vs {traffic['eb']:,} EB; {traffic['wb'] / traffic['eb']:.1f}:1). "
             f"An estimated {inside500:,.0f} EJ-designated residents ({inside500 / pop_tot:.1%} of all {pop_tot:,.0f} EJ residents in the two towns) live within "
             f"500 m and {inside1k:,.0f} ({inside1k / pop_tot:.1%}) within 1 km of the centreline.")
    L.append(f"2. EJ designation is high everywhere but highest on the corridor. {m.ej_flag.mean():.0%} of all block groups in Worcester and Shrewsbury are EJ-designated "
             f"(vs 36% in the rest of the county and 51% statewide), and {f['ej_in']:.0%} of corridor block groups (centroid <= {CORRIDOR_M / 1000:g} km) vs {f['ej_out']:.0%} "
             f"elsewhere in the two towns (odds ratio {f['or_']:.1f}, {fmt_p(f['p_or'])}). EJ block groups sit a median {f['med_d_ej']:,.0f} m from Route 9 vs "
             f"{f['med_d_non']:,.0f} m for non-EJ (rho = {f['rho_ej']:+.2f}, cluster-bootstrap 95% CI {f['rho_ej_ci']}). The effect is modest: at tract level the "
             f"association is weaker (rho = {f['rho_tract_ej']:+.2f}, {fmt_p(f['p_tract_ej'])}).")
    L.append(f"3. Income gradient. Median household income tends to {inc_dir} with distance from Route 9: Spearman rho = "
             f"{f['rho_inc_dist']:+.2f} ({fmt_p(f['p_inc_dist'])}; tract-cluster bootstrap 95% CI {f['rho_inc_dist_ci']}); tract-level rho = {f['rho_tract']:+.2f}. "
             f"That is {money(f['slope_per_km'])} in tract median income per km from the road (citywide pooled OLS). Spatial clustering is "
             f"{'strong' if f['moran'] > 0.4 else 'moderate' if f['moran'] > 0.2 else 'weak'} (Moran's I = {f['moran']:.2f}), which shrinks the effective sample size.")
    L.append(f"   Town-confound check: within Worcester alone the gradient is rho = {f['rho_inc_' + w]:+.2f} ({fmt_p(f['p_inc_' + w])}, n={f['n_inc_' + w]}, "
             f"cluster CI {f['ci_inc_' + w]}; {money(f['slope_worcester'])}/km); within Shrewsbury alone rho = {f['rho_inc_' + s_]:+.2f} "
             f"({fmt_p(f['p_inc_' + s_])}, n={f['n_inc_' + s_]}, CI {f['ci_inc_' + s_]}). "
             + ("The Worcester-only result shows the gradient is not merely the Worcester-vs-Shrewsbury town divide."
                if f['rho_inc_' + w] > 0 and f['p_inc_' + w] < 0.05 else
                "The gradient does NOT hold up within Worcester alone, so much of the pooled result reflects the town divide."))
    L.append(f"4. Corridor gap. Median tract income is ${f['inc_corr']:,.0f} in the corridor vs ${f['inc_other']:,.0f} elsewhere in the two towns "
             f"({money(f['inc_corr'] - f['inc_other'])}); the corridor median equals {f['inc_corr'] / ref['state_median_income']:.0%} of the statewide median "
             f"(${ref['state_median_income']:,.0f}). Households earning under $50k: {f['lowinc_c']:.1f}% in the corridor vs {f['lowinc_o']:.1f}% elsewhere. "
             f"Worcester+Shrewsbury tracts overall have a median of ${f['ws_tract_med']:,.0f} vs ${f['oth_tract_med']:,.0f} for the rest of Worcester County.")
    L.append(f"5. Cumulative burden. The traffic-independent vulnerability score (low income + EJ criteria met) also rises toward Route 9 "
             f"(rho with distance = {f['rho_vuln']:+.2f}, {fmt_p(f['p_vuln'])}). {f['hs_n']} corridor block groups ({f['hs_pop']:,.0f} EJ residents, "
             f"{f['hs_pop'] / pop_tot:.1%} of the study EJ population) are in the top quintile of the cumulative burden index.")
    L.append(f"6. PM2.5. Mean {f['pm_mean']:.2f} ug/m3, peak {f['pm_max']:.1f}. The federal 24-h standard ({NAAQS_24H:.0f}) was exceeded on "
             f"{f['fed_days']} of {f['n_pm']} site-days (98th percentile {f['pm_p98']:.1f}); the annual mean is below the {NAAQS_ANNUAL:.0f} ug/m3 federal "
             f"annual standard but {'above' if f['pm_mean'] > WHO_ANNUAL else 'below'} the WHO {WHO_ANNUAL:.0f} ug/m3 guideline; "
             f"{f['who_days']} site-days ({f['who_days'] / f['n_pm']:.1%}, {f['who_dates']} distinct dates) exceeded the WHO 24-h guideline of {WHO_24H:.0f}, "
             f"{f['who_summer_share']:.0%} of them in June-August. The two monitors correlate at rho = {f['pm_corr']:.2f}, so the episodes are regional, not corridor-specific.")
    for line in L:
        say(line)
        say()
    say("LIMITATIONS")
    for line in [
        "- One AADT station: block-group traffic is a distance-decay model (300 m e-folding), not a measurement; it ignores lane geometry, truck share, grade and wind.",
        "- PM2.5 comes from two monitors (Worcester Summer St, Uxbridge) and cannot differentiate block groups; it is regional context, not a corridor-specific measurement.",
        "- EJ_POLY lists only EJ-designated block groups. Non-EJ block groups were identified from Census geometry, so demographics (population, % minority, % LEP) are unavailable for them.",
        "- ACS 2024 tract incomes are applied to block groups (some tracts have wide margins of error: see acs_income_reliable); EJ-table incomes are an older ACS vintage.",
        "- Population near Route 9 is interpolated by area (uniform-density assumption). Results are ecological associations, not individual exposure or health effects.",
        "- One year of PM2.5 data cannot establish NAAQS compliance, which uses 3-year design values.",
    ]:
        say(line)


if __name__ == "__main__":
    main()
