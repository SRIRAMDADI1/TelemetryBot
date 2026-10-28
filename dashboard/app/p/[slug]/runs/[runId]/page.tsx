import Link from "next/link";
import { DataTable, Panel, StatCard } from "@/components/Shell";
import { money } from "@/lib/api";
import { withAuth } from "@/lib/auth";
import { fetchRun } from "@/lib/server-api";

export default async function RunDetailPage({
  params,
}: {
  params: { slug: string; runId: string };
}) {
  const { detail } = await withAuth(async () => {
    const detail = await fetchRun(params.runId);
    return { detail };
  });
  const run = detail.run;
  const spans: any[] = detail.spans || [];
  const llmCalls: any[] = detail.llm_calls || [];
  const toolCalls: any[] = detail.tool_calls || [];
  const handoffs: any[] = detail.handoffs || [];

  const agentBySpan = new Map<string, string>();
  for (const s of spans) agentBySpan.set(s.span_id, s.agent_name);

  // Spans replayed from fixtures record ~0ms wall-clock, so fall back to the
  // latency their LLM calls actually reported.
  const callLatencyBySpan = new Map<string, number>();
  for (const c of llmCalls) {
    if (!c.span_id) continue;
    callLatencyBySpan.set(c.span_id, (callLatencyBySpan.get(c.span_id) || 0) + (c.latency_ms || 0));
  }
  const bars = spans.map((s) => {
    const measured = s.latency_ms || 0;
    const derived = callLatencyBySpan.get(s.span_id) || 0;
    return { span: s, ms: measured || derived, estimated: measured === 0 && derived > 0 };
  });
  const maxLatency = bars.reduce((max, b) => Math.max(max, b.ms), 1);
  const hasEstimates = bars.some((b) => b.estimated);

  return (
    <>
      <p className="mt-4 font-mono text-sm text-mist">{run.external_id || run.run_id}</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Cost" value={money(run.total_cost_usd)} />
        <StatCard label="Tokens" value={String(run.total_tokens)} />
        <StatCard label="Duration" value={`${run.duration_ms}ms`} />
        <StatCard label="Channel" value={run.channel} hint={run.outcome || run.status} />
      </div>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Waterfall</h2>
        <Panel>
          <div className="space-y-2">
            {bars.map(({ span, ms, estimated }) => {
              const isError = span.status === "error";
              return (
                <div
                  key={span.span_id}
                  className="grid grid-cols-[minmax(120px,180px)_1fr_84px] items-center gap-3 text-sm"
                >
                  <div className="truncate font-mono text-xs text-mist" title={span.agent_name}>
                    {span.agent_name}
                  </div>
                  <div className="matte-sunk h-3 overflow-hidden rounded">
                    <div
                      className={`h-full rounded ${isError ? "hatch" : "bar-fill"}`}
                      style={{ width: `${Math.max(2, (ms / maxLatency) * 100)}%` }}
                      title={isError ? `error · ${ms}ms` : `${span.status} · ${ms}ms`}
                    />
                  </div>
                  <div className="text-right font-mono text-xs text-mist">
                    {estimated ? "~" : ""}
                    {ms}ms
                  </div>
                </div>
              );
            })}
            {bars.length === 0 && <p className="text-sm text-mist">No spans recorded.</p>}
          </div>
          {hasEstimates && (
            <p className="mt-4 text-xs text-mist">
              ~ estimated from LLM call latency; these spans reported no wall-clock duration.
            </p>
          )}
        </Panel>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">LLM calls</h2>
        <DataTable headers={["Agent", "Model", "Tokens", "Cost", "Latency"]}>
          {llmCalls.map((c) => (
            <tr key={c.call_id} className="border-t border-line/60 transition-colors hover:bg-white/[0.04]">
              <td className="px-3 py-2 font-mono text-xs">{c.agent_name}</td>
              <td className="px-3 py-2">{c.model}</td>
              <td className="px-3 py-2 font-mono">
                {c.total_tokens} ({c.prompt_tokens}/{c.completion_tokens})
              </td>
              <td className="px-3 py-2 font-mono">{money(c.cost_usd)}</td>
              <td className="px-3 py-2 font-mono">{c.latency_ms}ms</td>
            </tr>
          ))}
        </DataTable>
        {llmCalls.length === 0 && <p className="mt-3 text-sm text-mist">No LLM calls recorded.</p>}
      </section>

      {toolCalls.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold tracking-tight">Tool calls</h2>
          <DataTable headers={["Tool", "Agent", "Latency", "Result"]}>
            {toolCalls.map((t) => (
              <tr key={t.tool_call_id} className="border-t border-line/60 transition-colors hover:bg-white/[0.04]">
                <td className="px-3 py-2 font-mono text-xs">{t.tool_name}</td>
                <td className="px-3 py-2 font-mono text-xs">{t.agent_name}</td>
                <td className="px-3 py-2 font-mono">{t.latency_ms}ms</td>
                <td className="px-3 py-2 font-mono text-xs">
                  {t.success ? (
                    <span className="text-mist">ok</span>
                  ) : (
                    <span className="rounded border border-line bg-white/10 px-1.5 py-0.5 text-paper">
                      error
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </DataTable>
        </section>
      )}

      {handoffs.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold tracking-tight">Handoffs</h2>
          <DataTable headers={["From", "To", "Reason"]}>
            {handoffs.map((h) => (
              <tr key={h.handoff_id} className="border-t border-line/60 transition-colors hover:bg-white/[0.04]">
                <td className="px-3 py-2 font-mono text-xs">
                  {agentBySpan.get(h.from_span_id) || h.from_span_id}
                </td>
                <td className="px-3 py-2 font-mono text-xs">
                  {agentBySpan.get(h.to_span_id) || h.to_span_id}
                </td>
                <td className="px-3 py-2 text-sm text-mist">{h.reason || "—"}</td>
              </tr>
            ))}
          </DataTable>
        </section>
      )}

      <p className="mt-6 text-sm">
        <Link href={`/p/${params.slug}/runs`}>← Back to runs</Link>
      </p>
    </>
  );
}
