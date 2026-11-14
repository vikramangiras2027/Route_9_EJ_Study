import { useEffect, useState } from "react";
import { Download, Menu, X } from "lucide-react";
import { asset, LINKS, SITE } from "../config";
import { GithubIcon as Github } from "./ui";

export const NAV_ITEMS = [
  { id: "summary", label: "Findings" },
  { id: "explorer", label: "Corridor explorer" },
  { id: "air-quality", label: "Air quality" },
  { id: "evidence", label: "Evidence" },
  { id: "methodology", label: "Methodology" },
  { id: "resources", label: "Resources" },
];

export function Nav() {
  const [active, setActive] = useState<string>("");
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const els = NAV_ITEMS.map((i) => document.getElementById(i.id)).filter(Boolean) as HTMLElement[];
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: [0, 0.1, 0.4] },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const github = LINKS.githubRepo.trim();

  return (
    <header
      className={`sticky top-0 z-50 border-b transition-colors ${
        scrolled ? "border-rule bg-paper/90 backdrop-blur-md" : "border-transparent bg-paper"
      }`}
    >
      <div className="container-page flex h-14 items-center justify-between gap-4">
        <a href="#top" className="flex items-center gap-2.5 text-ink">
          <img src={asset("favicon.svg")} alt="" className="h-7 w-7" />
          <span className="font-serif text-[1.05rem] font-semibold tracking-tight">{SITE.shortTitle}</span>
        </a>

        <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
          {NAV_ITEMS.map((i) => (
            <a
              key={i.id}
              href={`#${i.id}`}
              aria-current={active === i.id ? "true" : undefined}
              className={`rounded-md px-3 py-1.5 text-[0.85rem] font-medium transition-colors ${
                active === i.id ? "bg-ink text-white" : "text-ink-2 hover:bg-rule/60 hover:text-ink"
              }`}
            >
              {i.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          {github ? (
            <a href={github} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1.5 rounded-lg border border-rule-2 bg-white px-3 py-1.5 text-[0.82rem] font-medium hover:border-ink-3">
              <Github className="h-4 w-4" /> GitHub
            </a>
          ) : (
            <span title="GitHub repository: coming soon" className="inline-flex cursor-default items-center gap-1.5 rounded-lg border border-dashed border-rule-2 px-3 py-1.5 text-[0.82rem] font-medium text-ink-3">
              <Github className="h-4 w-4" /> Code · soon
            </span>
          )}
          <a href={LINKS.datasetCsv} download className="inline-flex items-center gap-1.5 rounded-lg bg-navy px-3 py-1.5 text-[0.82rem] font-semibold text-white hover:bg-navy-2">
            <Download className="h-4 w-4" /> Data
          </a>
        </div>

        <button
          type="button"
          className="rounded-md p-2 text-ink lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Primary mobile" className="border-t border-rule bg-paper lg:hidden">
          <ul className="container-page grid gap-1 py-3">
            {NAV_ITEMS.map((i) => (
              <li key={i.id}>
                <a href={`#${i.id}`} onClick={() => setOpen(false)} className="block rounded-md px-3 py-2.5 text-[0.95rem] font-medium text-ink hover:bg-rule/60">
                  {i.label}
                </a>
              </li>
            ))}
            <li>
              <a href={LINKS.datasetCsv} download className="mt-1 flex items-center justify-center gap-2 rounded-lg bg-navy px-3 py-2.5 text-sm font-semibold text-white">
                <Download className="h-4 w-4" /> Download dataset
              </a>
            </li>
          </ul>
        </nav>
      )}
    </header>
  );
}
