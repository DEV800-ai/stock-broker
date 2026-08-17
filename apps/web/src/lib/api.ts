import type {
  AgentControl,
  AutonomyMode,
  HealthStatus,
  ManualExecutionOutcome,
  ManualExecutionResult,
  OrderPreview,
  OrderPreviewDetail,
  PaperTrade,
  Portfolio,
  ScanResult,
  ScanRun,
  StockThesis,
  UniverseStats,
  WatchlistEntry,
} from "@/types";

// Requests go to this Next.js app's own /api/backend proxy (see
// src/app/api/backend/[...path]/route.ts), never directly to the FastAPI backend. The proxy
// attaches X-API-Key server-side, so the key never ships in browser JS — see that route's
// comment for why. Do not reintroduce a NEXT_PUBLIC_API_KEY here.
const API_BASE = "/api/backend";
const ACTOR = process.env.NEXT_PUBLIC_ACTOR ?? "operator";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Actor": ACTOR,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<HealthStatus>("/api/v1/health"),

  universe: () => apiFetch<UniverseStats>("/api/v1/universe"),

  scanRuns: (limit = 20) => apiFetch<ScanRun[]>(`/api/v1/scanner/runs?limit=${limit}`),

  triggerScan: () =>
    apiFetch<{ message: string }>("/api/v1/scanner/trigger", { method: "POST" }),

  deleteScanRun: (runId: number) =>
    apiFetch<void>(`/api/v1/scanner/runs/${runId}`, { method: "DELETE" }),

  scanResults: (params?: { date?: string; min_score?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.date) q.set("scan_date", params.date);
    if (params?.min_score != null) q.set("min_score", String(params.min_score));
    if (params?.limit) q.set("limit", String(params.limit));
    return apiFetch<ScanResult[]>(`/api/v1/scanner/results?${q}`);
  },

  watchlist: (params?: { date?: string; status?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.date) q.set("watchlist_date", params.date);
    if (params?.status) q.set("status", params.status);
    if (params?.limit) q.set("limit", String(params.limit));
    return apiFetch<WatchlistEntry[]>(`/api/v1/watchlist?${q}`);
  },

  updateWatchlistStatus: (ticker: string, status: string) =>
    apiFetch<WatchlistEntry>(`/api/v1/watchlist/${ticker}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),

  thesis: (ticker: string) => apiFetch<StockThesis>(`/api/v1/thesis/${ticker}`),

  generateThesis: (ticker: string, scanResultId?: number) =>
    apiFetch<{ message: string }>("/api/v1/thesis/generate", {
      method: "POST",
      body: JSON.stringify({ ticker, scan_result_id: scanResultId }),
    }),

  latestScanResult: (ticker: string) =>
    apiFetch<ScanResult>(`/api/v1/scanner/results/${ticker}`),

  tradingViewUrl: (ticker: string) =>
    apiFetch<{ url: string }>(`/api/v1/scanner/results/${ticker}/tradingview`),

  paperTrades: () => apiFetch<PaperTrade[]>("/api/v1/paper-trades"),

  portfolio: () => apiFetch<Portfolio>("/api/v1/portfolio"),

  createPaperTrade: (body: {
    ticker: string;
    thesis_id?: number;
    entry_price: number;
    target_price?: number;
    stop_price?: number;
    shares?: number;
    notes?: string;
  }) =>
    apiFetch<PaperTrade>("/api/v1/paper-trades", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  approveTrade: (id: number) =>
    apiFetch<PaperTrade>(`/api/v1/paper-trades/${id}/approve`, { method: "PUT" }),

  rejectTrade: (id: number) =>
    apiFetch<PaperTrade>(`/api/v1/paper-trades/${id}/reject`, { method: "PUT" }),

  closeTrade: (id: number, exit_price: number, close_reason = "manual") =>
    apiFetch<PaperTrade>(`/api/v1/paper-trades/${id}/close`, {
      method: "PUT",
      body: JSON.stringify({ exit_price, close_reason }),
    }),

  createOrderPreview: (body: {
    ticker: string;
    action: string;
    reason: string;
    thesis_id?: number;
    shares?: number;
    amount_usd?: number;
    limit_price?: number;
    order_type?: string;
    time_in_force?: string;
    execution_mode?: string;
  }) =>
    apiFetch<OrderPreviewDetail>("/api/v1/orders/preview", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  orderQueue: () => apiFetch<OrderPreview[]>("/api/v1/orders/queue"),

  orderPreview: (id: number) => apiFetch<OrderPreviewDetail>(`/api/v1/orders/${id}`),

  approveOrder: (id: number) =>
    apiFetch<OrderPreview>(`/api/v1/orders/${id}/approve`, { method: "POST" }),

  rejectOrder: (id: number) =>
    apiFetch<OrderPreview>(`/api/v1/orders/${id}/reject`, { method: "POST" }),

  openOrderInTradingView: (id: number) =>
    apiFetch<{ url: string }>(`/api/v1/orders/${id}/open-tradingview`, { method: "POST" }),

  ordersAwaitingConfirmation: () => apiFetch<OrderPreview[]>("/api/v1/orders/awaiting-confirmation"),

  recordManualExecution: (
    id: number,
    body: {
      outcome: ManualExecutionOutcome;
      actual_price?: number;
      actual_quantity?: number;
      actual_order_type?: string;
      notes?: string;
    }
  ) =>
    apiFetch<ManualExecutionResult>(`/api/v1/manual-execution/${id}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  agentControl: () => apiFetch<AgentControl>("/api/v1/agent-control"),

  killAgent: (reason: string) =>
    apiFetch<AgentControl>("/api/v1/agent-control/kill", {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  unkillAgent: () =>
    apiFetch<AgentControl>("/api/v1/agent-control/unkill", { method: "POST" }),

  setAutonomyMode: (mode: AutonomyMode) =>
    apiFetch<AgentControl>("/api/v1/agent-control/autonomy-mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
};
