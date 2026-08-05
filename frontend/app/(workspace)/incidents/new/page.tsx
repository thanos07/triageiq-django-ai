"use client";

import {
  ArrowLeft,
  ArrowRight,
  Clock3,
  FileJson2,
  FileText,
  PencilLine,
  ShieldCheck,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import {
  Badge,
  Button,
  Card,
  Input,
  Label,
  PageHeader,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/status";
import type {
  IncidentDetail,
  UploadExtractionResponse,
} from "@/lib/types";

type EntryMode = "manual" | "upload";

type IncidentForm = {
  title: string;
  description: string;
  service_name: string;
  environment: string;
  reported_severity: string;
  business_impact: string;
};

const emptyForm: IncidentForm = {
  title: "",
  description: "",
  service_name: "",
  environment: "production",
  reported_severity: "unknown",
  business_impact: "",
};

export default function NewIncidentPage() {
  const router = useRouter();

  const [entryMode, setEntryMode] =
    useState<EntryMode>("manual");

  const [submitting, setSubmitting] =
    useState(false);

  const [uploading, setUploading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [form, setForm] =
    useState<IncidentForm>(emptyForm);

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [retentionDays, setRetentionDays] =
    useState("10");

  const [extraction, setExtraction] =
    useState<UploadExtractionResponse | null>(null);

  function update(
    key: keyof IncidentForm,
    value: string,
  ) {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function changeMode(mode: EntryMode) {
    setEntryMode(mode);
    setError("");

    if (mode === "manual") {
      setExtraction(null);
      setSelectedFile(null);
      setForm(emptyForm);
    }
  }

  async function extractUpload() {
    if (!selectedFile) {
      setError(
        "Select a PDF, JSON, CSV, TXT, or LOG file first.",
      );
      return;
    }

    setUploading(true);
    setError("");

    try {
      const body = new FormData();

      body.append("file", selectedFile);
      body.append(
        "retention_days",
        retentionDays,
      );

      const result =
        await apiFetch<UploadExtractionResponse>(
          "/incidents/extract-upload/",
          {
            method: "POST",
            body,
          },
        );

      setExtraction(result);

      setForm((current) => ({
        ...current,
        title: result.fields.title || "",
        description:
          result.fields.description || "",
        service_name:
          result.fields.service_name || "",
        environment:
          result.fields.environment || "other",
        reported_severity:
          result.fields.reported_severity
          || "unknown",
        business_impact:
          result.fields.business_impact || "",
      }));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The source file could not be extracted.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function submit(
    event: FormEvent,
  ) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const payload = {
        ...form,
        source_file_id:
          extraction?.source_file.id || null,
        extracted_context:
          extraction?.extracted_context || {},
        information_gaps:
          extraction?.information_gaps || [],
      };

      const incident =
        await apiFetch<IncidentDetail>(
          "/incidents/",
          {
            method: "POST",
            body: JSON.stringify(payload),
          },
        );

      router.push(
        `/incidents/${incident.id}`,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The incident could not be created.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Create record"
        title="Report a new incident"
        description="Enter the facts manually or extract them from a temporary source document. You review every extracted field before the incident is created."
        actions={
          <Link href="/incidents">
            <Button variant="ghost">
              <ArrowLeft className="size-4" />
              Back
            </Button>
          </Link>
        }
      />

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <button
          type="button"
          onClick={() =>
            changeMode("manual")
          }
          className={`rounded-[18px] border p-5 text-left transition ${
            entryMode === "manual"
              ? "border-[var(--camel)] bg-[var(--ivory)] shadow-[0_10px_35px_rgba(52,38,31,0.06)]"
              : "border-[var(--border)] bg-[#f4ecdf] hover:bg-[var(--ivory)]"
          }`}
        >
          <span className="grid size-11 place-items-center rounded-2xl bg-[var(--camel-soft)] text-[var(--camel-dark)]">
            <PencilLine className="size-5" />
          </span>

          <p className="mt-4 font-semibold">
            Enter manually
          </p>

          <p className="mt-1 text-sm leading-6 text-[var(--taupe)]">
            Best when the responder already
            knows the service, impact, and
            observed symptoms.
          </p>
        </button>

        <button
          type="button"
          onClick={() =>
            changeMode("upload")
          }
          className={`rounded-[18px] border p-5 text-left transition ${
            entryMode === "upload"
              ? "border-[var(--camel)] bg-[var(--ivory)] shadow-[0_10px_35px_rgba(52,38,31,0.06)]"
              : "border-[var(--border)] bg-[#f4ecdf] hover:bg-[var(--ivory)]"
          }`}
        >
          <span className="grid size-11 place-items-center rounded-2xl bg-[#e2eaec] text-[var(--info)]">
            <Upload className="size-5" />
          </span>

          <p className="mt-4 font-semibold">
            Upload a source document
          </p>

          <p className="mt-1 text-sm leading-6 text-[var(--taupe)]">
            Extract from PDF, JSON, CSV,
            TXT, or LOG and retain the
            original privately for 7 or 10
            days.
          </p>
        </button>
      </div>

      {entryMode === "upload" ? (
        <Card className="mb-6 p-6 md:p-8">
          <div className="grid gap-6 lg:grid-cols-[1fr_260px]">
            <div>
              <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-[var(--camel-soft)] text-[var(--camel-dark)]">
                  <FileText className="size-5" />
                </span>

                <div>
                  <h2 className="font-semibold">
                    Temporary source file
                  </h2>

                  <p className="mt-1 text-sm leading-6 text-[var(--taupe)]">
                    Maximum 4 MB. Scanned
                    PDFs without
                    machine-readable text are
                    rejected in this version.
                  </p>
                </div>
              </div>

              <label className="mt-5 flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[#fbf7ef] px-6 py-7 text-center transition hover:border-[var(--camel)]">
                <Upload className="size-6 text-[var(--camel-dark)]" />

                <span className="mt-3 text-sm font-semibold">
                  {selectedFile?.name
                    || "Choose a source document"}
                </span>

                <span className="mt-1 text-xs text-[var(--taupe)]">
                  PDF · JSON · CSV · TXT · LOG
                </span>

                <input
                  type="file"
                  accept=".pdf,.json,.csv,.txt,.log,application/pdf,application/json,text/csv,text/plain"
                  className="sr-only"
                  onChange={(event) => {
                    setSelectedFile(
                      event.target.files?.[0]
                      || null,
                    );
                    setExtraction(null);
                    setError("");
                  }}
                />
              </label>
            </div>

            <div>
              <Label htmlFor="retention">
                Original-file retention
              </Label>

              <Select
                id="retention"
                value={retentionDays}
                onChange={(event) =>
                  setRetentionDays(
                    event.target.value,
                  )
                }
                disabled={!!extraction}
              >
                <option value="7">
                  7 days
                </option>
                <option value="10">
                  10 days
                </option>
              </Select>

              <p className="mt-3 text-xs leading-5 text-[var(--taupe)]">
                A scheduled cleanup removes
                the private original after the
                selected retention period.
                Structured incident data,
                runbook, and audit history
                remain.
              </p>

              <Button
                type="button"
                className="mt-5 w-full"
                onClick={extractUpload}
                disabled={
                  !selectedFile
                  || uploading
                  || !!extraction
                }
              >
                {uploading ? (
                  <>
                    <Spinner />
                    Extracting…
                  </>
                ) : (
                  <>
                    <FileJson2 className="size-4" />
                    Extract and preview
                  </>
                )}
              </Button>
            </div>
          </div>

          {extraction ? (
            <div className="mt-6 grid gap-4 border-t border-[var(--border)] pt-6 lg:grid-cols-[1fr_320px]">
              <div className="rounded-2xl bg-[#edf2ed] p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="success">
                    Extraction ready
                  </Badge>

                  <Badge tone="neutral">
                    {
                      extraction.source_file
                        .file_type_label
                    }
                  </Badge>

                  <span className="text-xs text-[var(--taupe)]">
                    {Math.ceil(
                      extraction.source_file
                        .size_bytes / 1024,
                    )}{" "}
                    KB
                  </span>
                </div>

                <p className="mt-3 font-semibold">
                  {
                    extraction.source_file
                      .original_name
                  }
                </p>

                <p className="mt-1 flex items-center gap-2 text-sm text-[var(--taupe)]">
                  <Clock3 className="size-4" />
                  Available until{" "}
                  {formatDate(
                    extraction.source_file
                      .expires_at,
                  )}
                </p>

                <p className="mt-3 text-xs leading-5 text-[var(--taupe)]">
                  The original is private and
                  scheduled for deletion after
                  its retention period. Review
                  and edit the extracted fields
                  below before submitting.
                </p>
              </div>

              <div className="rounded-2xl bg-[#f8f1e7] p-5">
                <p className="text-sm font-semibold">
                  Extraction summary
                </p>

                <p className="mt-2 text-sm text-[var(--taupe)]">
                  {
                    extraction
                      .information_gaps.length
                  }{" "}
                  information gap
                  {extraction
                    .information_gaps.length
                    === 1
                    ? ""
                    : "s"}{" "}
                  detected
                </p>

                {extraction.warnings.map(
                  (warning) => (
                    <p
                      key={warning}
                      className="mt-2 text-xs leading-5 text-[var(--warning)]"
                    >
                      {warning}
                    </p>
                  ),
                )}
              </div>
            </div>
          ) : null}
        </Card>
      ) : null}

      <form
        onSubmit={submit}
        className="grid gap-6 xl:grid-cols-[1fr_360px]"
      >
        <Card className="p-6 md:p-8">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">
                Incident facts
              </h2>

              <p className="mt-1 text-sm leading-6 text-[var(--taupe)]">
                These values become the source
                of truth. Correct anything
                that extraction misunderstood.
              </p>
            </div>

            {extraction ? (
              <Badge tone="info">
                Editable preview
              </Badge>
            ) : null}
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <div className="md:col-span-2">
              <Label htmlFor="title">
                Incident title
              </Label>

              <Input
                id="title"
                placeholder="e.g. Checkout API returning 502 responses"
                value={form.title}
                onChange={(event) =>
                  update(
                    "title",
                    event.target.value,
                  )
                }
                required
              />
            </div>

            <div>
              <Label htmlFor="service">
                Affected service
              </Label>

              <Input
                id="service"
                placeholder="checkout-api"
                value={form.service_name}
                onChange={(event) =>
                  update(
                    "service_name",
                    event.target.value,
                  )
                }
                required
              />
            </div>

            <div>
              <Label htmlFor="environment">
                Environment
              </Label>

              <Select
                id="environment"
                value={form.environment}
                onChange={(event) =>
                  update(
                    "environment",
                    event.target.value,
                  )
                }
              >
                <option value="production">
                  Production
                </option>

                <option value="staging">
                  Staging
                </option>

                <option value="development">
                  Development
                </option>

                <option value="other">
                  Other / not identified
                </option>
              </Select>
            </div>

            <div className="md:col-span-2">
              <Label htmlFor="description">
                Observed symptoms
              </Label>

              <Textarea
                id="description"
                className="min-h-40"
                placeholder="What changed, when did it begin, what errors are visible, and which users are affected?"
                value={form.description}
                onChange={(event) =>
                  update(
                    "description",
                    event.target.value,
                  )
                }
                required
              />
            </div>

            <div>
              <Label htmlFor="severity">
                Reported severity
              </Label>

              <Select
                id="severity"
                value={
                  form.reported_severity
                }
                onChange={(event) =>
                  update(
                    "reported_severity",
                    event.target.value,
                  )
                }
              >
                <option value="unknown">
                  Unknown
                </option>

                <option value="critical">
                  Critical
                </option>

                <option value="high">
                  High
                </option>

                <option value="medium">
                  Medium
                </option>

                <option value="low">
                  Low
                </option>
              </Select>
            </div>

            <div className="md:col-span-2">
              <Label htmlFor="impact">
                Business impact
              </Label>

              <Textarea
                id="impact"
                placeholder="Describe affected customer journeys, transactions, data, or operational teams."
                value={form.business_impact}
                onChange={(event) =>
                  update(
                    "business_impact",
                    event.target.value,
                  )
                }
              />
            </div>
          </div>

          {error ? (
            <div className="mt-5 rounded-xl bg-[#f2dcd7] p-4 text-sm text-[#8b3e34]">
              {error}
            </div>
          ) : null}

          <div className="mt-7 flex justify-end">
            <Button
              disabled={
                submitting
                || (
                  entryMode === "upload"
                  && !extraction
                )
              }
            >
              {submitting ? (
                <>
                  <Spinner />
                  Creating…
                </>
              ) : (
                <>
                  Create incident
                  <ArrowRight className="size-4" />
                </>
              )}
            </Button>
          </div>
        </Card>

        <div className="space-y-4">
          {extraction?.information_gaps
            .length ? (
            <Card className="p-5">
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-0.5 size-5 shrink-0 text-[var(--warning)]" />

                <div>
                  <p className="font-semibold">
                    Information gaps
                  </p>

                  <p className="mt-1 text-sm leading-6 text-[var(--taupe)]">
                    You may continue. The
                    runbook will explain how
                    to collect every missing
                    item instead of inventing
                    it.
                  </p>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                {extraction.information_gaps.map(
                  (gap) => (
                    <div
                      key={gap.field}
                      className="rounded-xl bg-[#f8f1e7] p-3"
                    >
                      <p className="text-sm font-semibold capitalize">
                        {gap.field.replaceAll(
                          "_",
                          " ",
                        )}
                      </p>

                      <p className="mt-1 text-xs leading-5 text-[var(--taupe)]">
                        {
                          gap.collection_method
                        }
                      </p>
                    </div>
                  ),
                )}
              </div>
            </Card>
          ) : null}

          <Card className="p-5">
            <p className="font-semibold">
              What happens next?
            </p>

            <ol className="mt-4 space-y-4 text-sm leading-6 text-[var(--taupe)]">
              {[
                "The facts are normalised into a consistent schema.",
                "Four agents assess severity, root cause, response actions, and communications.",
                "Missing source information becomes an actionable runbook checklist.",
                "A human reviewer approves, rejects, or requests revision.",
                "The operator records actual actions and verifies recovery.",
              ].map((item, index) => (
                <li
                  key={item}
                  className="flex gap-3"
                >
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-[var(--camel-soft)] text-xs font-bold text-[var(--camel-dark)]">
                    {index + 1}
                  </span>

                  <span>{item}</span>
                </li>
              ))}
            </ol>
          </Card>

          <Card className="p-5">
            <p className="text-sm font-semibold">
              Retention principle
            </p>

            <p className="mt-2 text-sm leading-6 text-[var(--taupe)]">
              Only the original uploaded file is removed after its retention
              period. Extracted facts, information gaps, AI outputs, review
              decisions, resolution evidence, and final reports remain in Neon.
            </p>
          </Card>
        </div>
      </form>
    </>
  );
}