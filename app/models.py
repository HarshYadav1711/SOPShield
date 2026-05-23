"""Typed conversation state models for SOPShield."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


@dataclass(frozen=True)
class CustomerMessage:
    """A single inbound customer utterance."""

    text: str
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def parse(cls, raw: str) -> CustomerMessage:
        return cls(text=raw.strip())


@dataclass(frozen=True)
class SopSectionRef:
    title: str
    body: str

    @property
    def text(self) -> str:
        return f"## {self.title}\n\n{self.body.strip()}"


@dataclass(frozen=True)
class SopContext:
    """Retrieved SOP excerpts attached to a turn."""

    sections: tuple[SopSectionRef, ...]
    confidence: float
    matched_terms: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        if not self.sections:
            return ""
        return "\n\n---\n\n".join(section.text for section in self.sections)

    @property
    def has_match(self) -> bool:
        return bool(self.sections) and self.confidence > 0.0


@dataclass(frozen=True)
class QualificationAnswer:
    question: str
    answer: str


@dataclass
class QualificationAnswers:
    """Collected qualification responses for the session."""

    items: list[QualificationAnswer] = field(default_factory=list)

    def record(self, question: str, answer: str) -> None:
        self.items.append(QualificationAnswer(question=question, answer=answer))

    def as_bullets(self) -> str:
        if not self.items:
            return "  - No qualification answers recorded."
        return "\n".join(f"  - {item.question} -> {item.answer}" for item in self.items)


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    OUT_OF_SCOPE = "out_of_scope"
    ANGRY_SENTIMENT = "angry_sentiment"
    COMPLAINT = "complaint"
    EXPLICIT_REQUEST = "explicit_escalation"
    REPEATED_UNANSWERED = "repeated_unanswered"
    SOP_GAP = "sop_gap"


@dataclass(frozen=True)
class EscalationEvent:
    reason: EscalationReason
    detail: str
    user_message: str


@dataclass
class SummaryOutput:
    """Structured end-of-session handoff summary."""

    customer_intent: str
    key_details: str
    sop_gaps: tuple[str, ...]
    next_action: str
    escalation_status: str

    def format(self) -> str:
        gaps = "\n".join(f"  - {gap}" for gap in self.sop_gaps) or "  - None recorded"
        return f"""## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
{self.customer_intent}

### 2. Key details
{self.key_details}

### 3. SOP gaps
{gaps}

### 4. Recommended next action
{self.next_action}

### 5. Escalation status
{self.escalation_status}
"""
