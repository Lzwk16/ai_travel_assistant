import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { TripRead } from "../../lib/types";
import PipeTable, { FLIGHT_HEADERS, HOTEL_HEADERS } from "./PipeTable";

// Renders a completed trip's `result`, by trip_type:
// - itinerary → prose markdown (react-markdown)
// - flights / hotels → parsed into tables (the flows emit a pipe-delimited
//   machine format, not user-facing markdown — see PipeTable).
export default function TripResult({ trip }: { trip: TripRead }) {
  const result = trip.result;

  if (trip.status === "failed" || (result && "error" in result)) {
    const message =
      result && "error" in result ? result.error : "This trip failed to run.";
    return <div className="error">{message}</div>;
  }

  if (!result) {
    return <p className="notice">No result yet.</p>;
  }

  if ("flights_md" in result) {
    return <ResultCard heading="Flight options" md={result.flights_md} headers={FLIGHT_HEADERS} />;
  }
  if ("hotels_md" in result) {
    return <ResultCard heading="Hotel options" md={result.hotels_md} headers={HOTEL_HEADERS} />;
  }
  if ("itinerary_md" in result) {
    const sections = [
      { heading: "Local insights", md: result.insights_md },
      { heading: "Suggested itinerary", md: result.itinerary_md },
    ].filter((s) => s.md);
    if (sections.length === 0) {
      return <p className="notice">The run completed but produced no content.</p>;
    }
    return (
      <>
        {sections.map((s) => (
          <section key={s.heading} className="card">
            <h3>{s.heading}</h3>
            <div className="markdown">
              <Markdown remarkPlugins={[remarkGfm]}>{s.md}</Markdown>
            </div>
          </section>
        ))}
      </>
    );
  }

  return <p className="notice">The run completed but produced no content.</p>;
}

function ResultCard({
  heading,
  md,
  headers,
}: {
  heading: string;
  md: string | null;
  headers: string[];
}) {
  if (!md) {
    return <p className="notice">The run completed but produced no content.</p>;
  }
  return (
    <section className="card">
      <h3>{heading}</h3>
      <PipeTable md={md} headers={headers} />
    </section>
  );
}
