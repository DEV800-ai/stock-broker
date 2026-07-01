"use client";

import { useEffect, useState } from "react";
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
          <label className="text-zinc-500">Min score</label>
          <select
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="rounded border border-zinc-200 px-2 py-1 text-xs"
          >
            <option value={0}>All</option>
            <option value={0.3}>0.30+</option>
            <option value={0.5}>0.50+</option>
            <option value={0.75}>0.75+</option>
          </select>
        </div>
      </div>

      {results.length === 0 ? (
        <p className="text-sm text-zinc-400">No scan results yet.</p>
      ) : (
        <div className="rounded-md border border-zinc-200 bg-white overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-zinc-50">
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
                <TableRow key={r.id} className="hover:bg-zinc-50">
                  <TableCell className="font-medium">{r.ticker}</TableCell>
                  <TableCell className="text-right text-sm">
                    {r.composite_score != null ? (r.composite_score * 100).toFixed(0) + "%" : "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm text-zinc-500">
                    {r.volume_ratio != null ? r.volume_ratio.toFixed(1) + "×" : "—"}
                  </TableCell>
                  <TableCell className={`text-right text-sm ${(r.pct_change_5d ?? 0) >= 0 ? "text-green-600" : "text-red-500"}`}>
                    {r.pct_change_5d != null ? (r.pct_change_5d >= 0 ? "+" : "") + r.pct_change_5d.toFixed(1) + "%" : "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm text-zinc-500">
                    {r.rsi_14?.toFixed(0) ?? "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {r.price != null ? `$${r.price.toFixed(2)}` : "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {r.signals_fired &&
                        Object.entries(r.signals_fired)
                          .filter(([, v]) => v)
                          .map(([k]) => (
                            <span key={k} className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600">
                              {k}
                            </span>
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
