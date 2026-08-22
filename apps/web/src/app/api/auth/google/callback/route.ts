import { NextRequest, NextResponse } from "next/server";
import { createRemoteJWKSet, jwtVerify } from "jose";
import { createSession } from "@/lib/session";

export const dynamic = "force-dynamic";

const STATE_COOKIE = "oauth_state";
const GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token";
const GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs";
const GOOGLE_ISSUER = ["https://accounts.google.com", "accounts.google.com"];

const jwks = createRemoteJWKSet(new URL(GOOGLE_JWKS_URL));

function allowedEmails(): Set<string> {
  return new Set(
    (process.env.ALLOWED_EMAILS ?? "")
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean)
  );
}

function loginError(origin: string, message: string) {
  const url = new URL("/login", origin);
  url.searchParams.set("error", message);
  return NextResponse.redirect(url);
}

export async function GET(req: NextRequest) {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  if (!clientId || !clientSecret) {
    return NextResponse.json({ detail: "Server is misconfigured: GOOGLE_CLIENT_ID/SECRET not set" }, { status: 500 });
  }

  const allowed = allowedEmails();
  if (allowed.size === 0) {
    return NextResponse.json({ detail: "Server is misconfigured: ALLOWED_EMAILS is not set" }, { status: 500 });
  }

  const forwardedProto = req.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const origin = forwardedProto
    ? `${forwardedProto}://${req.headers.get("x-forwarded-host") ?? req.nextUrl.host}`
    : req.nextUrl.origin;

  const { searchParams } = req.nextUrl;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const expectedState = req.cookies.get(STATE_COOKIE)?.value;

  if (!code || !state || !expectedState || state !== expectedState) {
    return loginError(origin, "Login failed: invalid or expired state");
  }

  const redirectUri = new URL("/api/auth/google/callback", origin).toString();

  const tokenRes = await fetch(GOOGLE_TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: clientId,
      client_secret: clientSecret,
      redirect_uri: redirectUri,
      grant_type: "authorization_code",
    }),
  });

  if (!tokenRes.ok) {
    return loginError(origin, "Login failed: could not exchange code");
  }

  const tokenBody = (await tokenRes.json()) as { id_token?: string };
  if (!tokenBody.id_token) {
    return loginError(origin, "Login failed: no ID token returned");
  }

  let email: string | undefined;
  let name: string | undefined;
  let emailVerified: boolean | undefined;
  try {
    const { payload } = await jwtVerify(tokenBody.id_token, jwks, {
      issuer: GOOGLE_ISSUER,
      audience: clientId,
    });
    email = typeof payload.email === "string" ? payload.email : undefined;
    name = typeof payload.name === "string" ? payload.name : undefined;
    emailVerified = payload.email_verified === true;
  } catch {
    return loginError(origin, "Login failed: invalid ID token");
  }

  if (!email || !emailVerified) {
    return loginError(origin, "Login failed: email not verified");
  }
  if (!allowed.has(email.toLowerCase())) {
    return loginError(origin, "This Google account is not authorized for this app");
  }

  await createSession({ email, name: name ?? null });

  const res = NextResponse.redirect(new URL("/", origin));
  res.cookies.delete(STATE_COOKIE);
  return res;
}
