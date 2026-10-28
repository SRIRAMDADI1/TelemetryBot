"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PulseMark, PulseWordmark } from "@/components/Brand";
import {
  API_BASE,
  browserAuth,
  formatApiDetail,
  safeNextPath,
  type AuthProviders,
} from "@/lib/api";

type AuthTab = "signin" | "register";

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden="true">
      <path d="M12 .3a12 12 0 0 0-3.79 23.4c.6.11.82-.26.82-.58v-2.02c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.33-1.76-1.33-1.76-1.09-.74.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.83 2.8 1.3 3.49 1 .11-.78.42-1.3.76-1.6-2.66-.3-5.46-1.33-5.46-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.66.25 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.8 5.62-5.48 5.92.43.37.81 1.1.81 2.23v3.3c0 .32.22.7.82.58A12 12 0 0 0 12 .3z" />
    </svg>
  );
}

export function LoginForm({ providers }: { providers: AuthProviders }) {
  const router = useRouter();
  const search = useSearchParams();
  const next = safeNextPath(search.get("next"), "/");
  const magicFromUrl = search.get("magic");
  const errorFromUrl = search.get("error");

  const [tab, setTab] = useState<AuthTab>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(errorFromUrl);

  useEffect(() => {
    if (!magicFromUrl) return;
    let cancelled = false;
    (async () => {
      setBusy(true);
      try {
        const res = await fetch(`${API_BASE}/v1/auth/email/magic/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: magicFromUrl }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(formatApiDetail(data.detail, "Magic link invalid"));
        await browserAuth.persistSession(data.session_token);
        if (!cancelled) {
          router.replace(next);
          router.refresh();
        }
      } catch (err) {
        if (!cancelled) setMessage(err instanceof Error ? err.message : "Magic link failed");
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [magicFromUrl, next, router]);

  async function finish(token: string) {
    await browserAuth.persistSession(token);
    router.replace(next);
    router.refresh();
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const path = tab === "register" ? "/v1/auth/email/register" : "/v1/auth/email/login";
      const body =
        tab === "register"
          ? { email, password, name: name || undefined }
          : { email, password };
      const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(formatApiDetail(data.detail, "Sign-in failed"));
      await finish(data.session_token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  function startGitHub() {
    if (!providers.github) {
      setMessage("GitHub sign-in isn’t configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET on the server, or use email.");
      return;
    }
    if (!providers.github_real && !providers.dev_mode) {
      setMessage("GitHub sign-in isn’t configured. Set OAuth credentials on the server, or use email.");
      return;
    }
    const redirectTo = `/auth/callback?next=${encodeURIComponent(next)}`;
    const url = new URL(`${API_BASE}/v1/auth/github/start`);
    url.searchParams.set("intent", "login");
    url.searchParams.set("redirect_to", redirectTo);
    url.searchParams.set("t", String(Date.now()));
    window.location.assign(url.toString());
  }

  function switchTab(nextTab: AuthTab) {
    setTab(nextTab);
    setMessage(null);
    setPassword("");
  }

  const mockHint =
    providers.dev_mode && !providers.github_real
      ? " Dev mode can use a mock GitHub account when credentials aren’t set."
      : "";

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden px-12 py-12 lg:flex">
        <PulseWordmark size="lg" />
        <div className="relative max-w-lg">
          <svg
            viewBox="0 0 420 90"
            className="pointer-events-none absolute -left-6 -top-16 w-[28rem] text-paper/[0.07]"
            aria-hidden="true"
          >
            <path
              d="M0 52h72l18-34 28 68 22-34h280"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="font-serif text-5xl italic leading-[1.08] tracking-tight text-paper">
            Every agent has a pulse.
          </p>
          <p className="mt-5 max-w-md text-base leading-relaxed text-mist">
            Tokens, cost, and efficiency land here live — by repo, in one place.
          </p>
        </div>
        <p className="text-xs uppercase tracking-[0.22em] text-mist">Agent observability</p>
      </aside>

      <div className="flex items-center justify-center px-5 py-12 sm:px-8">
        <div className="login-panel matte w-full max-w-[26rem] p-7 sm:p-8">
          <div className="flex items-center gap-3 lg:hidden">
            <PulseMark className="h-8 w-8" />
            <span className="font-serif text-2xl italic tracking-tight text-paper">Pulse</span>
          </div>

          <h1 className="mt-5 text-2xl font-semibold tracking-tight text-paper lg:mt-0">
            {tab === "signin" ? "Welcome back" : "Create your Pulse"}
          </h1>
          <p className="mt-1.5 text-sm text-mist">
            {tab === "signin"
              ? "Sign in to watch your agents."
              : "Set up an account to start monitoring."}
          </p>

          <div className="mt-6 grid grid-cols-2 gap-1 rounded-lg border border-line bg-black/30 p-1">
            {(
              [
                ["signin", "Sign in"],
                ["register", "Register"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => switchTab(id)}
                className={
                  tab === id
                    ? "rounded-md bg-white/[0.1] py-2 text-sm font-medium text-paper"
                    : "rounded-md py-2 text-sm text-mist hover:text-paper"
                }
              >
                {label}
              </button>
            ))}
          </div>

          <div className="mt-5 space-y-2.5">
            <button
              type="button"
              className="btn w-full justify-center py-2.5 font-medium"
              disabled={busy}
              onClick={startGitHub}
            >
              <GitHubIcon />
              Continue with GitHub
            </button>
          </div>

          <div className="my-5 flex items-center gap-3">
            <span className="h-px flex-1 bg-line" />
            <span className="text-[11px] uppercase tracking-[0.18em] text-mist">or email</span>
            <span className="h-px flex-1 bg-line" />
          </div>

          <form onSubmit={onSubmit} className="space-y-3">
            {tab === "register" && (
              <label className="block text-sm">
                <span className="text-mist">Name</span>
                <input
                  className="matte-sunk mt-1 w-full px-3 py-2.5 text-paper outline-none placeholder:text-mist/40"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                  placeholder="Your name"
                />
              </label>
            )}
            <label className="block text-sm">
              <span className="text-mist">Email</span>
              <input
                type="email"
                required
                className="matte-sunk mt-1 w-full px-3 py-2.5 text-paper outline-none placeholder:text-mist/40"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                placeholder="you@company.com"
              />
            </label>
            <label className="block text-sm">
              <span className="text-mist">Password</span>
              <input
                type="password"
                required
                minLength={tab === "register" ? 4 : 1}
                className="matte-sunk mt-1 w-full px-3 py-2.5 text-paper outline-none placeholder:text-mist/40"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={tab === "register" ? "new-password" : "current-password"}
                placeholder="••••••••"
              />
            </label>
            <button type="submit" className="btn-primary mt-1 w-full" disabled={busy}>
              {busy ? "Working…" : tab === "register" ? "Create account" : "Sign in to Pulse"}
            </button>
          </form>

          {mockHint ? <p className="mt-4 text-xs leading-relaxed text-mist">{mockHint}</p> : null}

          {message && (
            <p className="mt-4 rounded-lg border border-line bg-black/25 px-3 py-2 text-sm text-paper">
              {message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
