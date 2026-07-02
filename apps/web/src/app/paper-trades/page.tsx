"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { PaperTrade } from "@/types";

const STATUS_BADGE: Record<string, string> = {
  pending_approval: "bg-yellow-100 text-yellow-800",
  open:             "bg-blue-100 text-blue-800",
  closed:           "bg-zinc-100 text-zinc-600",
  rejected:         "bg-red-100 text-red-700",
};

export default function PaperTradesPage() {
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [closingId, setClosingId] = useState<number | null>(null);
  const [exitPrice, setExitPrice] = useState("");
  const [busy, setBusy] = useState<number | null>(null);

  function load() {
    api.paperTrades().then(setTrades).catch(console.error);
  }

  useEffect(() => { load(); }, []);

  async function approve(id: number) {
    setBusy(id);
    try { await api.approveTrade(id); load(); } finally { setBusy(null); }
  }

  async function reject(id: number) {
    setBusy(id);
    try { await api.rejectTrade(id); load(); } finally { setBusy(null); }
  }

  async function close(id: number) {
    const price = parseFloat(exitPrice);
    if (!price) return;
    setBusy(id);
    try { await api.closeTrade(id, price); setClosingId(null); setExitPrice(""); load(); } finally { setBusy(null); }
  }

  const pending = trades.filter((t) => t.status === "pending_approval");
  const open    = trades.filter((t) => t.status === "open");
  const closed  = trades.filter((t) => t.status === "closed" || t.status === "rejected");

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold">Paper Trades</h1>

      {trades.length === 0 && (
        <p className="text-sm text-zinc-400">No paper trades yet. Generate a thesis on a watchlist ticker, then click Paper Trade.</p>
      )}

      {pending.length > 0 && (
        <Section title="Pending Approval">
          {pending.map((t) => (
            <TradeRow key={t.id} trade={t}>
              <Button size="sm" disabled={busy === t.id} onClick={() => approve(t.id)}>Approve</Button>
              <Button size="sm" variant="outline" disabled={busy === t.id} onClick={() => reject(t.id)}>Reject</Button>
            </TradeRow>
          ))}
        </Section>
      )}

      {open.length > 0 && (
        <Section title="Open">
          {open.map((t) => (
            <TradeRow key={t.id} trade={t}>
              {closingId === t.id ? (
                <div className="flex items-center gap-2">
                  <input
                    type="number" step="0.01" placeholder="Exit price"
                    className="w-28 rounded border border-zinc-200 px-2 py-1 text-sm"
                    value={exitPrice}
                    onChange={(e) => setExitPrice(e.target.value)}
                  />
                  <Button size="sm" disabled={!exitPrice || busy === t.id} onClick={() => close(t.id)}>Confirm</Button>
                  <Button size="sm" variant="outline" onClick={() => { setClosingId(null); setExitPrice(""); }}>Cancel</Button>
                </div>
              ) : (
                <Button size="sm" variant="outline" onClick={() => { setClosingId(t.id); setExitPrice(""); }}>Close</Button>
              )}
            </TradeRow>
          ))}
        </Section>
      )}

      {closed.length > 0 && (
        <Section title="History">
          {closed.map((t) => <TradeRow key={t.id} trade={t} />)}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-400 mb-2">{title}</h2>
      <div className="rounded-md border border-zinc-200 bg-white divide-y divide-zinc-100">
        {children}
      </div>
    </div>
  );
}

function TradeRow({ trade: t, children }: { trade: PaperTrade; children?: React.ReactNode }) {
  const pnlColor = t.pnl == null ? "" : t.pnl >= 0 ? "text-green-600" : "text-red-500";

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
      {/* ticker + status */}
      <div className="flex items-center gap-2 min-w-[120px]">
        <span className="font-semibold text-sm">{t.ticker}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[t.status] ?? ""}`}>
          {t.status.replace("_", " ")}
        </span>
      </div>

      {/* prices */}
      <div className="flex gap-4 text-xs text-zinc-500 flex-1">
        {t.entry_price != null && <span>Entry <strong className="text-zinc-800">${t.entry_price.toFixed(2)}</strong></span>}
        {t.target_price != null && <span>Target <strong className="text-zinc-800">${t.target_price.toFixed(2)}</strong></span>}
        {t.stop_price != null && <span>Stop <strong className="text-zinc-800">${t.stop_price.toFixed(2)}</strong></span>}
        {t.exit_price != null && <span>Exit <strong className="text-zinc-800">${t.exit_price.toFixed(2)}</strong></span>}
        {t.shares != null && <span>{t.shares} sh</span>}
        {t.hold_days != null && <span>{t.hold_days}d</span>}
      </div>

      {/* P&L */}
      {t.pnl != null && (
        <div className={`text-sm font-semibold ${pnlColor} min-w-[80px] text-right`}>
          {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
          {t.pnl_pct != null && (
            <span className="ml-1 text-xs font-normal">
              ({t.pnl_pct >= 0 ? "+" : ""}{(t.pnl_pct * 100).toFixed(1)}%)
            </span>
          )}
        </div>
      )}

      {/* actions */}
      {children && <div className="flex gap-2 ml-auto">{children}</div>}
    </div>
  );
}
