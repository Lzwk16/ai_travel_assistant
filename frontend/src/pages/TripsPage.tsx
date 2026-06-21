import { Link } from "react-router-dom";
import { useTrips } from "../hooks/useTrips";
import { formatError } from "../format";
import type { TripRead } from "../../lib/types";

const TYPE_LABEL: Record<TripRead["trip_type"], string> = {
  itinerary: "Itinerary",
  flights: "Flights",
  hotels: "Hotels",
};

function summarize(trip: TripRead): string {
  const r = trip.request as Record<string, unknown>;
  const dest = Array.isArray(r.destinations)
    ? (r.destinations as string[]).join(", ")
    : "";
  const origin = typeof r.origin === "string" ? `${r.origin} → ` : "";
  return `${origin}${dest}`;
}

export default function TripsPage() {
  const { data: trips, isLoading, error, isFetching } = useTrips();

  return (
    <div>
      <div className="spread">
        <h1>Your trips</h1>
        <Link to="/trips/new">
          <button>+ New trip</button>
        </Link>
      </div>

      {error && <div className="error">{formatError(error)}</div>}
      {isLoading && <p className="notice">Loading…</p>}

      {trips && trips.length === 0 && (
        <div className="card">
          <p className="notice">
            No trips yet. <Link to="/trips/new">Create your first one</Link>.
          </p>
        </div>
      )}

      {trips?.map((trip) => (
        <Link key={trip.id} to={`/trips/${trip.id}`} className="card card-link">
          <div className="spread">
            <strong>
              {TYPE_LABEL[trip.trip_type]} — {summarize(trip)}
            </strong>
            <span className={`badge ${trip.status}`}>{trip.status}</span>
          </div>
          <p className="muted">
            Created {new Date(trip.created_at).toLocaleString()}
          </p>
        </Link>
      ))}

      {isFetching && trips && trips.length > 0 && (
        <p className="muted">Refreshing…</p>
      )}
    </div>
  );
}
