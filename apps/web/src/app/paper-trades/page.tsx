"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { PaperTrade } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  pending_approval: "secondary",
  open: "default",
  closed: "outline",
  rejected: "destructive",
} as const;

export default function PaperTradesPage() {
  const [trades, setTrades] = useState<PaperTrade[]>([]);

  useEffect(() => {
    api.paperTrades().then(setTrades).catch(console.error);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Paper Trades</h1>
      {trades.length === 0 ? (
        <p className="text-sm text-zinc-400">
          No paper trades yet. Promote a watchlist entry to create one.
        </p>
      ) : (
        <div className="rounded-md border border-zinc-200 bg-white divide-y divide-zinc-100">
          {trades.map((t) => (
            <div key={t.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <span className="font-medium text-sm">{t.ticker}</span>
                {t.entry_price != null && (
                  <span className="ml-2 text-xs text-zinc-400">@ ${t.entry_price.toFixed(2)}</span>
                )}
              </div>
              <div className="flex items-center gap-3">
                {t.pnl != null && (
                  <span className={`text-sm font-medium ${t.pnl >= 0 ? "text-green-600" : "text-red-500"}`}>
                    {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                  </span>
                )}
                <Badge variant={(STATUS_COLORS[t.status] as any) ?? "secondary"}>
                  {t.status.replace("_", " ")}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
