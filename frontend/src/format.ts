import { ApiError } from "../lib/api";

// Maps an unknown thrown value to a human-readable message. FastAPI returns
// errors as JSON `{detail: ...}` (string, or a 422 validation array), so we try
// to unwrap that before falling back to the raw text.
export function formatError(err: unknown): string {
  if (err instanceof ApiError) {
    try {
      const parsed = JSON.parse(err.message);
      const detail = parsed?.detail ?? parsed;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        return detail
          .map((d) => {
            const loc = Array.isArray(d.loc) ? d.loc.slice(1).join(".") : "";
            return loc ? `${loc}: ${d.msg}` : d.msg;
          })
          .join("; ");
      }
      return err.message;
    } catch {
      return err.message;
    }
  }
  if (err instanceof Error) return err.message;
  return String(err);
}
