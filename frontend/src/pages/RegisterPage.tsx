import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, register } from "../../lib/api";
import { formatError } from "../format";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await register({ email, password });
      await login(email, password); // auto sign-in after registering
      navigate("/trips", { replace: true });
    } catch (err) {
      setError(formatError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container narrow">
      <h1>Create account</h1>
      <form className="card" onSubmit={onSubmit}>
        {error && <div className="error">{error}</div>}
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <p className="hint">At least 8 characters.</p>
        <div style={{ marginTop: "1rem" }}>
          <button type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create account"}
          </button>
        </div>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </div>
  );
}
