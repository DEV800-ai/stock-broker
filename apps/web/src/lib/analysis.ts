import { api } from "@/lib/api";
import type { StockThesis } from "@/types";

const POLL_INTERVAL_MS = 2000;
const MAX_ATTEMPTS = 30;

interface GenerateAndPollOptions {
  ticker: string;
  onDone: (analysis: StockThesis) => void;
  onTimeout: () => void;
}

/**
 * Fires POST /analysis/generate (fire-and-forget background job) then polls
 * GET /analysis/{ticker} until a report appears or MAX_ATTEMPTS is hit.
 * Mirrors generateAndPollThesis — a timeout is the only signal available
 * for background generation failures.
 */
export async function generateAndPollAnalysis({
  ticker,
  onDone,
  onTimeout,
}: GenerateAndPollOptions): Promise<void> {
  await api.generateAnalysis(ticker);

  let attempts = 0;
  const poll = setInterval(async () => {
    attempts++;
    try {
      const a = await api.analysis(ticker);
      clearInterval(poll);
      onDone(a);
    } catch {
      if (attempts >= MAX_ATTEMPTS) {
        clearInterval(poll);
        onTimeout();
      }
    }
  }, POLL_INTERVAL_MS);
}
