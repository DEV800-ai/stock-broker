import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Stock Broker",
  description: "AI-powered stock scanner and research assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className={`${geist.className} min-h-full bg-zinc-50 text-zinc-900`}>
        <header className="border-b border-zinc-200 bg-white px-6 py-3">
          <div className="mx-auto flex max-w-7xl items-center gap-6">
            <span className="text-sm font-semibold tracking-wide">Stock Broker</span>
            <nav className="flex gap-4 text-sm text-zinc-500">
              <Link href="/dashboard" className="hover:text-zinc-900">Dashboard</Link>
              <Link href="/watchlist" className="hover:text-zinc-900">Watchlist</Link>
              <Link href="/scanner" className="hover:text-zinc-900">Scanner</Link>
              <Link href="/paper-trades" className="hover:text-zinc-900">Paper Trades</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
