import { useState, type MouseEvent } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { getStoredToken, setStoredToken } from "../lib/api";

const links = [
  { to: "/", label: "Catalog" },
  { to: "/review", label: "Review" },
  { to: "/reproduce", label: "Reproduce" },
  { to: "/agent", label: "Agent" },
  { to: "/runs", label: "Swarm Runs" },
  { to: "/pool", label: "Alpha Pool" },
  { to: "/manual", label: "Manual Backtest" },
  { to: "/strategy", label: "Strategy Backtest" },
  { to: "/wiki", label: "Wiki" },
  { to: "/ops", label: "Operations" },
];

type WikiDirtyWindow = Window & {
  __aiminerConfirmWikiDiscard?: () => boolean;
};

export function Layout() {
  const [token, setToken] = useState(() => getStoredToken());
  const confirmNavigation = (event: MouseEvent<HTMLAnchorElement>) => {
    const guard = (window as WikiDirtyWindow).__aiminerConfirmWikiDiscard;
    if (guard && !guard()) {
      event.preventDefault();
    }
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">FinAlpha</p>
          <h1>Desk</h1>
          <p className="muted">
            Catalog, review, reproduce, swarm, and wiki. Report library remains on :8765.
          </p>
        </div>
        <label className="field">
          API Token
          <input
            type="password"
            autoComplete="off"
            placeholder="Bearer token or API key"
            value={token}
            onChange={(event) => {
              const nextToken = event.target.value;
              setToken(nextToken);
              setStoredToken(nextToken);
            }}
          />
        </label>
        <p className="muted">Stored in localStorage and sent as `Authorization` plus `X-API-Key`.</p>
        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              onClick={confirmNavigation}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
