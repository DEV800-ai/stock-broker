import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";

// Server-only — never prefixed with NEXT_PUBLIC_, so it never reaches the browser bundle.
// The FastAPI backend still validates X-API-Key on every non-/health route; this proxy is
// the only thing allowed to know that key. Set API_URL/API_KEY (and HUMAN_APPROVAL_KEY, if
// used) as plain server env vars on the Next.js Railway service, not NEXT_PUBLIC_* ones.
const API_URL = process.env.API_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_KEY ?? "";
const HUMAN_APPROVAL_KEY = process.env.HUMAN_APPROVAL_KEY ?? "";

export const dynamic = "force-dynamic";

// Mirrors the routes gated by require_human_actor in broker/auth.py (see broker/main.py's
// router wiring). X-Human-Key must only reach these — attaching it to every proxied request
// would silently collapse require_human_actor back to require_actor for anyone using the UI.
const HUMAN_GATED_ROUTES: { method: string; pattern: RegExp }[] = [
  { method: "POST", pattern: /^api\/v1\/manual-execution\/[^/]+$/ },
  { method: "POST", pattern: /^api\/v1\/agent-control\/unkill$/ },
  { method: "POST", pattern: /^api\/v1\/agent-control\/autonomy-mode$/ },
  { method: "PUT", pattern: /^api\/v1\/paper-trades\/[^/]+\/approve$/ },
  { method: "PUT", pattern: /^api\/v1\/paper-trades\/[^/]+\/reject$/ },
  { method: "PUT", pattern: /^api\/v1\/paper-trades\/[^/]+\/close$/ },
  { method: "POST", pattern: /^api\/v1\/orders\/[^/]+\/approve$/ },
  { method: "POST", pattern: /^api\/v1\/orders\/[^/]+\/reject$/ },
];

function isHumanGated(method: string, path: string[]): boolean {
  const joined = path.join("/");
  return HUMAN_GATED_ROUTES.some((r) => r.method === method && r.pattern.test(joined));
}

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const joined = path.join("/");
  const target = new URL(`/${joined}${req.nextUrl.search}`, API_URL);

  // Real login (Google OAuth) identifies who is acting — the browser can no longer assert
  // its own actor via a header. /health is exempt to match the backend's own auth rule.
  const session = joined === "api/v1/health" ? null : await getSession();
  if (joined !== "api/v1/health" && !session) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const headers = new Headers();
  headers.set("Content-Type", req.headers.get("content-type") ?? "application/json");
  headers.set("X-API-Key", API_KEY);
  if (session) headers.set("X-Actor", session.email);
  if (HUMAN_APPROVAL_KEY && isHumanGated(req.method, path)) {
    headers.set("X-Human-Key", HUMAN_APPROVAL_KEY);
  }

  const init: RequestInit = { method: req.method, headers };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  let res: Response;
  try {
    res = await fetch(target, init);
  } catch {
    return NextResponse.json({ detail: "Backend unreachable" }, { status: 502 });
  }

  if (res.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const body = await res.text();
  return new NextResponse(body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("content-type") ?? "application/json" },
  });
}

type RouteParams = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
export async function POST(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
export async function PUT(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
export async function PATCH(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
export async function DELETE(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
