"use client";

import { useEffect, useRef } from "react";

// Read-only embed of TradingView's public "Advanced Chart" widget (tradingview.com/widget-docs).
// This is display-only — no account/broker data, no order execution. TradingView explicitly
// allows this widget path to be iframed by third-party sites, unlike the main tradingview.com
// app which blocks embedding via frame-ancestors.
export function TradingViewWidget({ symbol, height = 320 }: { symbol: string; height?: number }) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = container.current;
    if (!el) return;
    el.innerHTML = "";

    const widgetDiv = document.createElement("div");
    widgetDiv.className = "tradingview-widget-container__widget";
    el.appendChild(widgetDiv);

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.text = JSON.stringify({
      symbol,
      width: "100%",
      height,
      locale: "en",
      dateRange: "3M",
      colorTheme: "dark",
      isTransparent: false,
      autosize: false,
      hide_side_toolbar: true,
      allow_symbol_change: false,
      support_host: "https://www.tradingview.com",
    });
    el.appendChild(script);

    return () => { el.innerHTML = ""; };
  }, [symbol, height]);

  return <div className="tradingview-widget-container" ref={container} style={{ height }} />;
}
