"""Conversation session state and transcript recording."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from sopshield.escalation import EscalationEvent, EscalationState


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
class QualificationAnswer:
    """Single asked-and-answered pair in the qualification stage."""

    question: str
    answer: str
    field: str = ""


@dataclass
class QualificationState:
    """Structured lead data collected during qualification."""

    service_interest: str | None = None
    service_detail: str | None = None
    client_status: str | None = None
    contact: str | None = None
    pending_field: str | None = None
    completed: bool = False

    def as_dict(self) -> dict[str, str | None | bool]:
        return asdict(self)

    def compact_summary(self) -> str:
        parts: list[str] = []
        if self.service_interest:
            line = self.service_interest
            if self.service_detail:
                line = f"{line} ({self.service_detail})"
            parts.append(f"Service: {line}")
        if self.client_status:
            parts.append(f"Client: {self.client_status}")
        if self.contact:
            parts.append(f"Contact: {self.contact}")
        if not parts:
            return "No qualification details captured."
        return " · ".join(parts)


@dataclass
class Session:
    session_id: str
    stage: Stage = Stage.FAQ
    turns: list[Turn] = field(default_factory=list)
    qualification: list[QualificationAnswer] = field(default_factory=list)
    qualification_state: QualificationState = field(default_factory=QualificationState)
    escalation: EscalationState = field(default_factory=EscalationState)
    sop_gaps: list[str] = field(default_factory=list)
    faq_count: int = 0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add(self, role: str, content: str, stage: Stage | None = None, **meta) -> None:
        self.turns.append(
            Turn(role=role, content=content, stage=stage or self.stage, metadata=meta)
        )

    def user_messages(self) -> list[str]:
        return [t.content for t in self.turns if t.role == "user"]

    def transcript_text(self) -> str:
        lines = []
        for t in self.turns:
            prefix = t.role.upper()
            lines.append(f"[{t.stage.value}] {prefix}: {t.content}")
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
        body = self.transcript_text()
        if self.qualification_state.completed or self.qualification:
            body += (
                f"\n\n{'=' * 60}\n"
                f"QUALIFICATION RECORD\n"
                f"{self.qualification_state.compact_summary()}\n\n"
                f"Structured state:\n{self.qualification_state.as_dict()}\n"
            )
        path.write_text(header + body, encoding="utf-8")
        return path
