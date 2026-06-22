// Types mirroring the FastAPI backend contract (backend/api/schemas.py +
// the per-trip-type request models). Dates are ISO strings over the wire.

export type Role = "user" | "admin";
export type TripType = "itinerary" | "flights" | "hotels";
export type TripStatus = "pending" | "running" | "completed" | "failed";
export type BudgetType = "budget" | "mid-range" | "luxury";
export type TravelStyle = "relax" | "adventure" | "business";

// ---- auth ----
export interface UserCreate {
  email: string;
  password: string; // min length 8 (enforced server-side)
}

export interface UserRead {
  id: number;
  email: string;
  role: Role;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string; // "bearer"
}

// ---- feedback (T1 Stage 0) ----
export interface FeedbackCreate {
  rating: number; // 1-5
  comment?: string | null;
}

export interface FeedbackRead {
  id: number;
  trip_id: number;
  user_id: number;
  rating: number;
  comment: string | null;
  created_at: string;
}

// ---- per-trip-type request payloads (the `request` field of TripCreate) ----
export interface ItineraryRequest {
  origin: string;
  destinations: string[];
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
  group_size: number;
  budget_type: BudgetType;
  interests: string[];
  travel_style: TravelStyle;
  currency?: string; // default "SGD"
}

export interface FlightRequest {
  origin: string;
  destinations: string[];
  start_date: string;
  end_date: string;
  currency?: string;
  adults?: number; // default 1, >= 1
}

export interface HotelRequest {
  destinations: string[];
  start_date: string;
  end_date: string;
  currency?: string;
  adults?: number; // default 2, >= 1
  children?: number; // default 0, >= 0
}

export type TripRequest = ItineraryRequest | FlightRequest | HotelRequest;

// Discriminated body for POST /trips.
export type TripCreate =
  | { trip_type: "itinerary"; request: ItineraryRequest }
  | { trip_type: "flights"; request: FlightRequest }
  | { trip_type: "hotels"; request: HotelRequest };

// ---- trip result shapes (the `result` field of TripRead, by trip_type) ----
export interface ItineraryResult {
  insights_md: string | null;
  itinerary_md: string | null;
}
export interface FlightsResult {
  flights_md: string | null;
}
export interface HotelsResult {
  hotels_md: string | null;
}
export type TripResult =
  | ItineraryResult
  | FlightsResult
  | HotelsResult
  | { error: string }
  | null;

export interface TripRead {
  id: number;
  trip_type: TripType;
  status: TripStatus;
  request: Record<string, unknown>;
  result: TripResult;
  created_at: string;
  completed_at: string | null;
}
