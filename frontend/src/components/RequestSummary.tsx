import type { TripRead } from "../../lib/types";

// Human-readable summary of a trip's request (replaces the raw JSON dump).
// Reads defensively from the free-form request dict, which varies by trip_type.

function str(v: unknown): string | null {
  return typeof v === "string" && v.trim() ? v.trim() : null;
}
function list(v: unknown): string[] {
  return Array.isArray(v) ? (v as unknown[]).map(String) : [];
}
function num(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

// Parse "YYYY-MM-DD" without timezone drift; returns null if unparseable.
function parseDate(s: string | null): { y: number; m: number; d: number } | null {
  if (!s) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
  if (!m) return null;
  return { y: Number(m[1]), m: Number(m[2]) - 1, d: Number(m[3]) };
}

function formatDateRange(startRaw: unknown, endRaw: unknown): string | null {
  const start = parseDate(str(startRaw));
  const end = parseDate(str(endRaw));
  if (!start && !end) return null;
  const fmt = (p: { y: number; m: number; d: number }) =>
    `${p.d} ${MONTHS[p.m]} ${p.y}`;
  if (start && end) {
    // Compact when same month & year: "1–5 Aug 2026".
    if (start.y === end.y && start.m === end.m) {
      return `${start.d}–${end.d} ${MONTHS[start.m]} ${start.y}`;
    }
    return `${fmt(start)} – ${fmt(end)}`;
  }
  return fmt((start ?? end)!);
}

function travelers(req: Record<string, unknown>): string | null {
  const group = num(req.group_size);
  if (group != null) return `${group} ${group === 1 ? "traveler" : "travelers"}`;

  const adults = num(req.adults);
  const children = num(req.children);
  const parts: string[] = [];
  if (adults != null) parts.push(`${adults} ${adults === 1 ? "adult" : "adults"}`);
  if (children != null && children > 0)
    parts.push(`${children} ${children === 1 ? "child" : "children"}`);
  return parts.length ? parts.join(", ") : null;
}

export default function RequestSummary({ trip }: { trip: TripRead }) {
  const req = trip.request as Record<string, unknown>;

  const origin = str(req.origin);
  const dests = list(req.destinations);
  const route =
    origin && dests.length
      ? `${origin} → ${dests.join(", ")}`
      : (origin ?? (dests.join(", ") || "—"));

  const meta = [
    formatDateRange(req.start_date, req.end_date),
    travelers(req),
    str(req.currency),
  ].filter(Boolean);

  const chips = [
    str(req.budget_type),
    str(req.travel_style),
    ...list(req.interests),
  ].filter(Boolean) as string[];

  return (
    <div className="card">
      <strong style={{ fontSize: "1.05rem" }}>{route}</strong>
      {meta.length > 0 && (
        <div className="muted" style={{ marginTop: "0.25rem" }}>
          {meta.join(" · ")}
        </div>
      )}
      {chips.length > 0 && (
        <div style={{ marginTop: "0.6rem", display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
          {chips.map((c) => (
            <span key={c} className="chip">
              {c}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
