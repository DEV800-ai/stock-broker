import { NextRequest, NextResponse } from "next/server";
import { requestOrigin } from "@/lib/request-origin";
import { deleteSession } from "@/lib/session";

export async function POST(req: NextRequest) {
  await deleteSession();
  return NextResponse.redirect(new URL("/login", requestOrigin(req.headers, req.nextUrl.origin)));
}
