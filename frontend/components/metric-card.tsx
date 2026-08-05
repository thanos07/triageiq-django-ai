import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui";

export function MetricCard({ label, value, helper, icon: Icon }: { label: string; value: string | number; helper: string; icon: LucideIcon }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-[var(--taupe)]">{label}</p>
          <p className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-[var(--espresso)]">{value}</p>
          <p className="mt-2 text-xs leading-5 text-[#8b7d72]">{helper}</p>
        </div>
        <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-[var(--camel-soft)] text-[var(--camel-dark)]"><Icon className="size-5" /></span>
      </div>
    </Card>
  );
}
