import { useMemo } from "react";
import { blockGroups, MA_MEDIAN_INCOME, type BlockGroup } from "../data";
import { EJ_CATEGORIES, EJ_COLOR } from "../lib/colors";
import { median } from "../lib/analysis";

const W = 680;
const H = 420;
const M = { l: 58, r: 18, t: 16, b: 50 };
const X0 = Math.log10(50);
const X1 = Math.log10(8000);
const Y0 = 20_000;
const Y1 = 190_000;
const sx = (d: number) => M.l + ((Math.log10(Math.max(50, d)) - X0) / (X1 - X0)) * (W - M.l - M.r);
const sy = (v: number) => H - M.b - ((v - Y0) / (Y1 - Y0)) * (H - M.t - M.b);

const X_TICKS = [100, 250, 500, 1000, 2000, 4000, 8000];
const Y_TICKS = [20_000, 60_000, 100_000, 140_000, 180_000];

interface Props {
  radius: number;
  hoveredId: string | null;
  pinnedId: string | null;
  activeBand: string | null;
  onHover: (id: string | null) => void;
  onPin: (id: string | null) => void;
}

export function Scatter({ radius, hoveredId, pinnedId, activeBand, onHover, onPin }: Props) {
  const pts = useMemo(() => blockGroups.filter((b): b is BlockGroup & { income: number; distM: number } => b.income !== null && b.distM !== null), []);

  // Octile medians (equal-count bins by distance), as in Figure 1C.
  const trend = useMemo(() => {
    const s = [...pts].sort((a, b) => a.distM - b.distM);
    const n = 8;
    const out: { x: number; y: number }[] = [];
    for (let i = 0; i < n; i++) {
      const g = s.slice(Math.floor((i * s.length) / n), Math.floor(((i + 1) * s.length) / n));
      out.push({ x: median(g.map((b) => b.distM)) as number, y: median(g.map((b) => b.income)) as number });
    }
    return out;
  }, [pts]);

  const focus = hoveredId ?? pinnedId;

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Scatter plot of tract median income against block-group distance to Route 9 on a log axis. Income rises with distance." className="block h-auto w-full" onPointerLeave={() => onHover(null)}>
        {/* grid */}
        <g stroke="#e6e2d8" strokeWidth={1}>
          {Y_TICKS.map((t) => (
            <line key={t} x1={M.l} x2={W - M.r} y1={sy(t)} y2={sy(t)} />
          ))}
          {X_TICKS.map((t) => (
            <line key={t} x1={sx(t)} x2={sx(t)} y1={M.t} y2={H - M.b} strokeDasharray="2 4" />
          ))}
        </g>
        <g fontSize={11} fill="#667085" fontFamily="Inter Variable, sans-serif">
          {Y_TICKS.map((t) => (
            <text key={t} x={M.l - 8} y={sy(t) + 4} textAnchor="end">
              ${t / 1000}k
            </text>
          ))}
          {X_TICKS.map((t) => (
            <text key={t} x={sx(t)} y={H - M.b + 18} textAnchor="middle">
              {t >= 1000 ? `${t / 1000} km` : `${t} m`}
            </text>
          ))}
          <text x={(M.l + W - M.r) / 2} y={H - 8} textAnchor="middle" fontSize={12} fill="#344054" fontWeight={600}>
            Distance from block-group centroid to Route 9 (log scale)
          </text>
          <text transform={`translate(14 ${(M.t + H - M.b) / 2}) rotate(-90)`} textAnchor="middle" fontSize={12} fill="#344054" fontWeight={600}>
            Tract median household income
          </text>
        </g>

        {/* statewide median */}
        <line x1={M.l} x2={W - M.r} y1={sy(MA_MEDIAN_INCOME)} y2={sy(MA_MEDIAN_INCOME)} stroke="#667085" strokeDasharray="1 4" strokeWidth={1.5} />
        <text x={M.l + 6} y={sy(MA_MEDIAN_INCOME) - 6} textAnchor="start" fontSize={11} fill="#667085" fontFamily="Inter Variable, sans-serif">
          MA median $103,960
        </text>

        {/* corridor radius */}
        <rect x={M.l} y={M.t} width={Math.max(0, sx(radius) - M.l)} height={H - M.t - M.b} fill="#c0001a" opacity={0.045} />
        <line x1={sx(radius)} x2={sx(radius)} y1={M.t} y2={H - M.b} stroke="#c0001a" strokeWidth={1.5} strokeDasharray="5 4" />
        <text x={sx(radius) + 6} y={M.t + 12} fontSize={11} fill="#c0001a" fontWeight={600} fontFamily="Inter Variable, sans-serif">
          corridor ≤ {radius >= 1000 ? `${+(radius / 1000).toFixed(2)} km` : `${radius} m`}
        </text>

        {/* points */}
        <g>
          {pts.map((b) => {
            const dim = activeBand !== null && b.band !== activeBand;
            const isFocus = focus === b.id;
            return (
              <circle
                key={b.id}
                cx={sx(b.distM)}
                cy={sy(b.income)}
                r={isFocus ? 7 : 4.6}
                fill={EJ_COLOR[b.ejDesc]}
                fillOpacity={dim ? 0.12 : 0.78}
                stroke={b.hotspot ? "#0f1b2d" : "#fff"}
                strokeWidth={b.hotspot ? 1.6 : 0.8}
                strokeOpacity={dim ? 0.2 : 1}
                style={{ cursor: "pointer" }}
                onPointerEnter={() => onHover(b.id)}
                onClick={() => onPin(pinnedId === b.id ? null : b.id)}
              />
            );
          })}
        </g>

        {/* octile medians */}
        <polyline points={trend.map((p) => `${sx(p.x)},${sy(p.y)}`).join(" ")} fill="none" stroke="#0f1b2d" strokeWidth={2.4} strokeLinejoin="round" pointerEvents="none" />
        {trend.map((p, i) => (
          <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={3.6} fill="#0f1b2d" stroke="#fff" strokeWidth={1.2} pointerEvents="none" />
        ))}
        {focus && (() => {
          const b = pts.find((p) => p.id === focus);
          return b ? <circle cx={sx(b.distM)} cy={sy(b.income)} r={9} fill="none" stroke="#0f1b2d" strokeWidth={2} pointerEvents="none" /> : null;
        })()}
      </svg>

      <ul className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[0.75rem] text-ink-2">
        {EJ_CATEGORIES.map((c) => (
          <li key={c.key} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
            {c.key}
          </li>
        ))}
        <li className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-5 bg-ink" /> Octile median
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-white ring-2 ring-ink" /> Hotspot
        </li>
      </ul>
    </div>
  );
}
