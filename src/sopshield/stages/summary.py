"""Stage 4 — structured end-of-session summary for human operators."""

from __future__ import annotations

import re

from sopshield.escalation import handoff_note_deterministic
from sopshield.prompts import SUMMARY_SYSTEM, SUMMARY_USER_TEMPLATE
from sopshield.providers.base import LLMProvider
from sopshield.session import Session
from sopshield.stages.qualification import detect_service

_INTENT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bhours?\b", re.I), "Clinic hours / scheduling"),
    (re.compile(r"\bbook|appointment|schedule\b", re.I), "Booking or appointment"),
    (re.compile(r"\bcancel|reschedul", re.I), "Cancellation or reschedule"),
    (re.compile(r"\bbotox|filler|laser|peel|microneedling\b", re.I), "Service information"),
    (re.compile(r"\bprice|cost|fee\b", re.I), "Pricing inquiry"),
    (re.compile(r"\bcomplain|refund|furious|ridiculous|frustrated\b", re.I), "Service concern / escalation"),
]


def generate_summary(session: Session, provider: LLMProvider) -> str:
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
    response = provider.complete(SUMMARY_SYSTEM, user_prompt)
    return response.text


def format_summary_deterministic(session: Session) -> str:
    """Structured handoff summary — always available without an API."""
    intent = infer_customer_intent(session)
    details = format_collected_details(session)
    unanswered = format_unanswered(session)
    gaps = format_sop_gaps(session)
    escalation = format_escalation_section(session)
    next_action = recommend_next_action(session)

    return f"""## Session Summary — Bloom Aesthetics Clinic

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


def explain_handoff(session: Session, provider: LLMProvider | None = None) -> str:
    """
    Short operator note after escalation.
    Deterministic by default; optional provider only elaborates the handoff.
    """
    if not session.escalation.events:
        return ""
    event = session.escalation.events[-1]
    if provider is None:
        return handoff_note_deterministic(event)

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
    return handoff_note_deterministic(event)


def infer_customer_intent(session: Session) -> str:
    user_msgs = [t.content for t in session.turns if t.role == "user"]
    if not user_msgs:
        return "Unknown — no customer messages captured."

    if session.qualification_state.service_interest:
        svc = session.qualification_state.service_interest
        return f"Inquiry about {svc} and clinic follow-up."

    combined = " ".join(user_msgs[:3])
    for pattern, label in _INTENT_PATTERNS:
        if pattern.search(combined):
            if session.escalation.escalated and re.search(
                r"\b(furious|angry|complain|refund|frustrated|ridiculous)\b",
                combined,
                re.I,
            ):
                return f"{label} — customer distressed; human follow-up required."
            return label

    first = user_msgs[0][:160].strip()
    if len(first) < len(user_msgs[0]):
        first += "…"
    return f"General inquiry: {first}"


def format_collected_details(session: Session) -> str:
    state = session.qualification_state
    if state.service_interest or state.client_status or state.contact:
        lines = [f"  - {state.compact_summary()}"]
        if state.service_detail:
            lines.append(f"  - Detail: {state.service_detail}")
        return "\n".join(lines)
    if not session.qualification:
        # Pull service hints from FAQ thread
        for msg in session.user_messages():
            svc = detect_service(msg)
            if svc:
                return f"  - Mentioned service (not fully qualified): {svc}"
        return "  - None collected."
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
        return "  - None recorded."
    return "\n".join(f"  - {g}" for g in session.sop_gaps)


def format_escalation_section(session: Session) -> str:
    if not session.escalation.escalated or not session.escalation.events:
        return "None."

    lines = []
    for e in session.escalation.events:
        lines.append(f"  - **{e.reason.value}**: {e.detail}")
    if session.handoff_note:
        lines.append(f"  - Operator note: {session.handoff_note}")
    return "\n".join(lines)


def recommend_next_action(session: Session) -> str:
    if not session.escalation.escalated:
        state = session.qualification_state
        if state.completed and state.contact:
            return (
                "Send booking link or confirm consultation per SOP; "
                f"callback at {state.contact} within one business day."
            )
        return (
            "Send booking link or confirm appointment per SOP if customer is ready."
        )

    last = session.escalation.events[-1]
    actions = {
        "explicit_escalation": "Assigned agent to call or email within 4 business hours.",
        "angry_sentiment": "Senior front-desk callback same day; acknowledge frustration first.",
        "complaint": "Open complaint ticket; supervisor review before clinical discussion.",
        "pricing_negotiation": "Front desk to share published pricing — no ad-hoc discounts via chat.",
        "sensitive_unsupported": "Nurse or provider to review clinical question — do not answer via bot.",
        "out_of_scope": "Clarify scope politely; offer in-clinic services only.",
        "low_confidence": "Research SOP/update KB, then respond with verified information.",
        "sop_gap": "Document gap for SOP owner; human answers question on callback.",
        "repeated_unanswered": "Phone intake to resolve open questions; update SOP if recurring.",
    }
    return actions.get(last.reason.value, "Human agent to contact customer within one business day.")


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
