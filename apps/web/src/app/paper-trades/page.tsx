"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { badgeVariants } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorAlert } from "@/components/error-alert";
import { api } from "@/lib/api";
import type { PaperTrade } from "@/types";
import type { VariantProps } from "class-variance-authority";

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

const STATUS_VARIANTS: Record<string, BadgeVariant> = {
  pending_approval: "warning",
  open: "secondary",
  closed: "outline",
  rejected: "destructive",
};

export default function PaperTradesPage() {
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [closingId, setClosingId] = useState<number | null>(null);
  const [exitPrice, setExitPrice] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const [actionError, setActionError] = useState<{ id: number; message: string } | null>(null);

  function load() {
    api.paperTrades().then(setTrades).catch(console.error);
  }

  useEffect(() => { load(); }, []);

  async function approve(id: number) {
    setBusy(id);
    setActionError(null);
    try {
      await api.approveTrade(id);
      load();
    } catch (err) {
      setActionError({ id, message: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(null);
    }
  }

  async function reject(id: number) {
    setBusy(id);
    setActionError(null);
    try {
      await api.rejectTrade(id);
      load();
    } catch (err) {
      setActionError({ id, message: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(null);
    }
  }

  async function close(id: number) {
    const price = parseFloat(exitPrice);
    if (!price) return;
    setBusy(id);
    setActionError(null);
    try {
      await api.closeTrade(id, price);
      setClosingId(null);
      setExitPrice("");
      load();
    } catch (err) {
      setActionError({ id, message: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(null);
    }
  }

  const pending = trades.filter((t) => t.status === "pending_approval");
  const open    = trades.filter((t) => t.status === "open");
  const closed  = trades.filter((t) => t.status === "closed" || t.status === "rejected");

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold">Paper Trades</h1>

      {trades.length === 0 && (
        <p className="text-sm text-muted-foreground">No paper trades yet. Generate a thesis on a watchlist ticker, then click Paper Trade.</p>
      )}

      {pending.length > 0 && (
        <Section title="Pending Approval">
          {pending.map((t) => (
            <TradeRow key={t.id} trade={t} error={actionError?.id === t.id ? actionError.message : null}>
              <Button size="sm" disabled={busy === t.id} onClick={() => approve(t.id)}>Approve</Button>
              <Button size="sm" variant="outline" disabled={busy === t.id} onClick={() => reject(t.id)}>Reject</Button>
            </TradeRow>
          ))}
        </Section>
      )}

      {open.length > 0 && (
        <Section title="Open">
          {open.map((t) => (
            <TradeRow key={t.id} trade={t} error={actionError?.id === t.id ? actionError.message : null}>
              {closingId === t.id ? (
                <div className="flex items-center gap-2">
                  <input
                    type="number" step="0.01" placeholder="Exit price"
                    className="w-28 rounded border border-border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
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
          {closed.map((t) => <TradeRow key={t.id} trade={t} error={actionError?.id === t.id ? actionError.message : null} />)}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">{title}</h2>
      <div className="rounded-md border border-border bg-card divide-y divide-border">
        {children}
      </div>
    </div>
  );
}

function TradeRow({ trade: t, children, error }: { trade: PaperTrade; children?: React.ReactNode; error?: string | null }) {
  const pnlColor = t.pnl == null ? "" : t.pnl >= 0 ? "text-emerald-400" : "text-rose-400";

  return (
    <div className="px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {/* ticker + status */}
        <div className="flex items-center gap-2 min-w-[120px]">
          <span className="font-mono font-semibold text-sm">{t.ticker}</span>
          <Badge variant={STATUS_VARIANTS[t.status] ?? "outline"}>
            {t.status.replace("_", " ")}
          </Badge>
        </div>

        {/* prices */}
        <div className="flex gap-4 text-xs text-muted-foreground flex-1 font-mono">
          {t.entry_price != null && <span>Entry <strong className="text-foreground">${t.entry_price.toFixed(2)}</strong></span>}
          {t.target_price != null && <span>Target <strong className="text-foreground">${t.target_price.toFixed(2)}</strong></span>}
          {t.stop_price != null && <span>Stop <strong className="text-foreground">${t.stop_price.toFixed(2)}</strong></span>}
          {t.exit_price != null && <span>Exit <strong className="text-foreground">${t.exit_price.toFixed(2)}</strong></span>}
          {t.shares != null && <span>{t.shares} sh</span>}
          {t.hold_days != null && <span>{t.hold_days}d</span>}
        </div>

        {/* P&L */}
        {t.pnl != null && (
          <div className={`text-sm font-mono font-semibold ${pnlColor} min-w-[80px] text-right`}>
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

      {error && <div className="mt-2"><ErrorAlert message={error} /></div>}
    </div>
  );
}
