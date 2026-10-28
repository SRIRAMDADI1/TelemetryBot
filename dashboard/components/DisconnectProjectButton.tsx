"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function DisconnectProjectButton({
  slug,
  name,
  isSystem = false,
}: {
  slug: string;
  name: string;
  isSystem?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  if (isSystem) {
    return (
      <div className="matte mt-8 p-5">
        <h2 className="text-lg font-semibold tracking-tight text-paper">Disconnect project</h2>
        <p className="mt-2 text-sm text-mist">
          <span className="text-paper">{name}</span> is a system demo tab and can’t be disconnected.
        </p>
      </div>
    );
  }

  async function disconnect() {
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(slug)}`, { method: "DELETE" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof data.error === "string" ? data.error : "Disconnect failed");
      }
      router.replace("/");
      router.refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Disconnect failed");
      setBusy(false);
      setConfirming(false);
    }
  }

  return (
    <div className="matte mt-8 p-5">
      <h2 className="text-lg font-semibold tracking-tight text-paper">Disconnect project</h2>
      <p className="mt-2 text-sm text-mist">
        Remove the <span className="font-mono text-paper">{slug}</span> monitoring tab and delete its
        stored runs. You can reconnect the repo later from Connect.
      </p>

      {!confirming ? (
        <button type="button" className="btn mt-4" onClick={() => setConfirming(true)} disabled={busy}>
          Disconnect project
        </button>
      ) : (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button type="button" className="btn" onClick={disconnect} disabled={busy}>
            {busy ? "Disconnecting…" : "Confirm disconnect"}
          </button>
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() => {
              setConfirming(false);
              setMessage(null);
            }}
          >
            Cancel
          </button>
        </div>
      )}

      {message && (
        <p className="mt-3 rounded-lg border border-line bg-black/25 px-3 py-2 text-sm text-paper">
          {message}
        </p>
      )}
    </div>
  );
}
