"""Conversation session state and transcript recording."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from app.escalation import EscalationState
from app.models import CustomerMessage, QualificationAnswers


class Stage(str, Enum):
    FAQ = "faq"
    QUALIFICATION = "qualification"
    ESCALATED = "escalated"
    SUMMARY = "summary"
    COMPLETE = "complete"


@dataclass
class Turn:
    role: str
    content: str
    stage: Stage
    metadata: dict = field(default_factory=dict)


@dataclass
class Session:
    session_id: str
    stage: Stage = Stage.FAQ
    turns: list[Turn] = field(default_factory=list)
    customer_messages: list[CustomerMessage] = field(default_factory=list)
    qualification: QualificationAnswers = field(default_factory=QualificationAnswers)
    escalation: EscalationState = field(default_factory=EscalationState)
    sop_gaps: list[str] = field(default_factory=list)
    faq_count: int = 0
    qualification_index: int = 0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add(self, role: str, content: str, stage: Stage | None = None, **meta) -> None:
        self.turns.append(
            Turn(role=role, content=content, stage=stage or self.stage, metadata=meta)
        )

    def record_customer_message(self, raw: str) -> CustomerMessage:
        message = CustomerMessage.parse(raw)
        self.customer_messages.append(message)
        self.add("user", message.text, self.stage)
        return message

    def transcript_text(self) -> str:
        lines = []
        for turn in self.turns:
            prefix = turn.role.upper()
            lines.append(f"[{turn.stage.value}] {prefix}: {turn.content}")
        return "\n".join(lines)

    def save_transcript(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.session_id}.txt"
        header = (
            f"SOPShield session {self.session_id}\n"
            f"Started: {self.started_at}\n"
            f"Escalated: {self.escalation.escalated}\n"
            f"{'=' * 60}\n\n"
        )
        path.write_text(header + self.transcript_text(), encoding="utf-8")
        return path
