import { Bot, Clock3, FileSearch, Gauge, GitCommitHorizontal, Search } from "lucide-react";

import { Badge, Card } from "@/components/ui";
import { percentage } from "@/lib/status";
import type { AgentExecution, AgentToolExecution, InvestigationResult } from "@/lib/types";

function toolLabel(name: string) {
  const labels: Record<string, string> = {
    get_service_metrics: "Service metrics",
    get_recent_deployments: "Recent deployments",
    search_logs: "Log search",
    search_runbooks: "Runbook search",
  };
  return labels[name] || name.replaceAll("_", " ");
}

function toolIcon(name: string) {
  if (name === "get_service_metrics") return <Gauge className="size-4" />;
  if (name === "get_recent_deployments") return <GitCommitHorizontal className="size-4" />;
  if (name === "search_runbooks") return <FileSearch className="size-4" />;
  return <Search className="size-4" />;
}

function compactArgs(args: Record<string, unknown>) {
  return Object.entries(args).map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`).join(" · ");
}

function resultSummary(tool: AgentToolExecution): string[] {
  const result = tool.result || {};
  if (typeof result.error === "string") return [result.error];

  if (tool.tool_name === "get_service_metrics" && Array.isArray(result.values)) {
    return result.values.slice(0, 4).map((item) => {
      const row = item as Record<string, unknown>;
      return `${String(row.name || "metric")}: ${String(row.before ?? "—")} → ${String(row.current ?? "—")} ${String(row.unit || "")}`.trim();
    });
  }
  if (tool.tool_name === "get_recent_deployments" && Array.isArray(result.deployments)) {
    return result.deployments.slice(0, 3).map((item) => {
      const row = item as Record<string, unknown>;
      return `${String(row.version || "version")} · ${String(row.deployed_at || "time unknown")} · ${String(row.change_summary || "no summary")}`;
    });
  }
  if (tool.tool_name === "search_logs" && Array.isArray(result.matches)) {
    return result.matches.slice(0, 4).map((item) => {
      const row = item as Record<string, unknown>;
      return `${String(row.level || "LOG")} · ${String(row.message || "")}`;
    });
  }
  if (tool.tool_name === "search_runbooks" && Array.isArray(result.matches)) {
    return result.matches.slice(0, 3).map((item) => {
      const row = item as Record<string, unknown>;
      return `${String(row.id || "")} · ${String(row.name || "Runbook")} · score ${String(row.match_score ?? "—")}`;
    });
  }
  if (result.found === false) return ["No matching local demo evidence was found."];
  return ["Tool completed with a compact local result."];
}

function Evidence({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-[var(--camel-dark)]">{title}</p>
      {items.length ? (
        <ul className="space-y-2">
          {items.map((item, index) => <li key={`${index}-${item}`} className="rounded-xl bg-[#faf5ed] px-3 py-2 text-sm leading-6 text-[var(--taupe)]">{item}</li>)}
        </ul>
      ) : <p className="text-sm text-[var(--taupe)]">None recorded.</p>}
    </div>
  );
}

export function InvestigationTrace({ output, execution }: { output: InvestigationResult | null; execution?: AgentExecution }) {
  const tools = execution?.tool_executions || [];

  return (
    <Card className="p-5 md:p-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-2xl bg-[var(--camel-soft)] text-[var(--camel-dark)]"><Bot className="size-5" /></span>
          <div><h3 className="font-semibold">Investigation agent</h3><p className="mt-0.5 text-xs text-[var(--taupe)]">{execution?.model_name || "Not run yet"} · bounded read-only tools</p></div>
        </div>
        <div className="flex items-center gap-2">
          {execution?.execution_mode ? <Badge tone={execution.execution_mode === "live" ? "success" : execution.execution_mode === "fallback" ? "warning" : "neutral"}>{execution.execution_mode}</Badge> : null}
          {output ? <Badge tone="info">{percentage(output.confidence)}</Badge> : null}
          {execution?.latency_ms ? <span className="inline-flex items-center gap-1 text-xs text-[var(--taupe)]"><Clock3 className="size-3.5" /> {execution.latency_ms} ms</span> : null}
        </div>
      </div>

      {!output ? <div className="rounded-xl border border-dashed border-[var(--border)] px-4 py-10 text-center text-sm text-[var(--taupe)]">This agent has not run yet.</div> : (
        <div className="space-y-6">
          <div><p className="mb-1.5 text-xs font-bold uppercase tracking-[0.12em] text-[var(--camel-dark)]">Leading hypothesis</p><p className="text-sm leading-6">{output.leading_hypothesis}</p></div>

          <div>
            <div className="mb-3 flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--camel-dark)]">Tool execution trace</p><span className="text-xs text-[var(--taupe)]">{tools.length} call{tools.length === 1 ? "" : "s"}</span></div>
            <div className="space-y-3">
              {tools.map((tool) => (
                <div key={tool.id} className="rounded-2xl border border-[var(--border)] bg-[#fbf7ef] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex gap-2.5"><span className="grid size-8 place-items-center rounded-xl bg-[var(--camel-soft)] text-[var(--camel-dark)]">{toolIcon(tool.tool_name)}</span><div><p className="text-sm font-semibold">{tool.sequence}. {toolLabel(tool.tool_name)}</p><p className="mt-0.5 text-xs text-[var(--taupe)]">{compactArgs(tool.arguments)}</p></div></div>
                    <div className="flex items-center gap-2"><Badge tone={tool.status === "success" ? "success" : tool.status === "started" ? "warning" : "danger"}>{tool.status}</Badge>{tool.execution_mode ? <Badge tone="neutral">{tool.execution_mode}</Badge> : null}<span className="text-xs text-[var(--taupe)]">{tool.latency_ms || 0} ms</span></div>
                  </div>
                  <div className="mt-3 space-y-1">{resultSummary(tool).map((line, index) => <p key={index} className="text-xs leading-5 text-[var(--taupe)]">{line}</p>)}</div>
                  {tool.error_message ? <p className="mt-2 text-xs text-[#8b3e34]">{tool.error_message}</p> : null}
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-2"><Evidence title="Supporting evidence" items={output.supporting_evidence || []} /><Evidence title="Missing evidence" items={output.missing_evidence || []} /></div>
          <Evidence title="Observations" items={output.observations || []} />
        </div>
      )}
    </Card>
  );
}
