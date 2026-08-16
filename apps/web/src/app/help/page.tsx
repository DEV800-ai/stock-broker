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
            generate an AI-written research thesis for any of them. From there you can prepare an
            order preview and track it through to a paper trade.
          </p>
          <p>
            <strong className="text-foreground">
              This app never places a live trade for you and never tells you to buy or sell.
            </strong>{" "}
            It only prepares research and an order preview. You review it and decide.
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
              <em>Run Scan</em> on <strong className="text-foreground">Top Ideas</strong> or the{" "}
              <strong className="text-foreground">Dashboard</strong>. It takes a few minutes to
              score the full ticker universe.
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
              <strong className="text-foreground">Set a status.</strong> Mark a ticker Watching,
              Researching, Paper Trading, or Avoided to track where it stands.
            </li>
            <li>
              <strong className="text-foreground">Prepare an order preview.</strong> From a
              ticker's detail panel, fill in shares/price and submit — this does not execute
              anything, it queues a preview for review on{" "}
              <strong className="text-foreground">Orders</strong>.
            </li>
            <li>
              <strong className="text-foreground">Approve or reject.</strong> On{" "}
              <strong className="text-foreground">Orders</strong>, a human reviews the preview
              and its risk evaluation, then approves or rejects it. Nothing moves without this
              step.
            </li>
            <li>
              <strong className="text-foreground">Track it.</strong> Approved trades show up on{" "}
              <strong className="text-foreground">Positions</strong> as simulated paper trades —
              no real money is involved.
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
            <li>It does not place live trades. Trades are simulated (paper) only.</li>
            <li>It does not tell you to buy or sell — theses describe conditions, not actions.</li>
            <li>It does not log in to TradingView, IBKR, or any broker on your behalf.</li>
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
            makes it eligible for an AI thesis.
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
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
