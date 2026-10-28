/** Shared client + server types and helpers (no next/headers). */

export const API_BASE =
  (typeof window === "undefined"
    ? process.env.COLLECTOR_URL || process.env.NEXT_PUBLIC_COLLECTOR_URL
    : process.env.NEXT_PUBLIC_COLLECTOR_URL || process.env.COLLECTOR_URL) ||
  "http://localhost:8100";

/** Bumped to invalidate leftover demo/dev sessions from earlier auth mocks. */
export const SESSION_COOKIE = "tb_auth";

export type User = {
  id: string;
  email: string;
  name: string;
  avatar_url?: string | null;
  is_demo?: boolean;
  github_connected?: boolean;
  github_login?: string | null;
  has_password?: boolean;
};

export type Project = {
  id: string;
  slug: string;
  name: string;
  repo_url?: string | null;
  local_path?: string | null;
  is_system?: boolean;
  owner_id?: string | null;
  github_full_name?: string | null;
  ingest_api_key_masked?: string;
  ingest_api_key?: string | null;
  coverage?: {
    files_scanned?: number;
    instrumented?: string[];
    missing?: string[];
    notes?: string | null;
    scanned_at?: string;
  } | null;
};

export type RunSummary = {
  run_id: string;
  project_id: string;
  external_id?: string | null;
  status: string;
  channel: string;
  outcome?: string | null;
  experiment?: string | null;
  started_at: string;
  ended_at?: string | null;
  total_tokens: number;
  total_cost_usd: number;
  span_count: number;
  duration_ms: number;
};

export type AuthProviders = {
  email: boolean;
  magic_link: boolean;
  github: boolean;
  github_real: boolean;
  dev_mode: boolean;
  demo_email: string;
};

export type EfficiencyMetrics = {
  project_id: string;
  run_count: number;
  successful_runs: number;
  success_rate: number;
  total_cost_usd: number;
  cost_per_outcome: number;
  waste_ratio: number;
  prompt_tokens: number;
  completion_tokens: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  tool_call_count: number;
  tool_error_count: number;
  tool_error_rate: number;
  model_mix: { model: string; cost_usd: number; tokens?: number }[];
  leaderboard: AgentStat[];
  today_run_count: number;
  today_cost_usd: number;
  avg_tokens_per_run: number;
};

export type AgentStat = {
  agent_name: string;
  run_count: number;
  span_count: number;
  error_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  cost_per_run: number;
  avg_latency_ms: number;
  llm_calls: number;
  error_rate: number;
  tool_calls: number;
  tool_errors: number;
  tool_error_rate: number;
  efficiency?: number;
};

export type GitHubRepo = {
  id: number;
  full_name: string;
  name: string;
  private: boolean;
  html_url: string;
  description?: string | null;
  default_branch?: string;
};

export class AuthError extends Error {
  constructor() {
    super("Authentication required");
    this.name = "AuthError";
  }
}

/** Same-origin relative path only (blocks open redirects). */
export function safeNextPath(raw: string | null | undefined, fallback = "/"): string {
  if (!raw) return fallback;
  if (!raw.startsWith("/") || raw.startsWith("//") || raw.includes("://")) return fallback;
  return raw;
}

export function formatApiDetail(detail: unknown, fallback = "Request failed"): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }
  return fallback;
}

export function money(n: number) {
  if (!n) return "$0.00";
  if (n < 0.01) return `$${n.toFixed(6)}`;
  return `$${n.toFixed(4)}`;
}

export function pct(value: unknown, digits = 1) {
  const n = typeof value === "number" && Number.isFinite(value) ? value : 0;
  return `${(n * 100).toFixed(digits)}%`;
}

export function ms(value: unknown) {
  const n = typeof value === "number" && Number.isFinite(value) ? value : 0;
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}s`;
  return `${Math.round(n)}ms`;
}

export async function fetchProviders(): Promise<AuthProviders> {
  const res = await fetch(`${API_BASE}/v1/auth/providers`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load auth providers");
  return res.json();
}

/** Browser-side auth helpers (persist cookie via Next route handlers). */
export const browserAuth = {
  collectorUrl: API_BASE,

  async persistSession(token: string) {
    const res = await fetch("/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(typeof data.error === "string" ? data.error : "Could not save session");
    }
  },

  async clearSession() {
    await fetch("/api/session", { method: "DELETE", cache: "no-store", credentials: "same-origin" });
  },
};
