// Renders the flight/hotel flow output as proper tables. The deterministic flows
// emit sections (`## <title>`) of `N. cell | cell | ... | cell` rows — a machine
// format, not something to show a user raw. We parse it here into tables.
// (Itinerary results are genuine prose markdown and are rendered with
// react-markdown instead.)

interface ParsedSection {
  title: string;
  rows: string[][];
  note?: string; // e.g. "No flights found."
}

function parse(md: string): ParsedSection[] {
  const sections: ParsedSection[] = [];
  let current: ParsedSection | null = null;

  for (const raw of md.split("\n")) {
    const line = raw.trim();
    if (!line) continue;

    if (line.startsWith("## ")) {
      current = { title: line.slice(3).trim(), rows: [] };
      sections.push(current);
      continue;
    }
    if (!current) continue;

    const stripped = line.replace(/^\d+\.\s*/, ""); // drop the leading "N. "
    if (stripped.includes("|")) {
      current.rows.push(stripped.split("|").map((c) => c.trim()));
    } else {
      current.note = stripped;
    }
  }
  return sections;
}

export default function PipeTable({
  md,
  headers,
}: {
  md: string;
  headers: string[];
}) {
  const sections = parse(md);

  return (
    <>
      {sections.map((section) => (
        <div key={section.title} style={{ marginBottom: "1.25rem" }}>
          <h4 style={{ margin: "0 0 0.5rem" }}>{section.title}</h4>
          {section.rows.length === 0 ? (
            <p className="notice">{section.note ?? "No results."}</p>
          ) : (
            <div className="markdown">
              <table>
                <thead>
                  <tr>
                    {headers.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {section.rows.map((cells, i) => (
                    <tr key={i}>
                      {headers.map((_, c) => (
                        <td key={c}>{cells[c] ?? ""}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </>
  );
}

// Column headers matching each flow's emitted row order.
export const FLIGHT_HEADERS = [
  "Flight",
  "Date",
  "Depart",
  "Arrive",
  "Duration",
  "Stops",
  "Price",
  "Airline",
  "From",
  "To",
];

export const HOTEL_HEADERS = [
  "Hotel",
  "City",
  "Class",
  "Rating",
  "Price / night",
  "Total",
  "Amenities",
];
