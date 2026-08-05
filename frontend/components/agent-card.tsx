import { Bot, Clock3 } from "lucide-react";
import { Badge, Card } from "@/components/ui";
import { percentage } from "@/lib/status";

function renderValue(value: unknown): React.ReactNode {
  if (Array.isArray(value)) {
    return <ul className="space-y-2">{value.map((item, index) => <li key={index} className="rounded-xl bg-[#faf5ed] px-3 py-2 text-sm leading-6 text-[var(--taupe)]">{typeof item === "object" && item !== null ? Object.entries(item).map(([key, child]) => <span key={key} className="mr-3 inline"><strong className="text-[var(--espresso)]">{key.replaceAll("_", " ")}:</strong> {String(child)}</span>) : String(item)}</li>)}</ul>;
  }
  if (typeof value === "object" && value !== null) return <pre className="overflow-auto rounded-xl bg-[#faf5ed] p-3 text-xs leading-5 text-[var(--taupe)]">{JSON.stringify(value, null, 2)}</pre>;
  return <p className="text-sm leading-6 text-[var(--taupe)]">{String(value)}</p>;
}

export function AgentCard({ title, output, confidence, model, latency, mode }: { title: string; output: Record<string, unknown> | null; confidence?: number | null; model?: string; latency?: number | null; mode?: string }) {
  return (
    <Card className="p-5 md:p-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-2xl bg-[var(--camel-soft)] text-[var(--camel-dark)]"><Bot className="size-5" /></span><div><h3 className="font-semibold text-[var(--espresso)]">{title}</h3><p className="mt-0.5 text-xs text-[var(--taupe)]">{model || "Not run yet"}</p></div></div>
        <div className="flex items-center gap-2">{mode ? <Badge tone={mode === "live" ? "success" : mode === "fallback" ? "warning" : "neutral"}>{mode}</Badge> : null}{confidence !== undefined ? <Badge tone="info">{percentage(confidence)}</Badge> : null}{latency ? <span className="inline-flex items-center gap-1 text-xs text-[var(--taupe)]"><Clock3 className="size-3.5" /> {latency} ms</span> : null}</div>
      </div>
      {output ? <div className="space-y-4">{Object.entries(output).map(([key, value]) => <div key={key}><p className="mb-1.5 text-xs font-bold uppercase tracking-[0.12em] text-[var(--camel-dark)]">{key.replaceAll("_", " ")}</p>{renderValue(value)}</div>)}</div> : <div className="rounded-xl border border-dashed border-[var(--border)] px-4 py-10 text-center text-sm text-[var(--taupe)]">This agent has not run yet.</div>}
    </Card>
  );
}
