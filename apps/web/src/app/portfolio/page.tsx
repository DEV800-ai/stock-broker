"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Portfolio, Position } from "@/types";

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);

  useEffect(() => {
    api.portfolio().then(setPortfolio).catch(console.error);
  }, []);

  const positions = portfolio?.positions ?? [];
  const sectors = Object.entries(portfolio?.sector_values ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Portfolio</h1>
      <p className="text-sm text-muted-foreground">
        Derived entirely from open paper trades — simulated and manually self-reported TradingView
        fills alike. There is no live broker connection.
      </p>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryTile label="Net Liquidation" value={portfolio ? fmtUsd(portfolio.net_liquidation) : "—"} />
        <SummaryTile label="Cash" value={portfolio ? fmtUsd(portfolio.cash) : "—"} />
        <SummaryTile label="Realized P&L (today)" value={portfolio ? fmtSigned(portfolio.realized_pnl_today) : "—"} signed={portfolio?.realized_pnl_today} />
        <SummaryTile label="Realized P&L (week)" value={portfolio ? fmtSigned(portfolio.realized_pnl_week) : "—"} signed={portfolio?.realized_pnl_week} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Positions</CardTitle>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No open positions.</p>
          ) : (
            <div className="divide-y divide-border">
              {positions.map((p) => (
                <PositionRow key={p.ticker} position={p} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {sectors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Sector Exposure</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {sectors.map(([sector, value]) => (
                <div key={sector} className="flex items-center justify-between text-sm">
                  <span>{sector}</span>
                  <span className="font-mono">{fmtUsd(value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function PositionRow({ position: p }: { position: Position }) {
  const pnlColor = p.unrealized_pnl >= 0 ? "text-emerald-400" : "text-rose-400";

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
      <div className="flex items-center gap-2 min-w-[120px]">
        <span className="font-mono font-semibold text-sm">{p.ticker}</span>
        <Badge variant="outline" className="text-xs">
          {p.source === "manual_tradingview" ? "TradingView" : "Paper"}
        </Badge>
      </div>

      <div className="flex gap-4 text-xs text-muted-foreground flex-1 font-mono">
        <span>{p.shares} sh</span>
        <span>Entry <strong className="text-foreground">${p.entry_price.toFixed(2)}</strong></span>
        <span>Current <strong className="text-foreground">${p.current_price.toFixed(2)}</strong></span>
      </div>

      <div className={`text-sm font-mono font-semibold ${pnlColor} min-w-[100px] text-right`}>
        {p.unrealized_pnl >= 0 ? "+" : ""}${p.unrealized_pnl.toFixed(2)}
        <span className="ml-1 text-xs font-normal">
          ({p.unrealized_pnl_pct >= 0 ? "+" : ""}{(p.unrealized_pnl_pct * 100).toFixed(1)}%)
        </span>
      </div>
    </div>
  );
}

function SummaryTile({ label, value, signed }: { label: string; value: string; signed?: number }) {
  const color = signed == null ? "" : signed >= 0 ? "text-emerald-400" : "text-rose-400";
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className={`mt-1 font-mono text-lg font-semibold ${color}`}>{value}</div>
      </CardContent>
    </Card>
  );
}

function fmtUsd(v: number): string {
  return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtSigned(v: number): string {
  return `${v >= 0 ? "+" : ""}${fmtUsd(v)}`;
}
