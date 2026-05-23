"""Lightweight required-field checks for SOP payloads."""

from __future__ import annotations

from pathlib import Path

from sopshield.sop.loader import SOPDocument


class SOPValidationError(ValueError):
    """Raised when a SOP file is missing fields required for the workflow."""

    def __init__(self, path: Path | str, issues: list[str]) -> None:
        self.path = Path(path)
        self.issues = issues
        detail = "; ".join(issues)
        super().__init__(f"SOP validation failed for {self.path.name}: {detail}")

    def message(self) -> str:
        lines = [f"SOP file is incomplete: {self.path}", ""]
        lines.extend(f"  - {issue}" for issue in self.issues)
        lines.append("")
        lines.append(
            "Required: business_name, services (qualification.services or a "
            "'services' section), escalation_rules (escalation config or "
            "'escalation' section), booking_policy ('booking' section with content)."
        )
        return "\n".join(lines)


def validate_sop_document(doc: SOPDocument) -> list[str]:
    """Return human-readable issue strings; empty list means valid."""
    issues: list[str] = []

    if not doc.business_name.strip():
        issues.append(
            "business_name: set document.business_name in JSON or a level-1 title in Markdown"
        )

    services_section = doc.section_by_id("services")
    has_qual_services = bool(doc.qualification.services)
    has_services_section = services_section is not None and bool(
        services_section.body.strip()
    )
    if not has_qual_services and not has_services_section:
        issues.append(
            "services: add qualification.services and/or a section with id 'services'"
        )
    elif services_section is not None and not services_section.body.strip():
        issues.append("services: section 'services' has an empty body")

    escalation_section = doc.section_by_id("escalation")
    esc = doc.escalation
    has_escalation_section = escalation_section is not None and bool(
        escalation_section.body.strip()
    )
    has_escalation_config = bool(esc.out_of_scope_patterns) or bool(
        esc.sensitive_patterns
    ) or bool(esc.handoff_notes)
    if not has_escalation_section and not has_escalation_config:
        issues.append(
            "escalation_rules: add an 'escalation' section and/or escalation "
            "patterns (out_of_scope_patterns, sensitive_patterns, handoff_notes)"
        )
    elif escalation_section is not None and not escalation_section.body.strip():
        issues.append("escalation_rules: section 'escalation' has an empty body")

    booking = doc.section_by_id("booking")
    if booking is None:
        issues.append(
            "booking_policy: add a section with id 'booking' (booking and appointments)"
        )
    elif not booking.body.strip():
        issues.append("booking_policy: section 'booking' has an empty body")

    if not doc.sections:
        issues.append("sections: at least one retrievable section is required")

    return issues


def ensure_valid_sop(doc: SOPDocument) -> None:
    issues = validate_sop_document(doc)
    if issues:
        raise SOPValidationError(doc.path, issues)
