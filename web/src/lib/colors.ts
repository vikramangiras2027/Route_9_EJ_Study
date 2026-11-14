const hex = (h: string): [number, number, number] => [
  parseInt(h.slice(1, 3), 16),
  parseInt(h.slice(3, 5), 16),
  parseInt(h.slice(5, 7), 16),
];

/** Interpolate across an array of hex stops; t is clamped to [0, 1]. */
export function ramp(stops: readonly string[], t: number): string {
  const x = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0)) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x));
  const f = x - i;
  const a = hex(stops[i]);
  const b = hex(stops[i + 1]);
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

export const YLGNBU = ["#ffffd9", "#edf8b1", "#c7e9b4", "#7fcdbb", "#41b6c4", "#1d91c0", "#225ea8", "#253494", "#081d58"] as const;
export const YLORRD = ["#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"] as const;
export const PURPLES = ["#fcfbfd", "#efedf5", "#dadaeb", "#bcbddc", "#9e9ac8", "#807dba", "#6a51a3", "#54278f", "#3f007d"] as const;

export const cssGradient = (stops: readonly string[]) => `linear-gradient(90deg, ${stops.join(", ")})`;

/** EJ criteria categories. Colours deliberately match Figure 1B of the paper. */
export const EJ_CATEGORIES = [
  { key: "Minority", color: "#4575b4" },
  { key: "Minority and income", color: "#f28e2b" },
  { key: "Minority, income and English isolation", color: "#b2182b" },
  { key: "Minority and English isolation", color: "#59a14f" },
  { key: "Income", color: "#9467bd" },
  { key: "Not EJ-designated", color: "#c9c9c9" },
] as const;

export const EJ_COLOR: Record<string, string> = Object.fromEntries(EJ_CATEGORIES.map((c) => [c.key, c.color]));
