"use client";

import { AlertTriangle, BookOpen, CheckCircle2, Search, ShieldAlert, Stethoscope } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge, Card, Input, PageHeader, Select, Spinner } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import type { RunbookCase, RunbookLibraryData } from "@/lib/types";

function StepList({ title, icon: Icon, items }: { title: string; icon: typeof Stethoscope; items: string[] }) {
  return (
    <section>
      <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold text-[var(--espresso)]"><Icon className="size-4 text-[var(--camel-dark)]" />{title}</h4>
      <ol className="space-y-2">
        {items.map((item, index) => <li key={item} className="flex gap-3 rounded-xl bg-[#faf5ed] px-3 py-2.5 text-sm leading-6 text-[var(--taupe)]"><span className="font-bold text-[var(--camel-dark)]">{index + 1}</span><span>{item}</span></li>)}
      </ol>
    </section>
  );
}

function RunbookCard({ item }: { item: RunbookCase }) {
  return (
    <Card className="overflow-hidden">
      <details className="group">
        <summary className="cursor-pointer list-none p-5 md:p-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
            <div>
              <div className="mb-3 flex flex-wrap items-center gap-2"><Badge tone="info">{item.id}</Badge><Badge>{item.category}</Badge>{item.severity_applicability.map((severity) => <Badge key={severity} tone={severity === "critical" ? "danger" : severity === "high" ? "warning" : "neutral"}>{severity}</Badge>)}</div>
              <h3 className="text-lg font-semibold text-[var(--espresso)]">{item.name}</h3>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-[var(--taupe)]">{item.problem}</p>
            </div>
            <span className="text-sm font-semibold text-[var(--camel-dark)] group-open:hidden">View response plan</span>
            <span className="hidden text-sm font-semibold text-[var(--camel-dark)] group-open:inline">Hide response plan</span>
          </div>
        </summary>
        <div className="border-t border-[var(--border)] px-5 pb-6 pt-5 md:px-6">
          <div className="grid gap-7 xl:grid-cols-2">
            <StepList title="Diagnosis" icon={Stethoscope} items={item.diagnostic_steps} />
            <StepList title="Safe solutions" icon={CheckCircle2} items={item.solution_steps} />
            <StepList title="Verification" icon={ShieldAlert} items={item.verification_steps} />
            <StepList title="Required evidence" icon={BookOpen} items={item.missing_information} />
          </div>
          <div className="mt-7 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-[#e9cfc8] bg-[#fbefec] p-4"><p className="flex items-center gap-2 text-sm font-semibold text-[var(--danger)]"><AlertTriangle className="size-4" />Safety caution</p><p className="mt-2 text-sm leading-6 text-[var(--taupe)]">{item.caution}</p></div>
            <div className="rounded-2xl border border-[var(--border)] bg-[#faf5ed] p-4"><p className="text-sm font-semibold text-[var(--espresso)]">Escalate when</p><ul className="mt-2 space-y-1.5 text-sm leading-6 text-[var(--taupe)]">{item.escalation_triggers.map((trigger) => <li key={trigger}>• {trigger}</li>)}</ul></div>
          </div>
        </div>
      </details>
    </Card>
  );
}

export default function RunbooksPage() {
  const [data, setData] = useState<RunbookLibraryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");

  useEffect(() => {
    apiFetch<RunbookLibraryData>("/runbooks/").then(setData).finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => (data?.results || []).filter((item) => {
    const text = `${item.id} ${item.name} ${item.problem} ${item.category} ${item.keywords.join(" ")}`.toLowerCase();
    return (!query || text.includes(query.toLowerCase())) && (!category || item.category === category);
  }), [data, query, category]);

  return (
    <div>
      <PageHeader eyebrow="Operational knowledge" title="Runbook library" description="Thirty curated problem–diagnosis–solution cases used by the Runbook Agent. Recommendations remain advisory and require human approval." />
      <Card className="mb-6 p-4 md:p-5">
        <div className="grid gap-3 md:grid-cols-[1fr_260px_auto] md:items-center">
          <div className="relative"><Search className="pointer-events-none absolute left-3.5 top-3.5 size-4 text-[var(--taupe)]" /><Input className="pl-10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search problems, symptoms, or keywords" /></div>
          <Select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">All categories</option>{data?.categories.map((item) => <option key={item} value={item}>{item}</option>)}</Select>
          <p className="whitespace-nowrap text-sm font-semibold text-[var(--taupe)]">{filtered.length} of {data?.total || 30} cases</p>
        </div>
      </Card>
      {loading ? <div className="grid min-h-60 place-items-center"><Spinner /></div> : <div className="space-y-4">{filtered.map((item) => <RunbookCard key={item.id} item={item} />)}{filtered.length === 0 ? <Card className="p-10 text-center text-sm text-[var(--taupe)]">No runbook case matches this search.</Card> : null}</div>}
    </div>
  );
}
