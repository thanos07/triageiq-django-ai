from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

CREAM = colors.HexColor("#F6F1E7")
IVORY = colors.HexColor("#FFFDF8")
CAMEL = colors.HexColor("#B9855A")
ESPRESSO = colors.HexColor("#29231F")
TAUPE = colors.HexColor("#74685E")
BORDER = colors.HexColor("#DED1C1")
GREEN = colors.HexColor("#54705A")
RED = colors.HexColor("#9D463A")


def safe(value: Any) -> str:
    if value is None or value == "":
        return "Not available"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return escape(str(value))


def friendly_key(value: str) -> str:
    return value.replace("_", " ").strip().title()


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(TAUPE)
    canvas.drawString(18 * mm, 12 * mm, f"{settings.REPORT_BRAND_NAME} · Incident Resolution Report")
    canvas.drawRightString(192 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="BrandTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        textColor=ESPRESSO,
        alignment=TA_CENTER,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubTitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=TAUPE,
        alignment=TA_CENTER,
        spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="Section",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=ESPRESSO,
        spaceBefore=10,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="SubSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=CAMEL,
        spaceBefore=8,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="BodyWarm",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        textColor=ESPRESSO,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="SmallWarm",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
        textColor=TAUPE,
    ))
    return styles


def details_table(rows, styles):
    data = [[Paragraph(f"<b>{safe(label)}</b>", styles["BodyWarm"]), Paragraph(safe(value), styles["BodyWarm"])] for label, value in rows]
    table = Table(data, colWidths=(46 * mm, 126 * mm), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), CREAM),
        ("BACKGROUND", (1, 0), (1, -1), IVORY),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def json_section(title: str, data: dict[str, Any] | None, styles):
    elements = [Paragraph(title, styles["SubSection"])]
    if not data:
        elements.append(Paragraph("No result is available for this stage.", styles["BodyWarm"]))
        return elements
    for key, value in data.items():
        if isinstance(value, list):
            elements.append(Paragraph(f"<b>{friendly_key(key)}</b>", styles["BodyWarm"]))
            if value and isinstance(value[0], dict):
                for item in value:
                    text = " · ".join(f"<b>{friendly_key(str(k))}:</b> {safe(v)}" for k, v in item.items())
                    elements.append(Paragraph(f"• {text}", styles["BodyWarm"]))
            else:
                for item in value:
                    elements.append(Paragraph(f"• {safe(item)}", styles["BodyWarm"]))
        elif isinstance(value, dict):
            elements.append(Paragraph(f"<b>{friendly_key(key)}</b>", styles["BodyWarm"]))
            for child_key, child_value in value.items():
                elements.append(Paragraph(f"• <b>{friendly_key(str(child_key))}:</b> {safe(child_value)}", styles["BodyWarm"]))
        else:
            elements.append(Paragraph(f"<b>{friendly_key(key)}:</b> {safe(value)}", styles["BodyWarm"]))
    return elements


def build_incident_pdf(incident, *, draft: bool = False) -> io.BytesIO:
    styles = build_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"{incident.reference} Incident Resolution Report",
        author=settings.REPORT_BRAND_NAME,
    )
    story = [
        Paragraph(settings.REPORT_BRAND_NAME, styles["BrandTitle"]),
        Paragraph(
            f"{'Draft AI Triage Report' if draft else 'Final Incident Resolution Report'} · {incident.reference}",
            styles["ReportSubTitle"],
        ),
    ]

    status_color = GREEN if incident.status in {"resolved", "closed"} else CAMEL
    status = Table([[Paragraph(f"<b>{incident.get_status_display()}</b>", styles["BodyWarm"]) ]], colWidths=(172 * mm,))
    status.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), status_color),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [status, Spacer(1, 8 * mm)]

    story += [
        Paragraph("1. Incident details", styles["Section"]),
        details_table([
            ("Incident", incident.reference),
            ("Title", incident.title),
            ("Service", incident.service_name),
            ("Environment", incident.get_environment_display()),
            ("Reported severity", incident.get_reported_severity_display()),
            ("Submitted by", safe(incident.submitted_by)),
            ("Submitted at", incident.submitted_at.isoformat()),
            ("Description", incident.description),
            ("Business impact", incident.business_impact),
            ("Source type", incident.source),
        ], styles),
        Spacer(1, 5 * mm),
    ]

    source_file = incident.temporary_files.first()
    if source_file:
        story += [
            Paragraph("Temporary source document", styles["SubSection"]),
            details_table([
                ("Original name", source_file.original_name),
                ("File type", source_file.get_file_type_display()),
                ("Retention", f"{source_file.retention_days} days"),
                ("Uploaded at", source_file.uploaded_at.isoformat()),
                ("Expires at", source_file.expires_at.isoformat()),
                ("Availability", source_file.availability),
                ("SHA-256", source_file.sha256),
            ], styles),
            Paragraph(
                "The original source document is temporary. Extracted incident facts and information gaps remain in the incident record after the file expires.",
                styles["SmallWarm"],
            ),
            Spacer(1, 4 * mm),
        ]

    if incident.information_gaps:
        story.append(Paragraph("Information gaps from source extraction", styles["SubSection"]))
        for gap in incident.information_gaps:
            if isinstance(gap, dict):
                story.append(Paragraph(
                    f"• <b>{friendly_key(str(gap.get('field', 'unknown')))}:</b> "
                    f"{safe(gap.get('reason_required'))}<br/>"
                    f"Collection: {safe(gap.get('collection_method'))}",
                    styles["BodyWarm"],
                ))
        story.append(Spacer(1, 4 * mm))

    workflow = getattr(incident, "workflow", None)
    story.append(Paragraph("2. AI-assisted triage", styles["Section"]))
    if workflow:
        story += json_section("Normalized incident", workflow.normalized_data, styles)
        story += json_section("Severity agent", workflow.severity_output, styles)
        story += json_section("Root-cause agent", workflow.root_cause_output, styles)
        story += json_section("Runbook agent", workflow.runbook_output, styles)
        story += json_section("Communication agent", workflow.summary_output, styles)
        story.append(details_table([
            ("Overall confidence", f"{(workflow.overall_confidence or 0) * 100:.1f}%"),
            ("Processing time", f"{workflow.processing_time_seconds:.2f} seconds"),
            ("Last model", workflow.active_model),
        ], styles))
    else:
        story.append(Paragraph("The AI workflow has not started.", styles["BodyWarm"]))

    story += [PageBreak(), Paragraph("3. Human review", styles["Section"])]
    reviews = list(incident.reviews.select_related("reviewer").all())
    if reviews:
        for review in reviews:
            story.append(KeepTogether([
                Paragraph(f"<b>{review.get_decision_display()}</b> · {safe(review.reviewer)}", styles["BodyWarm"]),
                Paragraph(safe(review.reviewer_note), styles["BodyWarm"]),
                Paragraph(review.decided_at.isoformat(), styles["SmallWarm"]),
                Spacer(1, 3 * mm),
            ]))
    else:
        story.append(Paragraph("No human review has been recorded.", styles["BodyWarm"]))

    story.append(Paragraph("4. Actual resolution", styles["Section"]))
    try:
        resolution = incident.resolution
    except Exception:
        resolution = None
    if resolution:
        story.append(details_table([
            ("Resolution summary", resolution.resolution_summary),
            ("Confirmed root cause", resolution.confirmed_root_cause),
            ("AI root cause confirmed", resolution.root_cause_confirmed),
            ("Verification notes", resolution.verification_notes),
            ("Resolved by", resolution.resolved_by),
            ("Resolved at", safe(resolution.resolved_at)),
        ], styles))
        story.append(Paragraph("Actions performed", styles["SubSection"]))
        for action in resolution.actions.all():
            story.append(Paragraph(
                f"<b>{action.order}. {safe(action.action)}</b><br/>Result: {safe(action.result)}<br/>Performed by: {safe(action.performed_by)}",
                styles["BodyWarm"],
            ))
    else:
        story.append(Paragraph("This incident has not yet been resolved.", styles["BodyWarm"]))

    story.append(Paragraph("5. Incident timeline", styles["Section"]))
    events = incident.status_events.select_related("changed_by").all()
    if events:
        timeline_data = [["Time", "Status", "Note", "Changed by"]]
        for event in events:
            timeline_data.append([
                event.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                friendly_key(event.new_status),
                event.note,
                safe(event.changed_by),
            ])
        timeline = Table(timeline_data, colWidths=(34 * mm, 35 * mm, 73 * mm, 30 * mm), repeatRows=1)
        timeline.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ESPRESSO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("LEADING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(timeline)

    story += [
        Spacer(1, 7 * mm),
        Paragraph(
            "AI outputs in this report are decision-support recommendations. A human reviewer remains accountable for approval, remediation, and closure.",
            styles["SmallWarm"],
        ),
        Paragraph(f"Generated at {datetime.now(timezone.utc).isoformat()}Z", styles["SmallWarm"]),
    ]

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    return buffer
