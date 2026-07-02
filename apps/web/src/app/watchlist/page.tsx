"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import type { StockThesis, WatchlistEntry } from "@/types";

interface TradeForm {
  entry_price: string;
  target_price: string;
  stop_price: string;
  shares: string;
  notes: string;
}

const STATUS_COLORS: Record<string, string> = {
  paper: "bg-green-100 text-green-800",
  research: "bg-blue-100 text-blue-800",
  watch: "bg-zinc-100 text-zinc-700",
  avoid: "bg-red-100 text-red-700",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-zinc-100 text-zinc-600",
};

const THESIS_MIN_SCORE = 0.50;

export default function WatchlistPage() {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [thesis, setThesis] = useState<StockThesis | null>(null);
  const [thesisOpen, setThesisOpen] = useState(false);
  const [loadingThesis, setLoadingThesis] = useState(false);
  const [generatingTickers, setGeneratingTickers] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [tradeEntry, setTradeEntry] = useState<WatchlistEntry | null>(null);
  const [tradeForm, setTradeForm] = useState<TradeForm>({ entry_price: "", target_price: "", stop_price: "", shares: "1", notes: "" });
  const [submittingTrade, setSubmittingTrade] = useState(false);

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
    setGeneratingTickers((prev) => new Set(prev).add(entry.ticker));
    try {
      await api.generateThesis(entry.ticker, entry.scan_result_id ?? undefined);
      // Poll until thesis_id appears on the entry (generation runs in background)
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const fresh = await api.watchlist({ limit: 50 });
        const updated = fresh.find((e) => e.ticker === entry.ticker);
        if (updated?.thesis_id || attempts >= 30) {
          clearInterval(poll);
          setEntries(fresh);
          setGeneratingTickers((prev) => {
            const next = new Set(prev);
            next.delete(entry.ticker);
            return next;
          });
        }
      }, 2000);
    } catch {
      setGeneratingTickers((prev) => {
        const next = new Set(prev);
        next.delete(entry.ticker);
        return next;
      });
    }
  }

  async function openTradeDialog(entry: WatchlistEntry) {
    setTradeForm({ entry_price: "", target_price: "", stop_price: "", shares: "1", notes: "" });
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
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              {s === "" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {entries.length === 0 ? (
        <p className="text-sm text-zinc-400">No watchlist entries yet. Run a scan first.</p>
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
            />
          ))}
        </div>
      )}

      <Dialog open={thesisOpen} onOpenChange={setThesisOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {loadingThesis ? (
            <div className="py-8 text-center text-sm text-zinc-400">Loading thesis…</div>
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

const inputCls = "w-full rounded-md border border-zinc-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400";

function Field({ label, children, required }: { label: string; children: React.ReactNode; required?: boolean }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-zinc-500">{label}{required && " *"}</label>
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
}: {
  entry: WatchlistEntry;
  onViewThesis: (e: WatchlistEntry) => void;
  onGenerateThesis: (e: WatchlistEntry) => void;
  onCreateTrade: (e: WatchlistEntry) => void;
  generating: boolean;
}) {
  const scorePercent = Math.round((entry.composite_score ?? 0) * 100);
  const eligible = !entry.thesis_id && (entry.composite_score ?? 0) >= THESIS_MIN_SCORE;
  const canTrade = entry.thesis_id && entry.status !== "paper" && entry.status !== "avoid";

  return (
    <Card className="hover:shadow-sm transition-shadow">
      <CardContent className="pt-4 pb-3 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-400">#{entry.rank}</span>
            <span className="text-base font-semibold">{entry.ticker}</span>
          </div>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[entry.status] ?? "bg-zinc-100 text-zinc-700"}`}>
            {entry.status.toUpperCase()}
          </span>
        </div>

        {/* Score bar */}
        <div>
          <div className="flex justify-between text-xs text-zinc-400 mb-1">
            <span>Score</span>
            <span>{scorePercent}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-zinc-100">
            <div
              className="h-1.5 rounded-full bg-zinc-800 transition-all"
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
      </CardContent>
    </Card>
  );
}

function ThesisView({ thesis }: { thesis: StockThesis }) {
  return (
    <>
      <DialogHeader>
        <div className="flex items-center gap-3">
          <DialogTitle className="text-lg">{thesis.ticker}</DialogTitle>
          {thesis.confidence && (
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CONFIDENCE_COLORS[thesis.confidence] ?? ""}`}>
              {thesis.confidence.toUpperCase()} CONFIDENCE
            </span>
          )}
        </div>
        <p className="text-xs text-zinc-400">
          Generated {new Date(thesis.generated_at).toLocaleString()} · {thesis.model}
        </p>
      </DialogHeader>

      <div className="space-y-4 mt-4">
        <Section title="Why Interesting" content={thesis.why_interesting} />
        <Section title="Risk Factors" content={thesis.risk_factors} />
        {thesis.sector_context && <Section title="Sector Context" content={thesis.sector_context} />}
        {thesis.news_summary && <Section title="News Summary" content={thesis.news_summary} />}
        {thesis.catalysts && <Section title="Catalysts" content={thesis.catalysts} />}
        {thesis.peer_comparison && <Section title="Peer Comparison" content={thesis.peer_comparison} />}
      </div>
    </>
  );
}

function Section({ title, content }: { title: string; content: string }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-400 mb-1">{title}</h3>
      <p className="text-sm text-zinc-700 leading-relaxed">{content}</p>
    </div>
  );
}
