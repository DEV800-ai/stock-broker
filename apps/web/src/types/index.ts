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
export type AutonomyMode = "research_only" | "paper_only" | "preview_required";

export interface HealthStatus {
  status: string;
  db: boolean;
  market_data: boolean;
  ai: boolean;
}

export interface UniverseStats {
  total: number;
  active: number;
  tickers_with_bars: number;
}

export interface ScanRun {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: ScanRunStatus;
  tickers_scanned: number | null;
  tickers_flagged: number | null;
  phase: "fetching_bars" | "scoring" | null;
  total_tickers: number | null;
  tickers_processed: number | null;
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
  elliott_wave_context: string | null;
  news_summary: string | null;
  catalysts: string | null;
  confidence: ThesisConfidence | null;
  news_score: number | null;
}

export interface ThesisTranslation {
  thesis_id: number;
  language: "he";
  why_interesting: string;
  risk_factors: string;
  sector_context: string | null;
  peer_comparison: string | null;
  elliott_wave_context: string | null;
  news_summary: string | null;
  catalysts: string | null;
}

export interface TrackedTicker {
  id: number;
  ticker: string;
  notes: string | null;
  created_at: string;
  latest_price: number | null;
  latest_composite_score: number | null;
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

export interface AgentControl {
  scope: string;
  autonomy_mode: AutonomyMode;
  is_killed: boolean;
  killed_reason: string | null;
  killed_at: string | null;
  updated_at: string;
  updated_by: string | null;
}

export interface Position {
  ticker: string;
  shares: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  source: string;
}

export interface Portfolio {
  net_liquidation: number;
  cash: number;
  sector_values: Record<string, number>;
  realized_pnl_today: number;
  realized_pnl_week: number;
  positions: Position[];
}

export interface SourceBreakdown {
  trade_count: number;
  trade_status_counts: Record<string, number>;
  closed_trade_count: number;
  win_count: number;
  win_rate: number | null;
  avg_pnl_pct: number | null;
  outcome_counts: Record<string, number>;
}

export interface PaperTradingHealthReport {
  since: string | null;
  generated_at: string;
  earliest_activity: string | null;
  days_of_history: number | null;
  preview_count: number;
  preview_status_counts: Record<string, number>;
  risk_verdict_counts: Record<string, number>;
  trade_count: number;
  trade_status_counts: Record<string, number>;
  fill_status_counts: Record<string, number>;
  trade_source_counts: Record<string, number>;
  by_source: Record<string, SourceBreakdown>;
  closed_trade_count: number;
  win_count: number;
  win_rate: number | null;
  avg_pnl_pct: number | null;
  avg_entry_slippage_pct: number | null;
}

export interface PerformanceReview {
  id: number;
  period_start: string;
  period_end: string;
  generated_at: string;
  triggered_by: string;
  report: PaperTradingHealthReport;
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
  source: string;
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
