"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

export function RefreshButton() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  // Set after mount so the server-rendered markup stays deterministic.
  useEffect(() => {
    setUpdatedAt(new Date().toLocaleTimeString());
  }, []);

  function refresh() {
    startTransition(() => {
      router.refresh();
      setUpdatedAt(new Date().toLocaleTimeString());
    });
  }

  return (
    <div className="flex items-center gap-3">
      <span className="hidden font-mono text-xs text-mist sm:inline" suppressHydrationWarning>
        {isPending ? "syncing…" : updatedAt ? `updated ${updatedAt}` : ""}
      </span>
      <button type="button" onClick={refresh} disabled={isPending} className="btn" aria-label="Refresh data">
        <svg
          viewBox="0 0 16 16"
          aria-hidden="true"
          className={`h-3.5 w-3.5 ${isPending ? "spinning" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        >
          <path d="M13.5 8a5.5 5.5 0 1 1-1.61-3.89" />
          <path d="M13.5 1.8v3.2h-3.2" />
        </svg>
        Refresh
      </button>
    </div>
  );
}
