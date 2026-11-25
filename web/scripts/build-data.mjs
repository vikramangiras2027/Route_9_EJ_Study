/**
 * build-data.mjs
 *
 * Turns the existing analysis outputs in the repository root into static assets
 * for the web app. It NEVER writes outside ./web and never modifies the originals:
 *
 *   ../outputs/master_route9_table.csv      -> public/data/master_route9_table.csv   (verbatim copy, download)
 *                                           -> src/data/generated/blockgroups.json   (compact, typed subset)
 *   ../charts/*.png                         -> public/figures/                       (verbatim copies)
 *   ../route9_deep_analysis.py              -> public/code/                          (verbatim copy, download)
 *   ../cache/tl_2024_25_*.zip (TIGER 2024)  -> src/data/generated/geometry.json      (simplified block groups,
 *                                                                                     Route 9 centreline, town outlines)
 *
 * It also re-derives the headline numbers from the CSV and compares them with
 * the values printed in ../outputs/summary_statistics.txt, so the UI can never
 * silently drift away from the analysis.
 *
 * If the TIGER cache is not present (e.g. a fresh clone) and geometry.json
 * already exists, the geometry step is skipped.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Papa from "papaparse";
import AdmZip from "adm-zip";
import * as shapefile from "shapefile";

const here = path.dirname(fileURLToPath(import.meta.url));
const WEB = path.resolve(here, "..");
const ROOT = path.resolve(WEB, "..");
const OUT_GEN = path.join(WEB, "src", "data", "generated");
const PUB = path.join(WEB, "public");

const mkdir = (p) => fs.mkdirSync(p, { recursive: true });
const copy = (from, to) => {
  mkdir(path.dirname(to));
  fs.copyFileSync(from, to);
  console.log(`  copied ${path.relative(ROOT, from)} -> web/${path.relative(WEB, to)}`);
};

/* ------------------------------------------------------------------ */
/* 1. Verbatim copies of existing assets                                */
/* ------------------------------------------------------------------ */
console.log("[1/4] Copying assets (originals are left untouched)");
const csvPath = path.join(ROOT, "outputs", "master_route9_table.csv");
if (!fs.existsSync(csvPath)) throw new Error(`Missing ${csvPath}. Run route9_deep_analysis.py first.`);
copy(csvPath, path.join(PUB, "data", "master_route9_table.csv"));
for (const f of ["figure1_income_traffic_ej.png", "figure2_pm25_distribution.png"]) {
  copy(path.join(ROOT, "charts", f), path.join(PUB, "figures", f));
}
copy(path.join(ROOT, "route9_deep_analysis.py"), path.join(PUB, "code", "route9_deep_analysis.py"));
copy(path.join(ROOT, "fetch_massdot_traffic_aadt.py"), path.join(PUB, "code", "fetch_massdot_traffic_aadt.py"));
const summaryTxt = path.join(ROOT, "outputs", "summary_statistics.txt");
if (fs.existsSync(summaryTxt)) copy(summaryTxt, path.join(PUB, "data", "summary_statistics.txt"));
for (const [rel, dest] of [
  ["outputs/data_dictionary.md", ["data", "data_dictionary.md"]],
  ["outputs/tract_table_route9.csv", ["data", "tract_table_route9.csv"]],
  ["charts/figure3_priority_hotspots.png", ["figures", "figure3_priority_hotspots.png"]],
]) {
  const from = path.join(ROOT, rel);
  if (fs.existsSync(from)) copy(from, path.join(PUB, ...dest));
}

/* ------------------------------------------------------------------ */
/* 2. Block-group table                                                  */
/* ------------------------------------------------------------------ */
console.log("[2/4] Parsing master table");
const parsed = Papa.parse(fs.readFileSync(csvPath, "utf8"), { header: true, dynamicTyping: true, skipEmptyLines: true });
if (parsed.errors.length) console.warn("  CSV parse warnings:", parsed.errors.slice(0, 3));
const rows = parsed.data;
const columns = parsed.meta.fields;
console.log(`  ${rows.length} rows x ${columns.length} columns`);

const num = (v, d = 1) => (v === null || v === undefined || v === "" || Number.isNaN(v) ? null : Number(Number(v).toFixed(d)));
const bool = (v) => v === true || v === "True" || v === "true" || v === 1;

const blockGroups = rows.map((r) => {
  const geoid = String(r.geoid_bg);
  const tract = String(r.geoid_tract);
  const tractCode = tract.slice(5); // 6 digits: 739101 -> 7391.01
  const tractLabel = `${Number(tractCode.slice(0, 4))}${tractCode.slice(4) === "00" ? "" : "." + tractCode.slice(4)}`;
  return {
    id: geoid,
    tract: tractLabel,
    bg: geoid.slice(-1),
    town: r.municipality,
    ej: bool(r.ej_designated),
    ejCount: num(r.ej_criteria_count, 0),
    ejDesc: r.ej_criteria_desc,
    pop: num(r.total_pop, 0),
    pctMinority: num(r.pct_minority, 1),
    pctLep: num(r.pct_lep_hh, 1),
    income: num(r.income_best, 0),
    incomeReliable: r.acs_income_reliable === null ? null : bool(r.acs_income_reliable),
    incomePctState: num(r.income_pct_of_state, 1),
    pctUnder50k: num(r.acs_pct_hh_under_50k, 1),
    distM: num(r.dist_centroid_m, 0),
    band: r.dist_band,
    corridor: bool(r.in_corridor),
    exposure: num(r.exposure_index, 1),
    ejPop300: num(r.est_ej_pop_within_300m, 1),
    ejPop500: num(r.est_ej_pop_within_500m, 1),
    ejPop1000: num(r.est_ej_pop_within_1000m, 1),
    cbi: num(r.cumulative_burden_index, 1),
    cbiQuintile: r.cbi_quintile,
    hotspot: bool(r.hotspot),
    areaKm2: num(r.area_km2, 2),
    lat: num(r.centroid_lat, 5),
    lon: num(r.centroid_lon, 5),
    // --- added in the measured-traffic / Worcester-primary refactor ---
    vulnerability: num(r.vulnerability_index, 1),
    vulnQuintile: r.vuln_quintile,
    priorityHotspot: bool(r.priority_hotspot),
    priorityRank: num(r.priority_rank, 0),
    nearestSegmentAadt: num(r.nearest_segment_aadt, 0),
    nearestSegmentAadtYear: num(r.nearest_segment_aadt_year, 0),
    estHouseholds: num(r.est_households, 1),
    estHhWithin500m: num(r.est_hh_within_500m, 1),
  };
});

/* ------------------------------------------------------------------ */
/* 3. Audit against summary_statistics.txt                               */
/* ------------------------------------------------------------------ */
console.log("[3/4] Auditing derived numbers against summary_statistics.txt");
const sum = (a) => a.reduce((s, v) => s + (v ?? 0), 0);
const median = (a) => {
  const s = a.filter((x) => x !== null && !Number.isNaN(x)).sort((x, y) => x - y);
  if (!s.length) return null;
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const rank = (a) => {
  const idx = a.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]);
  const r = new Array(a.length);
  for (let i = 0; i < idx.length; ) {
    let j = i;
    while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
    const avg = (i + j) / 2 + 1;
    for (let k = i; k <= j; k++) r[idx[k][1]] = avg;
    i = j + 1;
  }
  return r;
};
const pearson = (x, y) => {
  const n = x.length;
  const mx = x.reduce((a, b) => a + b, 0) / n;
  const my = y.reduce((a, b) => a + b, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
    syy += (y[i] - my) ** 2;
  }
  return { r: sxy / Math.sqrt(sxx * syy), slope: sxy / sxx };
};
const withInc = blockGroups.filter((b) => b.income !== null && b.distM !== null);
const rho = pearson(rank(withInc.map((b) => b.distM)), rank(withInc.map((b) => b.income))).r;
const slopePerKm = pearson(withInc.map((b) => b.distM / 1000), withInc.map((b) => b.income)).slope;
const corridor = blockGroups.filter((b) => b.corridor);
const corridorEj = corridor.filter((b) => b.ej).length;
const hotspots = blockGroups.filter((b) => b.hotspot).length;
const priorityHotspots = blockGroups.filter((b) => b.priorityHotspot);
const bandMedian = (label) => median(blockGroups.filter((b) => b.band === label).map((b) => b.income));

const checks = [
  ["block groups", blockGroups.length, 166, 0],
  ["corridor block groups", corridor.length, 81, 0],
  ["corridor EJ block groups", corridorEj, 78, 0],
  ["legacy CBI hotspots", hotspots, 33, 0],
  ["Spearman rho (distance, income), n=164", rho, 0.47, 0.005],
  ["OLS income slope $/km", slopePerKm, 10651, 1],
  ["median income <=0.5 km", bandMedian("<=0.5 km"), 41667, 1],
  ["median income >4 km", bandMedian(">4 km"), 99932, 1],
  ["AADT (M3002W anchor, legacy)", rows[0].aadt_station, 28112, 0],
  ["EJ residents within 300 m", sum(blockGroups.map((b) => b.ejPop300)), 28786, 3],
  ["EJ residents within 500 m", sum(blockGroups.map((b) => b.ejPop500)), 47144, 3],
  ["EJ residents within 1000 m", sum(blockGroups.map((b) => b.ejPop1000)), 81149, 3],
  ["EJ residents in legacy CBI hotspots", sum(blockGroups.filter((b) => b.hotspot).map((b) => b.pop)), 42416, 0],
  ["EJ residents in study area", sum(blockGroups.map((b) => b.pop)), 217466, 0],
  ["priority hotspots (traffic-independent)", priorityHotspots.length, 27, 0],
  ["EJ residents in priority hotspots", sum(priorityHotspots.map((b) => b.pop)), 34339, 0],
];
let failed = 0;
for (const [label, got, want, tol] of checks) {
  const ok = Math.abs(got - want) <= tol;
  if (!ok) failed++;
  console.log(`  ${ok ? "OK  " : "FAIL"} ${label}: derived ${typeof got === "number" ? +got.toFixed(3) : got} | reported ${want}`);
}
if (failed) {
  console.error(`\n${failed} audit check(s) failed: the CSV and summary_statistics.txt disagree. Re-run the analysis or update the checks.`);
  process.exit(1);
}

const traffic = {
  station: rows[0].aadt_station,
  aadt: rows[0].aadt_station,
  westbound: rows[0].aadt_westbound,
  eastbound: rows[0].aadt_eastbound,
  westboundShare: num(rows[0].westbound_share, 4),
};

mkdir(OUT_GEN);
fs.writeFileSync(
  path.join(OUT_GEN, "blockgroups.json"),
  JSON.stringify({ traffic, columns, blockGroups }),
);
console.log(`  wrote src/data/generated/blockgroups.json (${(fs.statSync(path.join(OUT_GEN, "blockgroups.json")).size / 1024).toFixed(0)} KB)`);

/* ------------------------------------------------------------------ */
/* 4. Geometry from cached Census TIGER/Line 2024                        */
/* ------------------------------------------------------------------ */
console.log("[4/4] Building simplified geometry");
const geoOut = path.join(OUT_GEN, "geometry.json");
const cache = path.join(ROOT, "cache");
const zipBg = path.join(cache, "tl_2024_25_bg.zip");
const zipRoads = path.join(cache, "tl_2024_25_prisecroads.zip");
const zipTowns = path.join(cache, "tl_2024_25_cousub.zip");

if (!fs.existsSync(zipBg) || !fs.existsSync(zipRoads) || !fs.existsSync(zipTowns)) {
  if (fs.existsSync(geoOut)) {
    console.log("  TIGER cache not found; keeping existing geometry.json");
    process.exit(0);
  }
  throw new Error("TIGER cache zips missing in ../cache and no pre-built geometry.json. Run route9_deep_analysis.py once to download them.");
}

const readZip = async (zipFile) => {
  const zip = new AdmZip(zipFile);
  const entry = (ext) => zip.getEntries().find((e) => e.entryName.toLowerCase().endsWith(ext));
  const shp = entry(".shp").getData();
  const dbf = entry(".dbf").getData();
  return shapefile.read(shp, dbf);
};

// Douglas-Peucker; tolerance in degrees (3e-5 deg ~ 3 m) - invisible at map scale, ~10x smaller files.
const sqSegDist = (p, a, b) => {
  let x = a[0], y = a[1], dx = b[0] - x, dy = b[1] - y;
  if (dx !== 0 || dy !== 0) {
    const t = ((p[0] - x) * dx + (p[1] - y) * dy) / (dx * dx + dy * dy);
    if (t > 1) { x = b[0]; y = b[1]; } else if (t > 0) { x += dx * t; y += dy * t; }
  }
  dx = p[0] - x; dy = p[1] - y;
  return dx * dx + dy * dy;
};
const simplify = (pts, tol, minPts = 2) => {
  if (pts.length <= minPts) return pts;
  const sq = tol * tol;
  const keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [first, last] = stack.pop();
    let max = 0, idx = -1;
    for (let i = first + 1; i < last; i++) {
      const d = sqSegDist(pts[i], pts[first], pts[last]);
      if (d > max) { max = d; idx = i; }
    }
    if (max > sq && idx !== -1) { keep[idx] = 1; stack.push([first, idx], [idx, last]); }
  }
  const out = pts.filter((_, i) => keep[i]);
  return out.length >= minPts ? out : pts;
};
const r5 = (p) => [Number(p[0].toFixed(5)), Number(p[1].toFixed(5))];
const simplifyRing = (ring, tol) => simplify(ring.map(r5), tol, 4);
const simplifyGeom = (g, tol) => {
  if (g.type === "Polygon") return { type: "Polygon", coordinates: g.coordinates.map((r) => simplifyRing(r, tol)) };
  if (g.type === "MultiPolygon") {
    return { type: "MultiPolygon", coordinates: g.coordinates.map((poly) => poly.map((r) => simplifyRing(r, tol))) };
  }
  if (g.type === "LineString") return { type: "LineString", coordinates: simplify(g.coordinates.map(r5), tol) };
  if (g.type === "MultiLineString") {
    return { type: "MultiLineString", coordinates: g.coordinates.map((l) => simplify(l.map(r5), tol)) };
  }
  return g;
};

const ids = new Set(blockGroups.map((b) => b.id));
const bg = await readZip(zipBg);
const studyBg = bg.features.filter((f) => ids.has(f.properties.GEOID));
if (studyBg.length !== ids.size) throw new Error(`Matched ${studyBg.length} of ${ids.size} block-group polygons`);

let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
const walk = (c) => {
  if (typeof c[0] === "number") {
    minX = Math.min(minX, c[0]); maxX = Math.max(maxX, c[0]);
    minY = Math.min(minY, c[1]); maxY = Math.max(maxY, c[1]);
  } else c.forEach(walk);
};
studyBg.forEach((f) => walk(f.geometry.coordinates));
const bbox = [minX, minY, maxX, maxY];

// Route 9: TIGER FULLNAME "State Rte 9" (same filter as route9_deep_analysis.py), clipped to a padded study bbox.
const roads = await readZip(zipRoads);
const pad = 0.02;
const inBox = ([x, y]) => x >= minX - pad && x <= maxX + pad && y >= minY - pad && y <= maxY + pad;
const route9 = roads.features
  .filter((f) => f.properties.FULLNAME === "State Rte 9")
  .flatMap((f) => (f.geometry.type === "LineString" ? [f.geometry.coordinates] : f.geometry.coordinates))
  .filter((line) => line.some(inBox))
  .map((line) => simplify(line.map(r5), 2e-5));

const towns = await readZip(zipTowns);
const townFeatures = towns.features
  .filter((f) => ["Worcester", "Shrewsbury"].includes(f.properties.NAME) && f.properties.COUNTYFP === "027")
  .map((f) => ({ type: "Feature", properties: { name: f.properties.NAME }, geometry: simplifyGeom(f.geometry, 6e-5) }));

const geometry = {
  bbox,
  blockGroups: {
    type: "FeatureCollection",
    features: studyBg.map((f) => ({ type: "Feature", properties: { id: f.properties.GEOID }, geometry: simplifyGeom(f.geometry, 3e-5) })),
  },
  route9: { type: "MultiLineString", coordinates: route9 },
  towns: { type: "FeatureCollection", features: townFeatures },
  source: "US Census Bureau TIGER/Line 2024 (block groups, primary & secondary roads, county subdivisions); simplified at ~3 m for display only.",
};
fs.writeFileSync(geoOut, JSON.stringify(geometry));
console.log(
  `  ${studyBg.length} block groups, ${route9.length} Route 9 segments, ${townFeatures.length} towns -> geometry.json (${(fs.statSync(geoOut).size / 1024).toFixed(0)} KB)`,
);
console.log("Done.");
