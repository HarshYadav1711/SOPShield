"""Stage 2 — stateful lead qualification (2–3 questions, conditional follow-ups)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sopshield.session import QualificationAnswer, QualificationState, Session
from sopshield.sop.loader import SOPDocument

FIELD_SERVICE = "service_interest"
FIELD_SERVICE_FOLLOWUP = "service_detail"
FIELD_CLIENT = "client_status"
FIELD_CONTACT = "contact"

CLIENT_NEW = re.compile(
    r"\b(new\s+client|first\s+time|first\s+visit|never\s+been|haven'?t\s+been|"
    r"new\s+patient|first\s+visit)\b",
    re.I,
)
CLIENT_RETURNING = re.compile(
    r"\b(returning|been\s+before|existing\s+client|came\s+in\s+before|"
    r"visited\s+before|regular|been\s+a\s+patient)\b",
    re.I,
)

PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

SKIP_RE = re.compile(r"^\s*(skip|pass|n/?a|none|prefer not)\s*$", re.I)


@dataclass
class QualificationTurnResult:
    reply: str
    done: bool
    summary: str | None = None


def start_qualification(session: Session, sop: SOPDocument) -> str:
    """Begin qualification after FAQ; prefill from earlier messages, ask first gap."""
    prefill_from_conversation(session, sop)
    field = _next_field(session.qualification_state, sop)
    intro = sop.conversation.qualification_intro
    if field is None:
        session.qualification_state.completed = True
        summary = format_qualification_summary(session)
        return f"{intro}\n\n{summary}"

    session.qualification_state.pending_field = field
    question = _questions(sop)[field]
    return f"{intro}\n\n{question}"


def process_qualification_turn(
    session: Session,
    answer: str,
    sop: SOPDocument,
) -> QualificationTurnResult:
    """Record one customer reply and return the next prompt or final summary."""
    state = session.qualification_state
    text = answer.strip()
    questions = _questions(sop)

    if state.completed:
        return QualificationTurnResult(
            reply=format_qualification_summary(session),
            done=True,
            summary=format_qualification_summary(session),
        )

    field = state.pending_field
    if field is None:
        field = _next_field(state, sop)
        if field is None:
            return _complete(session)

    cleaned = _normalize_answer(text, field, sop)
    _apply_answer(session, field, cleaned, sop)
    session.qualification.append(
        QualificationAnswer(question=questions[field], answer=cleaned, field=field)
    )

    next_field = _next_field(state, sop)
    if next_field is None:
        ack = _acknowledge(field, cleaned, sop)
        return _complete(session, prefix=ack)

    state.pending_field = next_field
    ack = _acknowledge(field, cleaned, sop)
    question = questions[next_field]
    reply = f"{ack} {question}".strip() if ack else question
    return QualificationTurnResult(reply=reply, done=False)


def format_qualification_summary(session: Session) -> str:
    """Compact handoff block for front-desk staff."""
    state = session.qualification_state
    lines = ["**Lead qualification**", state.compact_summary()]
    if (session.qualification):
        lines.append("")
        lines.append("_Captured during intake:_")
        for item in session.qualification:
            short_q = _short_label(item.field)
            lines.append(f"- {short_q}: {item.answer}")
    return "\n".join(lines)


def prefill_from_conversation(session: Session, sop: SOPDocument) -> None:
    """Infer qualification fields from FAQ-stage messages (no extra questions)."""
    state = session.qualification_state
    for message in session.user_messages():
        _infer_into_state(state, message, sop)


def detect_service(text: str, sop: SOPDocument) -> str | None:
    for pattern, label in _service_patterns(sop):
        if pattern.search(text):
            return label
    return None


def detect_contact(text: str) -> str | None:
    email = EMAIL_RE.search(text)
    if email:
        return email.group(0)
    phone = PHONE_RE.search(text)
    if phone:
        return phone.group(0).strip()
    return None


def detect_client_status(text: str) -> str | None:
    if CLIENT_NEW.search(text):
        return "new"
    if CLIENT_RETURNING.search(text):
        return "returning"
    if re.search(r"\bnew\b", text, re.I) and not CLIENT_RETURNING.search(text):
        return "new"
    return None


def _service_patterns(sop: SOPDocument) -> list[tuple[re.Pattern[str], str]]:
    return [(re.compile(pat, re.I), label) for pat, label in sop.qualification.services]


def _vague_hints(sop: SOPDocument) -> re.Pattern[str]:
    return re.compile(sop.qualification.vague_hints, re.I)


def _questions(sop: SOPDocument) -> dict[str, str]:
    return sop.qualification.questions


def _complete(session: Session, *, prefix: str = "") -> QualificationTurnResult:
    session.qualification_state.completed = True
    session.qualification_state.pending_field = None
    summary = format_qualification_summary(session)
    closing = (
        "Thank you — I have what our team needs for follow-up. "
        "Here's a quick summary of your visit:"
    )
    lead = f"{prefix} {closing}".strip() if prefix else closing
    return QualificationTurnResult(
        reply=f"{lead}\n\n{summary}",
        done=True,
        summary=summary,
    )


def _next_field(state: QualificationState, sop: SOPDocument) -> str | None:
    if not state.service_interest:
        return FIELD_SERVICE
    if state.service_interest and _service_needs_followup(state, sop) and not state.service_detail:
        return FIELD_SERVICE_FOLLOWUP
    if not state.client_status:
        return FIELD_CLIENT
    if not state.contact:
        return FIELD_CONTACT
    return None


def _apply_answer(
    session: Session,
    field: str,
    answer: str,
    sop: SOPDocument,
) -> None:
    state = session.qualification_state
    if field == FIELD_SERVICE:
        detected = detect_service(answer, sop)
        state.service_interest = detected or answer
    elif field == FIELD_SERVICE_FOLLOWUP:
        state.service_detail = answer
    elif field == FIELD_CLIENT:
        status = detect_client_status(answer)
        state.client_status = status or answer
    elif field == FIELD_CONTACT:
        contact = detect_contact(answer)
        state.contact = contact or answer


def _normalize_answer(text: str, field: str, sop: SOPDocument) -> str:
    if SKIP_RE.match(text):
        return "not provided"
    if field == FIELD_CLIENT:
        status = detect_client_status(text)
        if status:
            return status
    if field == FIELD_CONTACT:
        contact = detect_contact(text)
        if contact:
            return contact
    if field == FIELD_SERVICE:
        service = detect_service(text, sop)
        if service:
            return service
    return text.strip() or "not provided"


def _infer_into_state(
    state: QualificationState,
    message: str,
    sop: SOPDocument,
) -> None:
    if not state.service_interest:
        service = detect_service(message, sop)
        if service:
            state.service_interest = service
        elif _vague_hints(sop).search(message) and len(message.split()) <= 12:
            state.service_interest = message.strip()[:80]

    if not state.client_status:
        status = detect_client_status(message)
        if status:
            state.client_status = status

    if not state.contact:
        contact = detect_contact(message)
        if contact:
            state.contact = contact


def _service_needs_followup(state: QualificationState, sop: SOPDocument) -> bool:
    if not state.service_interest:
        return False
    known = {label for _, label in sop.qualification.services}
    if state.service_interest in known:
        return False
    return bool(_vague_hints(sop).search(state.service_interest))


def _acknowledge(field: str, answer: str, sop: SOPDocument) -> str:
    if answer == "not provided":
        return "No problem."
    template = sop.qualification.acknowledgments.get(field, "Thank you.")
    return template.format(value=answer)


def _short_label(field: str) -> str:
    return {
        FIELD_SERVICE: "Service interest",
        FIELD_SERVICE_FOLLOWUP: "Service detail",
        FIELD_CLIENT: "Client status",
        FIELD_CONTACT: "Contact",
    }.get(field, "Detail")
