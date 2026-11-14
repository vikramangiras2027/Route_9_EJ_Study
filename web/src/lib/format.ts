export const fmtInt = (n: number | null | undefined) =>
  n === null || n === undefined || Number.isNaN(n) ? "n/a" : Math.round(n).toLocaleString("en-US");

export const fmtUsd = (n: number | null | undefined) =>
  n === null || n === undefined || Number.isNaN(n) ? "n/a" : `$${Math.round(n).toLocaleString("en-US")}`;

export const fmtUsdK = (n: number) => `$${Math.round(n / 1000)}k`;

export const fmtPct = (n: number | null | undefined, digits = 0) =>
  n === null || n === undefined || Number.isNaN(n) ? "n/a" : `${n.toFixed(digits)}%`;

export const fmtDist = (m: number | null | undefined) => {
  if (m === null || m === undefined) return "n/a";
  return m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${Math.round(m)} m`;
};

export const fmtNum = (n: number | null | undefined, digits = 1) =>
  n === null || n === undefined || Number.isNaN(n) ? "n/a" : n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const signed = (n: number, digits = 2) => `${n >= 0 ? "+" : "\u2212"}${Math.abs(n).toFixed(digits)}`;
