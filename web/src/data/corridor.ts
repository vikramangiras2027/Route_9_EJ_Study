/**
 * Corridor-level traffic and Worcester-equity values, transcribed from
 * outputs/summary_statistics.txt (sections 3, 4 and 5). These are aggregate
 * statistics (length-weighted means, household-weighted pooled incomes,
 * tract-bootstrap confidence intervals) that the source CSV does not carry
 * row-by-row, so — like web/src/data/airQuality.ts — they are transcribed
 * here rather than re-derived in build-data.mjs. Everything else on the site
 * (block-group counts, EJ populations, priority-hotspot counts) is derived
 * from master_route9_table.csv and audited on every build.
 */

/** Measured MassDOT segment AADT along Route 9, by town (section 3). */
export const TRAFFIC_BY_TOWN = [
  { town: "Worcester", km: 10.8, meanAadt: 20_646, minAadt: 13_461, maxAadt: 34_260, pctAbove30k: 8 },
  { town: "Shrewsbury", km: 6.8, meanAadt: 40_615, minAadt: 34_260, maxAadt: 45_937, pctAbove30k: 100 },
  { town: "Pooled", km: 17.7, meanAadt: 28_373, minAadt: 13_461, maxAadt: 45_937, pctAbove30k: 44 },
];

export const TRAFFIC_VINTAGE_SHARE_2023_25 = 0.98;
export const STATIONS_ON_ROUTE9 = { n: 8, joinRatePct: 100 };

/** The old model: one station applied to the whole 17.7 km centreline. */
export const LEGACY_ANCHOR = { station: "M3002W", aadt: 28_112, westboundSharePct: 74.6, diffVsSegmentPct: 5.5 };

/** Worcester corridor vs rest of city, household-weighted (section 4A). */
export const WORCESTER_EQUITY = {
  corridor: { households: 35_920, medianIncome: 56_458, pctUnder50k: 45.9, pct150kPlus: 11.8, ejShare: 0.97 },
  rest: { households: 43_581, medianIncome: 82_432, pctUnder50k: 31.2, pct150kPlus: 22.9, ejShare: 0.88 },
};

/** Worcester, income vs distance to Route 9 (section 4B). Tract level is primary. */
export const WORCESTER_DISTANCE = {
  tract: { rho: 0.48, ciLo: 0.17, ciHi: 0.72, n: 44 },
  feSlopePerKm: { value: 11_243, ciLo: 6_609, ciHi: 15_876, n: 164, tracts: 52 },
  moransI: { allBlockGroups: 0.73, worcesterBlockGroups: 0.67, tracts: 0.4 },
};

/** Shrewsbury sensitivity case (section 5). */
export const SHREWSBURY = {
  blockGroups: 20,
  tracts: 8,
  corridorBlockGroups: 11,
  corridorHouseholds: 1924,
  pooledMedianIncomeCorridor: 126_980,
  pooledMedianIncomeRest: 166_499,
  tractRho: { value: 0.88, n: 8 },
  priorityHotspots: 0,
};

/** Traffic-independent vulnerability vs legacy CBI (section 6). */
export const VULNERABILITY = {
  priorityHotspots: { n: 27, ejResidents: 34_339, households: 13_565, allInWorcester: true },
  legacyCbiHotspots: { n: 33, ejResidents: 42_416 },
  overlap: 24,
  rhoWithDistance: { vulnerability: -0.449, legacyCbi: -0.755, trafficPercentile: -0.975 },
};

/** Nearest PM2.5 monitor to Route 9 (section 7) — context, not a corridor measurement. */
export const PM25_NEAREST = { site: "Worcester Summer Street", kmFromRoute9: 0.9, nearRoadZoneM: 300 };
