"""End-to-end four-stage conversation workflow orchestrator."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from sopshield.escalation import EscalationEvent, check_message
from sopshield.providers.base import LLMProvider
from sopshield.providers.rule_based import RuleBasedProvider
from sopshield.session import Session, Stage
from sopshield.sop.loader import SOPDocument, load_sop
from sopshield.stages.faq import answer_faq
from sopshield.stages.qualification import (
    record_qualification_answer,
    start_qualification,
)
from sopshield.stages.summary import format_summary_deterministic, generate_summary

HANDOFF_MESSAGE = (
    "I'm connecting you with our front-desk team now. "
    "They'll follow up shortly at the number on your account. "
    "Support email: support@bloom-aesthetics.example (business hours)."
)


@dataclass
class WorkflowReply:
    message: str
    stage: Stage
    done: bool = False
    escalated: bool = False


class ConversationWorkflow:
    def __init__(
        self,
        sop: SOPDocument,
        provider: LLMProvider | None = None,
        *,
        use_llm_summary: bool = False,
    ) -> None:
        self.sop = sop
        self.provider = provider or RuleBasedProvider()
        self.use_llm_summary = use_llm_summary
        self.session = Session(session_id=_new_id())

    @classmethod
    def from_paths(
        cls,
        sop_path: Path | str,
        provider: LLMProvider | None = None,
        **kwargs,
    ) -> ConversationWorkflow:
        return cls(load_sop(sop_path), provider, **kwargs)

    def start(self) -> WorkflowReply:
        greeting = (
            "Hello, and thank you for contacting Bloom Aesthetics Clinic. "
            "I'm here to help with hours, services, booking, and policies. "
            "What can I help you with today?"
        )
        self.session.add("assistant", greeting, Stage.FAQ)
        return WorkflowReply(message=greeting, stage=Stage.FAQ)

    def handle(self, user_message: str) -> WorkflowReply:
        text = user_message.strip()
        if not text:
            return WorkflowReply(
                message="Please type your question when you're ready.",
                stage=self.session.stage,
            )

        self.session.add("user", text, self.session.stage)

        if self.session.stage == Stage.COMPLETE:
            return WorkflowReply(
                message="This session has ended. Start a new session to continue.",
                stage=Stage.COMPLETE,
                done=True,
            )

        if self.session.stage == Stage.SUMMARY:
            return self._finalize_after_summary()

        if self.session.escalation.escalated or self.session.stage == Stage.ESCALATED:
            return self._escalation_path(text)

        if self.session.stage == Stage.FAQ:
            return self._handle_faq(text)

        if self.session.stage == Stage.QUALIFICATION:
            return self._handle_qualification(text)

        return WorkflowReply(
            message="Something went wrong. Please start a new session.",
            stage=self.session.stage,
        )

    def _handle_faq(self, text: str) -> WorkflowReply:
        # Pre-check user message for escalation signals
        pre = check_message(
            text,
            retrieval_confidence=1.0,
            answered_from_sop=True,
            state=self.session.escalation,
        )
        if pre and pre.reason.value in (
            "angry_sentiment",
            "complaint",
            "explicit_escalation",
            "out_of_scope",
        ):
            return self._trigger_escalation(pre)

        faq = answer_faq(self.sop, text, self.provider)
        self.session.faq_count += 1

        post = check_message(
            text,
            retrieval_confidence=faq.confidence,
            answered_from_sop=faq.answered_from_sop,
            state=self.session.escalation,
        )
        if post:
            if not faq.answered_from_sop:
                self.session.sop_gaps.append(text[:120])
            return self._trigger_escalation(post, partial_reply=faq.reply)

        self.session.add(
            "assistant",
            faq.reply,
            Stage.FAQ,
            confidence=faq.confidence,
        )

        # After at least one successful FAQ, move to qualification
        if self.session.faq_count >= 1 and faq.answered_from_sop:
            self.session.stage = Stage.QUALIFICATION
            qual_prompt = start_qualification(self.session)
            self.session.add("assistant", qual_prompt, Stage.QUALIFICATION)
            combined = f"{faq.reply}\n\n{qual_prompt}"
            return WorkflowReply(message=combined, stage=Stage.QUALIFICATION)

        return WorkflowReply(message=faq.reply, stage=Stage.FAQ)

    def _handle_qualification(self, text: str) -> WorkflowReply:
        pre = check_message(
            text,
            retrieval_confidence=1.0,
            answered_from_sop=True,
            state=self.session.escalation,
        )
        if pre and pre.reason.value in (
            "angry_sentiment",
            "complaint",
            "explicit_escalation",
        ):
            return self._trigger_escalation(pre)

        next_q = record_qualification_answer(self.session, text)
        if next_q:
            self.session.add("assistant", next_q, Stage.QUALIFICATION)
            ack = "Thank you. " + next_q
            return WorkflowReply(message=ack, stage=Stage.QUALIFICATION)

        self.session.stage = Stage.SUMMARY
        summary = self._build_summary()
        self.session.add("assistant", summary, Stage.SUMMARY)
        self.session.stage = Stage.COMPLETE
        return WorkflowReply(
            message=summary,
            stage=Stage.SUMMARY,
            done=True,
        )

    def _trigger_escalation(
        self,
        event: EscalationEvent,
        *,
        partial_reply: str | None = None,
    ) -> WorkflowReply:
        self.session.escalation.record(event)
        self.session.stage = Stage.ESCALATED
        parts = []
        if partial_reply:
            parts.append(partial_reply)
        parts.append(HANDOFF_MESSAGE)
        msg = "\n\n".join(parts)
        self.session.add("assistant", msg, Stage.ESCALATED, escalation=event.reason.value)
        self.session.stage = Stage.SUMMARY
        summary = self._build_summary()
        self.session.add("assistant", summary, Stage.SUMMARY)
        self.session.stage = Stage.COMPLETE
        full = f"{msg}\n\n---\n\n{summary}"
        return WorkflowReply(
            message=full,
            stage=Stage.SUMMARY,
            done=True,
            escalated=True,
        )

    def _escalation_path(self, text: str) -> WorkflowReply:
        self.session.add("user", text, Stage.ESCALATED)
        summary = self._build_summary()
        self.session.add("assistant", summary, Stage.SUMMARY)
        self.session.stage = Stage.COMPLETE
        return WorkflowReply(
            message=summary,
            stage=Stage.SUMMARY,
            done=True,
            escalated=True,
        )

    def _build_summary(self) -> str:
        if self.use_llm_summary:
            try:
                return generate_summary(self.session, self.provider)
            except Exception:
                pass
        return format_summary_deterministic(self.session)

    def _finalize_after_summary(self) -> WorkflowReply:
        return WorkflowReply(
            message="Session complete. Thank you for contacting Bloom Aesthetics Clinic.",
            stage=Stage.COMPLETE,
            done=True,
            escalated=self.session.escalation.escalated,
        )

    def save_transcript(self, directory: Path) -> Path:
        return self.session.save_transcript(directory)


def _new_id() -> str:
    return datetime_id()


def datetime_id() -> str:
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{uuid.uuid4().hex[:8]}"
