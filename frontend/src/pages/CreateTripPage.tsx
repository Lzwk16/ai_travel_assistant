import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { createTrip } from "../../lib/api";
import { formatError } from "../format";
import type {
  BudgetType,
  TravelStyle,
  TripCreate,
  TripType,
} from "../../lib/types";

const toList = (s: string): string[] =>
  s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

export default function CreateTripPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [tripType, setTripType] = useState<TripType>("itinerary");
  // shared
  const [origin, setOrigin] = useState("Singapore");
  const [destinations, setDestinations] = useState("Tokyo");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [currency, setCurrency] = useState("SGD");
  // itinerary
  const [groupSize, setGroupSize] = useState(2);
  const [budgetType, setBudgetType] = useState<BudgetType>("mid-range");
  const [interests, setInterests] = useState("food, culture");
  const [travelStyle, setTravelStyle] = useState<TravelStyle>("relax");
  // flights / hotels
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function buildBody(): TripCreate {
    const dests = toList(destinations);
    if (tripType === "itinerary") {
      return {
        trip_type: "itinerary",
        request: {
          origin,
          destinations: dests,
          start_date: startDate,
          end_date: endDate,
          group_size: groupSize,
          budget_type: budgetType,
          interests: toList(interests),
          travel_style: travelStyle,
          currency,
        },
      };
    }
    if (tripType === "flights") {
      return {
        trip_type: "flights",
        request: {
          origin,
          destinations: dests,
          start_date: startDate,
          end_date: endDate,
          currency,
          adults,
        },
      };
    }
    return {
      trip_type: "hotels",
      request: {
        destinations: dests,
        start_date: startDate,
        end_date: endDate,
        currency,
        adults,
        children,
      },
    };
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await createTrip(buildBody());
      await queryClient.invalidateQueries({ queryKey: ["trips"] });
      navigate("/trips");
    } catch (err) {
      setError(formatError(err));
    } finally {
      setBusy(false);
    }
  }

  const needsOrigin = tripType === "itinerary" || tripType === "flights";

  return (
    <div className="container narrow">
      <h1>New trip</h1>
      <form className="card" onSubmit={onSubmit}>
        {error && <div className="error">{error}</div>}

        <label htmlFor="trip_type">Trip type</label>
        <select
          id="trip_type"
          value={tripType}
          onChange={(e) => setTripType(e.target.value as TripType)}
        >
          <option value="itinerary">Itinerary — day-by-day plan</option>
          <option value="flights">Flights — round-trip search</option>
          <option value="hotels">Hotels — per-city search</option>
        </select>

        {needsOrigin && (
          <>
            <label htmlFor="origin">Origin</label>
            <input
              id="origin"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              required
            />
          </>
        )}

        <label htmlFor="destinations">Destinations</label>
        <input
          id="destinations"
          value={destinations}
          onChange={(e) => setDestinations(e.target.value)}
          required
        />
        <p className="hint">Comma-separated, e.g. "Tokyo, Osaka".</p>

        <div className="row">
          <div>
            <label htmlFor="start">Start date</label>
            <input
              id="start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="end">End date</label>
            <input
              id="end"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </div>
        </div>

        <label htmlFor="currency">Currency</label>
        <input
          id="currency"
          value={currency}
          onChange={(e) => setCurrency(e.target.value)}
        />

        {tripType === "itinerary" && (
          <>
            <div className="row">
              <div>
                <label htmlFor="group">Group size</label>
                <input
                  id="group"
                  type="number"
                  min={1}
                  value={groupSize}
                  onChange={(e) => setGroupSize(Number(e.target.value))}
                />
              </div>
              <div>
                <label htmlFor="budget">Budget</label>
                <select
                  id="budget"
                  value={budgetType}
                  onChange={(e) => setBudgetType(e.target.value as BudgetType)}
                >
                  <option value="budget">Budget</option>
                  <option value="mid-range">Mid-range</option>
                  <option value="luxury">Luxury</option>
                </select>
              </div>
            </div>
            <label htmlFor="style">Travel style</label>
            <select
              id="style"
              value={travelStyle}
              onChange={(e) => setTravelStyle(e.target.value as TravelStyle)}
            >
              <option value="relax">Relax</option>
              <option value="adventure">Adventure</option>
              <option value="business">Business</option>
            </select>
            <label htmlFor="interests">Interests</label>
            <input
              id="interests"
              value={interests}
              onChange={(e) => setInterests(e.target.value)}
            />
            <p className="hint">Comma-separated, e.g. "food, culture".</p>
          </>
        )}

        {(tripType === "flights" || tripType === "hotels") && (
          <div className="row">
            <div>
              <label htmlFor="adults">Adults</label>
              <input
                id="adults"
                type="number"
                min={1}
                value={adults}
                onChange={(e) => setAdults(Number(e.target.value))}
              />
            </div>
            {tripType === "hotels" && (
              <div>
                <label htmlFor="children">Children</label>
                <input
                  id="children"
                  type="number"
                  min={0}
                  value={children}
                  onChange={(e) => setChildren(Number(e.target.value))}
                />
              </div>
            )}
          </div>
        )}

        <div style={{ marginTop: "1.25rem" }}>
          <button type="submit" disabled={busy}>
            {busy ? "Submitting…" : "Create trip"}
          </button>
        </div>
        <p className="hint">
          Runs in the background — you'll see it as “pending” then “completed”.
        </p>
      </form>
    </div>
  );
}
