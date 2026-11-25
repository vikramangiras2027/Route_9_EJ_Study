import { useMemo, useState } from "react";
import { Layers, Route as RouteIcon, X } from "lucide-react";
import { byId } from "../data";
import { LINKS } from "../config";
import { allBandStats, BAND_LABEL, BAND_METRICS, bandStats, type Band } from "../lib/analysis";
import { fmtInt, fmtUsd } from "../lib/format";
import { CorridorMap, MAP_METRICS, MapLegend, type MapMetric } from "./CorridorMap";
import { BlockGroupDetail } from "./BlockGroupDetail";
import { Scatter } from "./Scatter";
import { CorridorSlider, NearRoadResidents } from "./CorridorSlider";
import { HotspotTable } from "./HotspotTable";
import { Bar, Callout, FigureCard, Section } from "./ui";

const BAND_COLORS = ["#7f0000", "#b4361f", "#d9822b", "#5a95b8", "#1d3a6b"];

export function Explorer() {
  const [metric, setMetric] = useState<MapMetric>("income");
  const [bandMetric, setBandMetric] = useState(BAND_METRICS[0].key);
  const [activeBand, setActiveBand] = useState<Band | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [pinnedId, setPinnedId] = useState<string | null>(null);
  const [showHotspots, setShowHotspots] = useState(true);
  const [radius, setRadius] = useState(1500);

  const focusId = hoveredId ?? pinnedId;
  const focusBg = focusId ? (byId.get(focusId) ?? null) : null;
  const m = BAND_METRICS.find((x) => x.key === bandMetric) ?? BAND_METRICS[0];
  const selected = useMemo(() => (activeBand ? bandStats(activeBand) : null), [activeBand]);

  const first = allBandStats[0];
  const last = allBandStats[allBandStats.length - 1];
  const incomeRatio = first.medianIncome && last.medianIncome ? last.medianIncome / first.medianIncome : null;

  return (
    <Section
      id="explorer"
      eyebrow="Interactive map · corridor explorer"
      title="How neighborhoods change moving away from Route 9"
      tone="white"
      intro={
        <>
          Every polygon is a Census block group. Switch the map layer, isolate a distance band, drag the corridor definition, and hover any block group (on the map or in the
          scatter plot) to see its full profile.
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-12">
        {/* ------------------------------ MAP ------------------------------ */}
        <div id="corridor-map" className="card scroll-mt-20 p-4 sm:p-5 lg:col-span-7">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div role="tablist" aria-label="Map layer" className="flex flex-wrap gap-1.5">
              {MAP_METRICS.map((x) => (
                <button key={x.key} role="tab" type="button" className="chip" aria-selected={metric === x.key} onClick={() => setMetric(x.key)}>
                  {x.label}
                </button>
              ))}
            </div>
            <label className="inline-flex cursor-pointer items-center gap-2 text-[0.8rem] font-medium text-ink-2">
              <input type="checkbox" checked={showHotspots} onChange={(e) => setShowHotspots(e.target.checked)} className="h-4 w-4 accent-ink" />
              Outline priority block groups
            </label>
          </div>

          <div className="relative overflow-hidden rounded-lg bg-[#eef3f8] ring-1 ring-rule">
            <CorridorMap
              metric={metric}
              activeBand={activeBand}
              hoveredId={hoveredId}
              pinnedId={pinnedId}
              onHover={setHoveredId}
              onPin={setPinnedId}
              showHotspots={showHotspots}
            />
            {activeBand && (
              <button
                type="button"
                onClick={() => setActiveBand(null)}
                className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-ink px-3 py-1.5 text-xs font-semibold text-white shadow"
              >
                Showing {BAND_LABEL[activeBand]} <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
            <MapLegend metric={metric} />
            <p className="flex items-center gap-1.5 text-[0.75rem] text-ink-3">
              <RouteIcon className="h-3.5 w-3.5 text-route" /> Route 9 (TIGER &ldquo;State Rte 9&rdquo;)
            </p>
          </div>

          <div className="mt-4">
            <BlockGroupDetail bg={focusBg} pinned={!!pinnedId && focusId === pinnedId} />
          </div>
        </div>

        {/* --------------------------- BAND EXPLORER ----------------------- */}
        <div className="card flex flex-col p-5 sm:p-6 lg:col-span-5">
          <div className="mb-1 flex items-center gap-2">
            <Layers className="h-4 w-4 text-route" aria-hidden />
            <h3 className="font-serif text-xl font-semibold text-ink">Distance bands</h3>
          </div>
          <p className="text-[0.88rem] leading-relaxed text-ink-2">
            Block groups grouped by centroid distance to Route 9. Click a band to isolate it on the map and scatter plot.
          </p>

          <div role="tablist" aria-label="Band metric" className="mt-4 flex flex-wrap gap-1.5">
            {BAND_METRICS.map((x) => (
              <button key={x.key} type="button" role="tab" className="chip !px-2.5 !py-1 !text-[0.74rem]" aria-selected={bandMetric === x.key} onClick={() => setBandMetric(x.key)}>
                {x.short}
              </button>
            ))}
          </div>
          <p className="mt-3 text-[0.78rem] font-semibold text-ink">{m.label}</p>
          <p className="mb-3 text-[0.72rem] leading-snug text-ink-3">{m.help}</p>

          <ul className="space-y-2">
            {allBandStats.map((s, i) => {
              const v = m.value(s);
              const on = activeBand === s.band;
              return (
                <li key={s.band}>
                  <button
                    type="button"
                    onClick={() => setActiveBand(on ? null : s.band)}
                    aria-pressed={on}
                    className={`group w-full rounded-lg border px-3 py-2.5 text-left transition-colors ${on ? "border-ink bg-sky-soft" : "border-transparent hover:border-rule-2 hover:bg-paper"}`}
                  >
                    <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
                      <span className="font-semibold text-ink">{BAND_LABEL[s.band]}</span>
                      <span className="tabular font-semibold text-ink">{v === null ? "n/a" : m.format(v)}</span>
                    </div>
                    <Bar value={v ?? 0} max={m.max} color={BAND_COLORS[i]} height={11} />
                    <div className="mt-1 text-[0.7rem] text-ink-3">
                      {s.n} block groups · {s.pctEj.toFixed(0)}% EJ
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="mt-auto pt-5">
            {selected ? (
              <div className="rounded-lg bg-paper p-4 text-sm">
                <p className="mb-2 font-semibold text-ink">{BAND_LABEL[selected.band]} snapshot</p>
                <dl className="grid grid-cols-3 gap-3">
                  <div>
                    <dt className="text-[0.66rem] uppercase tracking-wider text-ink-3">EJ residents</dt>
                    <dd className="font-semibold tabular">{fmtInt(selected.ejResidents)}</dd>
                  </div>
                  <div>
                    <dt className="text-[0.66rem] uppercase tracking-wider text-ink-3">Median income</dt>
                    <dd className="font-semibold tabular">{fmtUsd(selected.medianIncome)}</dd>
                  </div>
                  <div>
                    <dt className="text-[0.66rem] uppercase tracking-wider text-ink-3">Burden index</dt>
                    <dd className="font-semibold tabular">{selected.cbi?.toFixed(1)}</dd>
                  </div>
                </dl>
              </div>
            ) : (
              incomeRatio && (
                <div className="rounded-lg bg-paper p-4">
                  <p className="font-serif text-3xl font-semibold text-ink tabular">{incomeRatio.toFixed(1)}&times;</p>
                  <p className="mt-0.5 text-[0.82rem] leading-snug text-ink-2">
                    Median income in the &gt; 4 km band ({fmtUsd(last.medianIncome)}) vs the &le; 0.5 km band ({fmtUsd(first.medianIncome)}).
                  </p>
                </div>
              )
            )}
          </div>
        </div>

        {/* ----------------------------- SCATTER --------------------------- */}
        <div className="card flex flex-col p-4 sm:p-5 lg:col-span-7">
          <h3 className="font-serif text-xl font-semibold text-ink">Income climbs with distance</h3>
          <p className="mb-3 mt-1 text-[0.88rem] leading-relaxed text-ink-2">
            Each dot is a block group (n = 164 with an income estimate, both towns). The black line traces the median income of eight equal-sized distance groups.
            Spearman &rho; = <b>+0.47</b> pooled, tract-cluster 95% CI [0.20, 0.66] &mdash; Worcester alone, tract level: +0.48, CI [0.17, 0.72] (see Methodology).
          </p>
          <Scatter radius={radius} hoveredId={hoveredId} pinnedId={pinnedId} activeBand={activeBand} onHover={setHoveredId} onPin={setPinnedId} />
          <div className="mt-auto border-t border-rule pt-5">
            <NearRoadResidents />
          </div>
        </div>

        {/* ----------------------------- SLIDER ---------------------------- */}
        <div className="card p-5 sm:p-6 lg:col-span-5">
          <h3 className="mb-1 font-serif text-xl font-semibold text-ink">Test the corridor definition</h3>
          <p className="mb-4 text-[0.88rem] leading-relaxed text-ink-2">
            The paper defines the corridor as block-group centroids within 1.5 km. Move the slider to see whether the conclusions depend on that choice.
          </p>
          <CorridorSlider radius={radius} onChange={setRadius} />
        </div>
      </div>

      <div className="mt-6">
        <HotspotTable
          selectedId={pinnedId}
          onSelect={(id) => {
            setPinnedId(id);
            if (id) document.getElementById("corridor-map")?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
        />
      </div>

      <div className="mt-14">
        <div className="mb-5 max-w-3xl">
          <p className="eyebrow mb-2">Publication figure</p>
          <h3 className="font-serif text-2xl font-semibold text-ink">Figure 1. Measured traffic, income and who lives nearby</h3>
          <p className="mt-2 text-[0.95rem] leading-relaxed text-ink-2">
            The high-resolution figure produced by <code className="rounded bg-paper px-1.5 py-0.5 text-[0.82rem]">route9_deep_analysis.py</code>, exactly as it appears in the report. Click to open at full resolution.
          </p>
        </div>
        <FigureCard
          src={LINKS.figure1}
          alt="Five-panel figure. A: map of Worcester tract income with measured Route 9 AADT and count stations. B: the same for Shrewsbury. C: measured AADT profile along the corridor's milepost. D: Worcester tract income versus distance to Route 9. E: Worcester household income and EJ population, inside vs. beyond 300/500/1000 m buffers."
          title="Figure 1. Measured Route 9 traffic loading and neighbourhood income, Worcester (primary) and Shrewsbury (sensitivity), MA"
          caption={
            <p>
              (A) Worcester tract income with measured Route 9 AADT and count stations. (B) Shrewsbury, same layers, sensitivity. (C) Measured MassDOT segment AADT by milepost, Worcester vs. Shrewsbury, with the old single-station anchor for comparison. (D) Worcester tract income vs. distance (log scale), with quintile medians. (E) Worcester households and EJ residents inside vs. beyond each buffer, with median income and share under $50k.
            </p>
          }
          downloadName="figure1_income_traffic_ej.png"
        />
      </div>

      <div className="mt-14">
        <div className="mb-5 max-w-3xl">
          <p className="eyebrow mb-2">Publication figure</p>
          <h3 className="font-serif text-2xl font-semibold text-ink">Figure 3. Where to look first</h3>
          <p className="mt-2 text-[0.95rem] leading-relaxed text-ink-2">
            The 27 Worcester priority block groups (vulnerability index, no traffic term) ranked and mapped, with the top 15 labelled.
          </p>
        </div>
        <FigureCard
          src={LINKS.figure3}
          alt="Two-panel figure. A: map of Worcester block groups shaded by vulnerability quintile, with the 27 priority block groups outlined and the top 15 numbered, and Route 9 shown at measured AADT. B: horizontal bar chart of the top 15 priority block groups by vulnerability index, with adjacent AADT and EJ residents within 500 m."
          title="Figure 3. Where to look first: vulnerability without traffic, inside the Route 9 corridor"
          caption={
            <p>
              (A) Worcester block groups by vulnerability quintile (low income + EJ criteria, no traffic term); priority block groups (top quintile, in the 1.5 km corridor) outlined. (B) The top 15, ranked, with the adjacent measured AADT and EJ residents within 500 m for context.
            </p>
          }
          downloadName="figure3_priority_hotspots.png"
        />
      </div>

      <div className="mt-8">
        <Callout tone="caution" title="Reading the traffic and vulnerability layers">
          Route 9 traffic itself is <b>measured</b> by MassDOT, segment by segment. Exposure at a given block group is still a <b>model</b> built on that measured AADT, decaying with distance (300 m e-folding); it ignores truck share, grade, lane geometry and wind. The &ldquo;vulnerability&rdquo; layer deliberately has <i>no</i> traffic
          term &mdash; it is income and EJ criteria only &mdash; so its relationship with distance is an observation, not a construction, unlike the legacy burden index.
        </Callout>
      </div>
    </Section>
  );
}
