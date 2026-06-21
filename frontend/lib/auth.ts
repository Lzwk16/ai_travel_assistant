// JWT access-token storage for the web SPA.
// The backend issues a single bearer token from POST /auth/login (no refresh
// token), so on 401 the client clears it and routes back to login.
// localStorage is the pragmatic choice for bearer auth; swap to in-memory if you
// want stronger XSS resistance (at the cost of losing the session on refresh).
const TOKEN_KEY = "access_token";

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}
