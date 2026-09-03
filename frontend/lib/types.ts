export type UserRole = "admin" | "incident_manager" | "reviewer" | "viewer";

export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  display_name: string;
  role: UserRole;
}

export type IncidentStatus =
  | "draft"
  | "submitted"
  | "triaging"
  | "awaiting_review"
  | "approved"
  | "rejected"
  | "revision_required"
  | "remediation_in_progress"
  | "resolved"
  | "closed"
  | "failed"
  | "reopened";


export interface InformationGap {
  field: string;
  reason_required: string;
  collection_method: string;
  example_command?: string | null;
  blocks_resolution: boolean;
  fallback_action?: string | null;
}

export interface TemporarySourceFile {
  id: string;
  original_name: string;
  content_type: string;
  file_type: "pdf" | "json" | "csv" | "text" | "log";
  file_type_label: string;
  size_bytes: number;
  sha256: string;
  status: string;
  availability: "ready" | "failed" | "expired" | "deleted";
  has_expired: boolean;
  retention_days: number;
  uploaded_at: string;
  expires_at: string;
  deleted_at: string | null;
  extracted_fields: Record<string, unknown>;
  extracted_context: Record<string, unknown>;
  information_gaps: InformationGap[];
  extraction_error: string;
}

export interface UploadExtractionResponse {
  source_file: TemporarySourceFile;
  fields: Partial<{
    title: string;
    description: string;
    service_name: string;
    environment: string;
    reported_severity: string;
    business_impact: string;
    started_at: string;
  }>;
  extracted_context: Record<string, unknown>;
  information_gaps: InformationGap[];
  warnings: string[];
}

export interface InvestigationResult {
  observations: string[];
  tools_used: string[];
  leading_hypothesis: string;
  supporting_evidence: string[];
  missing_evidence: string[];
  confidence: number;
}

export interface Workflow {
  current_stage: string;
  progress_percent: number;
  normalized_data: Record<string, unknown> | null;
  severity_output: Record<string, unknown> | null;
  investigation_output: InvestigationResult | null;
  root_cause_output: Record<string, unknown> | null;
  runbook_output: Record<string, unknown> | null;
  summary_output: Record<string, unknown> | null;
  overall_confidence: number | null;
  processing_time_seconds: number;
  active_model: string;
  is_processing: boolean;
  failure_reason: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface AgentToolExecution {
  id: number;
  sequence: number;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
  status: "started" | "success" | "failed";
  execution_mode?: "live" | "mock" | "fallback";
  latency_ms: number | null;
  error_message: string;
  created_at: string;
}

export interface AgentExecution {
  id: number;
  stage: string;
  stage_label: string;
  status: string;
  execution_mode: "live" | "mock" | "fallback";
  model_name: string;
  output: Record<string, unknown>;
  confidence: number | null;
  latency_ms: number | null;
  retry_count: number;
  error_message: string;
  tool_executions: AgentToolExecution[];
  created_at: string;
}

export interface Review {
  id: number;
  decision: string;
  reviewer_note: string;
  overrides: Record<string, unknown>;
  reviewer: User;
  decided_at: string;
}

export interface ResolutionAction {
  id?: number;
  order: number;
  action: string;
  result: string;
  performed_by: string;
  performed_at?: string | null;
}

export interface Resolution {
  id: number;
  resolution_summary: string;
  confirmed_root_cause: string;
  root_cause_confirmed: boolean;
  verification_notes: string;
  resolved_by: User;
  started_at: string;
  resolved_at: string | null;
  actions: ResolutionAction[];
}

export interface StatusEvent {
  id: number;
  previous_status: string;
  new_status: string;
  note: string;
  changed_by: User | null;
  created_at: string;
}

export interface IncidentSummary {
  id: string;
  reference: string;
  title: string;
  service_name: string;
  environment: string;
  reported_severity: string;
  predicted_severity: string | null;
  status: IncidentStatus;
  status_label: string;
  overall_confidence: number | null;
  submitted_at: string;
  updated_at: string;
}

export interface IncidentDetail extends IncidentSummary {
  description: string;
  source: string;
  business_impact: string;
  extracted_context: Record<string, unknown>;
  information_gaps: InformationGap[];
  source_file: TemporarySourceFile | null;
  submitted_by: User | null;
  resolved_at: string | null;
  reopened_count: number;
  workflow: Workflow;
  agent_executions: AgentExecution[];
  reviews: Review[];
  resolution: Resolution | null;
  status_events: StatusEvent[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DashboardData {
  total: number;
  open: number;
  awaiting_review: number;
  critical: number;
  resolved: number;
  average_confidence: number;
  severity_counts: Record<string, number>;
  recent_incidents: IncidentSummary[];
}


export interface RunbookCase {
  id: string;
  name: string;
  category: string;
  problem: string;
  keywords: string[];
  severity_applicability: string[];
  diagnostic_steps: string[];
  solution_steps: string[];
  verification_steps: string[];
  rollback_plan: string[];
  escalation_triggers: string[];
  caution: string;
  missing_information: string[];
}

export interface RunbookLibraryData {
  count: number;
  total: number;
  categories: string[];
  results: RunbookCase[];
}
