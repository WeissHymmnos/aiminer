import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { getStoredToken, setStoredToken } from "../lib/api";

const links = [
  { to: "/", label: "Swarm Runs" },
  { to: "/pool", label: "Alpha Pool" },
  { to: "/manual", label: "Manual Backtest" },
  { to: "/strategy", label: "Strategy Backtest" },
  { to: "/wiki", label: "Wiki" },
];

export function Layout() {
  const [token, setToken] = useState("");

  useEffect(() => {
    setToken(getStoredToken());
  }, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">AIMiner</p>
          <h1>Web Workstation</h1>
          <p className="muted">
            Concurrent swarm runs, factor pool inspection, manual and strategy
            backtests, plus Obsidian-style wiki graph navigation.
          </p>
        </div>
        <label className="field">
          API Token
          <input
            type="password"
            value={token}
            onChange={(event) => {
              const next = event.target.value;
              setToken(next);
              setStoredToken(next);
            }}
            placeholder="AIMINER_AUTH_TOKEN"
          />
        </label>
        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
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
