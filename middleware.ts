import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE, expectedToken } from "@/lib/auth";

// Gate everything except the login page and its API. If APP_PASSWORD is unset,
// expectedToken() returns null and the app is open (matches the Streamlit
// behaviour where an unset secret skipped the gate).
export async function middleware(req: NextRequest) {
  const expected = await expectedToken();
  if (!expected) return NextResponse.next();

  const token = req.cookies.get(AUTH_COOKIE)?.value;
  if (token === expected) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("from", req.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = {
  // Skip the login page, the auth API, Next internals and static assets.
  matcher: ["/((?!login|api/login|_next/static|_next/image|favicon.ico).*)"],
};
