import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { NavBar } from "@/components/nav-bar";
import { getSession } from "@/lib/session";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: "Stock Broker",
  description: "AI-powered stock scanner and research assistant",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className={`${geist.variable} ${geistMono.variable} min-h-full bg-background font-sans text-foreground`}>
        <NavBar userEmail={session?.email ?? null} />
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
