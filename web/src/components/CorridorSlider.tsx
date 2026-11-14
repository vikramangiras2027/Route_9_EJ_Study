import { useMemo } from "react";
import { corridorCompare, headline } from "../lib/analysis";
import { fmtInt, fmtUsd } from "../lib/format";
import { Bar } from "./ui";

const PRESETS = [500, 1000, 1500, 2000, 3000];
const label = (m: number) => (m >= 1000 ? `${+(m / 1000).toFixed(2)} km` : `${m} m`);

export function CorridorSlider({ radius, onChange }: { radius: number; onChange: (r: number) => void }) {
  const c = useMemo(() => corridorCompare(radius), [radius]);
  const gap = c.incomeIn !== null && c.incomeOut !== null ? c.incomeIn - c.incomeOut : null;

  return (
    <div>
      <div className="flex items-end justify-between gap-3">
        <label htmlFor="corridor-radius" className="text-sm font-semibold text-ink">
          Corridor definition: centroid within{" "}
          <span className="rounded bg-route-soft px-1.5 py-0.5 font-bold text-route tabular">{label(radius)}</span> of Route 9
        </label>
      </div>
      <input
        id="corridor-radius"
        type="range"
        min={250}
        max={4000}
        step={50}
        value={radius}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full bg-rule accent-route"
        aria-valuetext={label(radius)}
      />
      <div className="mt-3 flex flex-wrap gap-2">
        {PRESETS.map((p) => (
          <button key={p} type="button" className="chip" aria-pressed={radius === p} onClick={() => onChange(p)}>
            {label(p)}
            {p === 1500 && <span className="text-[0.65rem] opacity-70">· paper</span>}
          </button>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 text-sm">
        {[
          { title: "Inside corridor", n: c.nIn, ej: c.pctEjIn, inc: c.incomeIn, color: "#c0001a" },
          { title: "Rest of the two towns", n: c.nOut, ej: c.pctEjOut, inc: c.incomeOut, color: "#1d3a6b" },
        ].map((col) => (
          <div key={col.title} className="rounded-lg border border-rule p-3.5">
            <p className="mb-2.5 text-[0.7rem] font-semibold uppercase tracking-wider text-ink-3">{col.title}</p>
            <p className="font-serif text-2xl font-semibold text-ink tabular">{col.n}</p>
            <p className="mb-3 text-[0.72rem] text-ink-3">block groups</p>
            <div className="mb-3">
              <div className="mb-1 flex justify-between text-[0.75rem]">
                <span className="text-ink-2">EJ-designated</span>
                <span className="font-semibold text-ink tabular">{col.ej.toFixed(1)}%</span>
              </div>
              <Bar value={col.ej} max={100} color={col.color} height={8} />
            </div>
            <div>
              <div className="mb-1 flex justify-between text-[0.75rem]">
                <span className="text-ink-2">Median income</span>
                <span className="font-semibold text-ink tabular">{fmtUsd(col.inc)}</span>
              </div>
              <Bar value={col.inc ?? 0} max={120_000} color={col.color} height={8} />
            </div>
          </div>
        ))}
      </div>

      <p className="mt-4 rounded-lg bg-paper px-3.5 py-3 text-[0.82rem] leading-relaxed text-ink-2" aria-live="polite">
        {gap !== null && (
          <>
            At <b>{label(radius)}</b> the corridor&rsquo;s median income is{" "}
            <b className={gap < 0 ? "text-route" : "text-teal"}>
              {gap < 0 ? "−" : "+"}
              {fmtUsd(Math.abs(gap))}
            </b>{" "}
            {gap < 0 ? "below" : "above"} the rest. The gap stays negative and statistically significant (Mann-Whitney p &lt; 0.001) at every radius from 500 m to 3 km tested in the paper, so
            the finding does not hinge on the corridor definition.
          </>
        )}
      </p>

    </div>
  );
}

/** Estimated EJ-designated residents living within 300 m / 500 m / 1 km of Route 9. */
export function NearRoadResidents() {
  return (
    <div>
      <p className="eyebrow mb-3 !text-ink-3">Estimated EJ residents near the road</p>
      <div className="grid grid-cols-3 gap-3">
        {[
          { d: "300 m", v: headline.ejPop300 },
          { d: "500 m", v: headline.ejPop500 },
          { d: "1 km", v: headline.ejPop1000 },
        ].map((t) => (
          <div key={t.d} className="rounded-lg border border-rule p-3">
            <p className="font-serif text-2xl font-semibold leading-none text-ink tabular">{fmtInt(t.v)}</p>
            <p className="mt-1.5 text-[0.72rem] leading-snug text-ink-3">
              within {t.d}
              <br />
              <b className="text-ink-2">{((100 * t.v) / headline.ejPopTotal).toFixed(1)}%</b> of EJ residents
            </p>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[0.7rem] leading-snug text-ink-3">Areal interpolation assuming uniform density within each block group; shares are of {fmtInt(headline.ejPopTotal)} EJ residents in Worcester and Shrewsbury.</p>
    </div>
  );
}
