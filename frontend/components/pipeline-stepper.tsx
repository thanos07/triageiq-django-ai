import { Check, Circle, Loader2 } from "lucide-react";

const stages = [
  { key: "submitted", label: "Submitted" },
  { key: "severity", label: "Severity" },
  { key: "investigation", label: "Investigation" },
  { key: "root_cause", label: "Root cause" },
  { key: "runbook", label: "Runbook" },
  { key: "summary", label: "Summary" },
  { key: "review", label: "Review" },
  { key: "resolution", label: "Resolution" },
];

function completedIndex(currentStage: string, status: string): number {
  if (["resolved", "closed"].includes(status)) return 7;
  if (status === "remediation_in_progress") return 6;
  if (["approved", "rejected", "revision_required"].includes(status)) return 6;
  if (status === "awaiting_review") return 5;
  const mapping: Record<string, number> = { not_started: 0, normalization: 0, severity: 1, investigation: 2, root_cause: 3, runbook: 4, summary: 5, complete: 5 };
  return mapping[currentStage] ?? 0;
}

export function PipelineStepper({ currentStage, status, processing }: { currentStage: string; status: string; processing: boolean }) {
  const current = completedIndex(currentStage, status);
  return (
    <div className="grid gap-3 sm:grid-cols-4 xl:grid-cols-8">
      {stages.map((stage, index) => {
        const done = index <= current;
        const active = index === current + 1 || (index === current && processing);
        return (
          <div key={stage.key} className={`rounded-2xl border p-3.5 ${done ? "border-[#c8d7ca] bg-[#f2f7f2]" : active ? "border-[#cfab87] bg-[#fbf3e9]" : "border-[var(--border)] bg-[var(--ivory)]"}`}>
            <div className="flex items-center gap-2.5">
              <span className={`grid size-7 place-items-center rounded-full ${done ? "bg-[var(--success)] text-white" : active ? "bg-[var(--camel)] text-white" : "bg-[#eee7dd] text-[#9a8d82]"}`}>
                {done ? <Check className="size-3.5" /> : active && processing ? <Loader2 className="size-3.5 animate-spin" /> : <Circle className="size-3" />}
              </span>
              <span className="text-xs font-semibold text-[var(--espresso)]">{stage.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
