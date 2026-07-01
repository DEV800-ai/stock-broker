import type {
  HealthStatus,
  PaperTrade,
  ScanResult,
  ScanRun,
  StockThesis,
  UniverseStats,
  WatchlistEntry,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<HealthStatus>("/api/v1/health"),

  universe: () => apiFetch<UniverseStats>("/api/v1/universe"),

  scanRuns: (limit = 20) => apiFetch<ScanRun[]>(`/api/v1/scanner/runs?limit=${limit}`),

  triggerScan: () =>
    apiFetch<{ message: string }>("/api/v1/scanner/trigger", { method: "POST" }),

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

  paperTrades: () => apiFetch<PaperTrade[]>("/api/v1/paper-trades"),
};
