import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState, type MouseEvent } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  TOKEN_CHANGED_EVENT,
  getStoredToken,
  setStoredToken,
} from '../lib/api';

const links = [
  { to: '/', label: 'Catalog' },
  { to: '/review', label: 'Review' },
  { to: '/reproduce', label: 'Reproduce' },
  { to: '/agent', label: 'Agent' },
  { to: '/runs', label: 'Swarm Runs' },
  { to: '/pool', label: 'Alpha Pool' },
  { to: '/manual', label: 'Manual Backtest' },
  { to: '/strategy', label: 'Strategy Backtest' },
  { to: '/wiki', label: 'Wiki' },
  { to: '/ops', label: 'Operations' },
];

type WikiDirtyWindow = Window & {
  __aiminerConfirmWikiDiscard?: () => boolean;
};

export function Layout() {
  const [token, setToken] = useState(() => getStoredToken());
  const queryClient = useQueryClient();

  useEffect(() => {
    const onTokenChanged = () => {
      setToken(getStoredToken());
      void queryClient.invalidateQueries();
    };
    window.addEventListener(TOKEN_CHANGED_EVENT, onTokenChanged);
    return () => window.removeEventListener(TOKEN_CHANGED_EVENT, onTokenChanged);
  }, [queryClient]);

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
            Catalog, review, reproduce, swarm, and wiki. Promote, reproduce, and
            agent need the desk token (`FINAINCE_DESK_TOKEN`).
          </p>
        </div>
        <form onSubmit={(event) => event.preventDefault()}>
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
        </form>
        <p className="muted">
          Stored in localStorage and sent as `Authorization` plus `X-API-Key`.
        </p>
        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                isActive ? 'nav-link active' : 'nav-link'
              }
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
