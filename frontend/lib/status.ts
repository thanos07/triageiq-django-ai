import type { IncidentStatus } from "@/lib/types";

export const statusLabels: Record<IncidentStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  triaging: "AI triage",
  awaiting_review: "Awaiting review",
  approved: "Approved",
  rejected: "Rejected",
  revision_required: "Revision required",
  remediation_in_progress: "Remediation",
  resolved: "Resolved",
  closed: "Closed",
  failed: "Failed",
  reopened: "Reopened",
};

export function statusTone(status: IncidentStatus): "neutral" | "info" | "warning" | "danger" | "success" {
  if (["resolved", "closed", "approved"].includes(status)) return "success";
  if (["failed", "rejected"].includes(status)) return "danger";
  if (["awaiting_review", "revision_required", "reopened"].includes(status)) return "warning";
  if (["triaging", "remediation_in_progress"].includes(status)) return "info";
  return "neutral";
}

export function severityTone(value?: string | null): "neutral" | "info" | "warning" | "danger" | "success" {
  if (value === "critical") return "danger";
  if (value === "high") return "warning";
  if (value === "medium") return "info";
  if (value === "low") return "success";
  return "neutral";
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function percentage(value?: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}
