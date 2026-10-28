import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/api";

const PUBLIC = ["/login", "/auth/callback"];
const LEGACY_SESSION_COOKIE = "tb_session";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".") // static assets
  ) {
    return NextResponse.next();
  }

  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const isPublic = PUBLIC.some((p) => pathname === p || pathname.startsWith(`${p}/`));

  if (!token && !isPublic) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    const res = NextResponse.redirect(url);
    res.headers.set("Cache-Control", "private, no-store");
    // Drop legacy cookie from earlier auth mocks so it cannot resurrect a session.
    if (request.cookies.get(LEGACY_SESSION_COOKIE)?.value) {
      res.cookies.set(LEGACY_SESSION_COOKIE, "", { path: "/", maxAge: 0 });
    }
    return res;
  }

  // Allow /login while signed in so users can open the form; Sign out clears the session.
  const res = NextResponse.next();
  if (request.cookies.get(LEGACY_SESSION_COOKIE)?.value) {
    res.cookies.set(LEGACY_SESSION_COOKIE, "", { path: "/", maxAge: 0 });
  }
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
