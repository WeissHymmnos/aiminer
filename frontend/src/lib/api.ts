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
export const TOKEN_STORAGE_KEY = "aiminer.apiToken";
export const TOKEN_CHANGED_EVENT = "aiminer:api-token-changed";

type PaginationParams = {
  offset?: number;
  limit?: number;
};

type RunScopedPaginationParams = PaginationParams & {
  runId?: string;
};

type RunLogParams = PaginationParams & {
  tail?: boolean;
};

type RunStatusView = {
  canStop: boolean;
  isStopping: boolean;
  isTerminal: boolean;
  label: string;
  showDelete: boolean;
};

export class ApiError extends Error {
  status: number;
  detail: string;
  retryable: boolean;

  constructor(message: string, options: { status: number; detail?: string; retryable: boolean }) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.detail = options.detail ?? message;
    this.retryable = options.retryable;
  }
}

export function getStoredToken() {
  if (typeof window === "undefined") {
    return (import.meta.env.VITE_API_AUTH_TOKEN ?? "").trim();
  }
  return (window.localStorage.getItem(TOKEN_STORAGE_KEY) ?? import.meta.env.VITE_API_AUTH_TOKEN ?? "").trim();
}

export function getBearerlessToken(value = getStoredToken()) {
  return value.replace(/^Bearer\s+/i, "").trim();
}

export function setStoredToken(value: string) {
  if (typeof window === "undefined") {
    return;
  }
  const previous = getStoredToken();
  const normalized = value.trim();
  if (normalized) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, normalized);
  } else {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
  const next = getStoredToken();
  if (next !== previous) {
    window.dispatchEvent(new CustomEvent(TOKEN_CHANGED_EVENT, { detail: { token: next } }));
  }
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

function extractErrorDetail(payload: unknown) {
  if (typeof payload === "string") {
    return payload;
  }
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (detail !== undefined) {
      try {
        return JSON.stringify(detail);
      } catch {
        return String(detail);
      }
    }
  }
  return "";
}

function toApiError(status: number, detail: string) {
  const message = detail || `Request failed: ${status}`;
  return new ApiError(message, {
    status,
    detail,
    retryable: status >= 500 || status === 429,
  });
}

function resolveRunScopedPagination(
  value?: string | RunScopedPaginationParams,
  page?: PaginationParams,
): RunScopedPaginationParams {
  if (typeof value === "string") {
    return { runId: value, ...(page ?? {}) };
  }
  return value ?? {};
}

export function getErrorMessage(error: unknown, fallback = "Request failed.") {
  if (error instanceof ApiError) {
    return error.detail || error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  return fallback;
}

export function getRunStatusView(
  run: Pick<SwarmRunSummary, "status" | "is_active"> | null | undefined,
  options: { stopRequested?: boolean } = {},
): RunStatusView {
  const rawStatus = String(run?.status ?? "loading").toLowerCase();
  const isActive = Boolean(run?.is_active);
  const stopRequested = Boolean(options.stopRequested);

  if (!run) {
    return {
      canStop: false,
      isStopping: false,
      isTerminal: false,
      label: "loading",
      showDelete: false,
    };
  }

  if (stopRequested || rawStatus === "stopping" || (rawStatus === "stopped" && isActive)) {
    return {
      canStop: false,
      isStopping: true,
      isTerminal: false,
      label: "stopping",
      showDelete: false,
    };
  }

  if (["completed", "failed", "stopped"].includes(rawStatus)) {
    return {
      canStop: false,
      isStopping: false,
      isTerminal: true,
      label: rawStatus,
      showDelete: true,
    };
  }

  if (["pending", "running"].includes(rawStatus)) {
    return {
      canStop: true,
      isStopping: false,
      isTerminal: false,
      label: rawStatus,
      showDelete: false,
    };
  }

  return {
    canStop: false,
    isStopping: false,
    isTerminal: false,
    label: rawStatus,
    showDelete: false,
  };
}

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const storedToken = getStoredToken();
  if (storedToken) {
    const apiKey = getBearerlessToken(storedToken);
    headers.set("Authorization", /^Bearer\s+/i.test(storedToken) ? storedToken : `Bearer ${apiKey}`);
    headers.set("X-API-Key", apiKey);
  }

  const response = await fetch(withBase(input), {
    ...init,
    headers,
  });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      try {
        const payload = (await response.json()) as unknown;
        throw toApiError(response.status, extractErrorDetail(payload));
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
      }
    }
    const text = await response.text();
    throw toApiError(response.status, text);
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>;
  }
  return response.text() as Promise<T>;
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
  manualBacktestChartUrl: (jobId: string, cacheKey?: string | number) =>
    withBase(withQuery(`/api/charts/${jobId}`, { t: cacheKey })),
  listRuns: (params: PaginationParams = {}) =>
    request<Paginated<SwarmRunSummary>>(withQuery("/api/swarm/runs", params)),
  getRun: (runId: string) => request<SwarmRunSummary>(`/api/swarm/runs/${runId}`),
  listAllRuns: () => requestAllPages<SwarmRunSummary>("/api/swarm/runs"),
  getRunLogs: (runId: string, paramsOrOffset: RunLogParams | number = 0, limit = 200, tail = false) => {
    const params =
      typeof paramsOrOffset === "number" ? { offset: paramsOrOffset, limit, tail } : paramsOrOffset;
    return request<Paginated<Record<string, unknown>>>(
      withQuery(`/api/swarm/runs/${runId}/logs`, {
        offset: params.offset,
        limit: params.limit,
        tail: params.tail || undefined,
      }),
    );
  },
  startRun: (payload: Record<string, unknown>) =>
    request<{ status: string; run_id: string }>("/api/swarm/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  stopRun: (runId: string) =>
    request<{ status: string; run_id: string }>(`/api/swarm/runs/${runId}/stop`, {
      method: "POST",
    }),
  deleteRun: (runId: string) =>
    request<{ status: string; run_id: string }>(`/api/swarm/runs/${runId}`, {
      method: "DELETE",
    }),
  swarmStatus: () =>
    request<{ running_count: number; active_run_ids: string[]; max_concurrent: number }>(
      "/api/swarm/status",
    ),
  listFactors: (options?: string | RunScopedPaginationParams, page?: PaginationParams) => {
    const { runId, offset, limit } = resolveRunScopedPagination(options, page);
    return request<Paginated<FactorSummary>>(withQuery("/api/results", { run_id: runId, offset, limit }));
  },
  listAllFactors: (runId?: string) =>
    requestAllPages<FactorSummary>(withQuery("/api/results", { run_id: runId })),
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
  deleteBacktest: (jobId: string) =>
    request<{ status: string; job_id: string }>(`/api/backtest/${jobId}`, {
      method: "DELETE",
    }),
  getStrategies: (options?: string | RunScopedPaginationParams, page?: PaginationParams) => {
    const { runId, offset, limit } = resolveRunScopedPagination(options, page);
    return request<Paginated<StrategySummary>>(
      withQuery("/api/strategies", { run_id: runId, offset, limit }),
    );
  },
  listAllStrategies: (runId?: string) =>
    requestAllPages<StrategySummary>(withQuery("/api/strategies", { run_id: runId })),
  getStrategy: (strategyId: string) =>
    request<Record<string, unknown>>(`/api/strategies/${strategyId}`),
  runStrategy: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/strategy/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  strategyHistory: () => request<Record<string, unknown>[]>("/api/strategy/history"),
  deleteStrategy: (strategyId: string) =>
    request<{ status: string; strategy_id: string }>(`/api/strategy/${strategyId}`, {
      method: "DELETE",
    }),
  wikiIndex: (params: PaginationParams = {}) =>
    request<Paginated<Record<string, unknown>>>(withQuery("/api/wiki/index", params)),
  wikiIndexAll: () => requestAllPages<Record<string, unknown>>("/api/wiki/index"),
  wikiPage: (slug: string) => request<string>(`/api/wiki/page/${slug}`),
  updateWikiPage: (slug: string, content: string) =>
    request<{ status: string; slug: string; bytes: number }>(`/api/wiki/page/${slug}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  wikiGraph: () => request<{ nodes: WikiGraphNode[]; edges: WikiGraphEdge[] }>("/api/wiki/graph"),
  wikiLint: (staleDays = 30) =>
    request<Record<string, unknown>>(withQuery("/api/wiki/lint", { stale_days: staleDays }), {
      method: "POST",
    }),
  wikiMigrate: (dryRun = true) =>
    request<Record<string, unknown>>(withQuery("/api/wiki/migrate", { dry_run: dryRun }), {
      method: "POST",
    }),
  adminReset: (payload: {
    scopes?: string[];
    confirm?: boolean;
    reset_token?: string;
  }) =>
    request<Record<string, unknown>>("/api/admin/reset", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
