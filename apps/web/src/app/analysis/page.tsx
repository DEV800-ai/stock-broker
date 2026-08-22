"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorAlert } from "@/components/error-alert";
import { ThesisView } from "@/components/thesis-view";
import { generateAndPollAnalysis } from "@/lib/analysis";
import type { StockThesis } from "@/types";

const inputCls = "w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

export default function AnalysisPage() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StockThesis | null>(null);

  async function handleGenerate() {
    const t = ticker.trim().toUpperCase();
    if (!t) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      await generateAndPollAnalysis({
        ticker: t,
        onDone: (a) => {
          setResult(a);
          setLoading(false);
        },
        onTimeout: () => {
          setLoading(false);
          setError("Analysis didn't complete in time — the ticker may be invalid or generation failed. Try again shortly.");
        },
      });
    } catch (err) {
      setLoading(false);
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">AI Analysis</h1>
      <p className="text-sm text-muted-foreground">
        Enter any stock symbol to get an AI-generated research report — this describes the stock, it doesn't
        recommend buying or selling.
      </p>

      <Card>
        <CardContent className="pt-4">
          <div className="flex gap-3">
            <input
              className={inputCls}
              placeholder="Ticker (e.g. AAPL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            />
            <Button onClick={handleGenerate} disabled={loading || !ticker.trim()}>
              {loading ? "Generating…" : "Get Analysis"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && <ErrorAlert message={error} />}
      {result && <ThesisView thesis={result} />}
    </div>
  );
}
