// Typed API client for the FastAPI backend (backend/api/routers/*).
// All calls go through `request()`, which attaches the bearer token and clears
// the session on 401. Endpoints mirror the backend contract exactly.
import { API_BASE } from "./env";
import { clearToken, getToken, saveToken } from "./auth";
import type {
  FeedbackCreate,
  FeedbackRead,
  Token,
  TripCreate,
  TripRead,
  UserCreate,
  UserRead,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (res.status === 401) {
    clearToken();
    throw new ApiError(401, "Session expired — please sign in again.");
  }
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  // 202/empty-safe JSON parse
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

// ---- auth ----
export function register(body: UserCreate): Promise<UserRead> {
  return request<UserRead>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// Current user for the active token (id, email, role). The login token carries
// only the user id, so the SPA calls this to know who is signed in.
export function getMe(): Promise<UserRead> {
  return request<UserRead>("/auth/me");
}

// OAuth2PasswordRequestForm: form-encoded, email carried in `username`.
export async function login(email: string, password: string): Promise<Token> {
  const form = new URLSearchParams({ username: email, password });
  const token = await request<Token>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  saveToken(token.access_token);
  return token;
}

// ---- trips ----
export function listTrips(): Promise<TripRead[]> {
  return request<TripRead[]>("/trips");
}

export function createTrip(body: TripCreate): Promise<TripRead> {
  return request<TripRead>("/trips", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function tripsAuthCheck(): Promise<{ message: string }> {
  return request<{ message: string }>("/trips/test");
}

// ---- feedback for a completed trip ----
// PUT (idempotent upsert): re-submitting a trip overwrites the prior feedback.
export function submitFeedback(
  tripId: number,
  body: FeedbackCreate,
): Promise<FeedbackRead> {
  return request<FeedbackRead>(`/trips/${tripId}/feedback`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// Current user's feedback for a trip; rejects with ApiError(404) if none yet.
export function getFeedback(tripId: number): Promise<FeedbackRead> {
  return request<FeedbackRead>(`/trips/${tripId}/feedback`);
}

// ---- admin ----
export function listUsers(): Promise<UserRead[]> {
  return request<UserRead[]>("/users");
}
