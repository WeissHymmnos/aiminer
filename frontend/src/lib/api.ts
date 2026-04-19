import type {
  FactorSummary,
  Paginated,
  StrategySummary,
  SwarmRunSummary,
  WikiGraphEdge,
  WikiGraphNode,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const PAGE_LIMIT = 200;

export function getStoredToken() {
  return window.localStorage.getItem("aiminer_auth_token") ?? "";
}

export function setStoredToken(value: string) {
  window.localStorage.setItem("aiminer_auth_token", value);
}

function withBase(path: string) {
  return `${API_BASE_URL}${path}`;
}

function withQuery(path: string, params: Record<string, string | number | boolean | null | undefined>) {
  const [pathname, search = ""] = path.split("?");
  const query = new URLSearchParams(search);
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    query.set(key, String(value));
  }
  const queryString = query.toString();
  return queryString ? `${pathname}?${queryString}` : pathname;
}

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const response = await fetch(withBase(input), {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      try {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail || `Request failed: ${response.status}`);
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
      }
    }
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>;
  }
  return response.text() as T;
}

async function requestAllPages<T>(path: string): Promise<T[]> {
  const items: T[] = [];
  let offset = 0;

  for (;;) {
    const page = await request<Paginated<T>>(withQuery(path, { offset, limit: PAGE_LIMIT }));
    items.push(...page.items);
    if (!page.items.length || page.next_offset <= offset || page.next_offset >= page.total) {
      break;
    }
    offset = page.next_offset;
  }

  return items;
}

export const api = {
  listRuns: () => request<Paginated<SwarmRunSummary>>("/api/swarm/runs"),
  getRun: (runId: string) => request<SwarmRunSummary>(`/api/swarm/runs/${runId}`),
  listAllRuns: () => requestAllPages<SwarmRunSummary>("/api/swarm/runs"),
  getRunLogs: (runId: string, offset = 0, limit = 200, tail = false) =>
    request<Paginated<Record<string, unknown>>>(
      withQuery(`/api/swarm/runs/${runId}/logs`, { offset, limit, tail: tail || undefined }),
    ),
  startRun: (payload: Record<string, unknown>) =>
    request<{ status: string; run_id: string }>("/api/swarm/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  stopRun: (runId: string) =>
    request<{ status: string; run_id: string }>(`/api/swarm/runs/${runId}/stop`, {
      method: "POST",
    }),
  swarmStatus: () =>
    request<{ running_count: number; active_run_ids: string[]; max_concurrent: number }>(
      "/api/swarm/status",
    ),
  listFactors: (runId?: string) =>
    request<Paginated<FactorSummary>>(runId ? `/api/results?run_id=${runId}` : "/api/results"),
  listAllFactors: (runId?: string) =>
    requestAllPages<FactorSummary>(runId ? withQuery("/api/results", { run_id: runId }) : "/api/results"),
  getFactor: (factorId: string) => request<Record<string, unknown>>(`/api/factors/${factorId}`),
  getBacktest: (jobId: string) => request<Record<string, unknown>>(`/api/backtest/${jobId}`),
  runBacktest: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/backtest/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  validateBacktest: (payload: Record<string, unknown>) =>
    request<{ ok: boolean; message: string }>("/api/backtest/validate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  backtestHistory: () => request<Record<string, unknown>[]>("/api/backtest/history"),
  getStrategies: (runId?: string) =>
    request<Paginated<StrategySummary>>(runId ? `/api/strategies?run_id=${runId}` : "/api/strategies"),
  listAllStrategies: (runId?: string) =>
    requestAllPages<StrategySummary>(
      runId ? withQuery("/api/strategies", { run_id: runId }) : "/api/strategies",
    ),
  getStrategy: (strategyId: string) =>
    request<Record<string, unknown>>(`/api/strategies/${strategyId}`),
  runStrategy: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/strategy/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  strategyHistory: () => request<Record<string, unknown>[]>("/api/strategy/history"),
  wikiIndex: () => request<Paginated<Record<string, unknown>>>("/api/wiki/index"),
  wikiIndexAll: () => requestAllPages<Record<string, unknown>>("/api/wiki/index"),
  wikiPage: (slug: string) => request<string>(`/api/wiki/page/${slug}`),
  wikiGraph: () => request<{ nodes: WikiGraphNode[]; edges: WikiGraphEdge[] }>("/api/wiki/graph"),
};
