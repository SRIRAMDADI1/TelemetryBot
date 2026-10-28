"use client";

import { useEffect, useRef, useState } from "react";
import { browserAuth, fetchProviders, type User } from "@/lib/api";

const NOT_CONFIGURED =
  "GitHub isn’t configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET on the server.";

export function UserMenu({ user }: { user: User }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function logout() {
    setBusy(true);
    await browserAuth.clearSession();
    window.location.replace("/login");
  }

  async function connectGitHub() {
    setMessage(null);
    if (user.is_demo) {
      window.location.href = "/api/auth/github-connect?next=/connect";
      return;
    }
    try {
      const providers = await fetchProviders();
      if (!providers.github_real) {
        setMessage(NOT_CONFIGURED);
        return;
      }
    } catch {
      setMessage(NOT_CONFIGURED);
      return;
    }
    window.location.href = "/api/auth/github-connect?next=/connect";
  }

  return (
    <div className="relative" ref={rootRef}>
      <button type="button" className="btn pl-1.5" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/[0.1] text-[11px] font-medium text-paper">
          {(user.name || user.email).slice(0, 1).toUpperCase()}
        </span>
        <span className="max-w-[10rem] truncate">{user.name || user.email}</span>
      </button>
      {open && (
        <div className="matte absolute right-0 z-20 mt-2 w-64 p-2 shadow-lift">
          <div className="px-2 py-1.5 text-xs text-mist">
            <div className="font-mono text-paper">{user.email}</div>
            {user.is_demo && <div className="mt-1">Demo account</div>}
            {user.github_connected ? (
              <div className="mt-1">GitHub · {user.github_login}</div>
            ) : (
              <div className="mt-1">GitHub not connected</div>
            )}
          </div>
          <div className="rule my-1" />
          {!user.github_connected && (
            <button
              type="button"
              className="w-full rounded-md px-2 py-2 text-left text-sm text-paper hover:bg-white/[0.06]"
              onClick={connectGitHub}
            >
              Connect GitHub
            </button>
          )}
          <a
            href="/connect"
            className="block rounded-md px-2 py-2 text-sm text-paper hover:bg-white/[0.06] hover:text-paper"
          >
            Connect repos
          </a>
          <button
            type="button"
            className="w-full rounded-md px-2 py-2 text-left text-sm text-paper hover:bg-white/[0.06]"
            disabled={busy}
            onClick={logout}
          >
            Sign out
          </button>
          {message && <p className="mt-1 px-2 py-1.5 text-xs leading-relaxed text-paper">{message}</p>}
        </div>
      )}
    </div>
  );
}
