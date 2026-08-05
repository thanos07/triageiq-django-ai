"use client";

import { Activity, AlertTriangle, Bot, CheckCircle2, Plus, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";

import { IncidentTable } from "@/components/incident-table";
import { MetricCard } from "@/components/metric-card";
import { Button, Card, PageHeader, Spinner } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import type { DashboardData, IncidentDetail } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: () => apiFetch<DashboardData>("/dashboard/") });
  const demo = useMutation({
    mutationFn: () => apiFetch<IncidentDetail>("/incidents/demo/", { method: "POST", body: "{}" }),
    onSuccess: (incident) => router.push(`/incidents/${incident.id}`),
  });

  if (dashboard.isLoading) return <div className="py-24 text-center text-sm text-[var(--taupe)]">Loading operational overview…</div>;
  if (dashboard.isError || !dashboard.data) return <div className="rounded-2xl bg-[#f2dcd7] p-5 text-sm text-[#8b3e34]">The dashboard could not be loaded. Confirm that the Django API is running.</div>;

  const data = dashboard.data;
  const maxSeverity = Math.max(1, ...Object.values(data.severity_counts));

  return (
    <>
      <PageHeader eyebrow="Operations overview" title="Good morning. Here is your incident posture." description="Focus on incidents that need human review or verified remediation. AI recommendations remain advisory throughout the workflow." actions={<><Button variant="secondary" onClick={() => demo.mutate()} disabled={demo.isPending}>{demo.isPending ? <Spinner /> : <Bot className="size-4" />} Try demo incident</Button><Link href="/incidents/new"><Button><Plus className="size-4" /> New incident</Button></Link></>} />

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Open incidents" value={data.open} helper="All incidents not yet resolved or closed" icon={Activity} />
        <MetricCard label="Awaiting review" value={data.awaiting_review} helper="AI analysis completed and needs a decision" icon={ShieldCheck} />
        <MetricCard label="Critical incidents" value={data.critical} helper="Predicted critical severity across the workspace" icon={AlertTriangle} />
        <MetricCard label="Resolved" value={data.resolved} helper="Incidents with verified remediation records" icon={CheckCircle2} />
      </section>

      <section className="mt-6 grid min-w-0 gap-6 2xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0">
          <div className="mb-4 flex items-end justify-between"><div><h2 className="text-xl font-semibold tracking-[-0.025em]">Recent incidents</h2><p className="mt-1 text-sm text-[var(--taupe)]">Latest activity across services and environments.</p></div><Link href="/incidents" className="text-sm font-semibold text-[var(--camel-dark)] hover:underline">View all</Link></div>
          <IncidentTable incidents={data.recent_incidents} />
        </div>
        <div className="grid min-w-0 gap-6 md:grid-cols-2 2xl:grid-cols-1">
          <Card className="p-5">
            <div className="flex items-center justify-between"><div><p className="text-sm font-semibold">Severity distribution</p><p className="mt-1 text-xs text-[var(--taupe)]">Based on AI predictions</p></div><span className="grid size-10 place-items-center rounded-2xl bg-[var(--camel-soft)] text-[var(--camel-dark)]"><AlertTriangle className="size-5" /></span></div>
            <div className="mt-6 space-y-4">{Object.entries(data.severity_counts).map(([level, count]) => <div key={level}><div className="mb-1.5 flex justify-between text-xs"><span className="font-semibold capitalize text-[var(--espresso)]">{level}</span><span className="text-[var(--taupe)]">{count}</span></div><div className="h-2 rounded-full bg-[#eee6db]"><div className="h-2 rounded-full bg-[var(--camel)]" style={{ width: `${Math.max(count ? 12 : 0, (count / maxSeverity) * 100)}%` }} /></div></div>)}</div>
          </Card>
          <Card className="overflow-hidden p-5">
            <p className="text-sm font-semibold">AI reliability</p><p className="mt-1 text-xs text-[var(--taupe)]">Average confidence on completed workflows</p>
            <div className="mt-6 flex items-end gap-3"><span className="text-4xl font-semibold tracking-[-0.05em]">{Math.round(data.average_confidence * 100)}%</span><span className="mb-1 text-xs text-[var(--taupe)]">human review required</span></div>
            <div className="mt-5 h-2 rounded-full bg-[#eee6db]"><div className="h-2 rounded-full bg-[var(--success)]" style={{ width: `${data.average_confidence * 100}%` }} /></div>
            <div className="mt-5 rounded-xl bg-[#f8f1e7] p-3 text-xs leading-5 text-[var(--taupe)]">Confidence supports prioritisation; it never authorises remediation or incident closure.</div>
          </Card>
        </div>
      </section>
    </>
  );
}
