import { api } from "@/lib/api";
import type { StockThesis } from "@/types";

const POLL_INTERVAL_MS = 2000;
const MAX_ATTEMPTS = 30;

interface GenerateAndPollOptions {
  ticker: string;
  scanResultId?: number;
  onDone: (thesis: StockThesis) => void;
  onTimeout: () => void;
}

/**
 * Fires POST /thesis/generate (fire-and-forget background job) then polls
 * GET /thesis/{ticker} until a thesis appears or MAX_ATTEMPTS is hit.
 * Generation failures (e.g. composite_score below thesis_min_score) happen
 * server-side in the background task and never surface on the initial
 * POST, so a timeout is the only signal we get — onTimeout should tell
 * the user generation didn't complete rather than failing silently.
 */
export async function generateAndPollThesis({
  ticker,
  scanResultId,
  onDone,
  onTimeout,
}: GenerateAndPollOptions): Promise<void> {
  await api.generateThesis(ticker, scanResultId);

  let attempts = 0;
  const poll = setInterval(async () => {
    attempts++;
    try {
      const t = await api.thesis(ticker);
      clearInterval(poll);
      onDone(t);
    } catch {
      if (attempts >= MAX_ATTEMPTS) {
        clearInterval(poll);
        onTimeout();
      }
    }
  }, POLL_INTERVAL_MS);
}
