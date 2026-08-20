import { NextRequest, NextResponse } from "next/server";
import { deleteSession } from "@/lib/session";

export async function POST(req: NextRequest) {
  await deleteSession();
  return NextResponse.redirect(new URL("/login", req.nextUrl.origin));
}
