import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { clearToken } from "../../lib/auth";
import { useMe } from "../hooks/useMe";

// App chrome for authenticated pages: header + routed <Outlet/>.
export default function Layout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: me } = useMe();

  function logout() {
    clearToken();
    queryClient.clear(); // drop cached user/trips so the next login starts clean
    navigate("/login", { replace: true });
  }

  return (
    <>
      <header className="app-header">
        <span className="brand">✈️ AI Travel Assistant</span>
        <nav>
          <NavLink to="/trips" end>
            Trips
          </NavLink>
          <NavLink to="/trips/new">New trip</NavLink>
          {me && (
            <span className="muted">
              {me.email}
              {me.role === "admin" ? " (admin)" : ""}
            </span>
          )}
          <button className="secondary" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
