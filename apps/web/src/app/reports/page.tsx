"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { PerformanceReview } from "@/types";

export default function ReportsPage() {
  const [latest, setLatest] = useState<PerformanceReview | null>(null);
  const [history, setHistory] = useState<PerformanceReview[]>([]);
  const [generating, setGenerating] = useState(false);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(() => {
    api
      .weeklyReviewLatest()
      .then((r) => {
        setLatest(r);
        setNotFound(false);
      })
      .catch(() => setNotFound(true));
    api.weeklyReviewHistory().then(setHistory).catch(console.error);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleGenerate() {
    setGenerating(true);
    try {
      await api.generateWeeklyReview();
      load();
    } catch (err) {
      console.error(err);
    } finally {
      setGenerating(false);
    }
  }

  const report = latest?.report;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Weekly Performance Review</h1>
          <p className="text-sm text-muted-foreground">
            Paper-trading track record over the trailing 7-day window — win rate, P&amp;L, and
            fill quality, generated on demand.
          </p>
        </div>
        <Button onClick={handleGenerate} disabled={generating}>
          {generating ? "Generating…" : "Generate Now"}
        </Button>
      </div>

      {notFound && !latest && (
        <p className="text-sm text-muted-foreground">
          No review has been generated yet. Click &quot;Generate Now&quot; to create one.
        </p>
      )}

      {latest && report && (
        <>
          <p className="text-xs text-muted-foreground">
            Period {latest.period_start} &ndash; {latest.period_end} · generated{" "}
            {new Date(latest.generated_at).toLocaleString()}
          </p>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <SummaryTile
              label="Win Rate"
              value={report.win_rate != null ? `${(report.win_rate * 100).toFixed(1)}%` : "—"}
            />
            <SummaryTile
              label="Avg P&L %"
              value={report.avg_pnl_pct != null ? `${(report.avg_pnl_pct * 100).toFixed(1)}%` : "—"}
              signed={report.avg_pnl_pct ?? undefined}
            />
            <SummaryTile label="Closed Trades" value={String(report.closed_trade_count)} />
            <SummaryTile label="Previews" value={String(report.preview_count)} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">Risk Verdicts</CardTitle>
            </CardHeader>
            <CardContent>
              <CountRow counts={report.risk_verdict_counts} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">Fill Status</CardTitle>
            </CardHeader>
            <CardContent>
              <CountRow counts={report.fill_status_counts} />
            </CardContent>
          </Card>

          {Object.keys(report.by_source).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">By Source</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {Object.entries(report.by_source).map(([source, s]) => (
                  <div key={source} className="flex items-center justify-between text-sm">
                    <span className="font-mono">{source}</span>
                    <span className="text-muted-foreground">
                      {s.trade_count} trades · {s.win_rate != null ? `${(s.win_rate * 100).toFixed(1)}% win` : "—"}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}

      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-border">
              {history.map((h) => (
                <div key={h.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="font-mono text-xs text-muted-foreground">
                    {h.period_start} – {h.period_end}
                  </span>
                  <span>
                    {h.report.win_rate != null ? `${(h.report.win_rate * 100).toFixed(1)}% win` : "—"}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function CountRow({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">No data for this period.</p>;
  }
  return (
    <div className="flex flex-wrap gap-4 text-sm">
      {entries.map(([key, value]) => (
        <span key={key} className="font-mono">
          {key}: <strong className="text-foreground">{value}</strong>
        </span>
      ))}
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
