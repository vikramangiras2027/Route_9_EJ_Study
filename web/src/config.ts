/**
 * ─────────────────────────────────────────────────────────────────────────────
 *  SITE CONFIGURATION: the only file you need to edit to "go live"
 * ─────────────────────────────────────────────────────────────────────────────
 *  Leave a link as "" and the UI automatically renders a clean "Coming soon"
 *  placeholder. Fill it in and the same slot becomes a working link/button.
 */

/** Resolve a file in /public relative to wherever the site is hosted. */
export const asset = (p: string) => `${import.meta.env.BASE_URL}${p}`.replace(/\/{2,}/g, "/").replace(/^\.\//, "./");

export const SITE = {
  title: "Spatial Equity, Traffic Exposure, and Environmental Justice along the Route 9 Corridor",
  subtitle: "Worcester & Shrewsbury, Massachusetts",
  shortTitle: "Route 9 EJ Study",
  /** Shown in the footer and citation block. Leave "" to keep the placeholder. */
  author: "Vikram Angiras",
  affiliation: "Independent research",
  year: 2026,
  contactEmail: "vikram.angiras99@gmail.com",
};

export const LINKS = {
  // ── OPTIONAL / STILL OPEN ──────────────────────────────────────────────────
  /** 1. Research paper PDF (live). File lives in web/public/paper/. */
  paperPdf: asset("paper/route9-ej-study.pdf"),
  /** 2. GitHub repository (analysis script, data, paper, and this site). */
  githubRepo: "https://github.com/vikramangiras2027/Route_9_EJ_Study",

  // ── LIVE ASSETS (already wired to the workspace outputs) ───────────────────
  /** 3. Master dataset: verbatim copy of outputs/master_route9_table.csv */
  datasetCsv: asset("data/master_route9_table.csv"),
  analysisScript: asset("code/route9_deep_analysis.py"),
  fetchScript: asset("code/fetch_massdot_traffic_aadt.py"),
  summaryStatistics: asset("data/summary_statistics.txt"),
  dataDictionaryMd: asset("data/data_dictionary.md"),
  tractTableCsv: asset("data/tract_table_route9.csv"),
  figure1: asset("figures/figure1_income_traffic_ej.png"),
  figure2: asset("figures/figure2_pm25_distribution.png"),
  figure3: asset("figures/figure3_priority_hotspots.png"),
};

/** Public-facing data sources, also rendered in the Methodology section. */
export const SOURCES = [
  {
    name: "MassDOT traffic counts & LRS segment AADT",
    detail: "RoadInventoryLRS Traffic (layer 56, continuous segment AADT, mostly 2024-25) joined to TrafficCountLocations stations by route + milepost; 8 stations on Route 9, 100% joined.",
    use: "Traffic loading input (measured)",
    href: "https://geo-massdot.opendata.arcgis.com/",
  },
  {
    name: "MassGIS Environmental Justice Populations",
    detail: "2020-census-based EJ block groups (minority, income and English-isolation criteria).",
    use: "EJ designation & demographics",
    href: "https://www.mass.gov/info-details/massgis-data-2020-environmental-justice-populations",
  },
  {
    name: "U.S. Census ACS 5-year 2024, table S1901",
    detail: "Tract-level median household income, margins of error, and income brackets.",
    use: "Income gradient",
    href: "https://data.census.gov/table/ACSST5Y2024.S1901",
  },
  {
    name: "U.S. Census TIGER/Line 2024",
    detail: "Block-group polygons, primary & secondary roads (Route 9 centreline: 'State Rte 9'), county subdivisions.",
    use: "Geometry & distance",
    href: "https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html",
  },
  {
    name: "EPA Air Quality System (AQS)",
    detail: "Daily PM2.5, Federal Reference/Equivalent Methods, 2025: Worcester Summer Street and Uxbridge monitors (705 site-days).",
    use: "Regional PM2.5 context",
    href: "https://www.epa.gov/outdoor-air-quality-data",
  },
];
