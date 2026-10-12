import { useState, type MouseEvent } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { getStoredToken, setStoredToken } from "../lib/api";

const links = [
  { to: "/", label: "Alpha Pool", icon: "📊" },
  { to: "/runs", label: "Swarm Research", icon: "🐝" },
  { to: "/manual", label: "Manual Lab", icon: "🧪" },
  { to: "/strategy", label: "Strategy Backtest", icon: "📈" },
  { to: "/wiki", label: "Knowledge Vault", icon: "🧠" },
  { to: "/ops", label: "Operations", icon: "⚙️" },
];

type WikiDirtyWindow = Window & {
  __aiminerConfirmWikiDiscard?: () => boolean;
};

export function Layout() {
  const [token, setToken] = useState(() => getStoredToken());
  const [showTokenSettings, setShowTokenSettings] = useState(false);

  const confirmNavigation = (event: MouseEvent<HTMLAnchorElement>) => {
    const guard = (window as WikiDirtyWindow).__aiminerConfirmWikiDiscard;
    if (guard && !guard()) {
      event.preventDefault();
    }
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="eyebrow">Autonomous Alpha Swarm</p>
          <h1 className="brand-title">AI Alpha Miner</h1>
          <p className="muted brand-subtitle">
            LangGraph quantitative factor discovery workstation.
          </p>
        </div>

        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              onClick={confirmNavigation}
            >
              <span className="nav-icon">{link.icon}</span>
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button
            type="button"
            className="button button-text-sm"
            onClick={() => setShowTokenSettings(!showTokenSettings)}
          >
            {showTokenSettings ? "Hide Auth Settings" : "⚙️ API Auth Settings"}
          </button>

          {showTokenSettings && (
            <div className="token-settings-box">
              <label className="field">
                API Token
                <input
                  type="password"
                  autoComplete="off"
                  placeholder="Bearer token (optional for local API)"
                  value={token}
                  onChange={(event) => {
                    const nextToken = event.target.value;
                    setToken(nextToken);
                    setStoredToken(nextToken);
                  }}
                />
              </label>
              <p className="muted text-xs">
                Stored in browser localStorage for requests to authenticated deployments.
              </p>
            </div>
          )}

          <div className="version-info">
            <span className="status-dot online"></span>
            <span>AIMiner Workstation</span>
            <span className="badge-pill">AGPLv3</span>
          </div>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
