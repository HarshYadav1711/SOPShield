"""Escalation detection — explicit rules before optional model judgment."""

from __future__ import annotations

import re

from app.models import EscalationEvent, EscalationReason

# Lexical signals — fast, auditable, no ML dependency
_ANGRY = re.compile(
    r"\b(furious|angry|outraged|ridiculous|terrible|awful|hate|worst|"
    r"unacceptable|disgusting|scam|lawsuit|sue|report you)\b",
    re.I,
)
_COMPLAINT = re.compile(
    r"\b(complain|complaint|refund|charged wrong|overcharged|"
    r"bad service|rude|botched|injured|hurt me|side effect)\b",
    re.I,
)
_EXPLICIT = re.compile(
    r"\b(speak to (a )?(human|person|manager|supervisor)|"
    r"real (person|human)|transfer me|escalate|get me someone)\b",
    re.I,
)
_OUT_OF_SCOPE = re.compile(
    r"\b(insurance claim|malpractice|prescription|diagnos|"
    r"dental|surgery|laser eye|covid vaccine|workers comp|"
    r"discount code|price match|financing plan)\b",
    re.I,
)

CONFIDENCE_THRESHOLD = 0.35


class EscalationState:
    events: list[EscalationEvent]
    unanswered_streak: int
    escalated: bool

    def __init__(self) -> None:
        self.events = []
        self.unanswered_streak = 0
        self.escalated = False

    def record(self, event: EscalationEvent) -> None:
        self.events.append(event)
        self.escalated = True


def check_message(
    message: str,
    *,
    retrieval_confidence: float,
    answered_from_sop: bool,
    state: EscalationState,
) -> EscalationEvent | None:
    if _EXPLICIT.search(message):
        return EscalationEvent(
            EscalationReason.EXPLICIT_REQUEST,
            "Customer requested a human agent.",
            message,
        )
    if _ANGRY.search(message):
        return EscalationEvent(
            EscalationReason.ANGRY_SENTIMENT,
            "Angry or hostile language detected.",
            message,
        )
    if _COMPLAINT.search(message):
        return EscalationEvent(
            EscalationReason.COMPLAINT,
            "Complaint or billing/clinical concern detected.",
            message,
        )
    if _OUT_OF_SCOPE.search(message):
        return EscalationEvent(
            EscalationReason.OUT_OF_SCOPE,
            "Topic appears outside clinic SOP scope.",
            message,
        )
    if not answered_from_sop:
        state.unanswered_streak += 1
        if state.unanswered_streak >= 2:
            return EscalationEvent(
                EscalationReason.REPEATED_UNANSWERED,
                "Same or similar question could not be answered twice from SOP.",
                message,
            )
        if retrieval_confidence < CONFIDENCE_THRESHOLD:
            return EscalationEvent(
                EscalationReason.LOW_CONFIDENCE,
                f"Retrieval confidence {retrieval_confidence:.2f} below threshold.",
                message,
            )
        return EscalationEvent(
            EscalationReason.SOP_GAP,
            "No supporting SOP content for this question.",
            message,
        )
    state.unanswered_streak = 0
    if retrieval_confidence < CONFIDENCE_THRESHOLD and not answered_from_sop:
        return EscalationEvent(
            EscalationReason.LOW_CONFIDENCE,
            f"Retrieval confidence {retrieval_confidence:.2f} below threshold.",
            message,
        )
    return None
