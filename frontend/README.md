# AI Travel Assistant — Frontend (React + TypeScript, web SPA)

Web single-page app for the FastAPI backend (issue #2). Vite + React + TypeScript,
with a typed API client (`lib/`) and the core screens wired up.

## Stack
- **React + TypeScript + Vite**
- **React Router** — SPA routing + auth guard
- **TanStack Query** — server state + the trip **polling** lifecycle
- **react-markdown** — render trip result markdown
- **OpenAPI-generated client** (`@hey-api/openapi-ts`) — later; supersedes the
  hand-written `lib/` client (needs the discriminated-union backend schema first)

## Test the frontend (step by step)

The SPA has no data of its own — every screen (login, trips, results) works only
through live API calls. So an end-to-end UI test needs **two terminals**: one for
the backend API, one for the Vite dev server. Run both from the repo root.

> Frontend-only checks that *don't* need the backend: `npm run typecheck` and
> `npm run build` (compile/bundle only — no login or trip behavior).

**1. Start the backend** (terminal 1):

```bash
cd backend
uv sync                 # first time only: install backend deps
uv run uvicorn api.travel_api:app --reload --port 8000
```

> Requires the backend `.env` (e.g. `JWT_SECRET_KEY`, `GROQ_API_KEY`,
> `SERP_API_KEY`). The server refuses to start without `JWT_SECRET_KEY`.

**2. Confirm the API URL** (terminal 2) — `frontend/.env` already points at the
backend; no edit needed for local dev:

```bash
cd frontend
cat .env                # → VITE_API_BASE=http://localhost:8000
```

**3. Install deps & start the dev server** (terminal 2):

```bash
npm install             # first time only
npm run dev             # → http://localhost:5173
```

**4. Click through in the browser** — open http://localhost:5173:
   1. **Register** a new account (password ≥ 8 chars) — you're signed in
      automatically and your email shows in the header.
   2. **New trip** → pick a type (try **flights**: origin `Singapore`,
      destination `Tokyo`, pick dates) → **Create trip**.
   3. On the **Trips** list the trip shows `pending` → `running` → `completed`
      (the list auto-refreshes every 3s; flights/hotels take ~1–2 min,
      itineraries a few minutes).
   4. Click the trip to see the rendered markdown result.
   5. On a **completed** trip, scroll to **Rate this trip** — pick stars (1–5),
      add an optional comment, **Submit rating**. Re-open the trip to see it
      prefilled; submitting again updates the rating (upsert).
   6. **Log out** (header) → you're routed back to login.

**5. Stop** — `Ctrl+C` in each terminal.

### Development scripts
All defined in `package.json`. During active development you mostly use
`npm run dev`; the others are for checking and shipping.

| Command | Type-checks? | Builds `dist/`? | Runs a server? | Use it to… |
|---|---|---|---|---|
| `npm run dev` | no | no (in-memory) | yes — :5173, hot reload | develop day-to-day (what step 3 above runs) |
| `npm run typecheck` | yes | no | no | quickly catch TypeScript errors; no backend needed |
| `npm run build` | yes | yes | no | produce the deployable bundle in `dist/` |
| `npm run preview` | no | no (serves existing `dist/`) | yes — :4173 | sanity-check the built `dist/` before deploying |

Details:
- **`dev`** (`vite`) — the dev server with hot module reload. Note Vite does
  **not** type-check here (it strips types for speed), so the app can run in the
  browser while still having type errors — run `typecheck` to surface them.
- **`typecheck`** (`tsc --noEmit`) — runs the TypeScript compiler as a pure
  checker (no output files). Fast correctness gate; safe to run anytime.
- **`build`** (`tsc && vite build`) — type-checks first (aborts on type errors),
  then bundles/minifies into `dist/`. That folder is the deployable artifact
  (gitignored).
- **`preview`** (`vite preview`) — serves the already-built `dist/` locally
  (~:4173) to test the *production* build. Run `npm run build` first; like `dev`,
  it still needs the backend reachable to actually function.

Normal loop while developing: `dev` to build features → `typecheck` to gate →
`build` + `preview` only when getting ready to deploy.

### Configuration
Backend URL via Vite env (`frontend/.env`):

```bash
VITE_API_BASE=http://localhost:8000   # configure to URL of FastAPI backend
# VITE_API_BASE=                       # same origin (if FastAPI serves the SPA)
```

## What's here
```
lib/                      # platform-agnostic typed client (reused by the app)
├── types.ts              # TS types mirroring backend schemas + 3 trip-type request shapes
├── env.ts                # API base URL (Vite import.meta.env.VITE_API_BASE)
├── auth.ts               # JWT token storage (localStorage)
└── api.ts                # typed client: register, login, listTrips, createTrip, ...
src/
├── main.tsx              # entry: QueryClientProvider + BrowserRouter
├── App.tsx               # routes (public login/register + guarded /trips/*)
├── format.ts             # ApiError → human-readable message
├── index.css             # styling
├── components/
│   ├── ProtectedRoute.tsx  # auth guard (redirect to /login)
│   ├── Layout.tsx          # header/nav + <Outlet/>
│   ├── TripResult.tsx      # renders result markdown by trip_type
│   ├── PipeTable.tsx       # flights/hotels pipe-delimited result → table
│   ├── RequestSummary.tsx  # renders a trip's request fields
│   └── FeedbackForm.tsx    # star rating + comment on a completed trip
├── hooks/
│   ├── useTrips.ts         # GET /trips with refetchInterval polling
│   └── useMe.ts            # GET /auth/me (current user)
└── pages/                # Login, Register, Trips, CreateTrip, TripDetail
```

## API contract (backend, on `develop`)
| Call | Endpoint | Notes |
|---|---|---|
| `register` | `POST /auth/register` | JSON `{email, password}` → `UserRead` |
| `login` | `POST /auth/login` | **form-encoded** (`username`=email) → `Token` |
| `getMe` | `GET /auth/me` | bearer; current user `{id, email, role}` |
| `listTrips` | `GET /trips` | bearer; newest-first |
| `createTrip` | `POST /trips` | bearer; `{trip_type, request}` → 202 `TripRead` (status `pending`) |
| `tripsAuthCheck` | `GET /trips/test` | bearer smoke-test |
| `submitFeedback` | `PUT /trips/{id}/feedback` | bearer; rate a **completed** trip `{rating 1-5, comment?}` → `FeedbackRead` (upsert) |
| `getFeedback` | `GET /trips/{id}/feedback` | bearer; the caller's feedback for a trip (404 if none yet) |
| `listUsers` | `GET /users` | bearer **admin only** |

Trip types: `itinerary` | `flights` | `hotels`, each with its own `request` shape
(see `types.ts`), incl. configurable guest counts (`adults`/`children`). Trips are
**async**: a create returns `status: pending` — **poll `GET /trips`** (TanStack
Query `refetchInterval`) until `completed`/`failed`, then render the markdown in
`result` (`itinerary_md`/`flights_md`/`hotels_md`).

## Screens
Built:
- Auth: **login**, **register**
- **Trips list** (polls for status) + **trip detail** (renders result markdown)
- **Create trip** form (type switch: itinerary / flights / hotels, incl. guests)
- **Feedback capture** — rate a completed trip (1–5 stars + comment) on the trip
  detail page; the rating UI upserts via `PUT /trips/{id}/feedback`.

Future work:
- **Admin users** screen (`GET /users`, role-gated) — the header already surfaces
  the current user's `admin` role via `GET /auth/me`.
