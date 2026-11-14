import { memo, useMemo } from "react";
import { blockGroups, byId, geometry, type BlockGroup } from "../data";
import { EJ_CATEGORIES, EJ_COLOR, YLGNBU, YLORRD, cssGradient, ramp } from "../lib/colors";

export type MapMetric = "income" | "ej" | "exposure" | "cbi";

export const MAP_METRICS: { key: MapMetric; label: string }[] = [
  { key: "income", label: "Household income" },
  { key: "ej", label: "EJ criteria" },
  { key: "exposure", label: "Traffic exposure" },
  { key: "cbi", label: "Cumulative burden" },
];

/* ---------- static projection (equirectangular, cos-latitude corrected) ---------- */
const [minLon, minLat, maxLon, maxLat] = geometry.bbox;
const midLat = (minLat + maxLat) / 2;
const kx = Math.cos((midLat * Math.PI) / 180);
const W = 1000;
const PAD = 14;
const spanX = (maxLon - minLon) * kx;
const spanY = maxLat - minLat;
const SCALE = (W - PAD * 2) / spanX;
const H = Math.round(spanY * SCALE + PAD * 2);
const px = (lon: number, lat: number): [number, number] => [PAD + (lon - minLon) * kx * SCALE, PAD + (maxLat - lat) * SCALE];
const f1 = (n: number) => Math.round(n * 10) / 10;
const ringD = (ring: number[][]) => ring.map((p, i) => `${i ? "L" : "M"}${f1(px(p[0], p[1])[0])},${f1(px(p[0], p[1])[1])}`).join("") + "Z";
const polyD = (g: GeoJSON.Polygon | GeoJSON.MultiPolygon) =>
  (g.type === "Polygon" ? [g.coordinates] : g.coordinates).map((poly) => poly.map(ringD).join("")).join("");
const lineD = (lines: number[][][]) =>
  lines.map((l) => l.map((p, i) => `${i ? "L" : "M"}${f1(px(p[0], p[1])[0])},${f1(px(p[0], p[1])[1])}`).join("")).join("");

const PATHS = geometry.blockGroups.features.map((f) => ({ id: f.properties.id, d: polyD(f.geometry) }));
const ROUTE_D = lineD(geometry.route9.coordinates);
const TOWN_D = geometry.towns.features.map((f) => ({ name: f.properties.name, d: polyD(f.geometry) }));
// Town labels sit at the mean block-group centroid of each town, nudged north so they clear Route 9.
const townCentre = (town: string) => {
  const g = blockGroups.filter((b) => b.town === town && b.lat !== null && b.lon !== null);
  return { lon: g.reduce((s, b) => s + (b.lon as number), 0) / g.length, lat: g.reduce((s, b) => s + (b.lat as number), 0) / g.length };
};
const LABELS = [
  { text: "WORCESTER", ...townCentre("Worcester"), dy: -70 },
  { text: "SHREWSBURY", ...townCentre("Shrewsbury"), dy: -55 },
].map((l) => {
  const [x, y] = px(l.lon, l.lat);
  return { text: l.text, xy: [x, y + l.dy] as [number, number] };
});
// "ROUTE 9" label: the centreline point closest to 86% of the map width (east of Worcester's core), lifted above the line.
const ROUTE_LABEL = (() => {
  const target = PAD + 0.86 * (W - PAD * 2);
  let best: [number, number] = [0, 0];
  let bestDx = Infinity;
  for (const line of geometry.route9.coordinates) {
    for (const p of line) {
      const [x, y] = px(p[0], p[1]);
      if (Math.abs(x - target) < bestDx) {
        bestDx = Math.abs(x - target);
        best = [x, y];
      }
    }
  }
  return { x: best[0], y: best[1] - 14 };
})();
// Scale bar: 5 km
const KM_PER_PX = 111.2 / SCALE;
const SCALEBAR_PX = 5 / KM_PER_PX;

/* ---------- colour logic ---------- */
const INC_LO = 25_000;
const INC_HI = 160_000;
const EXP_MAX = Math.log10(1 + 22_000);

export function fillFor(bg: BlockGroup, metric: MapMetric): string {
  switch (metric) {
    case "income":
      return bg.income === null ? "url(#nodata)" : ramp(YLGNBU, (bg.income - INC_LO) / (INC_HI - INC_LO));
    case "ej":
      return EJ_COLOR[bg.ejDesc] ?? "#ccc";
    case "exposure":
      return bg.exposure === null ? "url(#nodata)" : ramp(YLORRD, Math.log10(1 + bg.exposure) / EXP_MAX);
    case "cbi":
      return bg.cbi === null ? "url(#nodata)" : ramp(YLORRD, bg.cbi / 100);
  }
}

export function MapLegend({ metric }: { metric: MapMetric }) {
  if (metric === "ej") {
    return (
      <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[0.75rem] text-ink-2">
        {EJ_CATEGORIES.map((c) => (
          <li key={c.key} className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-[3px]" style={{ background: c.color }} />
            {c.key}
          </li>
        ))}
      </ul>
    );
  }
  const cfg = {
    income: { stops: YLGNBU, lo: "$25k", hi: "$160k+", title: "ACS 2024 tract median household income" },
    exposure: { stops: YLORRD, lo: "0", hi: "22k", title: "Modelled traffic exposure (AADT-equivalent veh/day, log scale)" },
    cbi: { stops: YLORRD, lo: "0", hi: "100", title: "Cumulative burden index (0–100)" },
  }[metric];
  return (
    <div className="max-w-sm">
      <div className="mb-1 text-[0.75rem] text-ink-2">{cfg.title}</div>
      <div className="h-2.5 w-full rounded-full ring-1 ring-black/10" style={{ background: cssGradient(cfg.stops) }} />
      <div className="mt-1 flex justify-between text-[0.7rem] text-ink-3 tabular">
        <span>{cfg.lo}</span>
        <span>{cfg.hi}</span>
      </div>
    </div>
  );
}

interface Props {
  metric: MapMetric;
  activeBand?: string | null;
  hoveredId?: string | null;
  pinnedId?: string | null;
  onHover?: (id: string | null) => void;
  onPin?: (id: string | null) => void;
  showHotspots?: boolean;
  interactive?: boolean;
  className?: string;
  ariaLabel?: string;
}

function CorridorMapImpl({
  metric,
  activeBand = null,
  hoveredId = null,
  pinnedId = null,
  onHover,
  onPin,
  showHotspots = true,
  interactive = true,
  className = "",
  ariaLabel = "Map of block groups in Worcester and Shrewsbury shaded by the selected metric, with Route 9 in red",
}: Props) {
  const fills = useMemo(() => {
    const m = new Map<string, string>();
    for (const p of PATHS) m.set(p.id, fillFor(byId.get(p.id) as BlockGroup, metric));
    return m;
  }, [metric]);

  const hotspotPaths = useMemo(() => PATHS.filter((p) => byId.get(p.id)?.hotspot), []);
  const focusId = hoveredId ?? pinnedId;
  const focusPath = focusId ? PATHS.find((p) => p.id === focusId) : undefined;
  const pinnedPath = pinnedId && pinnedId !== focusId ? PATHS.find((p) => p.id === pinnedId) : undefined;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={ariaLabel}
      className={`block h-auto w-full select-none ${className}`}
      onPointerLeave={() => interactive && onHover?.(null)}
    >
      <defs>
        <pattern id="nodata" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="6" height="6" fill="#f2f0ea" />
          <line x1="0" y1="0" x2="0" y2="6" stroke="#c9c5b8" strokeWidth="2" />
        </pattern>
      </defs>

      <g strokeLinejoin="round">
        {PATHS.map((p) => {
          const bg = byId.get(p.id) as BlockGroup;
          const dimmed = activeBand !== null && bg.band !== activeBand;
          return (
            <path
              key={p.id}
              d={p.d}
              fill={fills.get(p.id)}
              fillRule="evenodd"
              stroke="#ffffff"
              strokeWidth={0.7}
              opacity={dimmed ? 0.16 : 1}
              style={{ transition: "opacity 160ms ease", cursor: interactive ? "pointer" : "default" }}
              {...(interactive
                ? {
                    tabIndex: 0,
                    role: "button",
                    "aria-label": `Block group ${bg.bg}, tract ${bg.tract}, ${bg.town}. ${bg.ejDesc}.`,
                    onPointerEnter: () => onHover?.(p.id),
                    onFocus: () => onHover?.(p.id),
                    onBlur: () => onHover?.(null),
                    onClick: () => onPin?.(pinnedId === p.id ? null : p.id),
                    onKeyDown: (e: React.KeyboardEvent) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onPin?.(pinnedId === p.id ? null : p.id);
                      }
                    },
                  }
                : { "aria-hidden": true })}
            />
          );
        })}
      </g>

      {/* town outlines */}
      <g fill="none" stroke="#0f1b2d" strokeOpacity={0.55} strokeWidth={1.3} pointerEvents="none">
        {TOWN_D.map((t) => (
          <path key={t.name} d={t.d} fillRule="evenodd" />
        ))}
      </g>

      {/* hotspot outlines */}
      {showHotspots && (
        <g fill="none" stroke="#0f1b2d" strokeWidth={2.2} strokeLinejoin="round" pointerEvents="none">
          {hotspotPaths.map((p) => (
            <path
              key={p.id}
              d={p.d}
              fillRule="evenodd"
              opacity={activeBand !== null && byId.get(p.id)?.band !== activeBand ? 0.15 : 1}
            />
          ))}
        </g>
      )}

      {/* Route 9 */}
      <path d={ROUTE_D} fill="none" stroke="#fff" strokeWidth={7} strokeLinecap="round" strokeLinejoin="round" pointerEvents="none" />
      <path d={ROUTE_D} fill="none" stroke="#c0001a" strokeWidth={3.6} strokeLinecap="round" strokeLinejoin="round" pointerEvents="none" />

      {pinnedPath && (
        <path d={pinnedPath.d} fill="none" stroke="#c0001a" strokeWidth={2.4} strokeDasharray="6 4" fillRule="evenodd" pointerEvents="none" />
      )}
      {focusPath && <path d={focusPath.d} fill="none" stroke="#0f1b2d" strokeWidth={3.2} fillRule="evenodd" pointerEvents="none" />}

      {/* labels */}
      <g pointerEvents="none" fontFamily="Inter Variable, sans-serif" fontSize={15} fontWeight={700} letterSpacing={2.5} textAnchor="middle">
        {LABELS.map((l) => (
          <text key={l.text} x={l.xy[0]} y={l.xy[1]} fill="#0f1b2d" stroke="#fff" strokeWidth={4} paintOrder="stroke" opacity={0.75}>
            {l.text}
          </text>
        ))}
        <text x={ROUTE_LABEL.x} y={ROUTE_LABEL.y} fill="#c0001a" stroke="#fff" strokeWidth={4} paintOrder="stroke" fontSize={13} letterSpacing={1}>
          ROUTE 9
        </text>
      </g>

      {/* scale bar + north arrow */}
      <g pointerEvents="none" fontFamily="Inter Variable, sans-serif" fontSize={13} fill="#0f1b2d">
        <g transform={`translate(${PAD + 6}, ${H - 26})`}>
          <rect x={-4} y={-14} width={SCALEBAR_PX + 44} height={34} rx={6} fill="#fff" opacity={0.85} />
          <line x1={0} y1={0} x2={SCALEBAR_PX} y2={0} stroke="#0f1b2d" strokeWidth={3} />
          <line x1={0} y1={-5} x2={0} y2={5} stroke="#0f1b2d" strokeWidth={2} />
          <line x1={SCALEBAR_PX} y1={-5} x2={SCALEBAR_PX} y2={5} stroke="#0f1b2d" strokeWidth={2} />
          <text x={SCALEBAR_PX + 8} y={4}>
            5 km
          </text>
        </g>
        <g transform={`translate(${W - PAD - 22}, ${PAD + 26})`} textAnchor="middle">
          <path d="M0,-18 L7,4 L0,0 L-7,4 Z" fill="#0f1b2d" />
          <text y={22} fontWeight={700}>
            N
          </text>
        </g>
      </g>
    </svg>
  );
}

export const CorridorMap = memo(CorridorMapImpl);
