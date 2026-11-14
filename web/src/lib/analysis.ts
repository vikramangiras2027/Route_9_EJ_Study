import { blockGroups, type BlockGroup } from "../data";

/** Distance-band keys exactly as written by route9_deep_analysis.py. */
export const BAND_ORDER = ["<=0.5 km", "0.5-1 km", "1-2 km", "2-4 km", ">4 km"] as const;
export type Band = (typeof BAND_ORDER)[number];
export const BAND_LABEL: Record<Band, string> = {
  "<=0.5 km": "\u2264 0.5 km",
  "0.5-1 km": "0.5\u20131 km",
  "1-2 km": "1\u20132 km",
  "2-4 km": "2\u20134 km",
  ">4 km": "> 4 km",
};

const present = (a: Array<number | null | undefined>): number[] => a.filter((v): v is number => v !== null && v !== undefined && !Number.isNaN(v));

export const mean = (a: Array<number | null | undefined>): number | null => {
  const v = present(a);
  return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null;
};

export const median = (a: Array<number | null | undefined>): number | null => {
  const v = present(a).sort((x, y) => x - y);
  if (!v.length) return null;
  const m = v.length >> 1;
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
};

export const sum = (a: Array<number | null | undefined>): number => present(a).reduce((s, x) => s + x, 0);

export interface BandStats {
  band: Band;
  n: number;
  pctEj: number;
  ejResidents: number;
  medianIncome: number | null;
  pctMinority: number | null;
  pctLep: number | null;
  ejCriteria: number | null;
  exposure: number | null;
  cbi: number | null;
}

export function bandStats(band: Band, bgs: BlockGroup[] = blockGroups): BandStats {
  const g = bgs.filter((b) => b.band === band);
  return {
    band,
    n: g.length,
    pctEj: (100 * g.filter((b) => b.ej).length) / Math.max(1, g.length),
    ejResidents: sum(g.map((b) => b.pop)),
    medianIncome: median(g.map((b) => b.income)),
    pctMinority: mean(g.map((b) => b.pctMinority)),
    pctLep: mean(g.map((b) => b.pctLep)),
    ejCriteria: mean(g.map((b) => b.ejCount)),
    exposure: mean(g.map((b) => b.exposure)),
    cbi: mean(g.map((b) => b.cbi)),
  };
}

export const allBandStats = BAND_ORDER.map((b) => bandStats(b));

export interface CorridorCompare {
  radius: number;
  nIn: number;
  nOut: number;
  pctEjIn: number;
  pctEjOut: number;
  incomeIn: number | null;
  incomeOut: number | null;
}

export function corridorCompare(radius: number): CorridorCompare {
  const inn = blockGroups.filter((b) => b.distM !== null && b.distM <= radius);
  const out = blockGroups.filter((b) => b.distM !== null && b.distM > radius);
  const pct = (g: BlockGroup[]) => (g.length ? (100 * g.filter((b) => b.ej).length) / g.length : 0);
  return {
    radius,
    nIn: inn.length,
    nOut: out.length,
    pctEjIn: pct(inn),
    pctEjOut: pct(out),
    incomeIn: median(inn.map((b) => b.income)),
    incomeOut: median(out.map((b) => b.income)),
  };
}

/** Ordinary least squares slope of y on x (same estimator the paper reports as "$ per km"). */
export function olsSlope(x: number[], y: number[]): number {
  const n = x.length;
  const mx = x.reduce((a, b) => a + b, 0) / n;
  const my = y.reduce((a, b) => a + b, 0) / n;
  let sxy = 0;
  let sxx = 0;
  for (let i = 0; i < n; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
  }
  return sxy / sxx;
}

const withIncome = blockGroups.filter((b) => b.income !== null && b.distM !== null);

/** Headline numbers: all recomputed from the CSV at load time, never typed in by hand. */
export const headline = (() => {
  const corridor = blockGroups.filter((b) => b.corridor);
  const elsewhere = blockGroups.filter((b) => !b.corridor);
  const hotspots = blockGroups.filter((b) => b.hotspot);
  const ejRate = (g: BlockGroup[]) => (100 * g.filter((b) => b.ej).length) / g.length;
  const ejPop = sum(blockGroups.map((b) => b.pop));
  return {
    nBlockGroups: blockGroups.length,
    incomeSlopePerKm: olsSlope(
      withIncome.map((b) => (b.distM as number) / 1000),
      withIncome.map((b) => b.income as number),
    ),
    nIncome: withIncome.length,
    corridorN: corridor.length,
    corridorEj: corridor.filter((b) => b.ej).length,
    corridorEjRate: ejRate(corridor),
    elsewhereEjRate: ejRate(elsewhere),
    hotspots: hotspots.length,
    hotspotResidents: sum(hotspots.map((b) => b.pop)),
    ejPopTotal: ejPop,
    ejPop300: sum(blockGroups.map((b) => b.ejPop300)),
    ejPop500: sum(blockGroups.map((b) => b.ejPop500)),
    ejPop1000: sum(blockGroups.map((b) => b.ejPop1000)),
  };
})();

export interface Metric {
  key: string;
  label: string;
  short: string;
  help: string;
  value: (s: BandStats) => number | null;
  format: (n: number) => string;
  /** Upper bound for bar scaling. */
  max: number;
}

export const BAND_METRICS: Metric[] = [
  {
    key: "income",
    label: "Median household income",
    short: "Income",
    help: "Median of ACS 2024 tract median household income, assigned to each block group.",
    value: (s) => s.medianIncome,
    format: (n) => `$${Math.round(n).toLocaleString("en-US")}`,
    max: 110_000,
  },
  {
    key: "ej",
    label: "Share EJ-designated",
    short: "EJ share",
    help: "Percent of block groups on the MassGIS environmental justice list.",
    value: (s) => s.pctEj,
    format: (n) => `${n.toFixed(1)}%`,
    max: 100,
  },
  {
    key: "minority",
    label: "% minority residents",
    short: "% minority",
    help: "Mean of block-group % minority, EJ-designated block groups only (demographics unavailable for others).",
    value: (s) => s.pctMinority,
    format: (n) => `${n.toFixed(1)}%`,
    max: 70,
  },
  {
    key: "lep",
    label: "% limited-English households",
    short: "% LEP",
    help: "Mean share of households with limited English proficiency, EJ-designated block groups only.",
    value: (s) => s.pctLep,
    format: (n) => `${n.toFixed(1)}%`,
    max: 16,
  },
  {
    key: "exposure",
    label: "Modelled traffic exposure",
    short: "Traffic exposure",
    help: "Mean of AADT \u00d7 exp(\u2212d/300 m) averaged over each block group on a 50 m grid. Modelled, not measured.",
    value: (s) => s.exposure,
    format: (n) => `${Math.round(n).toLocaleString("en-US")} veh/day-eq.`,
    max: 14_000,
  },
  {
    key: "cbi",
    label: "Cumulative burden index",
    short: "Burden index",
    help: "0\u2013100: mean percentile rank of traffic exposure, low income and EJ criteria met.",
    value: (s) => s.cbi,
    format: (n) => n.toFixed(1),
    max: 100,
  },
];
