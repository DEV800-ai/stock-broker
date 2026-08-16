"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorAlert } from "@/components/error-alert";
import { api } from "@/lib/api";
import { formatUtc } from "@/lib/utils";
import type { AgentControl, AutonomyMode } from "@/types";

const AUTONOMY_MODES: { value: AutonomyMode; label: string; description: string }[] = [
  {
    value: "research_only",
    label: "Research only",
    description: "Scans and theses only — no order previews are created.",
  },
  {
    value: "paper_only",
    label: "Paper only",
    description: "Order previews are limited to simulated paper fills.",
  },
  {
    value: "preview_required",
    label: "Preview required",
    description: "Normal operation — every order still requires human approval.",
  },
];

export default function AgentControlPage() {
  const [control, setControl] = useState<AgentControl | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [killReason, setKillReason] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setControl(await api.agentControl());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
  }, []);

  async function handleKill() {
    if (!killReason.trim()) return;
    setBusy(true);
    try {
      setControl(await api.killAgent(killReason.trim()));
      setKillReason("");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleUnkill() {
    setBusy(true);
    try {
      setControl(await api.unkillAgent());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleModeChange(mode: AutonomyMode) {
    setBusy(true);
    try {
      setControl(await api.setAutonomyMode(mode));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Agent Control</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Kill switch and autonomy mode. These gate the risk engine directly — a kill stops every
          new order preview from being created, regardless of score or approval.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Kill switch</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <Badge variant={control?.is_killed ? "destructive" : "success"}>
              {control?.is_killed ? "Killed" : "Active"}
            </Badge>
            {control?.is_killed && control.killed_reason && (
              <span className="text-sm text-muted-foreground">
                &ldquo;{control.killed_reason}&rdquo;
                {control.killed_at && ` — ${formatUtc(control.killed_at)}`}
              </span>
            )}
          </div>

          {control?.is_killed ? (
            <Button variant="outline" size="sm" onClick={handleUnkill} disabled={busy}>
              {busy ? "Restoring…" : "Un-kill"}
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <input
                className="w-72 rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="Reason (required)"
                value={killReason}
                onChange={(e) => setKillReason(e.target.value)}
              />
              <Button
                variant="destructive"
                size="sm"
                onClick={handleKill}
                disabled={busy || !killReason.trim()}
              >
                {busy ? "Killing…" : "Kill"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Autonomy mode</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {AUTONOMY_MODES.map((m) => (
            <div key={m.value} className="flex items-center gap-3">
              <input
                type="radio"
                name="autonomy-mode"
                id={`mode-${m.value}`}
                checked={control?.autonomy_mode === m.value}
                disabled={busy || !control}
                onChange={() => handleModeChange(m.value)}
              />
              <label htmlFor={`mode-${m.value}`} className="text-sm">
                <span className="font-medium">{m.label}</span>{" "}
                <span className="text-muted-foreground">— {m.description}</span>
              </label>
            </div>
          ))}
        </CardContent>
      </Card>

      {control && (
        <p className="text-xs text-muted-foreground">
          Last updated {formatUtc(control.updated_at)}
          {control.updated_by && ` by ${control.updated_by}`}
        </p>
      )}
    </div>
  );
}
