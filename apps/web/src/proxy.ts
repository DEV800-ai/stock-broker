import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify } from "jose";
import { requestOrigin } from "@/lib/request-origin";

// Page-level guard: redirects unauthenticated browser navigation to /login. This is an
// optimistic check (reads the session cookie only, no DB) — the real enforcement point is
// src/app/api/backend/[...path]/route.ts, which independently verifies the session before
// proxying any request to the FastAPI backend and deriving the audit actor from it.
const PUBLIC_PATHS = ["/login"];

async function hasValidSession(req: NextRequest): Promise<boolean> {
  const token = req.cookies.get("session")?.value;
  if (!token) return false;
  const secret = process.env.SESSION_SECRET;
  if (!secret) return false;
  try {
    await jwtVerify(token, new TextEncoder().encode(secret), { algorithms: ["HS256"] });
    return true;
  } catch {
    return false;
  }
}

export default async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.includes(pathname)) return NextResponse.next();

  if (!(await hasValidSession(req))) {
    return NextResponse.redirect(new URL("/login", requestOrigin(req.headers, req.nextUrl.origin)));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
