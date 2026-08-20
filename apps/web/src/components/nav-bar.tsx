"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/ideas", label: "Top Ideas" },
  { href: "/orders", label: "Orders" },
  { href: "/paper-trades", label: "Positions" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/reports", label: "Reports" },
  { href: "/agent-control", label: "Agent Control" },
  { href: "/help", label: "Help" },
];

export function NavBar({ userEmail }: { userEmail: string | null }) {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-background px-6 py-3">
      <div className="mx-auto flex max-w-7xl items-center gap-6">
        <span className="font-mono text-sm font-semibold tracking-wide text-foreground">Stock Broker</span>
        <nav className="flex flex-1 gap-4 text-sm">
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
        {userEmail && (
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{userEmail}</span>
            <form action="/api/auth/logout" method="POST">
              <button type="submit" className="transition-colors hover:text-foreground">
                Sign out
              </button>
            </form>
          </div>
        )}
      </div>
    </header>
  );
}
