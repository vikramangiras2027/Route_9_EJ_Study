import bgRaw from "./generated/blockgroups.json";
import geoRaw from "./generated/geometry.json";

export interface BlockGroup {
  id: string;
  tract: string;
  bg: string;
  town: "Worcester" | "Shrewsbury";
  ej: boolean;
  ejCount: number | null;
  ejDesc: string;
  pop: number | null;
  pctMinority: number | null;
  pctLep: number | null;
  income: number | null;
  incomeReliable: boolean | null;
  incomePctState: number | null;
  pctUnder50k: number | null;
  distM: number | null;
  band: string;
  corridor: boolean;
  exposure: number | null;
  ejPop300: number | null;
  ejPop500: number | null;
  ejPop1000: number | null;
  cbi: number | null;
  cbiQuintile: string | null;
  hotspot: boolean;
  areaKm2: number | null;
  lat: number | null;
  lon: number | null;
}

export interface Traffic {
  station: number;
  aadt: number;
  westbound: number;
  eastbound: number;
  westboundShare: number;
}

export interface Geometry {
  bbox: [number, number, number, number];
  blockGroups: GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon, { id: string }>;
  route9: GeoJSON.MultiLineString;
  towns: GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon, { name: string }>;
  source: string;
}

const typed = bgRaw as unknown as { traffic: Traffic; columns: string[]; blockGroups: BlockGroup[] };

export const blockGroups: BlockGroup[] = typed.blockGroups;
export const traffic: Traffic = typed.traffic;
export const csvColumns: string[] = typed.columns;
export const geometry = geoRaw as unknown as Geometry;
export const byId: Map<string, BlockGroup> = new Map(blockGroups.map((b) => [b.id, b]));

/** Statewide median household income, ACS 2024 5-yr (from summary_statistics.txt). */
export const MA_MEDIAN_INCOME = 103_960;
