"use client";

import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Download,
  FileCheck2,
  FileText,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Trash2,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { AgentCard } from "@/components/agent-card";
import { useAuth } from "@/components/auth-provider";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { Badge, Button, Card, Input, Label, PageHeader, Select, Spinner, Textarea } from "@/components/ui";
import { apiFetch, downloadIncidentReport } from "@/lib/api";
import { formatDate, percentage, severityTone, statusTone } from "@/lib/status";
import type { IncidentDetail, ResolutionAction } from "@/lib/types";

type Tab = "overview" | "analysis" | "timeline" | "resolution";

const stageTitles: Record<string, string> = {
  normalization: "Incident normalizer",
  severity: "Severity agent",
  root_cause: "Root-cause agent",
  runbook: "Runbook agent",
  summary: "Communication agent",
};

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [review, setReview] = useState({ decision: "approved", reviewer_note: "", severity: "" });
  const [reopenReason, setReopenReason] = useState("");
  const [resolution, setResolution] = useState({
    resolution_summary: "",
    confirmed_root_cause: "",
    root_cause_confirmed: true,
    verification_notes: "",
    actions: [{ order: 1, action: "", result: "", performed_by: user?.display_name || "" }] as ResolutionAction[],
  });

  const incidentQuery = useQuery({
    queryKey: ["incident", id],
    queryFn: () => apiFetch<IncidentDetail>(`/incidents/${id}/`),
    refetchInterval: (query) => query.state.data?.workflow?.is_processing ? 1500 : false,
  });

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ["incident", id] });
    await queryClient.invalidateQueries({ queryKey: ["incidents"] });
    await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }

  async function perform(label: string, task: () => Promise<unknown>) {
    setBusy(label); setError("");
    try { await task(); await refresh(); }
    catch (err) { setError(err instanceof Error ? err.message : "The action could not be completed."); }
    finally { setBusy(""); }
  }

  async function runAllStages() {
    setBusy("pipeline"); setError("");
    try {
      for (let step = 0; step < 5; step += 1) {
        const response = await apiFetch<{ completed_stage: string; incident: IncidentDetail }>(`/incidents/${id}/advance/`, { method: "POST", body: "{}" });
        queryClient.setQueryData(["incident", id], response.incident);
        if (response.completed_stage === "complete") break;
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "The AI workflow could not continue.");
    } finally { setBusy(""); }
  }

  async function submitReview() {
    const overrides = review.severity ? { severity: review.severity } : {};
    await perform("review", () => apiFetch(`/incidents/${id}/review/`, {
      method: "POST",
      body: JSON.stringify({ decision: review.decision, reviewer_note: review.reviewer_note, overrides }),
    }));
  }

  async function submitResolution() {
    await perform("resolve", () => apiFetch(`/incidents/${id}/resolve/`, {
      method: "POST",
      body: JSON.stringify(resolution),
    }));
  }

  const incident = incidentQuery.data;
  const canManage = user?.role === "admin" || user?.role === "incident_manager";
  const canReview = user?.role === "admin" || user?.role === "reviewer";
  const latestExecutions = useMemo(() => {
    const map = new Map<string, IncidentDetail["agent_executions"][number]>();
    for (const execution of incident?.agent_executions || []) map.set(execution.stage, execution);
    return map;
  }, [incident?.agent_executions]);

  if (incidentQuery.isLoading) return <div className="py-24 text-center text-sm text-[var(--taupe)]">Loading incident workspace…</div>;
  if (incidentQuery.isError || !incident) return <div className="rounded-2xl bg-[#f2dcd7] p-5 text-sm text-[#8b3e34]">This incident could not be loaded.</div>;

  const predictedSeverity = String(incident.workflow?.severity_output?.level || incident.reported_severity);
  const pipelineRunnable = ["submitted", "triaging", "failed", "revision_required", "reopened"].includes(incident.status);

  return (
    <>
      <PageHeader
        eyebrow={incident.reference}
        title={incident.title}
        description={`${incident.service_name} · ${incident.environment} · submitted ${formatDate(incident.submitted_at)}`}
        actions={
          <>
            <Link href="/incidents"><Button variant="ghost"><ArrowLeft className="size-4" /> Back</Button></Link>
            {incident.workflow.current_stage !== "not_started" ? <Button variant="secondary" onClick={() => perform("draft", () => downloadIncidentReport(id, true))} disabled={!!busy}><Download className="size-4" /> Draft PDF</Button> : null}
            {["resolved", "closed"].includes(incident.status) ? <Button onClick={() => perform("final", () => downloadIncidentReport(id, false))} disabled={!!busy}><Download className="size-4" /> Final PDF</Button> : null}
          </>
        }
      />

      <Card className="mb-6 p-5 md:p-6">
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <Badge tone={severityTone(predictedSeverity)}>{predictedSeverity} severity</Badge>
          <Badge tone={statusTone(incident.status)}>{incident.status_label}</Badge>
          <Badge tone="neutral">{incident.environment}</Badge>
          {incident.workflow.overall_confidence !== null ? <Badge tone="info">{percentage(incident.workflow.overall_confidence)} confidence</Badge> : null}
          <span className="ml-auto text-xs text-[var(--taupe)]">Updated {formatDate(incident.updated_at)}</span>
        </div>
        <PipelineStepper currentStage={incident.workflow.current_stage} status={incident.status} processing={incident.workflow.is_processing || busy === "pipeline"} />
      </Card>

      {error ? <div className="mb-6 flex items-start gap-3 rounded-2xl bg-[#f2dcd7] p-4 text-sm text-[#8b3e34]"><AlertCircle className="mt-0.5 size-4 shrink-0" />{error}</div> : null}

      <div className="mb-6 flex gap-1 overflow-x-auto rounded-2xl border border-[var(--border)] bg-[#eee5d9] p-1.5">
        {(["overview", "analysis", "timeline", "resolution"] as Tab[]).map((item) => <button key={item} onClick={() => setTab(item)} className={`whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-semibold capitalize transition ${tab === item ? "bg-[var(--ivory)] text-[var(--espresso)] shadow-sm" : "text-[var(--taupe)] hover:text-[var(--espresso)]"}`}>{item}</button>)}
      </div>

      {tab === "overview" ? (
        <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-lg font-semibold">Incident report</h2>
              <div className="mt-5 grid gap-5 md:grid-cols-2">
                <Info label="Service" value={incident.service_name} />
                <Info label="Environment" value={incident.environment} />
                <Info label="Reported severity" value={incident.reported_severity} />
                <Info label="Source" value={incident.source} />
                <div className="md:col-span-2"><Info label="Observed symptoms" value={incident.description} /></div>
                <div className="md:col-span-2"><Info label="Business impact" value={incident.business_impact || "Not supplied"} /></div>
              </div>
            </Card>

            {incident.source_file ? (
              <Card className="p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-start gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-[var(--camel-soft)] text-[var(--camel-dark)]"><FileText className="size-5" /></span>
                    <div>
                      <h2 className="font-semibold">Temporary source document</h2>
                      <p className="mt-1 text-sm text-[var(--taupe)]">{incident.source_file.original_name} · {formatBytes(incident.source_file.size_bytes)}</p>
                    </div>
                  </div>
                  <Badge tone={incident.source_file.availability === "ready" ? "success" : incident.source_file.availability === "expired" ? "warning" : "neutral"}>{incident.source_file.availability}</Badge>
                </div>
                <div className="mt-5 grid gap-4 rounded-2xl bg-[#f8f1e7] p-4 sm:grid-cols-2">
                  <Info label="File type" value={incident.source_file.file_type_label} />
                  <Info label="Retention" value={`${incident.source_file.retention_days} days`} />
                  <Info label="Uploaded" value={formatDate(incident.source_file.uploaded_at)} />
                  <Info label="Expires" value={formatDate(incident.source_file.expires_at)} />
                </div>
                <p className="mt-4 flex items-start gap-2 text-sm leading-6 text-[var(--taupe)]"><Clock3 className="mt-1 size-4 shrink-0" /> The original file is automatically removed after expiry. Extracted facts, information gaps, AI outputs, and reports remain.</p>
                {incident.information_gaps.length ? <div className="mt-5"><p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--camel-dark)]">Information still needed</p><div className="mt-3 grid gap-3 md:grid-cols-2">{incident.information_gaps.map((gap) => <div key={gap.field} className="rounded-xl border border-[var(--border)] bg-[var(--ivory)] p-3"><p className="text-sm font-semibold capitalize">{gap.field.replaceAll("_", " ")}</p><p className="mt-1 text-xs leading-5 text-[var(--taupe)]">{gap.collection_method}</p></div>)}</div></div> : null}
                {canManage && incident.source_file.availability === "ready" ? <div className="mt-5 flex flex-wrap gap-2"><Button variant="secondary" onClick={() => perform("reextract", () => apiFetch(`/incidents/${id}/source-file/reextract/`, { method: "POST", body: "{}" }))} disabled={!!busy}>{busy === "reextract" ? <Spinner /> : <RefreshCw className="size-4" />} Re-extract</Button><Button variant="ghost" onClick={() => perform("delete-source", () => apiFetch(`/incidents/${id}/source-file/delete/`, { method: "POST", body: "{}" }))} disabled={!!busy}>{busy === "delete-source" ? <Spinner /> : <Trash2 className="size-4" />} Delete original now</Button></div> : null}
              </Card>
            ) : null}

            {incident.workflow.summary_output ? <AgentCard title="Current stakeholder summary" output={incident.workflow.summary_output} confidence={Number(incident.workflow.summary_output.confidence || 0)} model={latestExecutions.get("summary")?.model_name} mode={latestExecutions.get("summary")?.execution_mode} /> : null}
          </div>

          <div className="space-y-5">
            {pipelineRunnable && canManage ? (
              <Card className="p-5">
                <div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-[var(--camel-soft)] text-[var(--camel-dark)]"><Play className="size-5" /></span><div><h3 className="font-semibold">Run AI triage</h3><p className="mt-1 text-sm leading-6 text-[var(--taupe)]">The browser calls one recoverable stage at a time, avoiding a long serverless request.</p></div></div>
                <Button className="mt-5 w-full" onClick={runAllStages} disabled={!!busy}>{busy === "pipeline" ? <><Spinner /> Running agents…</> : <><Play className="size-4" /> Run complete analysis</>}</Button>
              </Card>
            ) : null}

            {incident.status === "awaiting_review" ? (
              <Card className="p-5">
                <div className="flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-[#e2eaec] text-[var(--info)]"><ShieldCheck className="size-5" /></span><div><h3 className="font-semibold">Human review required</h3><p className="mt-1 text-sm leading-6 text-[var(--taupe)]">Approve the plan, reject it, or request another triage pass.</p></div></div>
                {canReview ? <div className="mt-5 space-y-4"><div><Label>Decision</Label><Select value={review.decision} onChange={(event) => setReview({ ...review, decision: event.target.value })}><option value="approved">Approve</option><option value="revision_required">Request revision</option><option value="rejected">Reject</option></Select></div><div><Label>Severity override (optional)</Label><Select value={review.severity} onChange={(event) => setReview({ ...review, severity: event.target.value })}><option value="">Keep AI severity</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></Select></div><div><Label>Reviewer note</Label><Textarea value={review.reviewer_note} onChange={(event) => setReview({ ...review, reviewer_note: event.target.value })} placeholder="Reference the evidence behind your decision." /></div><Button className="w-full" onClick={submitReview} disabled={!!busy}>{busy === "review" ? <Spinner /> : <FileCheck2 className="size-4" />} Record decision</Button></div> : <p className="mt-4 rounded-xl bg-[#f8f1e7] p-3 text-sm text-[var(--taupe)]">Your role can view this decision but cannot submit it.</p>}
              </Card>
            ) : null}

            {incident.status === "approved" && canManage ? <Card className="p-5"><h3 className="font-semibold">Plan approved</h3><p className="mt-2 text-sm leading-6 text-[var(--taupe)]">Start remediation before recording actual actions and recovery evidence.</p><Button className="mt-5 w-full" onClick={() => perform("start", () => apiFetch(`/incidents/${id}/start-resolution/`, { method: "POST", body: "{}" }))} disabled={!!busy}>{busy === "start" ? <Spinner /> : <Wrench className="size-4" />} Start remediation</Button></Card> : null}

            {["resolved", "closed"].includes(incident.status) ? <Card className="p-5"><div className="flex gap-3"><CheckCircle2 className="size-5 text-[var(--success)]" /><div><h3 className="font-semibold">Verified resolution</h3><p className="mt-1 text-sm leading-6 text-[var(--taupe)]">The final report includes the AI analysis, review decision, actual actions, and timeline.</p></div></div></Card> : null}
          </div>
        </div>
      ) : null}

      {tab === "analysis" ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <AgentCard title="Severity agent" output={incident.workflow.severity_output} confidence={incident.workflow.severity_output ? Number(incident.workflow.severity_output.confidence || 0) : null} model={latestExecutions.get("severity")?.model_name} latency={latestExecutions.get("severity")?.latency_ms} mode={latestExecutions.get("severity")?.execution_mode} />
          <AgentCard title="Root-cause agent" output={incident.workflow.root_cause_output} confidence={incident.workflow.root_cause_output ? Number(incident.workflow.root_cause_output.confidence || 0) : null} model={latestExecutions.get("root_cause")?.model_name} latency={latestExecutions.get("root_cause")?.latency_ms} mode={latestExecutions.get("root_cause")?.execution_mode} />
          <AgentCard title="Runbook agent" output={incident.workflow.runbook_output} confidence={incident.workflow.runbook_output ? Number(incident.workflow.runbook_output.confidence || 0) : null} model={latestExecutions.get("runbook")?.model_name} latency={latestExecutions.get("runbook")?.latency_ms} mode={latestExecutions.get("runbook")?.execution_mode} />
          <AgentCard title="Communication agent" output={incident.workflow.summary_output} confidence={incident.workflow.summary_output ? Number(incident.workflow.summary_output.confidence || 0) : null} model={latestExecutions.get("summary")?.model_name} latency={latestExecutions.get("summary")?.latency_ms} mode={latestExecutions.get("summary")?.execution_mode} />
        </div>
      ) : null}

      {tab === "timeline" ? (
        <Card className="p-6">
          <h2 className="text-lg font-semibold">Status and execution timeline</h2>
          <div className="mt-6 space-y-0">
            {incident.status_events.map((event, index) => <div key={event.id} className="relative flex gap-4 pb-7 last:pb-0"><div className="flex flex-col items-center"><span className="mt-1 size-3 rounded-full bg-[var(--camel)] ring-4 ring-[var(--camel-soft)]" />{index < incident.status_events.length - 1 ? <span className="mt-2 h-full w-px bg-[var(--border)]" /> : null}</div><div><div className="flex flex-wrap items-center gap-2"><p className="font-semibold capitalize">{event.new_status.replaceAll("_", " ")}</p><span className="text-xs text-[var(--taupe)]">{formatDate(event.created_at)}</span></div><p className="mt-1 text-sm leading-6 text-[var(--taupe)]">{event.note || "Status updated."}</p><p className="mt-1 text-xs text-[#94877c]">{event.changed_by?.display_name || "System"}</p></div></div>)}
          </div>
          <div className="mt-8 border-t border-[var(--border)] pt-6"><h3 className="font-semibold">Agent execution audit</h3><div className="mt-4 grid gap-3 md:grid-cols-2">{incident.agent_executions.map((execution) => <div key={execution.id} className="rounded-2xl border border-[var(--border)] bg-[#fbf7ef] p-4"><div className="flex items-center justify-between gap-3"><p className="text-sm font-semibold">{stageTitles[execution.stage] || execution.stage_label}</p><Badge tone={execution.status === "success" ? "success" : "danger"}>{execution.status}</Badge></div><p className="mt-2 text-xs text-[var(--taupe)]">{execution.model_name || "No model"} · {execution.latency_ms || 0} ms · {execution.execution_mode}</p>{execution.error_message ? <p className="mt-2 text-xs text-[#8b3e34]">{execution.error_message}</p> : null}</div>)}</div></div>
        </Card>
      ) : null}

      {tab === "resolution" ? (
        <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
          <Card className="p-6 md:p-8">
            <h2 className="text-lg font-semibold">Actual remediation and recovery evidence</h2>
            {incident.status === "remediation_in_progress" && canManage ? (
              <div className="mt-6 space-y-5">
                <div><Label>Resolution summary</Label><Textarea value={resolution.resolution_summary} onChange={(event) => setResolution({ ...resolution, resolution_summary: event.target.value })} placeholder="Explain what restored the service and the final outcome." /></div>
                <div><Label>Confirmed root cause</Label><Textarea value={resolution.confirmed_root_cause} onChange={(event) => setResolution({ ...resolution, confirmed_root_cause: event.target.value })} placeholder="Record the root cause supported by evidence." /></div>
                <label className="flex items-center gap-3 rounded-xl bg-[#f8f1e7] p-4 text-sm"><input type="checkbox" checked={resolution.root_cause_confirmed} onChange={(event) => setResolution({ ...resolution, root_cause_confirmed: event.target.checked })} className="size-4 accent-[var(--camel-dark)]" /><span>The human-confirmed cause agrees with the AI hypothesis.</span></label>
                <div><Label>Verification notes</Label><Textarea value={resolution.verification_notes} onChange={(event) => setResolution({ ...resolution, verification_notes: event.target.value })} placeholder="Which health checks, user journeys, and business metrics prove recovery?" /></div>
                <div><div className="mb-3 flex items-center justify-between"><Label>Actions performed</Label><Button variant="secondary" size="sm" onClick={() => setResolution({ ...resolution, actions: [...resolution.actions, { order: resolution.actions.length + 1, action: "", result: "", performed_by: user?.display_name || "" }] })}><Plus className="size-4" /> Add action</Button></div><div className="space-y-3">{resolution.actions.map((action, index) => <div key={index} className="rounded-2xl border border-[var(--border)] bg-[#fbf7ef] p-4"><div className="mb-3 flex items-center justify-between"><p className="text-sm font-semibold">Action {index + 1}</p>{resolution.actions.length > 1 ? <button onClick={() => setResolution({ ...resolution, actions: resolution.actions.filter((_, itemIndex) => itemIndex !== index).map((item, itemIndex) => ({ ...item, order: itemIndex + 1 })) })} className="text-[var(--danger)]"><Trash2 className="size-4" /></button> : null}</div><div className="space-y-3"><Input placeholder="Action performed" value={action.action} onChange={(event) => setResolution({ ...resolution, actions: resolution.actions.map((item, itemIndex) => itemIndex === index ? { ...item, action: event.target.value } : item) })} /><Input placeholder="Observed result" value={action.result} onChange={(event) => setResolution({ ...resolution, actions: resolution.actions.map((item, itemIndex) => itemIndex === index ? { ...item, result: event.target.value } : item) })} /><Input placeholder="Performed by" value={action.performed_by} onChange={(event) => setResolution({ ...resolution, actions: resolution.actions.map((item, itemIndex) => itemIndex === index ? { ...item, performed_by: event.target.value } : item) })} /></div></div>)}</div></div>
                <Button onClick={submitResolution} disabled={!!busy} className="w-full">{busy === "resolve" ? <Spinner /> : <CheckCircle2 className="size-4" />} Verify and mark resolved</Button>
              </div>
            ) : incident.resolution ? (
              <div className="mt-6 space-y-6"><Info label="Resolution summary" value={incident.resolution.resolution_summary} /><Info label="Confirmed root cause" value={incident.resolution.confirmed_root_cause} /><Info label="Verification evidence" value={incident.resolution.verification_notes} /><div><p className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-[var(--camel-dark)]">Actions performed</p><div className="space-y-3">{incident.resolution.actions.map((action) => <div key={action.id || action.order} className="rounded-2xl bg-[#f8f1e7] p-4"><p className="font-semibold">{action.order}. {action.action}</p><p className="mt-2 text-sm text-[var(--taupe)]">{action.result}</p><p className="mt-2 text-xs text-[#94877c]">{action.performed_by}</p></div>)}</div></div></div>
            ) : <div className="mt-6 rounded-2xl border border-dashed border-[var(--border)] px-6 py-16 text-center text-sm leading-6 text-[var(--taupe)]">Resolution fields become available after the AI plan is approved and remediation begins.</div>}
          </Card>
          <div className="space-y-5">
            <Card className="p-5"><p className="font-semibold">Resolution gate</p><p className="mt-2 text-sm leading-6 text-[var(--taupe)]">An AI suggestion is not a resolution. Record the real action, its result, and evidence that service health and user journeys recovered.</p></Card>
            {["resolved", "closed"].includes(incident.status) && canManage ? <Card className="p-5"><p className="font-semibold">Reopen incident</p><p className="mt-2 text-sm leading-6 text-[var(--taupe)]">Use this only when symptoms return or the earlier resolution is invalid.</p><Textarea className="mt-4" placeholder="Reason for reopening" value={reopenReason} onChange={(event) => setReopenReason(event.target.value)} /><Button variant="secondary" className="mt-3 w-full" disabled={reopenReason.length < 8 || !!busy} onClick={() => perform("reopen", () => apiFetch(`/incidents/${id}/reopen/`, { method: "POST", body: JSON.stringify({ reason: reopenReason }) }))}>{busy === "reopen" ? <Spinner /> : <RotateCcw className="size-4" />} Reopen</Button></Card> : null}
          </div>
        </div>
      ) : null}
    </>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><p className="mb-1.5 text-xs font-bold uppercase tracking-[0.12em] text-[var(--camel-dark)]">{label}</p><p className="text-sm leading-6 text-[var(--taupe)]">{value}</p></div>;
}


function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.ceil(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
