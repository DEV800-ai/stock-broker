"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatUtc } from "@/lib/utils";
import type { HealthStatus, ScanRun, UniverseStats } from "@/types";

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [runs, setRuns] = useState<ScanRun[]>([]);
  const [universe, setUniverse] = useState<UniverseStats | null>(null);
  const [scanning, setScanning] = useState(false);

  async function load() {
    const [h, r, u] = await Promise.allSettled([
      api.health(),
      api.scanRuns(5),
      api.universe(),
    ]);
    if (h.status === "fulfilled") setHealth(h.value);
    if (r.status === "fulfilled") setRuns(r.value);
    if (u.status === "fulfilled") setUniverse(u.value);
  }

  const isRunning = runs[0]?.status === "running";

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const interval = setInterval(load, isRunning ? 3_000 : 60_000);
    return () => clearInterval(interval);
  }, [isRunning]);

  async function handleTriggerScan() {
    setScanning(true);
    try {
      await api.triggerScan();
      setTimeout(load, 2000);
    } finally {
      setScanning(false);
    }
  }

  async function handleClearRun(runId: number) {
    try {
      await api.deleteScanRun(runId);
      await load();
    } catch (err) {
      console.error(err);
    }
  }

  const lastRun = runs[0];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <Button onClick={handleTriggerScan} disabled={scanning} size="sm">
          {scanning ? "Triggering…" : "Run Scan Now"}
        </Button>
      </div>

      {/* System status */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatusTile label="Database" ok={health?.db} />
        <StatusTile label="Market Data" ok={health?.market_data} />
        <StatusTile label="OpenAI" ok={health?.ai} />
        <StatTile label="Universe" value={universe ? `${universe.active} tickers · ${universe.tickers_with_bars} with bars` : "—"} />
      </div>

      {/* Last scan */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Last Scan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {lastRun ? (
            <>
              <div className="flex items-center gap-4 text-sm">
                <Badge variant={lastRun.status === "complete" ? "success" : lastRun.status === "running" ? "secondary" : "destructive"}>
                  {lastRun.status}
                </Badge>
                <span className="font-mono text-muted-foreground">{formatUtc(lastRun.started_at)}</span>
                {lastRun.tickers_scanned != null && (
                  <span className="font-mono">{lastRun.tickers_scanned} scanned · {lastRun.tickers_flagged} flagged</span>
                )}
                {lastRun.status !== "complete" && (
                  <Button variant="ghost" size="sm" className="ml-auto" onClick={() => handleClearRun(lastRun.id)}>
                    Clear
                  </Button>
                )}
              </div>
              {lastRun.status === "running" && <ScanProgressBar run={lastRun} />}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No scans yet. Trigger a scan to start.</p>
          )}
        </CardContent>
      </Card>

      {/* Recent runs */}
      {runs.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Recent Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {runs.slice(1).map((run) => (
                <div key={run.id} className="flex items-center gap-3 text-sm">
                  <Badge variant={run.status === "complete" ? "outline" : "secondary"} className="text-xs">
                    {run.status}
                  </Badge>
                  <span className="font-mono text-muted-foreground">{formatUtc(run.started_at)}</span>
                  {run.tickers_flagged != null && (
                    <span className="font-mono text-muted-foreground">{run.tickers_flagged} flagged</span>
                  )}
                  {run.status !== "complete" && (
                    <Button variant="ghost" size="sm" className="ml-auto h-6 px-2 text-xs" onClick={() => handleClearRun(run.id)}>
                      Clear
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

const PHASE_LABELS: Record<string, string> = {
  fetching_bars: "Fetching price data",
  scoring: "Scoring tickers",
};

function ScanProgressBar({ run }: { run: ScanRun }) {
  const { phase, total_tickers, tickers_processed } = run;
  if (!phase || !total_tickers) {
    return <p className="text-xs text-muted-foreground">Starting…</p>;
  }
  const processed = tickers_processed ?? 0;
  // Two equal-weighted phases (fetch, then score) over the same ticker list.
  const phaseIndex = phase === "scoring" ? 1 : 0;
  const pct = Math.min(100, ((phaseIndex + processed / total_tickers) / 2) * 100);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{PHASE_LABELS[phase] ?? phase}</span>
        <span className="font-mono">{processed}/{total_tickers} · {pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function StatusTile({ label, ok }: { label: string; ok?: boolean }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="mt-1 flex items-center gap-1.5">
          <span className={`h-2 w-2 rounded-full ${ok === true ? "bg-emerald-400" : ok === false ? "bg-rose-400" : "bg-muted-foreground/40"}`} />
          <span className="text-sm font-medium">{ok === true ? "Online" : ok === false ? "Offline" : "—"}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 font-mono text-sm font-medium">{value}</p>
      </CardContent>
    </Card>
  );
}
