"""Stage 2 — structured lead qualification (2–3 questions)."""

from __future__ import annotations

from sopshield.prompts import QUALIFICATION_INTRO
from sopshield.session import QualificationAnswer, Session

QUALIFICATION_QUESTIONS: list[str] = [
    "What service are you interested in (e.g., Botox, fillers, laser hair removal)?",
    "Are you a new client or have you visited Bloom Aesthetics before?",
    "What is the best phone number or email for follow-up?",
]


def start_qualification(session: Session) -> str:
    session.qualification_index = 0
    first = next_qualification_prompt(session)
    return f"{QUALIFICATION_INTRO}\n\n{first}"


def next_qualification_prompt(session: Session) -> str | None:
    idx = session.qualification_index
    if idx >= len(QUALIFICATION_QUESTIONS):
        return None
    return f"({idx + 1}/{len(QUALIFICATION_QUESTIONS)}) {QUALIFICATION_QUESTIONS[idx]}"


def record_qualification_answer(session: Session, answer: str) -> str | None:
    idx = session.qualification_index
    if idx >= len(QUALIFICATION_QUESTIONS):
        return None
    q = QUALIFICATION_QUESTIONS[idx]
    cleaned = answer.strip() or "skipped"
    session.qualification.append(QualificationAnswer(question=q, answer=cleaned))
    session.qualification_index += 1
    return next_qualification_prompt(session)
