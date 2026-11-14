import { AlertTriangle, ArrowUpRight, Database, Gauge, Layers, Map as MapIcon, Ruler, Sigma } from "lucide-react";
import { LINKS, SOURCES } from "../config";
import { CodeBlock, Section } from "./ui";

const STEPS = [
  {
    icon: Database,
    title: "Ingest, clean & audit",
    body: "ACS S1901 tract incomes, the MassGIS EJ attribute table, the MassDOT count and 705 EPA PM2.5 site-days are loaded with explicit sentinel handling (ACS “-”, “(X)”, “**” and EJ income codes 0 / “U” become missing, never zero). A missing-value audit prints for every table; PM2.5 is de-duplicated by parameter occurrence code (POC).",
  },
  {
    icon: MapIcon,
    title: "Build the spatial layer",
    body: "The EJ file has attributes but no shapes and lists only EJ block groups, so Census TIGER/Line 2024 geometry supplies all 166 block groups in Worcester and Shrewsbury (149 EJ + 17 non-EJ). Everything is projected to NAD83 / Massachusetts Mainland (EPSG:26986) so distances are in metres.",
  },
  {
    icon: Ruler,
    title: "Measure distance to Route 9",
    body: "Route 9 is the 12 TIGER segments named “State Rte 9” (70.8 km within 5 km of the study area). Three distances are computed per block group: centroid (primary), nearest polygon edge, and area-weighted mean. Bands: ≤ 0.5, 0.5–1, 1–2, 2–4 and > 4 km; the corridor is centroid ≤ 1.5 km.",
  },
  {
    icon: Gauge,
    title: "Model traffic exposure",
    body: "One count station cannot give tract-level traffic, so exposure is modelled: AADT × exp(−d / 300 m), sampled on a 50 m grid and averaged inside each block group. Residents within 300 m, 500 m and 1 km are estimated by areal interpolation (uniform density within a block group).",
  },
  {
    icon: Layers,
    title: "Cumulative burden index",
    body: "A 0–100 score: the mean percentile rank of traffic exposure, low income (ACS tract) and EJ criteria met (0–3). Hotspots are corridor block groups in the top quintile, a transparent, equal-weight index rather than a black-box score.",
  },
  {
    icon: Sigma,
    title: "Inference & robustness",
    body: "Spearman rank correlations with tract-cluster bootstrap CIs; Mann-Whitney U with Cliff’s δ; Fisher’s exact odds ratio; OLS slope; Moran’s I (999 permutations); a within-town check for the Worcester/Shrewsbury confound; and sensitivity to corridor radius and distance definition.",
  },
];

const CONSTANTS = `# route9_deep_analysis.py: model parameters
CRS_MA = 26986            # NAD83 / MA Mainland (metres)
CORRIDOR_M = 1500         # centroid within ~1 mile
EXPOSURE_DECAY_M = 300    # e-folding distance (m)
GRID_M = 50               # exposure sampling grid
BUFFERS_M = (300, 500, 1000)
BANDS = [0, 500, 1000, 2000, 4000, np.inf]

# exposure at distance d from the centreline
#   E(d) = AADT * exp(-d / 300 m)   AADT = 28,112
# cumulative burden index (0-100)
#   CBI = mean(pct_rank(E),
#              pct_rank(low income),
#              pct_rank(EJ criteria met))`;

const REPRODUCE = `# 1. Python 3 environment
pip install numpy pandas geopandas dbfread \\
    scipy matplotlib shapely

# 2. Run the pipeline (TIGER cached in ./cache)
python route9_deep_analysis.py <data-folder>

# Writes (inputs are never modified):
#   outputs/master_route9_table.csv
#   outputs/summary_statistics.txt
#   charts/figure1_income_traffic_ej.png
#   charts/figure2_pm25_distribution.png

# 3. Rebuild this website from those outputs
#    (audits the CSV against the report first)
cd web && npm install && npm run build`;

const LIMITS = [
  "One AADT station: block-group traffic is a distance-decay model (300 m e-folding), not a measurement; it ignores lane geometry, truck share, grade and wind.",
  "PM2.5 comes from two monitors (Worcester Summer Street, Uxbridge) and cannot differentiate block groups; it is regional context, not a corridor-specific measurement.",
  "The EJ layer lists only EJ-designated block groups. Non-EJ block groups come from Census geometry, so population, % minority and % LEP are unavailable for them.",
  "ACS 2024 tract incomes are applied to block groups (some tracts have wide margins of error: see acs_income_reliable); EJ-table incomes are an older ACS vintage.",
  "Population near Route 9 is interpolated by area (uniform-density assumption). Results are ecological associations, not individual exposure or health effects.",
  "One year of PM2.5 data cannot establish NAAQS compliance, which uses 3-year design values.",
];

export function Methodology() {
  const github = LINKS.githubRepo.trim();
  return (
    <Section
      id="methodology"
      eyebrow="Open-source methodology & code"
      title="A transparent, reproducible spatial pipeline"
      intro={
        <>
          The whole analysis is one Python script (<code className="rounded bg-white px-1.5 py-0.5 text-[0.85em] ring-1 ring-rule">route9_deep_analysis.py</code>, ~1,080 lines) built on GeoPandas, SciPy and Matplotlib. Every number on this site is printed in{" "}
          <a className="font-medium text-navy-2 underline underline-offset-2" href={LINKS.summaryStatistics} target="_blank" rel="noreferrer">summary_statistics.txt</a> and re-checked against the master CSV each time the site is built.
        </>
      }
    >
      <ol className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {STEPS.map((s, i) => (
          <li key={s.title} className="card relative p-5 sm:p-6">
            <div className="mb-3 flex items-center justify-between">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-navy text-white">
                <s.icon className="h-5 w-5" aria-hidden />
              </span>
              <span className="font-serif text-3xl font-semibold text-rule-2 tabular">{String(i + 1).padStart(2, "0")}</span>
            </div>
            <h3 className="font-serif text-lg font-semibold text-ink">{s.title}</h3>
            <p className="mt-1.5 text-[0.88rem] leading-relaxed text-ink-2">{s.body}</p>
          </li>
        ))}
      </ol>

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <h3 className="font-serif text-xl font-semibold text-ink">Key parameters &amp; formulas</h3>
          <CodeBlock code={CONSTANTS} language="python" label="python · excerpt" />
        </div>
        <div className="space-y-4">
          <h3 className="font-serif text-xl font-semibold text-ink">Reproduce it</h3>
          <CodeBlock code={REPRODUCE} label="shell" />
          <div className="flex flex-wrap gap-2 text-sm">
            <a href={LINKS.analysisScript} download className="inline-flex items-center gap-1.5 rounded-lg border border-rule-2 bg-white px-3 py-2 font-medium hover:border-ink-3">
              Download route9_deep_analysis.py
            </a>
            {github ? (
              <a href={github} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3 py-2 font-semibold text-white hover:bg-navy-2">
                View on GitHub <ArrowUpRight className="h-4 w-4" />
              </a>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-lg border border-dashed border-rule-2 px-3 py-2 font-medium text-ink-3">GitHub repository · coming soon</span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-12 grid gap-6 lg:grid-cols-12">
        <div className="card overflow-hidden lg:col-span-7">
          <div className="p-5 pb-3 sm:p-6 sm:pb-3">
            <h3 className="font-serif text-xl font-semibold text-ink">Data sources</h3>
          </div>
          <ul className="divide-y divide-rule">
            {SOURCES.map((s) => (
              <li key={s.name} className="flex items-start justify-between gap-4 px-5 py-3.5 sm:px-6">
                <div>
                  <a href={s.href} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 font-semibold text-ink hover:text-navy-2">
                    {s.name} <ArrowUpRight className="h-3.5 w-3.5 text-ink-3" />
                  </a>
                  <p className="text-[0.82rem] leading-relaxed text-ink-2">{s.detail}</p>
                </div>
                <span className="mt-0.5 shrink-0 rounded-full bg-paper px-2.5 py-1 text-[0.7rem] font-medium text-ink-2 ring-1 ring-rule-2">{s.use}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card border-amber/25 bg-amber-soft/60 p-5 sm:p-6 lg:col-span-5">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber" aria-hidden />
            <h3 className="font-serif text-xl font-semibold text-ink">Limitations we state up front</h3>
          </div>
          <ul className="space-y-2.5 text-[0.86rem] leading-relaxed text-ink-2">
            {LIMITS.map((l) => (
              <li key={l} className="flex gap-2.5">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber" aria-hidden />
                <span>{l}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Section>
  );
}
