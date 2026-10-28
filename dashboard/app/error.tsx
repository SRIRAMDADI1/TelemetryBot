"use client";

import { useEffect } from "react";
import Link from "next/link";
import { BrandScreen } from "@/components/Brand";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const auth = error.message === "Authentication required";
  const title = auth ? "Session expired" : "Could not load this view";
  const body = auth
    ? "Sign in again to continue with Pulse."
    : "The collector may be down or still starting up. Retry, or check that the API is reachable.";

  return (
    <BrandScreen
      title={title}
      actions={
        <>
          {auth ? (
            <Link href="/login" className="btn-primary">
              Sign in
            </Link>
          ) : (
            <button type="button" onClick={reset} className="btn">
              Retry
            </button>
          )}
          <Link href="/" className="text-sm text-mist hover:text-paper">
            Back to Pulse
          </Link>
        </>
      }
    >
      <p>{body}</p>
      {!auth && (
        <pre className="matte-sunk mt-6 overflow-x-auto p-4 font-mono text-xs text-mist">
          {error.message || "Unknown error"}
        </pre>
      )}
    </BrandScreen>
  );
}
