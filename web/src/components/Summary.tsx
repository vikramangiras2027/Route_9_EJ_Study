import { headline } from "../lib/analysis";
import { blockGroups, traffic } from "../data";
import { fmtInt } from "../lib/format";
import { Callout, Section } from "./ui";

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
    title: "A heavily loaded arterial runs through the study area",
    strength: "Descriptive",
    body: (
      <>
        Route 9 carries <b>{fmtInt(traffic.aadt)}</b> vehicles a day at the MassDOT count station, {(traffic.westboundShare * 100).toFixed(1)}% of it westbound. An estimated{" "}
        <b>{fmtInt(headline.ejPop500)}</b> EJ-designated residents ({((100 * headline.ejPop500) / headline.ejPopTotal).toFixed(1)}%) live within 500 m of the centreline and{" "}
        <b>{fmtInt(headline.ejPop1000)}</b> ({((100 * headline.ejPop1000) / headline.ejPopTotal).toFixed(1)}%) within 1 km.
      </>
    ),
  },
  {
    title: "EJ designation is high everywhere, and highest on the corridor",
    strength: "Moderate association",
    body: (
      <>
        90% of block groups in the two towns are EJ-designated (vs 36% in the rest of the county and 51% statewide).{" "}
        <b>{headline.corridorEjRate.toFixed(1)}%</b> of corridor block groups are designated vs {headline.elsewhereEjRate.toFixed(1)}% elsewhere (odds ratio 5.1, Fisher p = 0.009). The effect is modest and weaker at tract level (ρ = −0.22, p = 0.103).
      </>
    ),
  },
  {
    title: "Household income rises with distance from the road",
    strength: "Strong association",
    body: (
      <>
        Spearman ρ = <b>+0.47</b> (p &lt; 0.001; tract-cluster bootstrap 95% CI 0.20–0.66), equivalent to <b>+${fmtInt(headline.incomeSlopePerKm)}</b> per km. The gradient persists <i>within</i> Worcester alone (ρ = +0.57), so it is not just the Worcester&ndash;Shrewsbury town divide.
      </>
    ),
  },
  {
    title: "A $32,000 income gap separates the corridor from the rest",
    strength: "Strong association",
    body: (
      <>
        Median tract income is <b>$52,011</b> in the corridor vs <b>$84,407</b> elsewhere in Worcester and Shrewsbury, and 44.6% of corridor households earn under $50k (31.3% elsewhere). The corridor median is about half the statewide median ($103,960).
      </>
    ),
  },
  {
    title: "Burdens stack up in a small set of neighborhoods",
    strength: "Index-based",
    body: (
      <>
        <b>{headline.hotspots}</b> corridor block groups rank in the top quintile of a cumulative burden index (traffic exposure, low income, EJ criteria met), housing {fmtInt(headline.hotspotResidents)} EJ residents. Because traffic is one of three components, the distance&ndash;burden link (ρ = −0.75) is partly by construction; the traffic-independent score still rises toward Route 9 (ρ = −0.45).
      </>
    ),
  },
  {
    title: "PM2.5 is regionally elevated in summer, not corridor-specific",
    strength: "Regional context",
    body: (
      <>
        2025 mean <b>5.65 µg/m³</b>, peak <b>33.5</b>. No day exceeded the federal 24-hour standard (35), but 23 site-days topped the WHO 24-hour guideline (15), all in June&ndash;August. Two monitors 23 km apart move together (ρ = 0.95): these are regional episodes that these data cannot attribute to Route 9.
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
          Environmental justice research asks whether the costs of infrastructure fall disproportionately on some communities. This study pairs a single measured traffic
          count with Census, state EJ and EPA air-quality data to test that question along one corridor, block group by block group.
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
              <li>Measured near-road air quality: traffic exposure is <i>modelled</i> from one count station using a distance-decay curve.</li>
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
