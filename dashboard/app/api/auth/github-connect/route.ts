import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_BASE, SESSION_COOKIE } from "@/lib/api";

const NOT_CONFIGURED =
  "GitHub isn’t configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET on the server.";

export async function GET(request: Request) {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const url = new URL(request.url);
  const next = url.searchParams.get("next") || "/connect";
  const back = new URL(next.startsWith("/") ? next : "/connect", request.url);

  let githubReal = false;
  let isDemo = false;
  try {
    const [providersRes, meRes] = await Promise.all([
      fetch(`${API_BASE}/v1/auth/providers`, { cache: "no-store" }),
      fetch(`${API_BASE}/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      }),
    ]);
    if (providersRes.ok) {
      const providers = await providersRes.json();
      githubReal = Boolean(providers.github_real);
    }
    if (meRes.ok) {
      const me = await meRes.json();
      isDemo = Boolean(me.user?.is_demo);
    }
  } catch {
    /* fall through — collector will reject if needed */
  }

  // Non-demo accounts must use real GitHub OAuth; do not attach octocat-dev.
  if (!githubReal && !isDemo) {
    back.searchParams.set("error", NOT_CONFIGURED);
    return NextResponse.redirect(back);
  }

  const redirectTo = `/auth/callback?next=${encodeURIComponent(next)}`;
  const target = new URL(`${API_BASE}/v1/auth/github/start`);
  target.searchParams.set("intent", "connect");
  target.searchParams.set("redirect_to", redirectTo);
  target.searchParams.set("session_token", token);
  return NextResponse.redirect(target.toString());
}
