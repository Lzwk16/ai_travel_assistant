import { Link, useParams } from "react-router-dom";
import { useTrips } from "../hooks/useTrips";
import { formatError } from "../format";
import TripResult from "../components/TripResult";
import RequestSummary from "../components/RequestSummary";

const TYPE_LABEL: Record<string, string> = {
  itinerary: "Itinerary",
  flights: "Flights",
  hotels: "Hotels",
};

export default function TripDetailPage() {
  const { id } = useParams();
  // There is no GET /trips/{id} endpoint, so we read from the polled list
  // (which keeps refetching while the trip is pending/running).
  const { data: trips, isLoading, error } = useTrips();
  const trip = trips?.find((t) => String(t.id) === id);

  if (isLoading) return <p className="notice">Loading…</p>;
  if (error) return <div className="error">{formatError(error)}</div>;
  if (!trip) {
    return (
      <div>
        <p className="notice">Trip not found.</p>
        <Link to="/trips">← Back to trips</Link>
      </div>
    );
  }

  const isActive = trip.status === "pending" || trip.status === "running";

  return (
    <div>
      <p>
        <Link to="/trips">← Back to trips</Link>
      </p>
      <div className="spread">
        <h1>{TYPE_LABEL[trip.trip_type] ?? trip.trip_type}</h1>
        <span className={`badge ${trip.status}`}>{trip.status}</span>
      </div>

      <RequestSummary trip={trip} />

      {isActive ? (
        <p className="notice">
          This trip is {trip.status}. The page refreshes automatically — results
          appear when it completes (itineraries take a few minutes).
        </p>
      ) : (
        <TripResult trip={trip} />
      )}
    </div>
  );
}
