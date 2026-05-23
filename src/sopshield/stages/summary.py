"""Stage 4 — structured end-of-session summary for human operators."""

from __future__ import annotations

import re

from sopshield.escalation import handoff_note_deterministic
from sopshield.prompts import SUMMARY_USER_TEMPLATE, summary_system
from sopshield.providers.base import LLMProvider
from sopshield.session import Session
from sopshield.sop.loader import SOPDocument
from sopshield.stages.qualification import detect_service

_INTENT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bhours?\b", re.I), "Hours / schedule"),
    (re.compile(r"\bbook|appointment|schedule\b", re.I), "Booking / appointment"),
    (re.compile(r"\bcancel|reschedul", re.I), "Cancel or reschedule"),
    (re.compile(r"\bprice|cost|fee|insurance\b", re.I), "Pricing / billing"),
    (re.compile(r"\bcomplain|refund|furious|ridiculous|frustrated\b", re.I), "Complaint — needs human"),
]

_REASON_SHORT: dict[str, str] = {
    "explicit_escalation": "Asked for a person or manager",
    "angry_sentiment": "Upset or frustrated tone",
    "complaint": "Complaint / billing language",
    "pricing_negotiation": "Discount or competitor price pressure",
    "sensitive_unsupported": "Clinical/safety — not in front-desk SOP",
    "out_of_scope": "Outside clinic SOP scope",
    "low_confidence": "Weak SOP match — verify before replying",
    "sop_gap": "SOP has no answer for this",
    "repeated_unanswered": "Two+ unanswered questions in a row",
}


def generate_summary(
    session: Session,
    sop: SOPDocument,
    provider: LLMProvider,
) -> str:
    """Optional LLM summary — escalation decisions are never delegated to the model."""
    esc_lines = _format_escalation_lines(session)
    qual_lines = _format_qualification_lines(session)
    gaps = "\n".join(f"- {g}" for g in session.sop_gaps) or "(none)"
    unanswered = "\n".join(f"- {q}" for q in session.unanswered_questions) or "(none)"

    user_prompt = SUMMARY_USER_TEMPLATE.format(
        transcript=session.transcript_text(),
        qualification=qual_lines,
        escalations=esc_lines,
        sop_gaps=gaps,
        unanswered=unanswered,
    )
    response = provider.complete(summary_system(sop), user_prompt)
    return response.text


def format_summary_deterministic(session: Session, sop: SOPDocument) -> str:
    """Structured handoff summary — always available without an API."""
    intent = infer_customer_intent(session, sop)
    details = format_collected_details(session, sop)
    unanswered = format_unanswered(session)
    gaps = format_sop_gaps(session)
    escalation = format_escalation_section(session, sop)
    next_action = recommend_next_action(session, sop)

    return f"""## Session Summary — {sop.business_name}

### 1. Customer intent
{intent}

### 2. Collected details
{details}

### 3. Unanswered or unsupported questions
{unanswered}

### 4. SOP gaps
{gaps}

### 5. Escalation reason
{escalation}

### 6. Recommended next action
{next_action}
"""


def explain_handoff(
    session: Session,
    sop: SOPDocument,
    provider: LLMProvider | None = None,
) -> str:
    """
    Short operator note after escalation.
    Deterministic by default; optional provider only elaborates the handoff.
    """
    if not session.escalation.events:
        return ""
    event = session.escalation.events[-1]
    if provider is None:
        return handoff_note_deterministic(event, sop)

    from sopshield.prompts import HANDOFF_EXPLAIN_SYSTEM, HANDOFF_EXPLAIN_USER

    user = HANDOFF_EXPLAIN_USER.format(
        reason=event.reason.value,
        detail=event.detail,
        message=event.user_message[:500],
    )
    try:
        response = provider.complete(HANDOFF_EXPLAIN_SYSTEM, user)
        text = response.text.strip()
        if text:
            return text
    except Exception:
        pass
    return handoff_note_deterministic(event, sop)


def infer_customer_intent(session: Session, sop: SOPDocument) -> str:
    user_msgs = [t.content for t in session.turns if t.role == "user"]
    if not user_msgs:
        return "No customer messages on file."

    if session.qualification_state.service_interest:
        svc = session.qualification_state.service_interest
        return f"{svc} — follow-up / booking."

    combined = " ".join(user_msgs[:3])
    for pattern, label in _INTENT_PATTERNS:
        if pattern.search(combined):
            if session.escalation.escalated and re.search(
                r"\b(furious|angry|complain|refund|frustrated|ridiculous)\b",
                combined,
                re.I,
            ):
                return f"{label}; needs callback."
            return label

    first = user_msgs[0][:120].strip()
    if len(first) < len(user_msgs[0]):
        first += "…"
    return f"Asked: {first}"


def format_collected_details(session: Session, sop: SOPDocument) -> str:
    state = session.qualification_state
    if state.service_interest or state.client_status or state.contact:
        lines = [f"  - {state.compact_summary()}"]
        if state.service_detail:
            lines.append(f"  - Extra: {state.service_detail}")
        return "\n".join(lines)
    if not session.qualification:
        for msg in session.user_messages():
            svc = detect_service(msg, sop)
            if svc:
                return f"  - Mentioned only: {svc} (not qualified)"
        return "  - None."
    lines = []
    for q in session.qualification:
        label = q.field.replace("_", " ").title() if q.field else q.question[:40]
        lines.append(f"  - {label}: {q.answer}")
    return "\n".join(lines)


def format_unanswered(session: Session) -> str:
    if not session.unanswered_questions:
        return "  - None."
    return "\n".join(f"  - {q}" for q in session.unanswered_questions)


def format_sop_gaps(session: Session) -> str:
    if not session.sop_gaps:
        return "  - None."
    return "\n".join(f"  - {g}" for g in session.sop_gaps)


def format_escalation_section(session: Session, sop: SOPDocument) -> str:
    if not session.escalation.escalated or not session.escalation.events:
        return "None."

    lines = []
    for e in session.escalation.events:
        label = _REASON_SHORT.get(e.reason.value, e.detail)
        lines.append(f"  - {e.reason.value}: {label}")
    if session.handoff_note:
        note = _strip_handoff_reason_suffix(session.handoff_note)
        lines.append(f"  - Note: {note}")
    return "\n".join(lines)


def recommend_next_action(session: Session, sop: SOPDocument) -> str:
    if not session.escalation.escalated:
        state = session.qualification_state
        if state.completed and state.contact:
            return (
                f"Callback {state.contact} within 1 business day; "
                "send booking link per SOP."
            )
        return "Send booking link per SOP if they're ready to schedule."

    last = session.escalation.events[-1]
    sop_action = _sop_next_action(last.reason.value, sop)
    if sop_action:
        return sop_action

    actions = {
        "explicit_escalation": "Assign agent — call or email within 4 business hours.",
        "angry_sentiment": "Same-day callback; acknowledge frustration first.",
        "complaint": "Open complaint ticket; billing/supervisor before clinical talk.",
        "pricing_negotiation": "Share published pricing only — no chat discounts.",
        "sensitive_unsupported": "Route to clinical staff — don't answer in chat.",
        "out_of_scope": "Clarify what the clinic offers; stay in scope.",
        "low_confidence": "Check SOP/KB, then reply with verified info.",
        "sop_gap": "Answer on callback; flag for SOP update.",
        "repeated_unanswered": "Phone intake for open items; update SOP if repeat.",
    }
    return actions.get(last.reason.value, "Human follow-up within 1 business day.")


def _sop_next_action(reason: str, sop: SOPDocument) -> str | None:
    """Use SOP handoff_notes when they read like an action (not a label)."""
    note = sop.escalation.handoff_notes.get(reason, "").strip()
    if not note:
        return None
    if note.endswith("."):
        return note
    return f"{note}."


def _strip_handoff_reason_suffix(handoff_note: str) -> str:
    """Drop trailing '(reason_code)' from operator notes in summaries."""
    if handoff_note.endswith(")") and " (" in handoff_note:
        return handoff_note.rsplit(" (", 1)[0]
    return handoff_note


def _format_escalation_lines(session: Session) -> str:
    if not session.escalation.events:
        return "(none)"
    return "\n".join(
        f"- {e.reason.value}: {e.detail}" for e in session.escalation.events
    )


def _format_qualification_lines(session: Session) -> str:
    if not session.qualification:
        return "(none collected)"
    return "\n".join(
        f"- Q: {q.question}\n  A: {q.answer}" for q in session.qualification
    )
