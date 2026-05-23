"""Escalation detection — explicit rules before optional model judgment."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.35
UNANSWERED_ESCALATION_LIMIT = 2


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    OUT_OF_SCOPE = "out_of_scope"
    ANGRY_SENTIMENT = "angry_sentiment"
    COMPLAINT = "complaint"
    EXPLICIT_REQUEST = "explicit_escalation"
    REPEATED_UNANSWERED = "repeated_unanswered"
    SOP_GAP = "sop_gap"
    PRICING_NEGOTIATION = "pricing_negotiation"
    SENSITIVE_UNSUPPORTED = "sensitive_unsupported"


# High-confidence lexical signals — conservative patterns (word boundaries, no fuzzy ML)
_EXPLICIT = re.compile(
    r"\b(speak to (a )?(human|person|manager|supervisor|agent)|"
    r"talk to (a )?(human|person|manager|supervisor)|"
    r"real (person|human)|transfer me|escalate|get me someone|"
    r"need a human|want a human)\b",
    re.I,
)
_ANGRY = re.compile(
    r"\b(furious|angry|outraged|ridiculous|terrible|awful|hate|worst|"
    r"unacceptable|disgusting|scam|lawsuit|sue|report you)\b",
    re.I,
)
_FRUSTRATED = re.compile(
    r"\b(frustrated|fed up|sick of|waste of (my )?time|never again|"
    r"so annoyed|infuriating|had enough)\b",
    re.I,
)
_COMPLAINT = re.compile(
    r"\b(complain|complaint|refund|charged wrong|overcharged|"
    r"bad service|rude|botched|injured|hurt me|side effect|"
    r"didn'?t work|made it worse)\b",
    re.I,
)
_PRICING = re.compile(
    r"\b(best price|lowest price|too expensive|price match|"
    r"beat (your|this) price|can you do better|lower the price|"
    r"negotiat(e|ion)|bulk discount|match (a )?competitor|"
    r"what(?:'s| is) your (cheapest|lowest))\b",
    re.I,
)
_SENSITIVE = re.compile(
    r"\b(pregnan(t|cy)|breastfeeding|nursing|blood thinner|warfarin|"
    r"on (?:these )?medication|drug interaction|allergic reaction|"
    r"anaphylaxis|diagnos(e|is)|symptoms?|mole (?:change|check)|"
    r"suspicious lump|skin cancer|chemo(?:therapy)?|infection|"
    r"pus|bleeding after|swollen|rash spreading|medical emergency|"
    r"is it safe (?:for|with|if)|can i (?:take|use).*(?:while|with))\b",
    re.I,
)
_OUT_OF_SCOPE = re.compile(
    r"\b(insurance claim|malpractice|prescription|dental|surgery|"
    r"laser eye|covid vaccine|workers comp|financing plan|"
    r"legal advice|attorney)\b",
    re.I,
)

# Immediate handoff — checked before FAQ / qualification
_IMMEDIATE_REASONS = frozenset(
    {
        EscalationReason.EXPLICIT_REQUEST,
        EscalationReason.ANGRY_SENTIMENT,
        EscalationReason.COMPLAINT,
        EscalationReason.OUT_OF_SCOPE,
        EscalationReason.PRICING_NEGOTIATION,
        EscalationReason.SENSITIVE_UNSUPPORTED,
    }
)


@dataclass
class EscalationEvent:
    reason: EscalationReason
    detail: str
    user_message: str


@dataclass
class EscalationState:
    events: list[EscalationEvent] = field(default_factory=list)
    unanswered_streak: int = 0
    escalated: bool = False

    def record(self, event: EscalationEvent) -> None:
        self.events.append(event)
        self.escalated = True
        logger.info(
            "Escalation recorded: reason=%s detail=%r user_message=%r",
            event.reason.value,
            event.detail,
            event.user_message[:200],
        )


def is_immediate_escalation(reason: EscalationReason) -> bool:
    return reason in _IMMEDIATE_REASONS


def check_message(
    message: str,
    *,
    retrieval_confidence: float,
    answered_from_sop: bool,
    state: EscalationState,
) -> EscalationEvent | None:
    """Return an escalation event when deterministic rules fire; else None."""
    text = message.strip()
    if not text:
        return None

    event = _check_lexical_signals(text)
    if event is not None:
        return event

    if not answered_from_sop:
        return _check_unanswered(text, retrieval_confidence, state)

    state.unanswered_streak = 0
    return None


def _check_lexical_signals(message: str) -> EscalationEvent | None:
    """Conservative, priority-ordered pattern checks (no escalation on weak matches)."""
    if _EXPLICIT.search(message):
        return EscalationEvent(
            EscalationReason.EXPLICIT_REQUEST,
            "Customer explicitly asked for a human team member.",
            message,
        )
    if _COMPLAINT.search(message):
        return EscalationEvent(
            EscalationReason.COMPLAINT,
            "Complaint, refund, or service-harm language detected.",
            message,
        )
    if _ANGRY.search(message) or _FRUSTRATED.search(message):
        tone = "angry" if _ANGRY.search(message) else "frustrated"
        return EscalationEvent(
            EscalationReason.ANGRY_SENTIMENT,
            f"Customer tone appears {tone} or distressed.",
            message,
        )
    if _PRICING.search(message):
        return EscalationEvent(
            EscalationReason.PRICING_NEGOTIATION,
            "Pricing negotiation or discount pressure beyond published SOP rates.",
            message,
        )
    if _SENSITIVE.search(message):
        return EscalationEvent(
            EscalationReason.SENSITIVE_UNSUPPORTED,
            "Medical or clinical safety question — not answerable from front-desk SOP.",
            message,
        )
    if _OUT_OF_SCOPE.search(message):
        return EscalationEvent(
            EscalationReason.OUT_OF_SCOPE,
            "Topic appears outside clinic SOP scope.",
            message,
        )
    return None


def _check_unanswered(
    message: str,
    retrieval_confidence: float,
    state: EscalationState,
) -> EscalationEvent | None:
    state.unanswered_streak += 1

    if state.unanswered_streak >= UNANSWERED_ESCALATION_LIMIT:
        return EscalationEvent(
            EscalationReason.REPEATED_UNANSWERED,
            (
                f"Question could not be answered from SOP "
                f"{state.unanswered_streak} time(s) in a row "
                f"(limit: {UNANSWERED_ESCALATION_LIMIT})."
            ),
            message,
        )

    if retrieval_confidence < CONFIDENCE_THRESHOLD:
        return EscalationEvent(
            EscalationReason.LOW_CONFIDENCE,
            (
                f"Retrieval confidence {retrieval_confidence:.2f} "
                f"below threshold {CONFIDENCE_THRESHOLD}."
            ),
            message,
        )

    return EscalationEvent(
        EscalationReason.SOP_GAP,
        "No supporting SOP content for this question.",
        message,
    )


def handoff_note_deterministic(event: EscalationEvent) -> str:
    """Operator-facing one-liner — no model required."""
    labels = {
        EscalationReason.EXPLICIT_REQUEST: "Customer requested a live agent.",
        EscalationReason.ANGRY_SENTIMENT: "De-escalate; customer upset — prioritize callback.",
        EscalationReason.COMPLAINT: "Review complaint and billing/service notes before contact.",
        EscalationReason.PRICING_NEGOTIATION: "Pricing outside bot scope — manager or front desk to quote.",
        EscalationReason.SENSITIVE_UNSUPPORTED: "Clinical/safety question — route to licensed staff, not chatbot.",
        EscalationReason.OUT_OF_SCOPE: "Out-of-scope topic — clarify what Bloom Aesthetics can offer.",
        EscalationReason.LOW_CONFIDENCE: "Low SOP match — verify answer manually before replying.",
        EscalationReason.SOP_GAP: "SOP missing topic — capture answer for future FAQ update.",
        EscalationReason.REPEATED_UNANSWERED: "Multiple unanswered questions — complete intake by phone.",
    }
    label = labels.get(event.reason, event.detail)
    return f"{label} ({event.reason.value})"
