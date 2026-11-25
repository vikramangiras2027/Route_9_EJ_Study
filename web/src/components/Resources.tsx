import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { FileCode2, FileText, FileSpreadsheet, Image as ImageIcon, ScrollText, Search } from "lucide-react";
import { LINKS, SITE } from "../config";
import { csvColumns, blockGroups } from "../data";
import { DICTIONARY } from "../data/dictionary";
import abstractMd from "../content/paper-abstract.md?raw";
import { CodeBlock, GithubIcon as Github, ResourceSlot, Section } from "./ui";

function DataDictionary() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const rows = useMemo(() => {
    const s = q.trim().toLowerCase();
    return csvColumns
      .map((c) => ({ name: c, ...(DICTIONARY[c] ?? { group: "Other", text: "" }) }))
      .filter((r) => !s || r.name.toLowerCase().includes(s) || r.text.toLowerCase().includes(s) || r.group.toLowerCase().includes(s));
  }, [q]);

  return (
    <div className="card overflow-hidden">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center justify-between gap-3 p-5 text-left sm:p-6">
        <div>
          <h3 className="font-serif text-xl font-semibold text-ink">Data dictionary</h3>
          <p className="mt-0.5 text-[0.88rem] text-ink-2">
            {blockGroups.length} rows × {csvColumns.length} columns in <code className="text-[0.82rem]">master_route9_table.csv</code>
          </p>
        </div>
        <span className="rounded-full border border-rule-2 px-3 py-1 text-xs font-semibold text-ink-2">{open ? "Hide" : "Show columns"}</span>
      </button>
      {open && (
        <div className="border-t border-rule">
          <div className="relative border-b border-rule p-3">
            <Search className="pointer-events-none absolute left-6 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" aria-hidden />
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filter columns, e.g. income, exposure, hotspot…"
              aria-label="Filter data dictionary"
              className="w-full rounded-lg border border-rule-2 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-navy-2"
            />
          </div>
          <div className="max-h-[420px] overflow-auto">
            <table className="w-full min-w-[560px] text-left text-[0.82rem]">
              <thead className="sticky top-0 bg-paper text-[0.68rem] uppercase tracking-wider text-ink-3">
                <tr>
                  <th className="px-4 py-2 font-semibold">Column</th>
                  <th className="px-2 py-2 font-semibold">Group</th>
                  <th className="px-2 py-2 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {rows.map((r) => (
                  <tr key={r.name}>
                    <td className="whitespace-nowrap px-4 py-2 font-mono text-[0.78rem] text-navy-2">{r.name}</td>
                    <td className="whitespace-nowrap px-2 py-2 text-ink-3">{r.group}</td>
                    <td className="px-2 py-2 text-ink-2">{r.text || "—"}</td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-center text-ink-3">
                      No columns match &ldquo;{q}&rdquo;.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export function Resources() {
  const author = SITE.author.trim() || "[Author name]";
  const cite = `${author} (${SITE.year}). ${SITE.title}: ${SITE.subtitle}. ${SITE.affiliation}. Dataset and code: ${LINKS.githubRepo.trim() || "[repository URL]"}`;
  const bib = `@misc{route9_ej_${SITE.year},
  author       = {${author}},
  title        = {${SITE.title}: ${SITE.subtitle}},
  year         = {${SITE.year}},
  howpublished = {${LINKS.githubRepo.trim() || "[repository URL]"}},
  note         = {Open-source environmental justice study and dataset}
}`;

  return (
    <Section
      id="resources"
      eyebrow="Open data & downloads"
      title="Take the paper, the code and the data"
      tone="white"
      intro="Everything behind this portal is meant to be inspected, reused and challenged. The manuscript, master table, figures and analysis script are all downloadable; the GitHub slot lights up once LINKS.githubRepo is set in src/config.ts."
    >
      <div className="grid gap-5 md:grid-cols-3">
        <ResourceSlot
          icon={<FileText className="h-5 w-5" />}
          title="Research paper (PDF)"
          description="Full manuscript by Vikram Angiras: methods, results, limitations and references (9 pages)."
          href={LINKS.paperPdf}
          actionLabel="Download PDF"
          placeholderLabel="PDF forthcoming"
          placeholderHint={
            <>
              Drop the file in <code>web/public/paper/</code> and set <code>LINKS.paperPdf</code> in <code>src/config.ts</code>.
            </>
          }
          download="route9-ej-study.pdf"
        />
        <ResourceSlot
          icon={<Github className="h-5 w-5" />}
          title="Analysis code on GitHub"
          description={
            <>
              Repository for <code className="text-[0.85em]">route9_deep_analysis.py</code>: issues, forks and pull requests welcome.
            </>
          }
          href={LINKS.githubRepo}
          actionLabel="Open repository"
          placeholderLabel="Repository coming soon"
          placeholderHint={
            <>
              Set <code>LINKS.githubRepo</code> in <code>src/config.ts</code>. Meanwhile the script is downloadable below.
            </>
          }
          external
        />
        <ResourceSlot
          icon={<FileSpreadsheet className="h-5 w-5" />}
          title="Master dataset (CSV)"
          description="One row per block group: demographics, income, distance to Route 9, measured segment AADT, modelled exposure, vulnerability index and priority-hotspot flag."
          href={LINKS.datasetCsv}
          actionLabel="Download master_route9_table.csv"
          placeholderLabel="Unavailable"
          placeholderHint=""
          download="master_route9_table.csv"
          meta={`${blockGroups.length} rows × ${csvColumns.length} columns · UTF-8`}
        />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { href: LINKS.analysisScript, name: "route9_deep_analysis.py", sub: "Full analysis script", icon: FileCode2, dl: "route9_deep_analysis.py" },
          { href: LINKS.fetchScript, name: "fetch_massdot_traffic_aadt.py", sub: "MassDOT traffic fetch/join", icon: FileCode2, dl: "fetch_massdot_traffic_aadt.py" },
          { href: LINKS.summaryStatistics, name: "summary_statistics.txt", sub: "Every statistic, as printed", icon: ScrollText, dl: "summary_statistics.txt" },
          { href: LINKS.dataDictionaryMd, name: "data_dictionary.md", sub: "Every column, explained", icon: ScrollText, dl: "data_dictionary.md" },
          { href: LINKS.tractTableCsv, name: "tract_table_route9.csv", sub: "One row per Worcester tract", icon: FileSpreadsheet, dl: "tract_table_route9.csv" },
          { href: LINKS.figure1, name: "figure1_income_traffic_ej.png", sub: "Figure 1, full resolution", icon: ImageIcon, dl: "figure1_income_traffic_ej.png" },
          { href: LINKS.figure2, name: "figure2_pm25_distribution.png", sub: "Appendix figure, PM2.5", icon: ImageIcon, dl: "figure2_pm25_distribution.png" },
          { href: LINKS.figure3, name: "figure3_priority_hotspots.png", sub: "Figure 3, priority map", icon: ImageIcon, dl: "figure3_priority_hotspots.png" },
        ].map((f) => (
          <a key={f.name} href={f.href} download={f.dl} className="card group flex items-center gap-3 p-4 transition-colors hover:border-ink-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-paper text-ink-2 group-hover:bg-navy group-hover:text-white">
              <f.icon className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[0.84rem] font-semibold text-ink">{f.name}</span>
              <span className="block text-[0.72rem] text-ink-3">{f.sub}</span>
            </span>
          </a>
        ))}
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        {/* MARKDOWN SLOT: abstract */}
        <div className="card p-5 sm:p-6">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="font-serif text-xl font-semibold text-ink">Abstract</h3>
            <code className="rounded bg-paper px-2 py-1 text-[0.68rem] text-ink-3 ring-1 ring-rule">src/content/paper-abstract.md</code>
          </div>
          <div className="prose-ej text-[0.92rem] [&_blockquote]:mb-4 [&_blockquote]:rounded-lg [&_blockquote]:border-l-4 [&_blockquote]:border-amber [&_blockquote]:bg-amber-soft [&_blockquote]:px-4 [&_blockquote]:py-3 [&_blockquote_p]:mb-0">
            <ReactMarkdown>{abstractMd}</ReactMarkdown>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="font-serif text-xl font-semibold text-ink">Cite this work</h3>
          <p className="text-[0.88rem] leading-relaxed text-ink-2">{cite}</p>
          <CodeBlock code={bib} language="bibtex" label="BibTeX" />
          {!SITE.author.trim() && (
            <p className="text-[0.75rem] text-ink-3">
              Set <code>SITE.author</code> and <code>LINKS.githubRepo</code> in <code>src/config.ts</code> to complete the citation.
            </p>
          )}
        </div>
      </div>

      <div className="mt-8">
        <DataDictionary />
      </div>
    </Section>
  );
}
