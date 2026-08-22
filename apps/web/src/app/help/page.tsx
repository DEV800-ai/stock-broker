import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HelpPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Help</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          What this app does, how to use it, and what it does not do.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">What this app does</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Stock Broker scans the market for tickers with notable technical signals, ranks the
            strongest ones on <strong className="text-foreground">Top Ideas</strong>, and can
            generate an AI-written research report for any ticker on{" "}
            <strong className="text-foreground">AI Analysis</strong>. Use{" "}
            <strong className="text-foreground">My Trades</strong> to keep a personal list of
            tickers you're following.
          </p>
          <p>
            <strong className="text-foreground">
              This app never places a live trade for you and never tells you to buy or sell.
            </strong>{" "}
            It only prepares research. Trading — paper or manual — happens through the workflow
            described below, and always requires a human decision.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Day-to-day workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal space-y-3 pl-4 text-sm text-muted-foreground">
            <li>
              <strong className="text-foreground">Run a scan.</strong> Click{" "}
              <em>Run New Scan</em> on the <strong className="text-foreground">Dashboard</strong>{" "}
              or <em>Run Scan</em> on <strong className="text-foreground">Top Ideas</strong>. It
              takes a few minutes to score the full ticker universe.
            </li>
            <li>
              <strong className="text-foreground">Review Top Ideas.</strong> Click a card to open
              its chart, see why it was flagged, and open it directly in TradingView.
            </li>
            <li>
              <strong className="text-foreground">Read or generate a thesis.</strong> Tickers
              scoring high enough get an AI-written summary of why they're interesting and what
              the risks are — description only, never a recommendation.
            </li>
            <li>
              <strong className="text-foreground">Track tickers you care about.</strong> Add any
              symbol to <strong className="text-foreground">My Trades</strong> to keep a personal
              watchlist with notes, enriched with the latest price and score when available.
            </li>
            <li>
              <strong className="text-foreground">Get an on-demand report.</strong> On{" "}
              <strong className="text-foreground">AI Analysis</strong>, type any ticker symbol —
              even one outside the scanned universe — to get the same kind of research report,
              generated on request.
            </li>
            <li>
              <strong className="text-foreground">Trade manually, if you choose.</strong> Any
              actual trade happens outside this app (e.g. in TradingView); you self-report the
              outcome so it's reflected in your paper-trading history.
            </li>
          </ol>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">What this app does not do</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
            <li>It does not place trades. Trades are either simulated (paper) or executed manually by you elsewhere (e.g. TradingView) and self-reported back.</li>
            <li>It does not tell you to buy or sell — reports describe conditions, not actions.</li>
            <li>It does not log in to TradingView or any broker on your behalf.</li>
            <li>It does not move a paper trade to open without a human clicking Approve.</li>
            <li>It does not file taxes or calculate tax liability.</li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Understanding the score</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Each ticker gets a composite score (0–100%) blending volume surge, momentum, relative
            strength vs. its sector, and gap size. A score of 30%+ puts it on the watchlist; 50%+
            makes it eligible for an AI thesis during a scan. On{" "}
            <strong className="text-foreground">AI Analysis</strong> this threshold doesn't apply —
            any ticker you enter gets a report on request.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Advanced pages</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            The order-preview/approval workflow, paper-trading positions, portfolio summary,
            weekly performance reports, and the agent kill switch are still fully available — they're
            just not in the top navigation anymore. Reach them directly at{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">/orders</code>,{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">/paper-trades</code>,{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">/portfolio</code>,{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">/reports</code>, and{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">/agent-control</code>.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">If something looks stuck or empty</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
            <li>
              <strong className="text-foreground">Dashboard tiles show "—"</strong> — the backend
              hasn't responded yet; wait a moment or check back after a scan.
            </li>
            <li>
              <strong className="text-foreground">A scan run stays stuck on "running"</strong> —
              click <strong className="text-foreground">Clear</strong> next to it on the
              Dashboard to remove it, then run a new scan.
            </li>
            <li>
              <strong className="text-foreground">Top Ideas shows no status badges</strong> — run
              a scan for today; badges are tied to the most recent day a scan completed.
            </li>
            <li>
              <strong className="text-foreground">AI Analysis is taking a while</strong> — reports
              are generated in the background and polled for; a slow ticker or busy API can take
              up to a minute.
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
