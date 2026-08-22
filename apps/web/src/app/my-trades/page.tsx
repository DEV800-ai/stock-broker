"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorAlert } from "@/components/error-alert";
import { api } from "@/lib/api";
import { formatUtc } from "@/lib/utils";
import type { TrackedTicker } from "@/types";

const inputCls = "w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

export default function MyTradesPage() {
  const [tickers, setTickers] = useState<TrackedTicker[]>([]);
  const [loading, setLoading] = useState(true);
  const [ticker, setTicker] = useState("");
  const [notes, setNotes] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.trackedTickers()
      .then(setTickers)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function handleAdd() {
    if (!ticker.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await api.addTrackedTicker(ticker.trim().toUpperCase(), notes.trim() || undefined);
      setTicker("");
      setNotes("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(t: string) {
    try {
      await api.removeTrackedTicker(t);
      setTickers((ts) => ts.filter((x) => x.ticker !== t));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">My Trades</h1>
      <p className="text-sm text-muted-foreground">
        Track tickers you're watching or trading manually. This is a personal watchlist, not a trade log —
        for actual paper positions see the Portfolio page (reachable by direct URL).
      </p>

      <Card>
        <CardContent className="space-y-3 pt-4">
          <div className="grid gap-3 sm:grid-cols-[160px_1fr_auto]">
            <input
              className={inputCls}
              placeholder="Ticker (e.g. AAPL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <input
              className={inputCls}
              placeholder="Notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <Button onClick={handleAdd} disabled={adding || !ticker.trim()}>
              {adding ? "Adding…" : "Add"}
            </Button>
          </div>
          {error && <ErrorAlert message={error} />}
        </CardContent>
      </Card>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : tickers.length === 0 ? (
        <p className="text-sm text-muted-foreground">No tickers tracked yet. Add one above.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {tickers.map((t) => (
            <Card key={t.id}>
              <CardContent className="space-y-2 pt-4 pb-3">
                <div className="flex items-start justify-between">
                  <span className="font-mono text-base font-semibold">{t.ticker}</span>
                  <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => handleRemove(t.ticker)}>
                    Remove
                  </Button>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-mono text-muted-foreground">
                    {t.latest_price != null ? `$${t.latest_price.toFixed(2)}` : "—"}
                  </span>
                  <span className="font-mono text-muted-foreground">
                    {t.latest_composite_score != null ? `score ${t.latest_composite_score.toFixed(2)}` : "no scan data"}
                  </span>
                </div>
                {t.notes && <p className="text-xs text-muted-foreground">{t.notes}</p>}
                <p className="text-xs text-muted-foreground">Added {formatUtc(t.created_at)}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
