"use client";

import { Plus, Search } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { IncidentTable } from "@/components/incident-table";
import { Button, Input, PageHeader, Select } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import type { IncidentSummary, Paginated } from "@/lib/types";

export default function IncidentsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    return params.toString();
  }, [search, status]);
  const incidents = useQuery({ queryKey: ["incidents", queryString], queryFn: () => apiFetch<Paginated<IncidentSummary>>(`/incidents/${queryString ? `?${queryString}` : ""}`) });

  return (
    <>
      <PageHeader eyebrow="Incident registry" title="Incidents" description="Search the complete lifecycle from initial report through AI triage, human review, remediation, and closure." actions={<Link href="/incidents/new"><Button><Plus className="size-4" /> New incident</Button></Link>} />
      <div className="mb-5 grid gap-3 md:grid-cols-[1fr_240px]">
        <div className="relative"><Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-[#9b8e83]" /><Input className="pl-10" placeholder="Search title, service, or description…" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
        <Select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="submitted">Submitted</option><option value="triaging">AI triage</option><option value="awaiting_review">Awaiting review</option><option value="approved">Approved</option><option value="remediation_in_progress">Remediation</option><option value="resolved">Resolved</option><option value="closed">Closed</option><option value="failed">Failed</option></Select>
      </div>
      {incidents.isLoading ? <div className="py-24 text-center text-sm text-[var(--taupe)]">Loading incidents…</div> : incidents.isError ? <div className="rounded-2xl bg-[#f2dcd7] p-5 text-sm text-[#8b3e34]">Incidents could not be loaded.</div> : <IncidentTable incidents={incidents.data?.results || []} />}
    </>
  );
}
