// Backend API base URL.
// - Dev (separate host): set VITE_API_BASE, e.g. http://localhost:8000
// - Served by FastAPI (app.frontend, same origin): set VITE_API_BASE="" so
//   requests are relative.
export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
