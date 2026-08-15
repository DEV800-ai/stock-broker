"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/scanner", label: "Scanner" },
  { href: "/paper-trades", label: "Paper Trades" },
  { href: "/orders", label: "Order Previews" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-background px-6 py-3">
      <div className="mx-auto flex max-w-7xl items-center gap-6">
        <span className="font-mono text-sm font-semibold tracking-wide text-foreground">Stock Broker</span>
        <nav className="flex gap-4 text-sm">
          {LINKS.map((link) => {
            const active = pathname === link.href || pathname?.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "transition-colors",
                  active ? "font-medium text-foreground" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
