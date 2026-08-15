"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import type { ScanResult } from "@/types";

export default function ScannerPage() {
  const [results, setResults] = useState<ScanResult[]>([]);
  const [minScore, setMinScore] = useState(0.3);

  useEffect(() => {
    api.scanResults({ min_score: minScore, limit: 100 })
      .then(setResults)
      .catch(console.error);
  }, [minScore]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Scanner Results</h1>
        <div className="flex items-center gap-2 text-sm">
          <label className="text-muted-foreground">Min score</label>
          <select
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="rounded border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value={0}>All</option>
            <option value={0.3}>0.30+</option>
            <option value={0.5}>0.50+</option>
            <option value={0.75}>0.75+</option>
          </select>
        </div>
      </div>

      {results.length === 0 ? (
        <p className="text-sm text-muted-foreground">No scan results yet.</p>
      ) : (
        <div className="rounded-md border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead>Ticker</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead className="text-right">Volume Ratio</TableHead>
                <TableHead className="text-right">5d %</TableHead>
                <TableHead className="text-right">RSI</TableHead>
                <TableHead className="text-right">Price</TableHead>
                <TableHead>Signals</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((r) => (
                <TableRow key={r.id} className="hover:bg-muted/40">
                  <TableCell className="font-mono font-medium">{r.ticker}</TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {r.composite_score != null ? (r.composite_score * 100).toFixed(0) + "%" : "—"}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm text-muted-foreground">
                    {r.volume_ratio != null ? r.volume_ratio.toFixed(1) + "×" : "—"}
                  </TableCell>
                  <TableCell className={`text-right font-mono text-sm ${(r.pct_change_5d ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {r.pct_change_5d != null ? (r.pct_change_5d >= 0 ? "+" : "") + r.pct_change_5d.toFixed(1) + "%" : "—"}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm text-muted-foreground">
                    {r.rsi_14?.toFixed(0) ?? "—"}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {r.price != null ? `$${r.price.toFixed(2)}` : "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {r.signals_fired &&
                        Object.entries(r.signals_fired)
                          .filter(([, v]) => v)
                          .map(([k]) => (
                            <Badge key={k} variant="outline" className="text-xs font-normal">
                              {k}
                            </Badge>
                          ))}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
