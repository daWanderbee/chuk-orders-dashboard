import { NextResponse } from "next/server";
import { AUTH_COOKIE, authToken } from "@/lib/auth";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const pw = process.env.APP_PASSWORD;
  if (!pw) {
    // No password configured → nothing to log in to.
    return NextResponse.json({ ok: true });
  }
  let password = "";
  try {
    const body = await req.json();
    password = String(body?.password ?? "");
  } catch {
    /* empty body */
  }
  if (password !== pw) {
    return NextResponse.json({ ok: false, error: "Wrong password." }, { status: 401 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(AUTH_COOKIE, await authToken(pw), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30, // 30 days
  });
  return res;
}
