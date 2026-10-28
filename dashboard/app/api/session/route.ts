import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_BASE, SESSION_COOKIE } from "@/lib/api";

const LEGACY_SESSION_COOKIE = "tb_session";

function clearAuthCookies(res: NextResponse) {
  const expired = {
    httpOnly: true,
    sameSite: "lax" as const,
    path: "/",
    maxAge: 0,
    expires: new Date(0),
  };
  res.cookies.set(SESSION_COOKIE, "", expired);
  res.cookies.set(LEGACY_SESSION_COOKIE, "", expired);
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const token = typeof body.token === "string" ? body.token : "";
  if (!token) {
    return NextResponse.json({ error: "token required" }, { status: 400 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return res;
}

export async function DELETE() {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value || jar.get(LEGACY_SESSION_COOKIE)?.value;
  if (token) {
    try {
      await fetch(`${API_BASE}/v1/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
    } catch {
      /* ignore */
    }
  }
  const res = NextResponse.json({ ok: true });
  clearAuthCookies(res);
  return res;
}
