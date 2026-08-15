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
import { api } from "@/lib/api";
import { generateAndPollThesis } from "@/lib/thesis";
import type { StockThesis, WatchlistEntry } from "@/types";

interface TradeForm {
  entry_price: string;
  target_price: string;
  stop_price: string;
  shares: string;
  notes: string;
}

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

const STATUS_VARIANTS: Record<string, BadgeVariant> = {
  paper: "success",
  research: "secondary",
  watch: "outline",
  avoid: "destructive",
};

const THESIS_MIN_SCORE = 0.50;

export default function WatchlistPage() {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [thesis, setThesis] = useState<StockThesis | null>(null);
  const [thesisOpen, setThesisOpen] = useState(false);
  const [loadingThesis, setLoadingThesis] = useState(false);
  const [generatingTickers, setGeneratingTickers] = useState<Set<string>>(new Set());
  const [thesisGenError, setThesisGenError] = useState<{ ticker: string; message: string } | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [tradeEntry, setTradeEntry] = useState<WatchlistEntry | null>(null);
  const [tradeForm, setTradeForm] = useState<TradeForm>({ entry_price: "", target_price: "", stop_price: "", shares: "1", notes: "" });
  const [submittingTrade, setSubmittingTrade] = useState(false);
  const [tradeError, setTradeError] = useState<string | null>(null);

  function loadEntries() {
    api.watchlist({ status: statusFilter || undefined, limit: 50 })
      .then(setEntries)
      .catch(console.error);
  }

  useEffect(() => { loadEntries(); }, [statusFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  async function openThesis(entry: WatchlistEntry) {
    if (!entry.thesis_id) return;
    setLoadingThesis(true);
    setThesisOpen(true);
    try {
      const t = await api.thesis(entry.ticker);
      setThesis(t);
    } finally {
      setLoadingThesis(false);
    }
  }

  async function generateThesis(entry: WatchlistEntry) {
    setThesisGenError(null);
    setGeneratingTickers((prev) => new Set(prev).add(entry.ticker));
    const stopGenerating = () => {
      setGeneratingTickers((prev) => {
        const next = new Set(prev);
        next.delete(entry.ticker);
        return next;
      });
    };
    try {
      await generateAndPollThesis({
        ticker: entry.ticker,
        scanResultId: entry.scan_result_id ?? undefined,
        onDone: () => {
          stopGenerating();
          loadEntries();
        },
        onTimeout: () => {
          stopGenerating();
          setThesisGenError({ ticker: entry.ticker, message: "Thesis generation didn't complete — the score may be below the auto-thesis threshold, or generation failed. Try again shortly." });
        },
      });
    } catch (err) {
      stopGenerating();
      setThesisGenError({ ticker: entry.ticker, message: err instanceof Error ? err.message : String(err) });
    }
  }

  async function openTradeDialog(entry: WatchlistEntry) {
    setTradeForm({ entry_price: "", target_price: "", stop_price: "", shares: "1", notes: "" });
    setTradeError(null);
    setTradeEntry(entry);
    try {
      const scan = await api.latestScanResult(entry.ticker);
      if (scan.price) {
        setTradeForm((f) => ({ ...f, entry_price: scan.price!.toFixed(2) }));
      }
    } catch { /* price prefill is best-effort */ }
  }

  async function submitTrade() {
    if (!tradeEntry) return;
    setSubmittingTrade(true);
    setTradeError(null);
    try {
      await api.createPaperTrade({
        ticker: tradeEntry.ticker,
        thesis_id: tradeEntry.thesis_id ?? undefined,
        entry_price: parseFloat(tradeForm.entry_price),
        target_price: tradeForm.target_price ? parseFloat(tradeForm.target_price) : undefined,
        stop_price: tradeForm.stop_price ? parseFloat(tradeForm.stop_price) : undefined,
        shares: parseInt(tradeForm.shares) || 1,
        notes: tradeForm.notes || undefined,
      });
      setTradeEntry(null);
      loadEntries();
    } catch (err) {
      setTradeError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmittingTrade(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Watchlist</h1>
        <div className="flex gap-2">
          {["", "paper", "research", "watch"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                statusFilter === s
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/70"
              }`}
            >
              {s === "" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No watchlist entries yet. Run a scan first.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {entries.map((entry) => (
            <WatchlistCard
              key={entry.id}
              entry={entry}
              onViewThesis={openThesis}
              onGenerateThesis={generateThesis}
              onCreateTrade={openTradeDialog}
              generating={generatingTickers.has(entry.ticker)}
              error={thesisGenError?.ticker === entry.ticker ? thesisGenError.message : null}
            />
          ))}
        </div>
      )}

      <Dialog open={thesisOpen} onOpenChange={setThesisOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {loadingThesis ? (
            <div className="py-8 text-center text-sm text-muted-foreground">Loading thesis…</div>
          ) : thesis ? (
            <ThesisView thesis={thesis} />
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={!!tradeEntry} onOpenChange={(o) => { if (!o) setTradeEntry(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Paper Trade — {tradeEntry?.ticker}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <Field label="Entry price ($)" required>
              <input
                type="number" step="0.01" className={inputCls}
                value={tradeForm.entry_price}
                onChange={(e) => setTradeForm((f) => ({ ...f, entry_price: e.target.value }))}
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Target price ($)">
                <input type="number" step="0.01" className={inputCls}
                  value={tradeForm.target_price}
                  onChange={(e) => setTradeForm((f) => ({ ...f, target_price: e.target.value }))} />
              </Field>
              <Field label="Stop price ($)">
                <input type="number" step="0.01" className={inputCls}
                  value={tradeForm.stop_price}
                  onChange={(e) => setTradeForm((f) => ({ ...f, stop_price: e.target.value }))} />
              </Field>
            </div>
            <Field label="Shares">
              <input type="number" min="1" className={inputCls}
                value={tradeForm.shares}
                onChange={(e) => setTradeForm((f) => ({ ...f, shares: e.target.value }))} />
            </Field>
            <Field label="Notes">
              <textarea rows={2} className={inputCls}
                value={tradeForm.notes}
                onChange={(e) => setTradeForm((f) => ({ ...f, notes: e.target.value }))} />
            </Field>
            {tradeError && <ErrorAlert message={tradeError} />}
            <div className="flex gap-2 pt-1">
              <Button className="flex-1" disabled={!tradeForm.entry_price || submittingTrade} onClick={submitTrade}>
                {submittingTrade ? "Submitting…" : "Submit for Approval"}
              </Button>
              <Button variant="outline" onClick={() => setTradeEntry(null)}>Cancel</Button>
            </div>
          </div>
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

function WatchlistCard({
  entry,
  onViewThesis,
  onGenerateThesis,
  onCreateTrade,
  generating,
  error,
}: {
  entry: WatchlistEntry;
  onViewThesis: (e: WatchlistEntry) => void;
  onGenerateThesis: (e: WatchlistEntry) => void;
  onCreateTrade: (e: WatchlistEntry) => void;
  generating: boolean;
  error?: string | null;
}) {
  const scorePercent = Math.round((entry.composite_score ?? 0) * 100);
  const eligible = !entry.thesis_id && (entry.composite_score ?? 0) >= THESIS_MIN_SCORE;
  const canTrade = entry.thesis_id && entry.status !== "paper" && entry.status !== "avoid";

  return (
    <Card className="hover:shadow-sm transition-shadow">
      <CardContent className="pt-4 pb-3 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">#{entry.rank}</span>
            <span className="font-mono text-base font-semibold">{entry.ticker}</span>
          </div>
          <Badge variant={STATUS_VARIANTS[entry.status] ?? "outline"}>
            {entry.status.toUpperCase()}
          </Badge>
        </div>

        {/* Score bar */}
        <div>
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Score</span>
            <span className="font-mono">{scorePercent}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted">
            <div
              className="h-1.5 rounded-full bg-primary transition-all"
              style={{ width: `${scorePercent}%` }}
            />
          </div>
        </div>

        <div className="flex gap-2">
          {entry.thesis_id ? (
            <Button variant="outline" size="sm" className="flex-1 text-xs" onClick={() => onViewThesis(entry)}>
              View Thesis
            </Button>
          ) : eligible ? (
            <Button variant="outline" size="sm" className="flex-1 text-xs" disabled={generating} onClick={() => onGenerateThesis(entry)}>
              {generating ? "Generating…" : "Generate Thesis"}
            </Button>
          ) : null}
          {canTrade && (
            <Button size="sm" className="flex-1 text-xs" onClick={() => onCreateTrade(entry)}>
              Paper Trade
            </Button>
          )}
        </div>
        {error && <ErrorAlert message={error} />}
      </CardContent>
    </Card>
  );
}
