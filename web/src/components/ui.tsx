import { useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, Check, Clock, Copy, Download, ExternalLink, Info, Maximize2, X } from "lucide-react";

/** lucide-react v1 no longer ships brand icons, so the GitHub mark is inlined. */
export function GithubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.69 1.25 3.35.96.1-.75.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  );
}

export function Section({
  id,
  eyebrow,
  title,
  intro,
  children,
  tone = "paper",
}: {
  id: string;
  eyebrow: string;
  title: string;
  intro?: ReactNode;
  children: ReactNode;
  tone?: "paper" | "white";
}) {
  return (
    <section id={id} className={`${tone === "white" ? "bg-white border-y border-rule" : ""} py-16 sm:py-24`}>
      <div className="container-page">
        <header className="mb-10 max-w-3xl">
          <p className="eyebrow mb-3">{eyebrow}</p>
          <h2 className="h-display text-3xl leading-[1.12] sm:text-[2.6rem]">{title}</h2>
          {intro && <div className="mt-4 text-[1.05rem] leading-relaxed text-ink-2">{intro}</div>}
        </header>
        {children}
      </div>
    </section>
  );
}

export function Callout({
  tone = "info",
  title,
  children,
}: {
  tone?: "info" | "caution";
  title: string;
  children: ReactNode;
}) {
  const caution = tone === "caution";
  const Icon = caution ? AlertTriangle : Info;
  return (
    <aside
      className={`flex gap-3 rounded-xl border p-4 text-[0.92rem] leading-relaxed ${
        caution ? "border-amber/25 bg-amber-soft text-ink-2" : "border-navy-2/15 bg-sky-soft text-ink-2"
      }`}
    >
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${caution ? "text-amber" : "text-navy-2"}`} aria-hidden />
      <div>
        <p className="mb-0.5 font-semibold text-ink">{title}</p>
        {children}
      </div>
    </aside>
  );
}

export function Pill({ children, color }: { children: ReactNode; color?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-paper px-2 py-0.5 text-[0.72rem] font-medium text-ink-2 ring-1 ring-rule-2">
      {color && <span className="h-2 w-2 rounded-full" style={{ background: color }} />}
      {children}
    </span>
  );
}

/** Horizontal bar with value label used throughout. */
export function Bar({ value, max, color = "#1d3a6b", height = 10 }: { value: number; max: number; color?: string; height?: number }) {
  return (
    <div className="w-full overflow-hidden rounded-full bg-rule/70" style={{ height }}>
      <div
        className="h-full rounded-full transition-[width] duration-500 ease-out"
        style={{ width: `${Math.max(0, Math.min(100, (value / max) * 100))}%`, background: color }}
      />
    </div>
  );
}

/* ----------------------------------------------------------------------------
 * Figure with full-resolution lightbox
 * -------------------------------------------------------------------------- */
export function FigureCard({
  src,
  alt,
  title,
  caption,
  downloadName,
}: {
  src: string;
  alt: string;
  title: string;
  caption: ReactNode;
  downloadName: string;
}) {
  const [open, setOpen] = useState(false);
  const [fit, setFit] = useState(true);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  return (
    <figure className="card overflow-hidden">
      <button
        type="button"
        onClick={() => {
          setFit(true);
          setOpen(true);
        }}
        className="group relative block w-full cursor-zoom-in bg-white"
        aria-label={`Open ${title} at full resolution`}
      >
        <img src={src} alt={alt} loading="lazy" className="block h-auto w-full" />
        <span className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-ink/85 px-3 py-1.5 text-xs font-medium text-white opacity-0 shadow transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
          <Maximize2 className="h-3.5 w-3.5" /> Full resolution
        </span>
      </button>
      <figcaption className="flex flex-col gap-3 border-t border-rule p-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-3xl text-[0.9rem] leading-relaxed text-ink-2">
          <p className="mb-1 font-semibold text-ink">{title}</p>
          {caption}
        </div>
        <a
          href={src}
          download={downloadName}
          className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg border border-rule-2 bg-white px-3 py-2 text-sm font-medium text-ink hover:border-ink-3"
        >
          <Download className="h-4 w-4" /> PNG
        </a>
      </figcaption>

      {open && (
        <div role="dialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-[100] flex flex-col bg-ink/90 backdrop-blur-sm">
          <div className="flex items-center justify-between gap-3 px-4 py-3 text-white">
            <p className="truncate text-sm font-medium">{title}</p>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => setFit((v) => !v)} className="rounded-lg bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20">
                {fit ? "View at 100%" : "Fit to screen"}
              </button>
              <a href={src} download={downloadName} className="rounded-lg bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20">
                Download
              </a>
              <button
                type="button"
                autoFocus
                onClick={() => setOpen(false)}
                className="rounded-lg bg-white/10 p-2 hover:bg-white/20"
                aria-label="Close full-resolution view"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto p-4" onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
            <img src={src} alt={alt} className={`mx-auto rounded bg-white ${fit ? "max-h-full w-auto max-w-full object-contain" : "max-w-none"}`} />
          </div>
        </div>
      )}
    </figure>
  );
}

/* ----------------------------------------------------------------------------
 * Resource slot: renders a live link when `href` is set, otherwise a clean
 * "Coming soon" placeholder. Used for paper PDF / GitHub / dataset.
 * -------------------------------------------------------------------------- */
export function ResourceSlot({
  icon,
  title,
  description,
  href,
  actionLabel,
  placeholderLabel,
  placeholderHint,
  download,
  meta,
  external,
}: {
  icon: ReactNode;
  title: string;
  description: ReactNode;
  href: string;
  actionLabel: string;
  placeholderLabel: string;
  placeholderHint: ReactNode;
  download?: string | boolean;
  meta?: ReactNode;
  external?: boolean;
}) {
  const live = href.trim().length > 0;
  return (
    <div className={`card flex flex-col p-6 ${live ? "" : "border-dashed bg-paper/60"}`}>
      <div className="mb-4 flex items-start justify-between">
        <span className={`inline-flex h-11 w-11 items-center justify-center rounded-xl ${live ? "bg-navy text-white" : "bg-rule/70 text-ink-3"}`}>{icon}</span>
        {live ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-[0.72rem] font-semibold text-emerald-800 ring-1 ring-emerald-600/20">
            <Check className="h-3 w-3" /> Available
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-soft px-2.5 py-1 text-[0.72rem] font-semibold text-amber ring-1 ring-amber/25">
            <Clock className="h-3 w-3" /> Coming soon
          </span>
        )}
      </div>
      <h3 className="font-serif text-xl font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 text-[0.92rem] leading-relaxed text-ink-2">{description}</p>
      {meta && <p className="mt-2 text-xs text-ink-3">{meta}</p>}
      <div className="mt-auto pt-5">
        {live ? (
          <a
            href={href}
            {...(download ? { download: typeof download === "string" ? download : "" } : {})}
            {...(external ? { target: "_blank", rel: "noreferrer noopener" } : {})}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-navy px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-navy-2"
          >
            {download ? <Download className="h-4 w-4" /> : <ExternalLink className="h-4 w-4" />}
            {actionLabel}
          </a>
        ) : (
          <>
            <button
              type="button"
              disabled
              aria-disabled="true"
              className="inline-flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-dashed border-rule-2 bg-white px-4 py-2.5 text-sm font-semibold text-ink-3"
            >
              <Clock className="h-4 w-4" /> {placeholderLabel}
            </button>
            <p className="mt-2 text-[0.72rem] leading-snug text-ink-3">{placeholderHint}</p>
          </>
        )}
      </div>
    </div>
  );
}

export function CodeBlock({ code, label, language = "bash" }: { code: string; label?: string; language?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="overflow-hidden rounded-xl border border-ink/10 bg-[#0c1626] text-slate-100">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-2 text-[0.72rem] text-slate-400">
        <span>{label ?? language}</span>
        <button
          type="button"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(code);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            } catch {
              /* clipboard unavailable */
            }
          }}
          className="inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 hover:bg-white/10 hover:text-white"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-[0.8rem] leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}
