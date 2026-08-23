"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ErrorAlert } from "@/components/error-alert";
import { ThesisView } from "@/components/thesis-view";
import { TradingViewWidget } from "@/components/tradingview-widget";
import { api } from "@/lib/api";
import { generateAndPollThesis } from "@/lib/thesis";
import type { ScanResult, StockThesis, WatchlistStatus } from "@/types";

const TOP_N = 10;

const STATUS_LABEL: Record<WatchlistStatus, string> = {
  watch: "Watching",
  research: "Researching",
  paper: "Paper Trading",
  avoid: "Avoided",
};

interface CreateForm {
  action: "BUY" | "SELL";
  reason: string;
  shares: string;
  limit_price: string;
  order_type: string;
  time_in_force: string;
  execution_mode: "paper" | "manual_tradingview";
}

function emptyForm(scan: ScanResult): CreateForm {
  return {
    action: "BUY",
    reason: "",
    shares: "1",
    limit_price: scan.price != null ? scan.price.toFixed(2) : "",
    order_type: "LIMIT",
    time_in_force: "DAY",
    execution_mode: "paper",
  };
}

export default function IdeasPage() {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [statuses, setStatuses] = useState<Record<string, WatchlistStatus>>({});
  const [scanning, setScanning] = useState(false);

  const [active, setActive] = useState<ScanResult | null>(null);
  const [thesis, setThesis] = useState<StockThesis | null>(null);
  const [loadingThesis, setLoadingThesis] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [thesisError, setThesisError] = useState<string | null>(null);
  const [statusSaving, setStatusSaving] = useState(false);

  const [form, setForm] = useState<CreateForm | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [created, setCreated] = useState(false);

  function loadTop() {
    api.scanResults({ limit: TOP_N }).then(setResults).catch(console.error);
    api.watchlist({ limit: TOP_N })
      .then((entries) => {
        const map: Record<string, WatchlistStatus> = {};
        for (const e of entries) map[e.ticker] = e.status;
        setStatuses(map);
      })
      .catch(console.error);
  }

  useEffect(() => { loadTop(); }, []);

  async function setStatus(ticker: string, status: WatchlistStatus) {
    setStatusSaving(true);
    try {
      await api.updateWatchlistStatus(ticker, status);
      setStatuses((s) => ({ ...s, [ticker]: status }));
    } catch (err) {
      console.error(err);
    } finally {
      setStatusSaving(false);
    }
  }

  async function openInTradingView(ticker: string) {
    try {
      const { url } = await api.tradingViewUrl(ticker);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      console.error(err);
    }
  }

  async function runScan() {
    setScanning(true);
    try {
      await api.triggerScan();
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const runs = await api.scanRuns(1);
        const latest = runs[0];
        if (!latest || latest.status !== "running" || attempts >= 60) {
          clearInterval(poll);
          setScanning(false);
          loadTop();
        }
      }, 3000);
    } catch {
      setScanning(false);
    }
  }

  async function openDetail(scan: ScanResult) {
    setActive(scan);
    setThesis(null);
    setThesisError(null);
    setForm(emptyForm(scan));
    setCreateError(null);
    setCreated(false);
    setLoadingThesis(true);
    try {
      const t = await api.thesis(scan.ticker);
      setThesis(t);
    } catch {
      setThesis(null);
    } finally {
      setLoadingThesis(false);
    }
  }

  async function generateThesis() {
    if (!active) return;
    setThesisError(null);
    setGenerating(true);
    try {
      await generateAndPollThesis({
        ticker: active.ticker,
        scanResultId: active.id,
        onDone: (t) => {
          setThesis(t);
          setGenerating(false);
        },
        onTimeout: () => {
          setGenerating(false);
          setThesisError("Thesis generation didn't complete — the score may be below the auto-thesis threshold, or generation failed. Try again shortly.");
        },
      });
    } catch (err) {
      setGenerating(false);
      setThesisError(err instanceof Error ? err.message : String(err));
    }
  }

  async function submitCreate() {
    if (!active || !form) return;
    setSubmitting(true);
    setCreateError(null);
    try {
      await api.createOrderPreview({
        ticker: active.ticker,
        action: form.action,
        reason: form.reason || `Scanner flagged ${active.ticker} — composite score ${((active.composite_score ?? 0) * 100).toFixed(0)}%`,
        thesis_id: thesis?.id,
        shares: form.shares ? parseInt(form.shares) : undefined,
        limit_price: form.limit_price ? parseFloat(form.limit_price) : undefined,
        order_type: form.order_type,
        time_in_force: form.time_in_force,
        execution_mode: form.execution_mode,
      });
      setCreated(true);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Top Ideas</h1>
        <Button size="sm" onClick={runScan} disabled={scanning}>
          {scanning ? "Scanning…" : "Run Scan"}
        </Button>
      </div>

      {results.length === 0 ? (
        <p className="text-sm text-muted-foreground">No scan results yet. Run a scan to populate this list.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {results.map((r, i) => (
            <IdeaCard key={r.id} rank={i + 1} scan={r} status={statuses[r.ticker]} onClick={() => openDetail(r)} />
          ))}
        </div>
      )}

      <Dialog open={!!active} onOpenChange={(o) => { if (!o) setActive(null); }}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          {active && (
            <div className="space-y-5">
              <DialogHeader>
                <div className="flex items-center justify-between pr-6">
                  <DialogTitle className="font-mono text-lg">{active.ticker}</DialogTitle>
                  <Button size="sm" variant="outline" onClick={() => openInTradingView(active.ticker)}>
                    Open in TradingView ↗
                  </Button>
                </div>
              </DialogHeader>

              <TradingViewWidget symbol={active.ticker} height={280} />

              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-muted-foreground mr-1">Status:</span>
                {(Object.keys(STATUS_LABEL) as WatchlistStatus[]).map((s) => (
                  <button
                    key={s}
                    disabled={statusSaving}
                    onClick={() => setStatus(active.ticker, s)}
                    className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                      statuses[active.ticker] === s
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:bg-muted/70"
                    }`}
                  >
                    {STATUS_LABEL[s]}
                  </button>
                ))}
              </div>

              <div>
                <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Thesis</h2>
                {loadingThesis ? (
                  <p className="text-sm text-muted-foreground">Loading thesis…</p>
                ) : thesis ? (
                  <ThesisView thesis={thesis} />
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">No thesis generated yet for {active.ticker}.</p>
                    <Button size="sm" variant="outline" disabled={generating} onClick={generateThesis}>
                      {generating ? "Generating…" : "Generate Thesis"}
                    </Button>
                    {thesisError && <ErrorAlert message={thesisError} />}
                  </div>
                )}
              </div>

              <div>
                <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">New Order Preview</h2>
                {created ? (
                  <div className="space-y-2">
                    <p className="text-sm text-emerald-400">Order preview created.</p>
                  </div>
                ) : form && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Action" required>
                        <select className={inputCls} value={form.action}
                          onChange={(e) => setForm((f) => f && ({ ...f, action: e.target.value as CreateForm["action"] }))}>
                          <option value="BUY">BUY</option>
                          <option value="SELL">SELL</option>
                        </select>
                      </Field>
                      <Field label="Shares">
                        <input type="number" min="1" className={inputCls} value={form.shares}
                          onChange={(e) => setForm((f) => f && ({ ...f, shares: e.target.value }))} />
                      </Field>
                    </div>
                    <Field label="Reason" required>
                      <textarea rows={2} className={inputCls}
                        placeholder={`Scanner flagged ${active.ticker} — composite score ${((active.composite_score ?? 0) * 100).toFixed(0)}%`}
                        value={form.reason}
                        onChange={(e) => setForm((f) => f && ({ ...f, reason: e.target.value }))} />
                    </Field>
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Limit price ($)">
                        <input type="number" step="0.01" className={inputCls} value={form.limit_price}
                          onChange={(e) => setForm((f) => f && ({ ...f, limit_price: e.target.value }))} />
                      </Field>
                      <Field label="Execution mode" required>
                        <select className={inputCls} value={form.execution_mode}
                          onChange={(e) => setForm((f) => f && ({ ...f, execution_mode: e.target.value as CreateForm["execution_mode"] }))}>
                          <option value="paper">Paper</option>
                          <option value="manual_tradingview">Manual via TradingView</option>
                        </select>
                      </Field>
                    </div>
                    {createError && <ErrorAlert message={createError} />}
                    <Button className="w-full" disabled={submitting} onClick={submitCreate}>
                      {submitting ? "Submitting…" : "Create Preview"}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

const inputCls = "w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function Field({ label, children, required }: { label: string; children: React.ReactNode; required?: boolean }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">{label}{required && " *"}</label>
      {children}
    </div>
  );
}

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

const STATUS_BADGE: Record<WatchlistStatus, BadgeVariant> = {
  watch: "outline",
  research: "secondary",
  paper: "success",
  avoid: "destructive",
};

function IdeaCard({
  rank,
  scan,
  status,
  onClick,
}: {
  rank: number;
  scan: ScanResult;
  status?: WatchlistStatus;
  onClick: () => void;
}) {
  const scorePercent = Math.round((scan.composite_score ?? 0) * 100);
  const change = scan.pct_change_5d;

  return (
    <Card className="hover:shadow-sm transition-shadow cursor-pointer" onClick={onClick}>
      <CardContent className="pt-4 pb-3 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">#{rank}</span>
            <span className="font-mono text-base font-semibold">{scan.ticker}</span>
            {status && (
              <Badge variant={STATUS_BADGE[status]} className="text-xs font-normal">
                {STATUS_LABEL[status]}
              </Badge>
            )}
          </div>
          <span className="font-mono text-sm">{scan.price != null ? `$${scan.price.toFixed(2)}` : "—"}</span>
        </div>

        <div>
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Score</span>
            <span className="font-mono">{scorePercent}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted">
            <div className="h-1.5 rounded-full bg-primary transition-all" style={{ width: `${scorePercent}%` }} />
          </div>
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className={`font-mono ${change != null && change >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
            {change != null ? (change >= 0 ? "+" : "") + change.toFixed(1) + "%" : "—"}
          </span>
          <div className="flex flex-wrap gap-1 justify-end">
            {scan.signals_fired &&
              Object.entries(scan.signals_fired)
                .filter(([, v]) => v)
                .slice(0, 3)
                .map(([k]) => (
                  <Badge key={k} variant="outline" className="text-xs font-normal">{k}</Badge>
                ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
