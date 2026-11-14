import { ArrowDown, Clock, Download, FileText } from "lucide-react";
import { LINKS, SITE } from "../config";
import { headline } from "../lib/analysis";
import { traffic } from "../data";
import { fmtInt } from "../lib/format";
import { CorridorMap, MapLegend } from "./CorridorMap";

function Stat({
  value,
  unit,
  label,
  note,
  accent,
}: {
  value: string;
  unit?: string;
  label: string;
  note: string;
  accent: string;
}) {
  return (
    <div className="card relative overflow-hidden p-5 sm:p-6">
      <span className="absolute inset-x-0 top-0 h-1" style={{ background: accent }} aria-hidden />
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="font-serif text-[2.6rem] font-semibold leading-none tracking-tight text-ink tabular sm:text-5xl">{value}</span>
        {unit && <span className="whitespace-nowrap text-sm font-medium text-ink-3">{unit}</span>}
      </div>
      <p className="mt-3 text-[0.95rem] font-semibold leading-snug text-ink">{label}</p>
      <p className="mt-1 text-[0.8rem] leading-relaxed text-ink-3">{note}</p>
    </div>
  );
}

export function Hero() {
  const paperLive = LINKS.paperPdf.trim().length > 0;
  return (
    <div id="top" className="relative overflow-hidden border-b border-rule">
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(60rem_30rem_at_85%_-10%,#eaf1fb_0%,transparent_60%),radial-gradient(40rem_24rem_at_-5%_10%,#fdeff0_0%,transparent_60%)]" />
      <div className="container-page relative pb-14 pt-12 sm:pb-20 sm:pt-16">
        <div className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
          <div>
            <p className="eyebrow mb-4 flex items-center gap-2">
              <span className="inline-block h-px w-8 bg-route" /> Independent environmental justice study · {SITE.year}
            </p>
            <h1 className="h-display text-[2.25rem] leading-[1.08] sm:text-5xl lg:text-[3.35rem]">
              Spatial equity, traffic exposure, and environmental justice along the{" "}
              <span className="text-route">Route 9</span> corridor
            </h1>
            <p className="mt-3 font-serif text-xl italic text-ink-3">{SITE.subtitle}</p>
            <p className="mt-6 max-w-xl text-[1.08rem] leading-relaxed text-ink-2">
              Across {headline.nBlockGroups} Census block groups, the neighborhoods closest to Route 9 have lower incomes, are more often
              designated environmental justice populations, and sit in the highest modelled traffic exposure. Explore the evidence, inspect
              the method, and download everything.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <a href="#explorer" className="inline-flex items-center gap-2 rounded-lg bg-ink px-5 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-navy-2">
                Explore the corridor <ArrowDown className="h-4 w-4" />
              </a>
              <a href={LINKS.datasetCsv} download className="inline-flex items-center gap-2 rounded-lg border border-rule-2 bg-white px-5 py-3 text-sm font-semibold text-ink transition-colors hover:border-ink-3">
                <Download className="h-4 w-4" /> Download dataset
              </a>
              {paperLive ? (
                <a href={LINKS.paperPdf} className="inline-flex items-center gap-2 rounded-lg px-3 py-3 text-sm font-semibold text-navy-2 hover:underline">
                  <FileText className="h-4 w-4" /> Read the paper (PDF)
                </a>
              ) : (
                <span className="inline-flex items-center gap-2 px-3 py-3 text-sm font-medium text-ink-3">
                  <Clock className="h-4 w-4" /> Paper PDF · coming soon
                </span>
              )}
            </div>
          </div>

          <figure className="card p-3 sm:p-4">
            <div className="overflow-hidden rounded-lg bg-[#eef3f8]">
              <CorridorMap metric="income" interactive={false} showHotspots ariaLabel="Map of Worcester and Shrewsbury block groups shaded by median household income, with Route 9 in red and cumulative-burden hotspots outlined" />
            </div>
            <figcaption className="mt-3 flex flex-col gap-2 px-1 pb-1">
              <MapLegend metric="income" />
              <p className="text-[0.75rem] leading-snug text-ink-3">
                Income by block group (ACS 2024). <span className="font-semibold text-route">Red line:</span> Route 9. <span className="font-semibold text-ink">Dark outlines:</span> the{" "}
                {headline.hotspots} cumulative-burden hotspots.
              </p>
            </figcaption>
          </figure>
        </div>

        <dl className="mt-12 grid gap-4 sm:grid-cols-2 lg:mt-16 lg:grid-cols-4">
          <Stat
            accent="#c0001a"
            value={fmtInt(traffic.aadt)}
            unit="vehicles / day"
            label="Annual average daily traffic on Route 9"
            note={`MassDOT station M3002W. ${(traffic.westboundShare * 100).toFixed(1)}% runs westbound (${fmtInt(traffic.westbound)} WB vs ${fmtInt(traffic.eastbound)} EB).`}
          />
          <Stat
            accent="#1d91c0"
            value={`+$${fmtInt(headline.incomeSlopePerKm)}`}
            unit="per km"
            label="Income gradient moving away from Route 9"
            note="Tract median household income rises with distance (Spearman ρ = +0.47, 95% CI 0.20–0.66)."
          />
          <Stat
            accent="#b45309"
            value={`${Math.round(headline.corridorEjRate)}%`}
            label="Corridor block groups designated EJ"
            note={`${headline.corridorEj} of ${headline.corridorN} within 1.5 km, vs ${headline.elsewhereEjRate.toFixed(1)}% elsewhere in the two towns (odds ratio 5.1, p = 0.009).`}
          />
          <Stat
            accent="#0f1b2d"
            value={String(headline.hotspots)}
            label="Cumulative-burden hotspots"
            note={`Corridor block groups in the top burden quintile, home to ${fmtInt(headline.hotspotResidents)} EJ-designated residents (${((100 * headline.hotspotResidents) / headline.ejPopTotal).toFixed(1)}%).`}
          />
        </dl>
      </div>
    </div>
  );
}
