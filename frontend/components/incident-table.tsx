import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { Badge, Card } from "@/components/ui";
import { formatDate, percentage, severityTone, statusTone } from "@/lib/status";
import type { IncidentSummary } from "@/lib/types";

const compactStatusLabels: Record<string, string> = {
  awaiting_review: "Awaiting review",
  revision_required: "Revision needed",
  action_in_progress: "In remediation",
  pipeline_failed: "Pipeline failed",
};

function compactStatus(status: string, fallback: string) {
  return compactStatusLabels[status] || fallback.replace("Awaiting human review", "Awaiting review");
}

export function IncidentTable({ incidents, emptyText = "No incidents found." }: { incidents: IncidentSummary[]; emptyText?: string }) {
  return (
    <Card className="w-full min-w-0 overflow-hidden">
      <div className="w-full overflow-x-auto overscroll-x-contain">
        <table className="w-full min-w-[760px] table-fixed text-left">
          <colgroup>
            <col className="w-[34%]" />
            <col className="w-[14%]" />
            <col className="w-[12%]" />
            <col className="w-[16%]" />
            <col className="w-[11%]" />
            <col className="w-[11%]" />
            <col className="w-[44px]" />
          </colgroup>
          <thead className="border-b border-[var(--border)] bg-[#fbf7ef] text-[10px] font-bold uppercase tracking-[0.11em] text-[#8c7f75]">
            <tr>
              <th className="px-4 py-4">Incident</th>
              <th className="px-3 py-4">Service</th>
              <th className="px-3 py-4">Severity</th>
              <th className="px-3 py-4">Status</th>
              <th className="px-3 py-4">Confidence</th>
              <th className="px-3 py-4">Submitted</th>
              <th className="px-2 py-4" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {incidents.map((incident) => {
              const statusLabel = compactStatus(incident.status, incident.status_label);
              return (
                <tr key={incident.id} className="transition hover:bg-[#fcf8f1]">
                  <td className="px-4 py-4">
                    <p className="truncate text-xs font-bold text-[var(--camel-dark)]">{incident.reference}</p>
                    <p className="mt-1 truncate text-sm font-semibold text-[var(--espresso)]" title={incident.title}>{incident.title}</p>
                  </td>
                  <td className="px-3 py-4 text-sm text-[var(--taupe)]">
                    <span className="block truncate" title={incident.service_name}>{incident.service_name}</span>
                  </td>
                  <td className="px-3 py-4">
                    <Badge tone={severityTone(incident.predicted_severity || incident.reported_severity)}>{incident.predicted_severity || incident.reported_severity}</Badge>
                  </td>
                  <td className="px-3 py-4">
                    <Badge tone={statusTone(incident.status)} className="max-w-full" >
                      <span className="truncate" title={incident.status_label}>{statusLabel}</span>
                    </Badge>
                  </td>
                  <td className="px-3 py-4 text-sm font-semibold text-[var(--espresso)]">{percentage(incident.overall_confidence)}</td>
                  <td className="px-3 py-4 text-xs leading-5 text-[var(--taupe)]">{formatDate(incident.submitted_at)}</td>
                  <td className="px-2 py-4">
                    <Link href={`/incidents/${incident.id}`} className="grid size-9 place-items-center rounded-xl text-[var(--taupe)] transition hover:bg-[var(--camel-soft)] hover:text-[var(--espresso)]" aria-label={`Open ${incident.reference}`}>
                      <ArrowUpRight className="size-4" />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!incidents.length ? <div className="px-6 py-16 text-center text-sm text-[var(--taupe)]">{emptyText}</div> : null}
    </Card>
  );
}
