"""Stage 2 — stateful lead qualification (2–3 questions, conditional follow-ups)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sopshield.prompts import QUALIFICATION_INTRO
from sopshield.session import QualificationAnswer, QualificationState, Session

# Fields we may collect; only those still unknown are asked.
FIELD_SERVICE = "service_interest"
FIELD_SERVICE_FOLLOWUP = "service_detail"
FIELD_CLIENT = "client_status"
FIELD_CONTACT = "contact"

SERVICE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bbotox\b", re.I), "Botox"),
    (re.compile(r"\b(dermal\s+)?fillers?\b", re.I), "Dermal fillers"),
    (re.compile(r"\bchemical\s+peels?\b", re.I), "Chemical peel"),
    (re.compile(r"\blaser\s+hair\s+removal\b", re.I), "Laser hair removal"),
    (re.compile(r"\blaser\b", re.I), "Laser hair removal"),
    (re.compile(r"\bmicroneedling\b", re.I), "Microneedling"),
]

VAGUE_SERVICE_HINTS = re.compile(
    r"\b(something|treatment|procedure|help with my face|skin care|"
    r"anti-?aging|wrinkles?|face)\b",
    re.I,
)

CLIENT_NEW = re.compile(
    r"\b(new\s+client|first\s+time|first\s+visit|never\s+been|haven'?t\s+been)\b",
    re.I,
)
CLIENT_RETURNING = re.compile(
    r"\b(returning|been\s+before|existing\s+client|came\s+in\s+before|"
    r"visited\s+before|regular)\b",
    re.I,
)

PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

SKIP_RE = re.compile(r"^\s*(skip|pass|n/?a|none|prefer not)\s*$", re.I)

QUESTIONS: dict[str, str] = {
    FIELD_SERVICE: (
        "Which treatment were you hoping to learn about or book? "
        "(For example, Botox, fillers, laser hair removal, or a chemical peel.)"
    ),
    FIELD_SERVICE_FOLLOWUP: (
        "Could you tell me a bit more about what you're looking for "
        "— for example, area or main concern — so our team can prepare?"
    ),
    FIELD_CLIENT: (
        "Have you visited Bloom Aesthetics before, or would this be your first time with us?"
    ),
    FIELD_CONTACT: (
        "What's the best phone number or email for our front-desk team to follow up?"
    ),
}

ACKNOWLEDGMENTS: dict[str, str] = {
    FIELD_SERVICE: "Got it — {value}.",
    FIELD_SERVICE_FOLLOWUP: "Thank you, that's helpful.",
    FIELD_CLIENT: "Thanks — I've noted you're a {value} client.",
    FIELD_CONTACT: "Perfect — we'll use {value} to reach you.",
}


@dataclass
class QualificationTurnResult:
    reply: str
    done: bool
    summary: str | None = None


def start_qualification(session: Session) -> str:
    """Begin qualification after FAQ; prefill from earlier messages, ask first gap."""
    prefill_from_conversation(session)
    field = _next_field(session.qualification_state)
    if field is None:
        session.qualification_state.completed = True
        summary = format_qualification_summary(session)
        return f"{QUALIFICATION_INTRO}\n\n{summary}"

    session.qualification_state.pending_field = field
    question = QUESTIONS[field]
    return f"{QUALIFICATION_INTRO}\n\n{question}"


def process_qualification_turn(session: Session, answer: str) -> QualificationTurnResult:
    """Record one customer reply and return the next prompt or final summary."""
    state = session.qualification_state
    text = answer.strip()

    if state.completed:
        return QualificationTurnResult(
            reply=format_qualification_summary(session),
            done=True,
            summary=format_qualification_summary(session),
        )

    field = state.pending_field
    if field is None:
        field = _next_field(state)
        if field is None:
            return _complete(session)

    cleaned = _normalize_answer(text, field)
    _apply_answer(session, field, cleaned)
    session.qualification.append(
        QualificationAnswer(question=QUESTIONS[field], answer=cleaned, field=field)
    )

    next_field = _next_field(state)
    if next_field is None:
        ack = _acknowledge(field, cleaned)
        return _complete(session, prefix=ack)

    state.pending_field = next_field
    ack = _acknowledge(field, cleaned)
    question = QUESTIONS[next_field]
    reply = f"{ack} {question}".strip() if ack else question
    return QualificationTurnResult(reply=reply, done=False)


def format_qualification_summary(session: Session) -> str:
    """Compact handoff block for front-desk staff."""
    state = session.qualification_state
    lines = ["**Lead qualification**", state.compact_summary()]
    if session.qualification:
        lines.append("")
        lines.append("_Captured during intake:_")
        for item in session.qualification:
            short_q = _short_label(item.field)
            lines.append(f"- {short_q}: {item.answer}")
    return "\n".join(lines)


def prefill_from_conversation(session: Session) -> None:
    """Infer qualification fields from FAQ-stage messages (no extra questions)."""
    state = session.qualification_state
    for message in session.user_messages():
        _infer_into_state(state, message)


# Backward-compatible exports for tests and __init__
QUALIFICATION_QUESTIONS: list[str] = list(QUESTIONS.values())


def next_qualification_prompt(session: Session) -> str | None:
    field = _next_field(session.qualification_state)
    if field is None:
        return None
    return QUESTIONS[field]


def record_qualification_answer(session: Session, answer: str) -> str | None:
    """Legacy API — prefer process_qualification_turn."""
    result = process_qualification_turn(session, answer)
    if result.done:
        return None
    return result.reply


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


def _next_field(state: QualificationState) -> str | None:
    if not state.service_interest:
        return FIELD_SERVICE
    if state.service_interest and _service_needs_followup(state) and not state.service_detail:
        return FIELD_SERVICE_FOLLOWUP
    if not state.client_status:
        return FIELD_CLIENT
    if not state.contact:
        return FIELD_CONTACT
    return None


def _apply_answer(session: Session, field: str, answer: str) -> None:
    state = session.qualification_state
    if field == FIELD_SERVICE:
        detected = detect_service(answer)
        state.service_interest = detected or answer
    elif field == FIELD_SERVICE_FOLLOWUP:
        state.service_detail = answer
    elif field == FIELD_CLIENT:
        status = detect_client_status(answer)
        state.client_status = status or answer
    elif field == FIELD_CONTACT:
        contact = detect_contact(answer)
        state.contact = contact or answer


def _normalize_answer(text: str, field: str) -> str:
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
        service = detect_service(text)
        if service:
            return service
    return text.strip() or "not provided"


def _infer_into_state(state: QualificationState, message: str) -> None:
    if not state.service_interest:
        service = detect_service(message)
        if service:
            state.service_interest = service
        elif VAGUE_SERVICE_HINTS.search(message) and len(message.split()) <= 12:
            state.service_interest = message.strip()[:80]

    if not state.client_status:
        status = detect_client_status(message)
        if status:
            state.client_status = status

    if not state.contact:
        contact = detect_contact(message)
        if contact:
            state.contact = contact


def detect_service(text: str) -> str | None:
    for pattern, label in SERVICE_PATTERNS:
        if pattern.search(text):
            return label
    return None


def detect_client_status(text: str) -> str | None:
    if CLIENT_NEW.search(text):
        return "new"
    if CLIENT_RETURNING.search(text):
        return "returning"
    if re.search(r"\bnew\b", text, re.I) and not CLIENT_RETURNING.search(text):
        return "new"
    return None


def detect_contact(text: str) -> str | None:
    email = EMAIL_RE.search(text)
    if email:
        return email.group(0)
    phone = PHONE_RE.search(text)
    if phone:
        return phone.group(0).strip()
    return None


def _service_needs_followup(state: QualificationState) -> bool:
    if not state.service_interest:
        return False
    if state.service_interest in {s[1] for s in SERVICE_PATTERNS}:
        return False
    return bool(VAGUE_SERVICE_HINTS.search(state.service_interest))


def _acknowledge(field: str, answer: str) -> str:
    if answer == "not provided":
        return "No problem."
    template = ACKNOWLEDGMENTS.get(field, "Thank you.")
    value = answer
    if field == FIELD_CLIENT:
        value = answer
    return template.format(value=value)


def _short_label(field: str) -> str:
    return {
        FIELD_SERVICE: "Service interest",
        FIELD_SERVICE_FOLLOWUP: "Service detail",
        FIELD_CLIENT: "Client status",
        FIELD_CONTACT: "Contact",
    }.get(field, "Detail")
