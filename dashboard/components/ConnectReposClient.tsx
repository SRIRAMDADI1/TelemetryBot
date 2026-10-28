"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ConnectGuide } from "@/components/ConnectGuide";
import type { GitHubRepo, Project, User } from "@/lib/api";

const NOT_CONFIGURED =
  "GitHub isn’t configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET on the server.";

export function ConnectReposClient({
  user,
  projects,
  initialRepos,
  reposError,
  githubReal = false,
}: {
  user: User;
  projects: Project[];
  initialRepos: GitHubRepo[];
  reposError?: string | null;
  githubReal?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(reposError || null);
  const [created, setCreated] = useState<{ slug: string; ingestKey: string | null } | null>(null);
  const [copied, setCopied] = useState(false);
  const connected = useMemo(
    () => new Set(projects.map((p) => p.github_full_name).filter(Boolean) as string[]),
    [projects]
  );

  const canMockConnect = Boolean(user.is_demo) && !githubReal;

  function connectGitHub() {
    if (!githubReal && !user.is_demo) {
      setMessage(NOT_CONFIGURED);
      return;
    }
    window.location.href = "/api/auth/github-connect?next=/connect";
  }

  async function importRepo(repo: GitHubRepo) {
    setBusy(repo.full_name);
    setMessage(null);
    setCreated(null);
    setCopied(false);
    try {
      const res = await fetch("/api/projects/from-github", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: repo.full_name,
          html_url: repo.html_url,
          name: repo.name.replace(/-/g, " ").replace(/_/g, " "),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || data.detail || "Import failed");
      const ingestKey = typeof data.ingest_api_key === "string" ? data.ingest_api_key : null;
      if (ingestKey) {
        try {
          sessionStorage.setItem(`tb_ingest_key:${data.slug}`, ingestKey);
        } catch {
          /* private mode */
        }
      }
      setCreated({ slug: data.slug, ingestKey });
      setMessage(`Connected ${data.slug}. Copy the ingest key below — it won’t be shown again.`);
      router.prefetch(`/p/${data.slug}`);
      router.refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(null);
    }
  }

  async function copyKey() {
    if (!created?.ingestKey) return;
    try {
      await navigator.clipboard.writeText(created.ingestKey);
      setCopied(true);
    } catch {
      setMessage("Could not copy — select the key and copy manually.");
    }
  }

  return (
    <div className="mt-6 space-y-6">
      <div className="matte p-5">
        <h2 className="text-lg font-semibold tracking-tight">GitHub</h2>
        {user.github_connected ? (
          <p className="mt-2 text-sm text-mist">
            Connected as <span className="font-mono text-paper">{user.github_login}</span>. Connect a
            repo to open a tab, then install the Pulse SDK in that repo so traces can reach the
            collector.
          </p>
        ) : (
          <>
            <p className="mt-2 text-sm text-mist">
              {canMockConnect
                ? "Demo account can attach sample GitHub repos without a real OAuth app."
                : githubReal
                  ? "You signed in without GitHub. Connect it to import repositories as project tabs."
                  : "Connect GitHub after configuring OAuth on the server, or sign in with the demo account to try sample repos."}
            </p>
            <button type="button" className="btn mt-4" onClick={connectGitHub}>
              Connect GitHub
            </button>
          </>
        )}
      </div>

      {user.github_connected && (
        <section>
          <h2 className="mb-3 text-lg font-semibold tracking-tight">Your repositories</h2>
          {initialRepos.length === 0 ? (
            <p className="text-sm text-mist">No repositories returned.</p>
          ) : (
            <ul className="space-y-2">
              {initialRepos.map((repo) => {
                const already = connected.has(repo.full_name);
                return (
                  <li key={repo.id} className="matte flex flex-wrap items-center justify-between gap-3 p-4">
                    <div>
                      <div className="font-mono text-sm text-paper">{repo.full_name}</div>
                      <div className="mt-1 text-xs text-mist">
                        {repo.private ? "Private" : "Public"}
                        {repo.description ? ` · ${repo.description}` : ""}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn"
                      disabled={already || busy === repo.full_name}
                      onClick={() => importRepo(repo)}
                    >
                      {already ? "Connected" : busy === repo.full_name ? "Connecting…" : "Connect"}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}

      {created?.ingestKey && (
        <div className="matte border-mist/40 p-5">
          <h2 className="text-lg font-semibold tracking-tight text-paper">Ingest API key</h2>
          <p className="mt-2 text-sm text-mist">
            This is the <span className="font-mono text-paper">api_key</span> in{" "}
            <span className="font-mono text-paper">telemetry.yaml</span> below. Settings only shows a
            masked value later.
          </p>
          <code className="matte-sunk mt-3 block overflow-x-auto px-3 py-2.5 font-mono text-sm text-paper">
            {created.ingestKey}
          </code>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="btn" onClick={copyKey}>
              {copied ? "Copied" : "Copy key"}
            </button>
            <button type="button" className="btn" onClick={() => router.push(`/p/${created.slug}`)}>
              Open {created.slug}
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => router.push(`/p/${created.slug}/settings`)}
            >
              Settings
            </button>
          </div>
        </div>
      )}

      {created ? <ConnectGuide slug={created.slug} ingestKey={created.ingestKey} /> : null}

      {message && (
        <p className="rounded-lg border border-line bg-black/25 px-3 py-2 text-sm text-paper">{message}</p>
      )}

      <p className="text-xs text-mist">
        Prefer a local folder instead of GitHub? Run <span className="font-mono text-paper">telemetry login</span>{" "}
        then <span className="font-mono text-paper">telemetry connect ./your-repo</span> — you still need the
        SDK in that repo before traces appear.
      </p>
    </div>
  );
}

/** Client widget that reveals a one-time ingest key saved during Connect. */
export function PendingIngestKey({ slug }: { slug: string }) {
  const [key, setKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const cleared = useRef(false);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(`tb_ingest_key:${slug}`);
      if (stored) setKey(stored);
    } catch {
      /* ignore */
    }
  }, [slug]);

  async function copy() {
    if (!key) return;
    try {
      await navigator.clipboard.writeText(key);
      setCopied(true);
    } catch {
      /* ignore */
    }
  }

  function dismiss() {
    try {
      sessionStorage.removeItem(`tb_ingest_key:${slug}`);
    } catch {
      /* ignore */
    }
    cleared.current = true;
    setKey(null);
  }

  if (!key || cleared.current) return null;

  return (
    <div className="matte mt-6 border-mist/40 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium tracking-wide text-mist">One-time ingest API key</h2>
          <p className="mt-1 text-xs text-mist">
            Goes in <span className="font-mono text-paper">telemetry.yaml</span> as{" "}
            <span className="font-mono text-paper">api_key</span>.
          </p>
          <code className="mt-2 block font-mono text-sm text-paper">{key}</code>
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn" onClick={copy}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button type="button" className="btn" onClick={dismiss}>
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
