export type WatchlistStatus = "watch" | "research" | "paper" | "avoid";
export type ThesisConfidence = "high" | "medium" | "low";
export type ScanRunStatus = "running" | "complete" | "failed";
export type PaperTradeStatus = "pending_approval" | "open" | "closed" | "rejected";
export type OrderAction = "BUY" | "SELL";
export type OrderExecutionMode = "paper" | "manual_tradingview";
export type OrderRiskStatus = "approved" | "warning" | "blocked";
export type OrderPreviewStatus = "pending" | "blocked" | "approved" | "rejected" | "expired" | "manual_recorded";
export type ManualExecutionOutcome =
  | "executed"
  | "executed_with_changes"
  | "rejected"
  | "watch_only"
  | "paper_tracked"
  | "cancelled";

export interface HealthStatus {
  status: string;
  db: boolean;
  ibkr_gateway: boolean;
  ai: boolean;
}

export interface UniverseStats {
  total: number;
  active: number;
  with_conid: number;
  tickers_with_bars: number;
}

export interface ScanRun {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: ScanRunStatus;
  tickers_scanned: number | null;
  tickers_flagged: number | null;
}

export interface ScanResult {
  id: number;
  ticker: string;
  scan_date: string;
  composite_score: number | null;
  volume_score: number | null;
  momentum_score: number | null;
  rs_score: number | null;
  gap_score: number | null;
  price: number | null;
  volume_ratio: number | null;
  pct_change_1d: number | null;
  pct_change_5d: number | null;
  rsi_14: number | null;
  signals_fired: Record<string, boolean> | null;
}

export interface WatchlistEntry {
  id: number;
  ticker: string;
  watchlist_date: string;
  rank: number;
  status: WatchlistStatus;
  composite_score: number | null;
  scan_result_id: number | null;
  thesis_id: number | null;
  notes: string | null;
  created_at: string;
}

export interface StockThesis {
  id: number;
  ticker: string;
  scan_result_id: number | null;
  generated_at: string;
  model: string | null;
  why_interesting: string;
  risk_factors: string;
  sector_context: string | null;
  peer_comparison: string | null;
  news_summary: string | null;
  catalysts: string | null;
  confidence: ThesisConfidence | null;
  news_score: number | null;
}

export interface OrderPreview {
  id: number;
  ticker: string;
  thesis_id: number | null;
  action: OrderAction;
  shares: number;
  order_type: string;
  limit_price: number;
  time_in_force: string;
  reason: string;
  bull_case: string | null;
  bear_case: string | null;
  portfolio_impact: string | null;
  risk_status: OrderRiskStatus;
  approval_required: boolean;
  status: OrderPreviewStatus;
  execution_mode: OrderExecutionMode;
  paper_trade_id: number | null;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface OrderPreviewDetail extends OrderPreview {
  risk_results: Record<string, unknown>[] | null;
}

export interface ManualExecutionResult {
  id: number;
  ticker: string;
  status: OrderPreviewStatus;
  execution_mode: OrderExecutionMode;
  paper_trade_id: number | null;
}

export interface PaperTrade {
  id: number;
  ticker: string;
  thesis_id: number | null;
  entry_date: string | null;
  entry_price: number | null;
  target_price: number | null;
  stop_price: number | null;
  shares: number | null;
  status: PaperTradeStatus;
  approved_by: string | null;
  approved_at: string | null;
  exit_price: number | null;
  exit_date: string | null;
  pnl: number | null;
  pnl_pct: number | null;
  hold_days: number | null;
  close_reason: string | null;
  notes: string | null;
  created_at: string;
}
