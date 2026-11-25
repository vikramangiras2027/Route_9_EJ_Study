import { headline, priorityHeadline } from "../lib/analysis";
import { blockGroups } from "../data";
import { fmtInt, fmtUsd } from "../lib/format";
import { TRAFFIC_BY_TOWN, WORCESTER_EQUITY, WORCESTER_DISTANCE, VULNERABILITY, PM25_NEAREST } from "../data/corridor";
import { Callout, Section } from "./ui";

const tWorc = TRAFFIC_BY_TOWN.find((t) => t.town === "Worcester")!;
const tShrews = TRAFFIC_BY_TOWN.find((t) => t.town === "Shrewsbury")!;
const tPooled = TRAFFIC_BY_TOWN.find((t) => t.town === "Pooled")!;

type Strength = "Strong association" | "Moderate association" | "Descriptive" | "Index-based" | "Regional context";

const STRENGTH_STYLE: Record<Strength, string> = {
  "Strong association": "bg-emerald-50 text-emerald-800 ring-emerald-600/20",
  "Moderate association": "bg-amber-soft text-amber ring-amber/25",
  Descriptive: "bg-sky-soft text-navy-2 ring-navy-2/20",
  "Index-based": "bg-violet-50 text-violet-800 ring-violet-600/20",
  "Regional context": "bg-slate-100 text-slate-700 ring-slate-500/20",
};

const FINDINGS: { title: string; body: React.ReactNode; strength: Strength }[] = [
  {
    title: "Route 9's traffic is measured, and it is uneven",
    strength: "Descriptive",
    body: (
      <>
        MassDOT segment counts cover the whole {tPooled.km} km corridor: <b>{fmtInt(tWorc.meanAadt)}</b> veh/day average in Worcester vs <b>{fmtInt(tShrews.meanAadt)}</b> in Shrewsbury (range{" "}
        {fmtInt(tPooled.minAadt)}&ndash;{fmtInt(tPooled.maxAadt)}; {tPooled.pctAbove30k}% of the corridor carries 30,000+). The old one-station figure (28,112) misstated both ends.
      </>
    ),
  },
  {
    title: "EJ designation is high everywhere, and highest on the corridor",
    strength: "Moderate association",
    body: (
      <>
        90% of block groups in the two towns are EJ-designated (vs 36% in the rest of the county and 51% statewide).{" "}
        <b>{headline.corridorEjRate.toFixed(1)}%</b> of corridor block groups are designated vs {headline.elsewhereEjRate.toFixed(1)}% elsewhere (odds ratio 5.1, Fisher p = 0.009). High everywhere, with only a suggestive, not conclusive, edge nearer the road.
      </>
    ),
  },
  {
    title: "Household income rises with distance from the road",
    strength: "Strong association",
    body: (
      <>
        Spearman ρ = <b>+0.47</b> pooled (p &lt; 0.001; tract-cluster bootstrap 95% CI 0.20&ndash;0.66), equivalent to <b>+${fmtInt(headline.incomeSlopePerKm)}</b> per km. In Worcester alone, the primary tract-level result is ρ = <b>+{WORCESTER_DISTANCE.tract.rho.toFixed(2)}</b> (CI {WORCESTER_DISTANCE.tract.ciLo.toFixed(2)}&ndash;{WORCESTER_DISTANCE.tract.ciHi.toFixed(2)}, n = {WORCESTER_DISTANCE.tract.n} tracts); with town effects the slope is +${fmtInt(WORCESTER_DISTANCE.feSlopePerKm.value)}/km. Not just the Worcester&ndash;Shrewsbury town divide.
      </>
    ),
  },
  {
    title: "Worcester is the equity story: a $26,000 household-weighted income gap",
    strength: "Strong association",
    body: (
      <>
        Household-weighted pooled median income is <b>{fmtUsd(WORCESTER_EQUITY.corridor.medianIncome)}</b> inside the Worcester corridor vs <b>{fmtUsd(WORCESTER_EQUITY.rest.medianIncome)}</b> in the rest of the city, and {WORCESTER_EQUITY.corridor.pctUnder50k}% of corridor households earn under $50k ({WORCESTER_EQUITY.rest.pctUnder50k}% elsewhere). The corridor median is about half the statewide median ($103,960). Shrewsbury is reported as a sensitivity check, not the headline: it has the heaviest traffic but far fewer low-income corridor neighbors.
      </>
    ),
  },
  {
    title: "27 neighborhoods stand out on vulnerability alone, no traffic involved",
    strength: "Index-based",
    body: (
      <>
        <b>{priorityHeadline.n}</b> corridor block groups &mdash; all in Worcester &mdash; rank in the top vulnerability quintile using only low income and EJ criteria, housing {fmtInt(priorityHeadline.ejResidents)} EJ residents. This is the primary screening list. The older cumulative burden index (which folds in modelled traffic) flagged {VULNERABILITY.legacyCbiHotspots.n} block groups; because its traffic term is itself a function of distance, its correlation with distance (ρ = {VULNERABILITY.rhoWithDistance.legacyCbi}) is partly by construction, vs {VULNERABILITY.rhoWithDistance.vulnerability} for the traffic-independent score.
      </>
    ),
  },
  {
    title: "PM2.5 is regionally elevated in summer, not corridor-specific",
    strength: "Regional context",
    body: (
      <>
        2025 mean <b>5.65 µg/m³</b>, peak <b>33.5</b>. No day exceeded the federal 24-hour standard (35), but 23 site-days topped the WHO 24-hour guideline (15), all in June&ndash;August. The nearest monitor ({PM25_NEAREST.site}) sits {PM25_NEAREST.kmFromRoute9} km from Route 9 &mdash; an urban-background site, not a near-road one &mdash; and the two monitors 23 km apart move together (ρ = 0.95): these are regional episodes these data cannot attribute to Route 9.
      </>
    ),
  },
];

export function Summary() {
  return (
    <Section
      id="summary"
      eyebrow="Executive summary"
      title="Who lives closest to Route 9, and what burdens do they share?"
      intro={
        <>
          Environmental justice research asks whether the costs of infrastructure fall disproportionately on some communities. This study pairs measured MassDOT traffic
          counts along the whole corridor with Census, state EJ and EPA air-quality data to test that question, with Worcester as the primary case and Shrewsbury as a
          sensitivity check.
        </>
      }
    >
      <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
        <ol className="space-y-4">
          {FINDINGS.map((f, i) => (
            <li key={f.title} className="card flex gap-4 p-5 sm:gap-5 sm:p-6">
              <span className="font-serif text-3xl font-semibold leading-none text-route/80 tabular">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-serif text-[1.2rem] font-semibold leading-snug text-ink">{f.title}</h3>
                </div>
                <span className={`mt-2 inline-block rounded-full px-2.5 py-0.5 text-[0.7rem] font-semibold ring-1 ${STRENGTH_STYLE[f.strength]}`}>{f.strength}</span>
                <p className="mt-2.5 text-[0.95rem] leading-relaxed text-ink-2">{f.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <Callout tone="caution" title="What this study does not show">
            <ul className="mt-1 list-disc space-y-1 pl-4">
              <li>Individual exposure or health outcomes: all results are neighborhood-level associations.</li>
              <li>Pollution or noise at the roadside: traffic on Route 9 itself is measured, but exposure at a given home is still <i>modelled</i> by distance decay, not measured.</li>
              <li>Air quality on Route 9: PM2.5 comes from two county monitors, both away from the road; it cannot be localized to the corridor.</li>
              <li>Causation. Route 9 may follow, rather than create, patterns of lower-income housing.</li>
            </ul>
          </Callout>
          <div className="card p-5">
            <p className="eyebrow mb-3">Study at a glance</p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              {[
                ["Block groups", String(headline.nBlockGroups)],
                ["Census tracts", String(new Set(blockGroups.map((b) => b.tract)).size)],
                ["EJ residents", fmtInt(headline.ejPopTotal)],
                ["Corridor", "≤ 1.5 km"],
                ["PM2.5 monitors", "2 (705 site-days)"],
                ["Spatial layer", "TIGER 2024"],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-[0.72rem] uppercase tracking-wider text-ink-3">{k}</dt>
                  <dd className="font-semibold text-ink tabular">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
        </aside>
      </div>
    </Section>
  );
}
