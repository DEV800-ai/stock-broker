import { NextRequest, NextResponse } from "next/server";

// Server-only — never prefixed with NEXT_PUBLIC_, so it never reaches the browser bundle.
// The FastAPI backend still validates X-API-Key on every non-/health route; this proxy is
// the only thing allowed to know that key. Set API_URL/API_KEY (and HUMAN_APPROVAL_KEY, if
// used) as plain server env vars on the Next.js Railway service, not NEXT_PUBLIC_* ones.
const API_URL = process.env.API_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_KEY ?? "";
const HUMAN_APPROVAL_KEY = process.env.HUMAN_APPROVAL_KEY ?? "";

export const dynamic = "force-dynamic";

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const target = new URL(`/${path.join("/")}${req.nextUrl.search}`, API_URL);

  const headers = new Headers();
  headers.set("Content-Type", req.headers.get("content-type") ?? "application/json");
  headers.set("X-API-Key", API_KEY);
  const actor = req.headers.get("x-actor");
  if (actor) headers.set("X-Actor", actor);
  if (HUMAN_APPROVAL_KEY) headers.set("X-Human-Key", HUMAN_APPROVAL_KEY);

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
