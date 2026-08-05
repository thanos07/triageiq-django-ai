from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from pypdf import PdfReader

from .temporary_storage import storage


class UploadExtractionError(ValueError):
    """Safe validation error for a source document upload."""


ALLOWED_EXTENSIONS = {".pdf", ".json", ".csv", ".txt", ".log"}
FILE_TYPE_BY_EXTENSION = {
    ".pdf": "pdf",
    ".json": "json",
    ".csv": "csv",
    ".txt": "text",
    ".log": "log",
}
FIELD_ALIASES = {
    "title": ("title", "incident_title", "subject", "summary", "incident"),
    "description": ("description", "details", "body", "message", "symptoms", "observed_symptoms"),
    "service_name": ("service_name", "service", "application", "component", "affected_service"),
    "environment": ("environment", "env", "stage"),
    "reported_severity": ("reported_severity", "severity", "priority", "impact_level"),
    "business_impact": ("business_impact", "impact", "customer_impact", "user_impact"),
    "started_at": ("started_at", "start_time", "incident_start", "timestamp", "detected_at"),
}
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)authorization:\s*bearer\s+[^\s]+"),
]


@dataclass(slots=True)
class ExtractionResult:
    file_type: str
    fields: dict[str, Any]
    extracted_context: dict[str, Any]
    information_gaps: list[dict[str, Any]]
    warnings: list[str]
    text_excerpt: str


def _clean_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return " ".join(str(value).split())


def _normalise_environment(value: str) -> str:
    candidate = value.strip().lower()
    mapping = {
        "prod": "production",
        "production": "production",
        "live": "production",
        "stage": "staging",
        "staging": "staging",
        "test": "staging",
        "dev": "development",
        "development": "development",
        "local": "development",
    }
    return mapping.get(candidate, "other" if candidate else "")


def _normalise_severity(value: str) -> str:
    candidate = value.strip().lower()
    mapping = {
        "sev0": "critical", "sev-0": "critical", "p0": "critical", "critical": "critical",
        "sev1": "high", "sev-1": "high", "p1": "high", "high": "high", "major": "high",
        "sev2": "medium", "sev-2": "medium", "p2": "medium", "medium": "medium", "moderate": "medium",
        "sev3": "low", "sev-3": "low", "p3": "low", "low": "low", "minor": "low",
    }
    return mapping.get(candidate, "unknown" if candidate else "")


def _extract_from_mapping(data: dict[str, Any]) -> dict[str, Any]:
    normalised = {_clean_key(str(key)): value for key, value in data.items()}
    fields: dict[str, Any] = {}
    for destination, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in normalised and normalised[alias] not in (None, "", [], {}):
                fields[destination] = _string(normalised[alias])
                break
    if fields.get("environment"):
        fields["environment"] = _normalise_environment(fields["environment"])
    if fields.get("reported_severity"):
        fields["reported_severity"] = _normalise_severity(fields["reported_severity"])
    return fields


def _redact(text: str) -> str:
    safe = text
    for pattern in SECRET_PATTERNS:
        safe = pattern.sub(lambda match: f"{match.group(1) if match.lastindex and match.lastindex > 1 else 'authorization'}: [REDACTED]", safe)
    return safe


def _labelled_value(text: str, labels: tuple[str, ...]) -> str:
    for label in labels:
        match = re.search(rf"(?im)^\s*{re.escape(label)}\s*[:=-]\s*(.+)$", text)
        if match:
            return " ".join(match.group(1).strip().split())
    return ""


def _extract_from_text(text: str, *, filename: str) -> tuple[dict[str, Any], dict[str, Any]]:
    clean = _redact(text).replace("\x00", "")
    lines = [" ".join(line.split()) for line in clean.splitlines() if line.strip()]
    title = _labelled_value(clean, ("title", "incident", "summary", "subject"))
    if not title and lines:
        title = lines[0][:240]

    description = _labelled_value(clean, ("description", "details", "symptoms", "issue"))
    if not description:
        description = " ".join(lines[:24])[:5000]

    service = _labelled_value(clean, ("service", "service name", "application", "component"))
    environment = _normalise_environment(_labelled_value(clean, ("environment", "env", "stage")))
    severity = _normalise_severity(_labelled_value(clean, ("severity", "priority", "impact level")))
    impact = _labelled_value(clean, ("business impact", "customer impact", "impact", "user impact"))

    timestamps = list(dict.fromkeys(re.findall(r"\b\d{4}-\d{2}-\d{2}[T ][0-9:.+-Z]+", clean)))[:20]
    status_codes = list(dict.fromkeys(re.findall(r"\b[1-5]\d{2}\b", clean)))[:20]
    hosts = list(dict.fromkeys(re.findall(r"\b[a-zA-Z0-9][a-zA-Z0-9.-]{2,}\.(?:internal|local|com|net|io)\b", clean)))[:20]
    error_lines = [line for line in lines if re.search(r"(?i)\b(error|fatal|exception|failed|timeout|unavailable)\b", line)][:50]

    fields = {
        "title": title,
        "description": description,
        "service_name": service,
        "environment": environment,
        "reported_severity": severity,
        "business_impact": impact,
    }
    context = {
        "source_filename": filename,
        "detected_timestamps": timestamps,
        "detected_status_codes": status_codes,
        "detected_hosts": hosts,
        "error_evidence": error_lines,
        "character_count": len(clean),
    }
    return {key: value for key, value in fields.items() if value}, context


def _information_gaps(fields: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    definitions = {
        "title": ("A clear incident title is required for ownership and search.", "Enter a concise summary of the observed failure."),
        "description": ("Observed symptoms are required before a safe diagnosis can be attempted.", "Add errors, behaviour changes, timing, and affected user journeys."),
        "service_name": ("The affected service is needed to select service-specific checks.", "Identify the application, API, job, database, or dependency involved."),
        "environment": ("Environment changes the risk and severity of any response action.", "Confirm whether this is production, staging, development, or another environment."),
        "reported_severity": ("Reported priority helps compare the AI classification with the responder's view.", "Provide the initial severity when known; otherwise leave it unknown."),
        "business_impact": ("Business impact is required for escalation and severity validation.", "Estimate affected users, transactions, regions, or internal teams."),
    }
    gaps = []
    for field, (reason, collection) in definitions.items():
        if not fields.get(field):
            gaps.append({
                "field": field,
                "reason_required": reason,
                "collection_method": collection,
                "blocks_resolution": field in {"description", "service_name"},
                "fallback_action": "Continue only with reversible diagnostics and record uncertainty." if field != "title" else "Use a temporary factual title and revise it after confirmation.",
            })
    if not context.get("detected_timestamps"):
        gaps.append({
            "field": "incident_start_time",
            "reason_required": "Timing is needed to correlate the incident with deployments, alerts, and configuration changes.",
            "collection_method": "Check monitoring alerts, deployment history, and the earliest matching log event.",
            "blocks_resolution": False,
            "fallback_action": "Use the earliest confirmed observation time and label it as approximate.",
        })
    if not context.get("error_evidence"):
        gaps.append({
            "field": "diagnostic_evidence",
            "reason_required": "Logs, traces, metrics, or error messages are needed to validate a root-cause hypothesis.",
            "collection_method": "Collect ERROR/FATAL log lines, recent traces, saturation metrics, and dependency health around the incident window.",
            "blocks_resolution": False,
            "fallback_action": "Avoid irreversible remediation and begin with health checks and telemetry collection.",
        })
    return gaps


def _parse_pdf(payload: bytes, filename: str) -> tuple[str, dict[str, Any], list[str]]:
    try:
        reader = PdfReader(io.BytesIO(payload))
    except Exception as exc:
        raise UploadExtractionError("The PDF could not be read or may be corrupted.") from exc
    if len(reader.pages) > settings.TEMP_UPLOAD_MAX_PDF_PAGES:
        raise UploadExtractionError(
            f"PDFs are limited to {settings.TEMP_UPLOAD_MAX_PDF_PAGES} pages for the free deployment."
        )
    page_text = []
    for page in reader.pages:
        page_text.append(page.extract_text() or "")
    text = "\n".join(page_text).strip()
    if not text:
        raise UploadExtractionError(
            "No machine-readable text was found. Upload a text-based PDF or paste the incident details manually."
        )
    return text, {"pdf_page_count": len(reader.pages)}, []


def _parse_json(payload: bytes) -> tuple[dict[str, Any], dict[str, Any], list[str], str]:
    try:
        decoded = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UploadExtractionError("The JSON file is not valid UTF-8 JSON.") from exc
    warnings: list[str] = []
    context: dict[str, Any] = {}
    if isinstance(decoded, list):
        if not decoded or not isinstance(decoded[0], dict):
            raise UploadExtractionError("A JSON array must contain incident objects.")
        context["record_count"] = len(decoded)
        if len(decoded) > 1:
            warnings.append(f"The JSON array contains {len(decoded)} records; this preview uses the first incident.")
        decoded = decoded[0]
    if not isinstance(decoded, dict):
        raise UploadExtractionError("The JSON root must be an object or an array of objects.")
    fields = _extract_from_mapping(decoded)
    context["unmapped_fields"] = sorted(set(map(str, decoded.keys())) - {
        alias for aliases in FIELD_ALIASES.values() for alias in aliases
    })[:30]
    return fields, context, warnings, json.dumps(decoded, ensure_ascii=False, indent=2)[:15000]


def _parse_csv(payload: bytes) -> tuple[dict[str, Any], dict[str, Any], list[str], str]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadExtractionError("The CSV file must use UTF-8 encoding.") from exc
    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader if any(value not in (None, "") for value in row.values())]
    if not rows:
        raise UploadExtractionError("The CSV file contains no incident rows.")
    warnings = []
    if len(rows) > 1:
        warnings.append(f"The CSV contains {len(rows)} rows; this preview uses the first incident.")
    fields = _extract_from_mapping(rows[0])
    return fields, {"record_count": len(rows), "columns": reader.fieldnames or []}, warnings, text[:15000]


def extract_from_bytes(*, payload: bytes, filename: str, content_type: str = "") -> ExtractionResult:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UploadExtractionError("Supported files are PDF, JSON, CSV, TXT, and LOG.")
    file_type = FILE_TYPE_BY_EXTENSION[suffix]
    warnings: list[str] = []

    if suffix == ".pdf":
        if not payload.startswith(b"%PDF-"):
            raise UploadExtractionError("The uploaded file does not have a valid PDF signature.")
        text, extra_context, warnings = _parse_pdf(payload, filename)
        fields, text_context = _extract_from_text(text, filename=filename)
        context = {**extra_context, **text_context}
    elif suffix == ".json":
        fields, context, warnings, text = _parse_json(payload)
    elif suffix == ".csv":
        fields, context, warnings, text = _parse_csv(payload)
    else:
        if b"\x00" in payload[:2048]:
            raise UploadExtractionError("Binary files are not accepted as TXT or LOG input.")
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UploadExtractionError("TXT and LOG files must use UTF-8 encoding.") from exc
        if suffix == ".log":
            lines = text.splitlines()[: settings.TEMP_UPLOAD_MAX_LOG_LINES]
            if len(text.splitlines()) > settings.TEMP_UPLOAD_MAX_LOG_LINES:
                warnings.append(
                    f"Only the first {settings.TEMP_UPLOAD_MAX_LOG_LINES} log lines were processed."
                )
            relevant = [
                line for line in lines
                if re.search(r"(?i)\b(error|fatal|exception|failed|warn|timeout|unavailable|5\d\d)\b", line)
            ]
            text = "\n".join(relevant or lines)
        fields, context = _extract_from_text(text, filename=filename)

    safe_excerpt = _redact(text)[: settings.TEMP_UPLOAD_MAX_EXTRACTED_CHARS]
    context["content_type"] = content_type
    context["file_type"] = file_type
    context["warnings"] = warnings
    gaps = _information_gaps(fields, context)
    return ExtractionResult(
        file_type=file_type,
        fields=fields,
        extracted_context=context,
        information_gaps=gaps,
        warnings=warnings,
        text_excerpt=safe_excerpt,
    )


def process_uploaded_file(uploaded_file: UploadedFile, *, retention_days: int) -> tuple[ExtractionResult, dict[str, Any]]:
    if retention_days not in settings.TEMP_UPLOAD_RETENTION_CHOICES:
        raise UploadExtractionError("Retention must be either 7 or 10 days.")
    if uploaded_file.size > settings.TEMP_UPLOAD_MAX_BYTES:
        max_mb = settings.TEMP_UPLOAD_MAX_BYTES // (1024 * 1024)
        raise UploadExtractionError(f"The maximum source file size is {max_mb} MB.")

    payload = uploaded_file.read()
    result = extract_from_bytes(
        payload=payload,
        filename=uploaded_file.name,
        content_type=uploaded_file.content_type or "",
    )
    digest = hashlib.sha256(payload).hexdigest()
    suffix = Path(uploaded_file.name).suffix.lower()
    key = f"temporary-incidents/{retention_days}-days/{uuid.uuid4().hex}{suffix}"
    storage.put(
        key=key,
        payload=payload,
        content_type=uploaded_file.content_type or "application/octet-stream",
        metadata={
            "sha256": digest,
            "retention-days": str(retention_days),
        },
    )
    metadata = {
        "storage_key": key,
        "original_name": Path(uploaded_file.name).name[:255],
        "content_type": uploaded_file.content_type or "application/octet-stream",
        "size_bytes": len(payload),
        "sha256": digest,
        "retention_days": retention_days,
    }
    return result, metadata
