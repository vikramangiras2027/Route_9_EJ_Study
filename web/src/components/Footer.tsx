import { Mail } from "lucide-react";
import { asset, LINKS, SITE } from "../config";
import { NAV_ITEMS } from "./Nav";

export function Footer() {
  return (
    <footer className="bg-ink text-slate-300">
      <div className="container-page grid gap-10 py-14 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <div className="flex items-center gap-2.5">
            <img src={asset("favicon.svg")} alt="" className="h-8 w-8" />
            <p className="font-serif text-lg font-semibold text-white">{SITE.shortTitle}</p>
          </div>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-400">
            {SITE.title}: {SITE.subtitle}. An independent, open-source environmental justice study. Findings describe neighborhood-level associations, not individual exposure, health outcomes or causation.
          </p>
          {SITE.author.trim() && (
            <p className="mt-4 text-sm text-slate-300">
              {SITE.author} · {SITE.affiliation}
            </p>
          )}
          {SITE.contactEmail.trim() && (
            <a href={`mailto:${SITE.contactEmail}`} className="mt-2 inline-flex items-center gap-1.5 text-sm text-slate-300 hover:text-white">
              <Mail className="h-4 w-4" /> {SITE.contactEmail}
            </a>
          )}
        </div>
        <nav aria-label="Footer">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Explore</p>
          <ul className="space-y-2 text-sm">
            {NAV_ITEMS.map((i) => (
              <li key={i.id}>
                <a href={`#${i.id}`} className="hover:text-white">
                  {i.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Open assets</p>
          <ul className="space-y-2 text-sm">
            <li>
              <a href={LINKS.datasetCsv} download className="hover:text-white">
                Master dataset (CSV)
              </a>
            </li>
            <li>
              <a href={LINKS.analysisScript} download className="hover:text-white">
                Analysis script (Python)
              </a>
            </li>
            <li>{LINKS.githubRepo.trim() ? <a href={LINKS.githubRepo} className="hover:text-white">GitHub repository</a> : <span className="text-slate-500">GitHub repository · soon</span>}</li>
            <li>{LINKS.paperPdf.trim() ? <a href={LINKS.paperPdf} className="hover:text-white">Research paper (PDF)</a> : <span className="text-slate-500">Research paper · soon</span>}</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="container-page flex flex-col gap-2 py-5 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {SITE.year} · Data: MassDOT, MassGIS, U.S. Census Bureau (ACS 2024, TIGER/Line 2024), U.S. EPA AQS. Boundaries simplified for display.
          </p>
          <p>Built with React, Tailwind CSS &amp; Lucide. No tracking, no cookies.</p>
        </div>
      </div>
    </footer>
  );
}
