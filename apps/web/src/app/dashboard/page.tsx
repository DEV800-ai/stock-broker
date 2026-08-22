"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatUtc } from "@/lib/utils";
import type { AgentControl, HealthStatus, ScanResult, ScanRun, UniverseStats } from "@/types";

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [runs, setRuns] = useState<ScanRun[]>([]);
  const [universe, setUniverse] = useState<UniverseStats | null>(null);
  const [agentControl, setAgentControl] = useState<AgentControl | null>(null);
  const [topIdeas, setTopIdeas] = useState<ScanResult[]>([]);
  const [scanning, setScanning] = useState(false);

  async function load() {
    const [h, r, u, a, s] = await Promise.allSettled([
      api.health(),
      api.scanRuns(5),
      api.universe(),
      api.agentControl(),
      api.scanResults({ limit: 5 }),
    ]);
    if (h.status === "fulfilled") setHealth(h.value);
    if (r.status === "fulfilled") setRuns(r.value);
    if (u.status === "fulfilled") setUniverse(u.value);
    if (a.status === "fulfilled") setAgentControl(a.value);
    if (s.status === "fulfilled") setTopIdeas(s.value);
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
          {scanning ? "Triggering…" : "Run New Scan"}
        </Button>
      </div>

      {/* Market Data + Agent Status */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Market Data</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-3 gap-4">
            <StatusTile label="Database" ok={health?.db} />
            <StatusTile label="Market Data" ok={health?.market_data} />
            <StatusTile label="OpenAI" ok={health?.ai} />
            <div className="col-span-3">
              <p className="text-xs text-muted-foreground">Universe</p>
              <p className="mt-1 font-mono text-sm font-medium">
                {universe ? `${universe.active} tickers · ${universe.tickers_with_bars} with bars` : "—"}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Agent Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {agentControl ? (
              <>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">Kill switch:</span>
                  <Badge variant={agentControl.is_killed ? "destructive" : "success"}>
                    {agentControl.is_killed ? "Killed" : "Active"}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">Autonomy mode:</span>
                  <span className="font-mono">{agentControl.autonomy_mode}</span>
                </div>
                {agentControl.is_killed && agentControl.killed_reason && (
                  <p className="text-xs text-muted-foreground">Reason: {agentControl.killed_reason}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Manage from the{" "}
                  <Link href="/agent-control" className="underline hover:text-foreground">
                    Agent Control
                  </Link>{" "}
                  page.
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">—</p>
            )}
          </CardContent>
        </Card>
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

      {/* Top 5 Ideas */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Top 5 Ideas</CardTitle>
        </CardHeader>
        <CardContent>
          {topIdeas.length > 0 ? (
            <div className="space-y-2">
              {topIdeas.map((r) => (
                <Link
                  key={r.id}
                  href="/ideas"
                  className="flex items-center gap-4 rounded-md px-2 py-2 text-sm transition-colors hover:bg-muted"
                >
                  <span className="w-16 font-mono font-medium">{r.ticker}</span>
                  <span className="font-mono text-muted-foreground">
                    {r.price != null ? `$${r.price.toFixed(2)}` : "—"}
                  </span>
                  <span className="ml-auto font-mono text-muted-foreground">
                    score {r.composite_score != null ? r.composite_score.toFixed(2) : "—"}
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No scan results yet. Trigger a scan to populate ideas.</p>
          )}
        </CardContent>
      </Card>
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
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <div className="mt-1 flex items-center gap-1.5">
        <span className={`h-2 w-2 rounded-full ${ok === true ? "bg-emerald-400" : ok === false ? "bg-rose-400" : "bg-muted-foreground/40"}`} />
        <span className="text-sm font-medium">{ok === true ? "Online" : ok === false ? "Offline" : "—"}</span>
      </div>
    </div>
  );
}
