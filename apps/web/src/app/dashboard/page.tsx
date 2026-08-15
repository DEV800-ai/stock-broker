"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
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

  useEffect(() => {
    load();
    const interval = setInterval(load, 60_000);
    return () => clearInterval(interval);
  }, []);

  async function handleTriggerScan() {
    setScanning(true);
    try {
      await api.triggerScan();
      setTimeout(load, 2000);
    } finally {
      setScanning(false);
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
        <StatusTile label="IBKR Gateway" ok={health?.ibkr_gateway} />
        <StatusTile label="OpenAI" ok={health?.ai} />
        <StatTile label="Universe" value={universe ? `${universe.active} tickers · ${universe.tickers_with_bars} with bars` : "—"} />
      </div>

      {/* Last scan */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Last Scan</CardTitle>
        </CardHeader>
        <CardContent>
          {lastRun ? (
            <div className="flex items-center gap-4 text-sm">
              <Badge variant={lastRun.status === "complete" ? "success" : lastRun.status === "running" ? "secondary" : "destructive"}>
                {lastRun.status}
              </Badge>
              <span className="font-mono text-muted-foreground">{new Date(lastRun.started_at).toLocaleString()}</span>
              {lastRun.tickers_scanned != null && (
                <span className="font-mono">{lastRun.tickers_scanned} scanned · {lastRun.tickers_flagged} flagged</span>
              )}
            </div>
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
                  <span className="font-mono text-muted-foreground">{new Date(run.started_at).toLocaleString()}</span>
                  {run.tickers_flagged != null && (
                    <span className="font-mono text-muted-foreground">{run.tickers_flagged} flagged</span>
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
