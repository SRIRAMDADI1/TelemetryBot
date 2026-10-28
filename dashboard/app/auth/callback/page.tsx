"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BrandScreen, PulseWordmark } from "@/components/Brand";
import { browserAuth, safeNextPath } from "@/lib/api";

function CallbackInner() {
  const router = useRouter();
  const search = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = search.get("token");
    const next = safeNextPath(search.get("next"), "/");
    if (!token) {
      setError("Missing session token");
      return;
    }
    (async () => {
      try {
        await browserAuth.persistSession(token);
        // Drop the token from the address bar / history as soon as the cookie is set.
        window.history.replaceState({}, "", "/auth/callback");
        router.replace(next);
        router.refresh();
      } catch {
        setError("Could not persist session");
      }
    })();
  }, [router, search]);

  if (error) {
    return (
      <BrandScreen
        title="Sign-in incomplete"
        actions={
          <a href="/login" className="btn-primary">
            Back to Pulse
          </a>
        }
      >
        <p>{error}</p>
      </BrandScreen>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6 py-20 text-center">
      <PulseWordmark />
      <p className="mt-6 text-mist">Finishing sign-in…</p>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <main className="px-6 py-20 text-center text-mist">
          <span className="font-serif italic text-paper">Pulse</span>
          <p className="mt-4">Finishing sign-in…</p>
        </main>
      }
    >
      <CallbackInner />
    </Suspense>
  );
}
