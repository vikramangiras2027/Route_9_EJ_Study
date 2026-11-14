import { Activity, CalendarRange, ShieldCheck, Wind } from "lucide-react";
import { LINKS } from "../config";
import { BENCHMARKS, EXCEEDANCES, MONITORS, MONTHS, PM_ALL, TOP_DAYS, WHO_EXCEED_BY_MONTH } from "../data/airQuality";
import { Callout, FigureCard, Section } from "./ui";

const AXIS_MAX = 40;

/** Observed value vs. regulatory/health benchmarks on a shared 0–40 µg/m³ axis. */
function BenchmarkBars() {
  const W = 540;
  const L = 140;
  const R = 16;
  const x = (v: number) => L + (v / AXIS_MAX) * (W - L - R);
  const rows = [
    {
      label: "Annual mean",
      sub: "2025, both monitors",
      value: PM_ALL.mean,
      marks: [
        { v: BENCHMARKS.whoAnnual, name: "WHO 5", color: "#0f766e" },
        { v: BENCHMARKS.naaqsAnnual, name: "EPA 9", color: "#14284b" },
      ],
    },
    {
      label: "98th percentile day",
      sub: "daily mean PM2.5",
      value: PM_ALL.p98,
      marks: [
        { v: BENCHMARKS.whoDaily, name: "WHO 15", color: "#0f766e" },
        { v: BENCHMARKS.naaqsDaily, name: "EPA 35", color: "#14284b" },
      ],
    },
    {
      label: "Worst day",
      sub: `${PM_ALL.maxDate}, ${PM_ALL.maxSite}`,
      value: PM_ALL.max,
      marks: [
        { v: BENCHMARKS.whoDaily, name: "WHO 15", color: "#0f766e" },
        { v: BENCHMARKS.naaqsDaily, name: "EPA 35", color: "#14284b" },
      ],
    },
  ];
  const rowH = 84;
  const H = rows.length * rowH + 44;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label="Bar chart comparing observed PM2.5 statistics with WHO and EPA benchmarks. The annual mean of 5.65 exceeds the WHO guideline of 5 but is below the EPA standard of 9. The worst day of 33.5 exceeds the WHO 24-hour guideline of 15 but is below the EPA standard of 35.">
      <g fontFamily="Inter Variable, sans-serif">
        {[0, 10, 20, 30, 40].map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={6} y2={H - 30} stroke="#e6e2d8" />
            <text x={x(t)} y={H - 12} textAnchor="middle" fontSize={11} fill="#667085">
              {t}
            </text>
          </g>
        ))}
        <text x={(L + W - R) / 2} y={H - 0} textAnchor="middle" fontSize={11} fill="#667085">
          Daily-mean or annual-mean PM2.5 (µg/m³)
        </text>
        {rows.map((r, i) => {
          const y = 14 + i * rowH;
          return (
            <g key={r.label}>
              <text x={0} y={y + 22} fontSize={13} fontWeight={600} fill="#0f1b2d">
                {r.label}
              </text>
              <text x={0} y={y + 38} fontSize={10.5} fill="#667085">
                {r.sub}
              </text>
              <rect x={L} y={y + 8} width={x(r.value) - L} height={26} rx={4} fill="#1d3a6b" />
              <text x={x(r.value) - 8} y={y + 26} textAnchor="end" fontSize={13} fontWeight={700} fill="#fff">
                {r.value}
              </text>
              {r.marks.map((m) => (
                <g key={m.name}>
                  <line x1={x(m.v)} x2={x(m.v)} y1={y + 2} y2={y + 44} stroke={m.color} strokeWidth={2.2} strokeDasharray="4 3" />
                  <text x={x(m.v)} y={y + 58} textAnchor="middle" fontSize={10.5} fontWeight={600} fill={m.color}>
                    {m.name}
                  </text>
                </g>
              ))}
            </g>
          );
        })}
      </g>
    </svg>
  );
}

function ExceedanceBars() {
  const W = 420;
  const H = 300;
  const M = { l: 38, r: 6, t: 22, b: 58 };
  const max = 60;
  const gw = (W - M.l - M.r) / EXCEEDANCES.length;
  const bw = gw * 0.32;
  const y = (v: number) => H - M.b - (v / max) * (H - M.t - M.b);
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label="Number of days each monitor exceeded daily PM2.5 thresholds of 9, 12, 15, 25 and 35 micrograms per cubic metre. Zero days exceeded 35.">
        <g fontFamily="Inter Variable, sans-serif" fontSize={11} fill="#667085">
          {[0, 20, 40, 60].map((t) => (
            <g key={t}>
              <line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} stroke="#e6e2d8" />
              <text x={M.l - 8} y={y(t) + 4} textAnchor="end">
                {t}
              </text>
            </g>
          ))}
          {EXCEEDANCES.map((e, i) => {
            const cx = M.l + gw * i + gw / 2;
            return (
              <g key={e.threshold}>
                <rect x={cx - bw - 2} y={y(e.wss)} width={bw} height={Math.max(0, H - M.b - y(e.wss))} rx={3} fill="#1d3a6b" />
                <rect x={cx + 2} y={y(e.uxb)} width={bw} height={Math.max(0, H - M.b - y(e.uxb))} rx={3} fill="#e07b00" />
                <text x={cx - bw / 2 - 2} y={y(e.wss) - 5} textAnchor="middle" fontSize={11} fontWeight={700} fill="#0f1b2d">
                  {e.wss}
                </text>
                <text x={cx + bw / 2 + 2} y={y(e.uxb) - 5} textAnchor="middle" fontSize={11} fontWeight={700} fill="#0f1b2d">
                  {e.uxb}
                </text>
                <text x={cx} y={H - M.b + 18} textAnchor="middle" fontSize={12} fontWeight={600} fill="#0f1b2d">
                  {e.label}
                </text>
                <text x={cx} y={H - M.b + 32} textAnchor="middle" fontSize={9.5}>
                  {e.note}
                </text>
              </g>
            );
          })}
          <text transform={`translate(11 ${(M.t + H - M.b) / 2}) rotate(-90)`} textAnchor="middle" fontSize={11}>
            Days exceeding threshold
          </text>
        </g>
      </svg>
      <div className="mt-1 flex gap-4 text-[0.75rem] text-ink-2">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-[#1d3a6b]" /> Worcester Summer Street</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-[#e07b00]" /> Uxbridge</span>
      </div>
    </div>
  );
}

function MonthlyBars() {
  const max = Math.max(...WHO_EXCEED_BY_MONTH);
  return (
    <div>
      <div className="flex h-52 items-end gap-1.5" role="img" aria-label="WHO 24-hour exceedance site-days by month: June 11, July 7, August 5, all other months zero.">
        {WHO_EXCEED_BY_MONTH.map((v, i) => (
          <div key={MONTHS[i]} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
            <span className="h-4 text-[0.78rem] font-semibold leading-4 text-ink tabular">{v || ""}</span>
            <div className="w-full rounded-t-md" style={{ height: v ? `${(v / max) * 150}px` : "3px", background: v ? "#e07b00" : "#e6e2d8" }} />
            <span className="text-[0.68rem] text-ink-3">{MONTHS[i]}</span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-[0.8rem] leading-relaxed text-ink-3">
        Site-days above the WHO 24-hour guideline (15 µg/m³), both monitors combined. 100% fall in June&ndash;August (14 distinct dates). Monthly means peak in June (9.9) and bottom out in October (3.7).
      </p>
    </div>
  );
}

function Kpi({ icon, value, unit, label, note }: { icon: React.ReactNode; value: string; unit?: string; label: string; note: string }) {
  return (
    <div className="card p-5">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-sky-soft text-navy-2">{icon}</div>
      <div className="flex items-baseline gap-1">
        <span className="font-serif text-4xl font-semibold leading-none text-ink tabular">{value}</span>
        {unit && <span className="text-xs font-medium text-ink-3">{unit}</span>}
      </div>
      <p className="mt-2.5 text-sm font-semibold text-ink">{label}</p>
      <p className="mt-0.5 text-[0.78rem] leading-relaxed text-ink-3">{note}</p>
    </div>
  );
}

export function AirQuality() {
  return (
    <Section
      id="air-quality"
      eyebrow="Air quality & exposure hub"
      title="PM2.5: well within federal limits, above WHO guidelines, and regional in origin"
      intro={
        <>
          Fine particulate matter (PM<sub>2.5</sub>) is the pollutant most closely tied to traffic-related health burdens. The 2025 EPA monitoring record for Worcester County shows summer spikes up to{" "}
          <b>{PM_ALL.max} µg/m³</b>, but the two monitors move in lockstep, so these episodes are regional rather than attributable to Route 9.
        </>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi icon={<Wind className="h-5 w-5" />} value={PM_ALL.mean.toFixed(2)} unit="µg/m³" label="2025 mean, all site-days" note={`Median ${PM_ALL.median}; 95th percentile ${PM_ALL.p95}. WHO annual guideline: ${BENCHMARKS.whoAnnual}.`} />
        <Kpi icon={<Activity className="h-5 w-5" />} value={PM_ALL.max.toFixed(1)} unit="µg/m³" label="Peak daily mean" note={`${PM_ALL.maxDate} at ${PM_ALL.maxSite} (AQI ${PM_ALL.maxAqi}); Worcester recorded 32.9 the same day.`} />
        <Kpi icon={<ShieldCheck className="h-5 w-5" />} value={`${PM_ALL.daysOverNaaqs} / ${PM_ALL.siteDays}`} label="Days above the federal 24-h standard (35)" note="Single-year screen; official compliance uses 3-year design values." />
        <Kpi icon={<CalendarRange className="h-5 w-5" />} value={String(PM_ALL.daysOverWho)} label="Site-days above the WHO 24-h guideline (15)" note={`${PM_ALL.distinctDatesOverWho} distinct dates, 3.3% of site-days, all in June–August.`} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-12">
        <div className="card p-5 sm:p-6 lg:col-span-7">
          <h3 className="font-serif text-xl font-semibold text-ink">Observed levels against benchmarks</h3>
          <p className="mb-4 mt-1 text-[0.88rem] leading-relaxed text-ink-2">
            Dashed lines mark the WHO 2021 guideline (teal, health reference) and the EPA primary standard (navy, regulatory). The annual mean clears the federal limit but not the WHO guideline.
          </p>
          <BenchmarkBars />
        </div>
        <div className="card p-5 sm:p-6 lg:col-span-5">
          <h3 className="font-serif text-xl font-semibold text-ink">How often thresholds were crossed</h3>
          <p className="mb-3 mt-1 text-[0.88rem] leading-relaxed text-ink-2">Days exceeding each daily-mean level, by monitor (values from Figure 2C).</p>
          <ExceedanceBars />
        </div>

        <div className="card p-5 sm:p-6 lg:col-span-5">
          <h3 className="font-serif text-xl font-semibold text-ink">A summer phenomenon</h3>
          <p className="mb-4 mt-1 text-[0.88rem] leading-relaxed text-ink-2">Every WHO-guideline exceedance occurred between June and August.</p>
          <MonthlyBars />
        </div>
        <div className="card overflow-hidden lg:col-span-7">
          <div className="p-5 pb-3 sm:p-6 sm:pb-3">
            <h3 className="font-serif text-xl font-semibold text-ink">Monitors &amp; worst days</h3>
          </div>
          <div className="overflow-x-auto px-5 sm:px-6">
            <table className="w-full min-w-[520px] text-left text-[0.84rem]">
              <thead className="text-[0.68rem] uppercase tracking-wider text-ink-3">
                <tr className="border-b border-rule">
                  <th className="py-2 pr-3 font-semibold">Monitor</th>
                  <th className="px-2 py-2 text-right font-semibold">Days</th>
                  <th className="px-2 py-2 text-right font-semibold">Mean</th>
                  <th className="px-2 py-2 text-right font-semibold">p98</th>
                  <th className="px-2 py-2 text-right font-semibold">Max</th>
                  <th className="py-2 pl-2 text-right font-semibold">Days &gt; WHO 15</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule tabular">
                {MONITORS.map((m) => (
                  <tr key={m.name}>
                    <td className="py-2.5 pr-3 font-medium text-ink">{m.name}</td>
                    <td className="px-2 py-2.5 text-right">{m.days}</td>
                    <td className="px-2 py-2.5 text-right">{m.mean.toFixed(2)}</td>
                    <td className="px-2 py-2.5 text-right">{m.p98.toFixed(1)}</td>
                    <td className="px-2 py-2.5 text-right">{m.max.toFixed(1)}</td>
                    <td className="py-2.5 pl-2 text-right">
                      {m.overWho} <span className="text-ink-3">({m.shareOverWho}%)</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 border-t border-rule bg-paper/60 px-5 py-4 sm:px-6">
            <p className="mb-2 text-[0.68rem] font-semibold uppercase tracking-wider text-ink-3">Five highest site-days</p>
            <ul className="grid gap-y-1.5 text-[0.82rem]">
              {TOP_DAYS.map((d) => (
                <li key={d.date + d.site} className="flex items-baseline justify-between gap-3">
                  <span className="text-ink-2">
                    {d.date} · {d.site}
                  </span>
                  <span className="shrink-0 font-semibold text-ink tabular">
                    {d.pm25} <span className="font-normal text-ink-3">AQI {d.aqi}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Callout tone="caution" title="Why this is context, not a corridor finding">
          The monitors are about {PM_ALL.monitorDistanceKm} km apart and correlate at &rho; = {PM_ALL.agreementRho}, so spikes are synchronous across the county. Every block group is assigned to its nearest monitor
          (median distance 3.2 km), so PM<sub>2.5</sub> cannot differentiate neighborhoods and is <b>not</b> used in the cumulative burden index.
        </Callout>
        <Callout title="How corridor exposure is estimated instead">
          Near-road exposure is modelled as <b>AADT &times; exp(&minus;d / 300 m)</b>, area-averaged over each block group. A true near-road gradient needs local sensors, an obvious extension for future work.
        </Callout>
      </div>

      <div className="mt-12">
        <div className="mb-5 max-w-3xl">
          <p className="eyebrow mb-2">Publication figure</p>
          <h3 className="font-serif text-2xl font-semibold text-ink">Figure 2. Daily PM2.5 distribution and exceedances</h3>
        </div>
        <FigureCard
          src={LINKS.figure2}
          alt="Three-panel figure. A: daily PM2.5 time series at two Worcester County monitors in 2025 with WHO and EPA thresholds and the 33.5 microgram peak on August 5. B: violin and box plots by monitor. C: grouped bars of days exceeding benchmark thresholds."
          title="Figure 2. Daily PM2.5 distribution and exceedances of air-quality standards, Worcester County, MA"
          caption={
            <p>
              (A) Daily mean PM<sub>2.5</sub> at the Worcester Summer Street and Uxbridge monitors, 2025; circled points exceed the WHO 24-hour guideline. (B) Distribution by monitor. (C) Days exceeding benchmark thresholds. Source: EPA AQS daily PM<sub>2.5</sub>. NAAQS compliance is judged on 3-year design values, so this is a single-year screen.
            </p>
          }
          downloadName="figure2_pm25_distribution.png"
        />
      </div>
    </Section>
  );
}
