/** Server-only collector fetches (uses next/headers cookies). Do not import from client components. */

import { cache } from "react";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import {
  API_BASE,
  AuthError,
  SESSION_COOKIE,
  type AgentStat,
  type EfficiencyMetrics,
  type GitHubRepo,
  type Project,
  type RunSummary,
  type User,
} from "@/lib/api";

export const getSessionToken = cache(async (): Promise<string | null> => {
  try {
    const jar = await cookies();
    return jar.get(SESSION_COOKIE)?.value || null;
  } catch {
    return null;
  }
});

function authHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function apiFetch(path: string, init: RequestInit = {}, token?: string | null) {
  const session = token === undefined ? await getSessionToken() : token;
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...authHeaders(session),
      ...(init.headers || {}),
    },
    cache: "no-store",
  });
}

export const fetchMe = cache(async (): Promise<User | null> => {
  const res = await apiFetch("/v1/auth/me");
  if (res.status === 401) return null;
  if (!res.ok) throw new Error("Failed to load session");
  const data = await res.json();
  return data.user as User;
});

export const fetchProjects = cache(async (): Promise<Project[]> => {
  const res = await apiFetch("/v1/projects");
  if (res.status === 401) throw new AuthError();
  if (!res.ok) throw new Error(`Failed to load projects (${res.status})`);
  return res.json();
});

export const fetchProject = cache(async (slug: string): Promise<Project> => {
  const res = await apiFetch(`/v1/projects/${slug}`);
  if (res.status === 401) throw new AuthError();
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`Failed to load project (${res.status})`);
  return res.json();
});

export const fetchRuns = cache(async (projectId: string): Promise<RunSummary[]> => {
  const res = await apiFetch(`/v1/runs?project_id=${encodeURIComponent(projectId)}&limit=100`);
  if (res.status === 401) throw new AuthError();
  if (!res.ok) throw new Error("Failed to load runs");
  return res.json();
});

export async function fetchRun(runId: string) {
  const res = await apiFetch(`/v1/runs/${runId}`);
  if (res.status === 401) throw new AuthError();
  if (!res.ok) throw new Error("Run not found");
  return res.json();
}

export const fetchAgentStats = cache(async (
  projectId: string,
): Promise<{ project_id: string; agents: AgentStat[] }> => {
  const res = await apiFetch(`/v1/agents/stats?project_id=${encodeURIComponent(projectId)}`);
  if (res.status === 401) throw new AuthError();
  if (!res.ok) throw new Error("Failed to load agent stats");
  return res.json();
});

export const fetchEfficiency = cache(async (projectId: string): Promise<EfficiencyMetrics> => {
  const res = await apiFetch(`/v1/metrics/efficiency?project_id=${encodeURIComponent(projectId)}`);
  if (res.status === 401) throw new AuthError();
  if (!res.ok) throw new Error("Failed to load efficiency metrics");
  return res.json();
});

/** All section data for a project — fetched once when the workspace mounts. */
export const fetchProjectBundle = cache(async (slug: string) => {
  const project = await fetchProject(slug);
  const [runs, agentStats, efficiency] = await Promise.all([
    fetchRuns(project.id),
    fetchAgentStats(project.id),
    fetchEfficiency(project.id),
  ]);
  return {
    project,
    runs,
    agents: agentStats.agents || [],
    efficiency,
  };
});

export async function fetchGitHubRepos(): Promise<{ repos: GitHubRepo[]; source: string }> {
  const res = await apiFetch("/v1/github/repos");
  if (res.status === 401) throw new AuthError();
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || "Failed to load GitHub repos");
  }
  return res.json();
}

export async function fetchGitHubStatus(): Promise<{
  connected: boolean;
  login?: string | null;
  dev_mode?: boolean;
}> {
  const res = await apiFetch("/v1/github/status");
  if (res.status === 401) throw new AuthError();
  if (!res.ok) throw new Error("Failed to load GitHub status");
  return res.json();
}
