"use client";

import { useEffect, useState, type ReactNode } from "react";
import { API_BASE } from "@/lib/api";

function CodeBlock({ code, label }: { code: string; label: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-line">
      <div className="flex items-center justify-between border-b border-line bg-black/25 px-3 py-1.5">
        <span className="text-[11px] uppercase tracking-[0.16em] text-mist">{label}</span>
        <button type="button" className="text-xs text-mist hover:text-paper" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto bg-black/30 px-3 py-3 font-mono text-[12px] leading-relaxed text-paper">
        {code}
      </pre>
    </div>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
      <span className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full border border-line bg-white/[0.06] font-mono text-xs text-paper">
        {n}
      </span>
      <h3 className="text-sm font-medium text-paper">{title}</h3>
      <div className="col-start-2 text-sm leading-relaxed text-mist">{children}</div>
    </li>
  );
}

export function ConnectGuide({
  collectorUrl = API_BASE,
  slug,
  ingestKey,
  repoName,
}: {
  collectorUrl?: string;
  slug?: string;
  ingestKey?: string | null;
  repoName?: string | null;
}) {
  const [storedKey, setStoredKey] = useState<string | null>(null);

  useEffect(() => {
    if (!slug || ingestKey) return;
    try {
      setStoredKey(sessionStorage.getItem(`tb_ingest_key:${slug}`));
    } catch {
      /* ignore */
    }
  }, [slug, ingestKey]);

  const project = slug || "your-repo-slug";
  const repo = repoName || project;
  const key = ingestKey || storedKey || "${TELEMETRY_API_KEY}";
  const yaml = [
    `collector_url: ${collectorUrl}`,
    `project_id: ${project}`,
    `project_slug: ${project}`,
    `api_key: ${key}`,
    "enabled: true",
  ].join("\n");

  const instrument = [
    "from agentelemetry import TelemetryClient, trace_agent, record_llm_usage",
    "",
    'client = TelemetryClient.from_config("telemetry.yaml")',
    "",
    'with client.start_run(external_id="run-1", channel="cli") as run:',
    "",
    '    @trace_agent("MyAgent")',
    "    def work():",
    "        record_llm_usage(",
    '            agent_name="MyAgent",',
    '            model="gpt-4o-mini",',
    "            prompt_tokens=120,",
    "            completion_tokens=40,",
    "        )",
    '        return "ok"',
    "",
    "    work()",
    '    run.outcome = "succeeded"',
  ].join("\n");

  return (
    <section className="matte p-5 sm:p-6">
      <p className="eyebrow">This repo</p>
      <h2 className="mt-2 text-lg font-semibold tracking-tight text-paper">Send traces from the repo</h2>
      <p className="mt-2 text-sm leading-relaxed text-mist">
        <span className="font-mono text-paper">{repo}</span> is already a Pulse tab. Pulse does not run
        its agents. Do the following in that repository so runs post to this collector.
      </p>

      <ol className="mt-6 space-y-6">
        <Step n={1} title="Install the Pulse SDK">
          Add <span className="font-mono text-paper">agentelemetry</span> to{" "}
          <span className="font-mono text-paper">{repo}</span>’s environment:
          <CodeBlock label="shell" code={"pip install -e /path/to/Pulse/packages/agentelemetry"} />
        </Step>

        <Step n={2} title="Add telemetry.yaml at the repo root">
          This file is how the SDK finds the collector and this tab (
          <span className="font-mono text-paper">{project}</span>). The{" "}
          <span className="font-mono text-paper">api_key</span> field is the ingest key for this
          project — it belongs in the file, not as a separate dashboard action.
          <CodeBlock label="telemetry.yaml" code={yaml} />
        </Step>

        <Step n={3} title="Instrument the agents">
          Wrap workload execution in that repo’s code.
          <CodeBlock label="python" code={instrument} />
        </Step>

        <Step n={4} title="Run the repo">
          Start the app or CLI in <span className="font-mono text-paper">{repo}</span> as usual, then
          refresh this tab. Traces should appear within a few seconds.
        </Step>
      </ol>
    </section>
  );
}
