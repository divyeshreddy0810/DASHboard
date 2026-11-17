const compact = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 });
const full = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });

export function formatCompact(v: unknown): string {
  return typeof v === "number" ? compact.format(v) : String(v ?? "");
}

export function formatFull(v: unknown): string {
  return typeof v === "number" ? full.format(v) : String(v ?? "");
}
