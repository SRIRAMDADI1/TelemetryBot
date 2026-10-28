"use client";

import Link from "next/link";
import { AgentCostChart, ModelMixChart } from "@/components/Charts";
import { ConnectGuide } from "@/components/ConnectGuide";
import { PendingIngestKey } from "@/components/ConnectReposClient";
import { DisconnectProjectButton } from "@/components/DisconnectProjectButton";
import { DataTable, EmptyState, Panel, StatCard } from "@/components/Shell";
import { useProjectNav } from "@/components/ProjectShell";
import {
  API_BASE,
  money,
  ms,
  pct,
  type AgentStat,
  type EfficiencyMetrics,
  type Project,
  type RunSummary,
} from "@/lib/api";

export type ProjectBundle = {
  project: Project;
  runs: RunSummary[];
  agents: AgentStat[];
  efficiency: EfficiencyMetrics;
};

/** Every section’s data is already in memory; switching tabs only changes which panel renders. */
export function ProjectWorkspace({ project, runs, agents, efficiency }: ProjectBundle) {
  const { section } = useProjectNav();

  if (section === "runs") return <RunsPanel slug={project.slug} runs={runs} />;
  if (section === "agents") return <AgentsPanel agents={agents} />;
  if (section === "efficiency") return <EfficiencyPanel efficiency={efficiency} />;
  if (section === "settings") return <SettingsPanel project={project} />;
  return <OverviewPanel project={project} runs={runs} efficiency={efficiency} />;
}

function OverviewPanel({
  project,
  runs,
  efficiency,
}: {
  project: Project;
  runs: RunSummary[];
  efficiency: EfficiencyMetrics;
}) {
  const { setSection } = useProjectNav();

  if (runs.length === 0) {
    return (
      <div className="mt-8 space-y-4">
        {project.is_system ? (
          <p className="text-sm leading-relaxed text-mist">
            This demo tab is already instrumented. Run the matching workload (Sales IVR chat/CLI, or{" "}
            <span className="font-mono text-paper">python telemetry_smoke.py --demo-seed</span> for ADO).
          </p>
        ) : null}
        <ConnectGuide
          slug={project.slug}
          collectorUrl={API_BASE}
          repoName={project.github_full_name || project.slug}
        />
      </div>
    );
  }

  return (
    <>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Success rate"
          value={pct(efficiency.success_rate)}
          hint={`${efficiency.successful_runs ?? 0}/${efficiency.run_count ?? 0} runs`}
        />
        <StatCard label="Today's cost" value={money(efficiency.today_cost_usd || 0)} />
        <StatCard label="P95 latency" value={ms(efficiency.p95_latency_ms)} />
        <StatCard label="Cost / outcome" value={money(efficiency.cost_per_outcome || 0)} />
      </div>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Recent runs</h2>
          <button
            type="button"
            className="text-sm text-mist hover:text-paper"
            onClick={() => setSection("runs")}
          >
            View all
          </button>
        </div>
        <DataTable headers={["External ID", "Channel", "Status", "Cost", "Tokens", "Spans"]}>
          {runs.slice(0, 8).map((r) => (
            <tr key={r.run_id} className="border-t border-line/60 transition-colors hover:bg-white/[0.04]">
              <td className="px-3 py-2 font-mono text-xs">
                <Link href={`/p/${project.slug}/runs/${r.run_id}`} className="text-paper hover:text-accent2">
                  {r.external_id || r.run_id}
                </Link>
              </td>
              <td className="px-3 py-2">{r.channel}</td>
              <td className="px-3 py-2">{r.outcome || r.status}</td>
              <td className="px-3 py-2 font-mono">{money(r.total_cost_usd)}</td>
              <td className="px-3 py-2 font-mono">{r.total_tokens}</td>
              <td className="px-3 py-2 font-mono">{r.span_count}</td>
            </tr>
          ))}
        </DataTable>
      </section>
    </>
  );
}

function RunsPanel({ slug, runs }: { slug: string; runs: RunSummary[] }) {
  if (runs.length === 0) {
    return (
      <EmptyState
        title="No runs"
        body="No traces yet. Overview has the steps to send runs from this repo."
      />
    );
  }

  return (
    <div className="mt-6">
      <DataTable
        headers={["External ID", "Channel", "Experiment", "Status", "Cost", "Duration", "Tokens", "Spans"]}
      >
        {runs.map((r) => (
          <tr key={r.run_id} className="border-t border-line/60 transition-colors hover:bg-white/[0.04]">
            <td className="px-3 py-2 font-mono text-xs">
              <Link href={`/p/${slug}/runs/${r.run_id}`} className="text-paper hover:text-accent2">
                {r.external_id || r.run_id}
              </Link>
            </td>
            <td className="px-3 py-2">{r.channel}</td>
            <td className="px-3 py-2 font-mono text-xs">{r.experiment || "—"}</td>
            <td className="px-3 py-2">{r.outcome || r.status}</td>
            <td className="px-3 py-2 font-mono">{money(r.total_cost_usd)}</td>
            <td className="px-3 py-2 font-mono">{r.duration_ms}ms</td>
            <td className="px-3 py-2 font-mono">{r.total_tokens}</td>
            <td className="px-3 py-2 font-mono">{r.span_count}</td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}

function AgentsPanel({ agents }: { agents: AgentStat[] }) {
  if (agents.length === 0) {
    return (
      <EmptyState
        title="No agent stats"
        body="No agent stats yet. Overview has the steps to send runs from this repo."
      />
    );
  }

  return (
    <>
      <Panel title="Cost by agent" className="mt-6">
        <AgentCostChart data={agents} />
      </Panel>
      <div className="mt-6">
        <DataTable headers={["Agent", "Cost", "Prompt / Completion", "Avg latency", "Tools", "Errors", "Runs"]}>
          {agents.map((a) => (
            <tr key={a.agent_name} className="border-t border-line/60 transition-colors hover:bg-white/[0.04]">
              <td className="px-3 py-2 font-mono text-xs">{a.agent_name}</td>
              <td className="px-3 py-2 font-mono">{money(a.cost_usd)}</td>
              <td className="px-3 py-2 font-mono text-xs">
                {a.prompt_tokens}/{a.completion_tokens}
              </td>
              <td className="px-3 py-2 font-mono">{a.avg_latency_ms}ms</td>
              <td className="px-3 py-2 font-mono text-xs">
                {a.tool_calls > 0 ? (
                  <span>
                    {a.tool_calls - a.tool_errors}/{a.tool_errors}
                    <span className="text-mist"> ok/err</span>
                  </span>
                ) : (
                  <span className="text-mist">—</span>
                )}
              </td>
              <td className="px-3 py-2 font-mono">
                {a.error_count > 0 ? (
                  <span className="rounded border border-line bg-white/10 px-1.5 py-0.5 text-paper">
                    {a.error_count}
                  </span>
                ) : (
                  <span className="text-mist">0</span>
                )}
              </td>
              <td className="px-3 py-2 font-mono">{a.run_count}</td>
            </tr>
          ))}
        </DataTable>
      </div>
    </>
  );
}

function EfficiencyPanel({ efficiency: eff }: { efficiency: EfficiencyMetrics }) {
  const leaderboard = eff.leaderboard || [];

  if (!eff.run_count) {
    return (
      <EmptyState
        title="No efficiency data"
        body="Need successful runs to compute cost-per-outcome. Overview has the steps to send runs from this repo."
      />
    );
  }

  return (
    <>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Cost / outcome" value={money(eff.cost_per_outcome)} />
        <StatCard label="Waste ratio" value={pct(eff.waste_ratio)} hint="Tokens on error spans" />
        <StatCard
          label="Tool errors"
          value={pct(eff.tool_error_rate)}
          hint={`${eff.tool_error_count ?? 0}/${eff.tool_call_count ?? 0} calls`}
        />
        <StatCard label="P95 latency" value={ms(eff.p95_latency_ms)} hint={`P50 ${ms(eff.p50_latency_ms)}`} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Panel title="Model mix (cost)">
          <ModelMixChart data={eff.model_mix || []} />
        </Panel>
        <Panel title="Agent leaderboard (cost)">
          <AgentCostChart data={leaderboard} />
        </Panel>
      </div>

      <div className="mt-6">
        <DataTable headers={["Agent", "Cost / run", "Error rate", "Cost"]}>
          {leaderboard.map((a) => (
            <tr key={a.agent_name} className="border-t border-line/60 transition-colors hover:bg-white/[0.04]">
              <td className="px-3 py-2 font-mono text-xs">{a.agent_name}</td>
              <td className="px-3 py-2 font-mono">{money(a.cost_per_run ?? a.efficiency ?? 0)}</td>
              <td className="px-3 py-2 font-mono">{pct(a.error_rate)}</td>
              <td className="px-3 py-2 font-mono">{money(a.cost_usd)}</td>
            </tr>
          ))}
        </DataTable>
      </div>
    </>
  );
}

function Field({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-[0.18em] text-mist">{label}</div>
      <div className={`mt-1 text-paper ${mono ? "font-mono text-sm" : "text-sm"}`}>{value}</div>
    </div>
  );
}

function SettingsPanel({ project }: { project: Project }) {
  const coverage = project.coverage;

  return (
    <>
      <PendingIngestKey slug={project.slug} />

      <div className="matte mt-6 grid gap-5 p-5 sm:grid-cols-2">
        <Field label="Project ID" value={project.id} />
        <Field label="Slug / tab" value={project.slug} />
        <Field label="Local path" value={project.local_path || "—"} />
        <Field label="GitHub" value={project.github_full_name || project.repo_url || "—"} />
        <Field label="Ingest API key" value={project.ingest_api_key_masked || "••••"} />
        <Field label="System demo project" value={project.is_system ? "Yes" : "No"} mono={false} />
      </div>

      <div className="mt-8">
        <ConnectGuide slug={project.slug} repoName={project.github_full_name || project.slug} />
      </div>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Instrumentation coverage</h2>
        {!coverage ? (
          <EmptyState
            title="No coverage scan yet"
            body={`After the SDK is in the repo, run: telemetry scan ${project.local_path || "./" + project.slug} --project ${project.slug}`}
          />
        ) : (
          <Panel>
            <p className="text-sm text-mist">
              Scanned {coverage.files_scanned ?? 0} files
              {coverage.scanned_at ? ` · ${coverage.scanned_at}` : ""}
            </p>
            <div className="rule my-4" />
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-paper">Instrumented</h3>
                <ul className="mt-2 space-y-1 font-mono text-xs text-mist">
                  {(coverage.instrumented || []).map((f) => (
                    <li key={f}>
                      <span className="text-paper">✓</span> {f}
                    </li>
                  ))}
                  {(coverage.instrumented || []).length === 0 && <li>None detected</li>}
                </ul>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-mist">Possibly missing</h3>
                <ul className="mt-2 space-y-1 font-mono text-xs text-mist">
                  {(coverage.missing || []).map((f) => (
                    <li key={f}>? {f}</li>
                  ))}
                  {(coverage.missing || []).length === 0 && <li>None</li>}
                </ul>
              </div>
            </div>
            {coverage.notes && <p className="mt-4 text-sm text-mist">{coverage.notes}</p>}
          </Panel>
        )}
      </section>

      <DisconnectProjectButton
        slug={project.slug}
        name={project.name}
        isSystem={Boolean(project.is_system)}
      />
    </>
  );
}
