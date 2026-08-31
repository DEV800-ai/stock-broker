import { NextRequest, NextResponse } from "next/server";
import { randomBytes } from "crypto";
import { requestOrigin } from "@/lib/request-origin";

export const dynamic = "force-dynamic";

const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const STATE_COOKIE = "oauth_state";

export async function GET(req: NextRequest) {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  if (!clientId) {
    return NextResponse.json({ detail: "Server is misconfigured: GOOGLE_CLIENT_ID is not set" }, { status: 500 });
  }

  const state = randomBytes(16).toString("hex");
  const origin = requestOrigin(req.headers, req.nextUrl.origin);
  const redirectUri = new URL("/api/auth/google/callback", origin).toString();

  const authUrl = new URL(GOOGLE_AUTH_URL);
  authUrl.searchParams.set("client_id", clientId);
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("scope", "openid email profile");
  authUrl.searchParams.set("state", state);
  authUrl.searchParams.set("prompt", "select_account");

  const res = NextResponse.redirect(authUrl);
  res.cookies.set(STATE_COOKIE, state, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 600,
    path: "/",
  });
  return res;
}
