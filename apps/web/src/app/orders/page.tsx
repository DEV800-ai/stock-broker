"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { TradingViewWidget } from "@/components/tradingview-widget";
import type { ManualExecutionOutcome, OrderPreview } from "@/types";

interface CreateForm {
  ticker: string;
  action: "BUY" | "SELL";
  reason: string;
  shares: string;
  limit_price: string;
  order_type: string;
  time_in_force: string;
  execution_mode: "paper" | "manual_tradingview";
}

const EMPTY_FORM: CreateForm = {
  ticker: "",
  action: "BUY",
  reason: "",
  shares: "1",
  limit_price: "",
  order_type: "LIMIT",
  time_in_force: "DAY",
  execution_mode: "paper",
};

const RISK_BADGE: Record<string, string> = {
  approved: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  blocked: "bg-red-100 text-red-700",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-blue-100 text-blue-800",
  blocked: "bg-red-100 text-red-700",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-zinc-100 text-zinc-600",
  expired: "bg-zinc-100 text-zinc-600",
  manual_recorded: "bg-zinc-100 text-zinc-600",
};

const OUTCOMES: { value: ManualExecutionOutcome; label: string }[] = [
  { value: "executed", label: "Executed as previewed" },
  { value: "executed_with_changes", label: "Executed with changes" },
  { value: "rejected", label: "Rejected in TradingView" },
  { value: "watch_only", label: "Watch only — no trade" },
  { value: "paper_tracked", label: "Tracking as paper only" },
  { value: "cancelled", label: "Cancelled" },
];

const POSITION_OUTCOMES: ManualExecutionOutcome[] = ["executed", "executed_with_changes"];

interface OutcomeForm {
  outcome: ManualExecutionOutcome;
  actual_price: string;
  actual_quantity: string;
  actual_order_type: string;
  notes: string;
}

function emptyOutcomeForm(p: OrderPreview): OutcomeForm {
  return {
    outcome: "executed",
    actual_price: String(p.limit_price),
    actual_quantity: String(p.shares),
    actual_order_type: p.order_type,
    notes: "",
  };
}

function orderDetailText(p: OrderPreview): string {
  return [
    `${p.action} ${p.shares} ${p.ticker}`,
    `${p.order_type} @ ${p.limit_price.toFixed(2)}`,
    `TIF: ${p.time_in_force}`,
  ].join("\n");
}

export default function OrdersPage() {
  const [previews, setPreviews] = useState<OrderPreview[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [tvPreview, setTvPreview] = useState<OrderPreview | null>(null);
  const [copied, setCopied] = useState(false);
  const [chartId, setChartId] = useState<number | null>(null);
  const [awaiting, setAwaiting] = useState<OrderPreview[]>([]);
  const [awaitChartId, setAwaitChartId] = useState<number | null>(null);
  const [outcomePreview, setOutcomePreview] = useState<OrderPreview | null>(null);
  const [outcomeForm, setOutcomeForm] = useState<OutcomeForm | null>(null);
  const [outcomeSubmitting, setOutcomeSubmitting] = useState(false);
  const [outcomeError, setOutcomeError] = useState<string | null>(null);

  function load() {
    api.orderQueue().then(setPreviews).catch(console.error);
    api.ordersAwaitingConfirmation().then(setAwaiting).catch(console.error);
  }

  useEffect(() => { load(); }, []);

  async function approve(id: number) {
    setBusy(id);
    try { await api.approveOrder(id); load(); } finally { setBusy(null); }
  }

  async function reject(id: number) {
    setBusy(id);
    try { await api.rejectOrder(id); load(); } finally { setBusy(null); }
  }

  async function openTradingView(p: OrderPreview) {
    setCopied(false);
    setTvPreview(p);
    try {
      const { url } = await api.openOrderInTradingView(p.id);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      console.error(err);
    }
  }

  async function copyOrderDetail() {
    if (!tvPreview) return;
    await navigator.clipboard.writeText(orderDetailText(tvPreview));
    setCopied(true);
  }

  function openOutcome(p: OrderPreview) {
    setOutcomeError(null);
    setOutcomePreview(p);
    setOutcomeForm(emptyOutcomeForm(p));
  }

  async function submitOutcome() {
    if (!outcomePreview || !outcomeForm) return;
    setOutcomeSubmitting(true);
    setOutcomeError(null);
    try {
      const isPosition = POSITION_OUTCOMES.includes(outcomeForm.outcome);
      await api.recordManualExecution(outcomePreview.id, {
        outcome: outcomeForm.outcome,
        actual_price: isPosition && outcomeForm.actual_price ? parseFloat(outcomeForm.actual_price) : undefined,
        actual_quantity: isPosition && outcomeForm.actual_quantity ? parseInt(outcomeForm.actual_quantity) : undefined,
        actual_order_type: isPosition ? outcomeForm.actual_order_type || undefined : undefined,
        notes: outcomeForm.notes || undefined,
      });
      setOutcomePreview(null);
      setOutcomeForm(null);
      load();
    } catch (err) {
      setOutcomeError(err instanceof Error ? err.message : String(err));
    } finally {
      setOutcomeSubmitting(false);
    }
  }

  async function submitCreate() {
    setSubmitting(true);
    setCreateError(null);
    try {
      await api.createOrderPreview({
        ticker: form.ticker.trim().toUpperCase(),
        action: form.action,
        reason: form.reason,
        shares: form.shares ? parseInt(form.shares) : undefined,
        limit_price: form.limit_price ? parseFloat(form.limit_price) : undefined,
        order_type: form.order_type,
        time_in_force: form.time_in_force,
        execution_mode: form.execution_mode,
      });
      setCreateOpen(false);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Order Preview Queue</h1>
        <Button size="sm" onClick={() => { setForm(EMPTY_FORM); setCreateError(null); setCreateOpen(true); }}>
          New Order Preview
        </Button>
      </div>

      {previews.length === 0 ? (
        <p className="text-sm text-zinc-400">No pending order previews.</p>
      ) : (
        <div className="rounded-md border border-zinc-200 bg-white divide-y divide-zinc-100">
          {previews.map((p) => (
            <div key={p.id}>
              <OrderRow
                preview={p}
                busy={busy === p.id}
                chartOpen={chartId === p.id}
                onApprove={() => approve(p.id)}
                onReject={() => reject(p.id)}
                onOpenTradingView={() => openTradingView(p)}
                onToggleChart={() => setChartId((cur) => (cur === p.id ? null : p.id))}
              />
              {chartId === p.id && (
                <div className="px-4 pb-4">
                  <TradingViewWidget symbol={p.ticker} height={320} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-zinc-700">Awaiting Manual Confirmation</h2>
        {awaiting.length === 0 ? (
          <p className="text-sm text-zinc-400">No previews awaiting manual execution confirmation.</p>
        ) : (
          <div className="rounded-md border border-zinc-200 bg-white divide-y divide-zinc-100">
            {awaiting.map((p) => (
              <div key={p.id}>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
                  <div className="flex items-center gap-2 min-w-[140px]">
                    <span className="font-semibold text-sm">{p.ticker}</span>
                    <span className="text-xs text-zinc-500">{p.action}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[p.status] ?? ""}`}>
                      {p.status}
                    </span>
                  </div>
                  <div className="flex gap-4 text-xs text-zinc-500 flex-1">
                    <span>{p.shares} sh</span>
                    <span>{p.order_type} @ ${p.limit_price.toFixed(2)}</span>
                    <span>{p.time_in_force}</span>
                  </div>
                  <div className="flex gap-2 ml-auto">
                    <Button size="sm" variant="outline"
                      onClick={() => setAwaitChartId((cur) => (cur === p.id ? null : p.id))}>
                      {awaitChartId === p.id ? "Hide Chart" : "Chart"}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => openTradingView(p)}>Open in TradingView</Button>
                    <Button size="sm" onClick={() => openOutcome(p)}>Record Outcome</Button>
                  </div>
                </div>
                {awaitChartId === p.id && (
                  <div className="px-4 pb-4">
                    <TradingViewWidget symbol={p.ticker} height={320} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>New Order Preview</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <Field label="Ticker" required>
              <input className={inputCls} value={form.ticker}
                onChange={(e) => setForm((f) => ({ ...f, ticker: e.target.value }))} />
            </Field>
            <Field label="Action" required>
              <select className={inputCls} value={form.action}
                onChange={(e) => setForm((f) => ({ ...f, action: e.target.value as CreateForm["action"] }))}>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>
            </Field>
            <Field label="Reason" required>
              <textarea rows={2} className={inputCls} value={form.reason}
                onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Shares">
                <input type="number" min="1" className={inputCls} value={form.shares}
                  onChange={(e) => setForm((f) => ({ ...f, shares: e.target.value }))} />
              </Field>
              <Field label="Limit price ($)">
                <input type="number" step="0.01" className={inputCls} value={form.limit_price}
                  onChange={(e) => setForm((f) => ({ ...f, limit_price: e.target.value }))} />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Order type">
                <input className={inputCls} value={form.order_type}
                  onChange={(e) => setForm((f) => ({ ...f, order_type: e.target.value }))} />
              </Field>
              <Field label="Time in force">
                <input className={inputCls} value={form.time_in_force}
                  onChange={(e) => setForm((f) => ({ ...f, time_in_force: e.target.value }))} />
              </Field>
            </div>
            <Field label="Execution mode" required>
              <select className={inputCls} value={form.execution_mode}
                onChange={(e) => setForm((f) => ({ ...f, execution_mode: e.target.value as CreateForm["execution_mode"] }))}>
                <option value="paper">Paper (auto-fills on approval)</option>
                <option value="manual_tradingview">Manual via TradingView</option>
              </select>
            </Field>
            {createError && <p className="text-xs text-red-600">{createError}</p>}
            <div className="flex gap-2 pt-1">
              <Button className="flex-1" disabled={!form.ticker || !form.reason || submitting} onClick={submitCreate}>
                {submitting ? "Submitting…" : "Create Preview"}
              </Button>
              <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!tvPreview} onOpenChange={(o) => { if (!o) setTvPreview(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Open in TradingView — {tvPreview?.ticker}</DialogTitle>
          </DialogHeader>
          {tvPreview && (
            <div className="space-y-3 mt-2">
              <p className="text-xs text-zinc-500">
                TradingView doesn&apos;t support pre-filling order details from third-party apps.
                A chart for {tvPreview.ticker} opened in a new tab — copy the details below and
                enter them manually into the order ticket.
              </p>
              <pre className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs whitespace-pre-wrap">
                {orderDetailText(tvPreview)}
              </pre>
              <Button size="sm" variant="outline" onClick={copyOrderDetail}>
                {copied ? "Copied!" : "Copy order details"}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!outcomePreview} onOpenChange={(o) => { if (!o) { setOutcomePreview(null); setOutcomeForm(null); } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Record Outcome — {outcomePreview?.ticker}</DialogTitle>
          </DialogHeader>
          {outcomeForm && (
            <div className="space-y-3 mt-2">
              <Field label="Outcome" required>
                <select className={inputCls} value={outcomeForm.outcome}
                  onChange={(e) => setOutcomeForm((f) => f && ({ ...f, outcome: e.target.value as ManualExecutionOutcome }))}>
                  {OUTCOMES.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </Field>
              {POSITION_OUTCOMES.includes(outcomeForm.outcome) && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Actual price ($)">
                      <input type="number" step="0.01" className={inputCls} value={outcomeForm.actual_price}
                        onChange={(e) => setOutcomeForm((f) => f && ({ ...f, actual_price: e.target.value }))} />
                    </Field>
                    <Field label="Actual quantity">
                      <input type="number" min="1" className={inputCls} value={outcomeForm.actual_quantity}
                        onChange={(e) => setOutcomeForm((f) => f && ({ ...f, actual_quantity: e.target.value }))} />
                    </Field>
                  </div>
                  <Field label="Actual order type">
                    <input className={inputCls} value={outcomeForm.actual_order_type}
                      onChange={(e) => setOutcomeForm((f) => f && ({ ...f, actual_order_type: e.target.value }))} />
                  </Field>
                </>
              )}
              <Field label="Notes">
                <textarea rows={2} className={inputCls} value={outcomeForm.notes}
                  onChange={(e) => setOutcomeForm((f) => f && ({ ...f, notes: e.target.value }))} />
              </Field>
              {outcomeError && <p className="text-xs text-red-600">{outcomeError}</p>}
              <div className="flex gap-2 pt-1">
                <Button className="flex-1" disabled={outcomeSubmitting} onClick={submitOutcome}>
                  {outcomeSubmitting ? "Submitting…" : "Record Outcome"}
                </Button>
                <Button variant="outline" onClick={() => { setOutcomePreview(null); setOutcomeForm(null); }}>Cancel</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

const inputCls = "w-full rounded-md border border-zinc-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400";

function Field({ label, children, required }: { label: string; children: React.ReactNode; required?: boolean }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-zinc-500">{label}{required && " *"}</label>
      {children}
    </div>
  );
}

function OrderRow({
  preview: p,
  busy,
  chartOpen,
  onApprove,
  onReject,
  onOpenTradingView,
  onToggleChart,
}: {
  preview: OrderPreview;
  busy: boolean;
  chartOpen: boolean;
  onApprove: () => void;
  onReject: () => void;
  onOpenTradingView: () => void;
  onToggleChart: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
      <div className="flex items-center gap-2 min-w-[140px]">
        <span className="font-semibold text-sm">{p.ticker}</span>
        <span className="text-xs text-zinc-500">{p.action}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${RISK_BADGE[p.risk_status] ?? ""}`}>
          {p.risk_status}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[p.status] ?? ""}`}>
          {p.status}
        </span>
      </div>

      <div className="flex gap-4 text-xs text-zinc-500 flex-1">
        <span>{p.shares} sh</span>
        <span>{p.order_type} @ ${p.limit_price.toFixed(2)}</span>
        <span>{p.time_in_force}</span>
        <span className="text-zinc-400">{p.execution_mode === "manual_tradingview" ? "manual · TradingView" : "paper"}</span>
      </div>

      <div className="flex gap-2 ml-auto">
        <Button size="sm" variant="outline" onClick={onToggleChart}>{chartOpen ? "Hide Chart" : "Chart"}</Button>
        {p.execution_mode === "manual_tradingview" && (
          <Button size="sm" variant="outline" onClick={onOpenTradingView}>Open in TradingView</Button>
        )}
        <Button size="sm" disabled={busy} onClick={onApprove}>Approve</Button>
        <Button size="sm" variant="outline" disabled={busy} onClick={onReject}>Reject</Button>
      </div>
    </div>
  );
}
