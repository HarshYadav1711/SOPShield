"""End-to-end four-stage conversation workflow orchestrator."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from sopshield.audit_log import log_escalation
from sopshield.escalation import EscalationEvent, check_message, is_immediate_escalation
from sopshield.providers.base import LLMProvider
from sopshield.providers.rule_based import RuleBasedProvider
from sopshield.session import Session, Stage
from sopshield.sop.loader import SOPDocument, load_sop, resolve_sop_path
from sopshield.stages.faq import answer_faq
from sopshield.stages.qualification import (
    process_qualification_turn,
    start_qualification,
)
from sopshield.stages.summary import (
    explain_handoff,
    format_summary_deterministic,
    generate_summary,
)

logger = logging.getLogger(__name__)


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
        use_llm_handoff_note: bool = False,
    ) -> None:
        self.sop = sop
        self.provider = provider or RuleBasedProvider()
        self.use_llm_summary = use_llm_summary
        self.use_llm_handoff_note = use_llm_handoff_note
        self.session = Session(session_id=_new_id())

    @classmethod
    def from_paths(
        cls,
        sop_path: Path | str,
        provider: LLMProvider | None = None,
        **kwargs,
    ) -> ConversationWorkflow:
        path = resolve_sop_path(sop_path)
        return cls(load_sop(path), provider, **kwargs)

    def start(self) -> WorkflowReply:
        greeting = self.sop.conversation.greeting
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
        pre = check_message(
            text,
            retrieval_confidence=1.0,
            answered_from_sop=True,
            state=self.session.escalation,
            sop=self.sop,
        )
        if pre is not None and is_immediate_escalation(pre.reason):
            return self._trigger_escalation(pre, confidence=1.0)

        faq = answer_faq(self.sop, text, self.provider)
        self.session.faq_count += 1

        post = check_message(
            text,
            retrieval_confidence=faq.confidence,
            answered_from_sop=faq.answered_from_sop,
            state=self.session.escalation,
            sop=self.sop,
        )
        if post is not None:
            if not faq.answered_from_sop:
                snippet = text[:120]
                self.session.sop_gaps.append(snippet)
                self.session.unanswered_questions.append(snippet)
            return self._trigger_escalation(
                post, partial_reply=faq.reply, confidence=faq.confidence
            )

        self.session.add(
            "assistant",
            faq.reply,
            Stage.FAQ,
            confidence=faq.confidence,
        )

        if self.session.faq_count >= 1 and faq.answered_from_sop:
            self.session.stage = Stage.QUALIFICATION
            qual_prompt = start_qualification(self.session, self.sop)
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
            sop=self.sop,
        )
        if pre is not None and is_immediate_escalation(pre.reason):
            return self._trigger_escalation(pre, confidence=1.0)

        result = process_qualification_turn(self.session, text, self.sop)
        if not result.done:
            self.session.add("assistant", result.reply, Stage.QUALIFICATION)
            return WorkflowReply(message=result.reply, stage=Stage.QUALIFICATION)

        self.session.stage = Stage.SUMMARY
        session_summary = self._build_summary()
        combined = f"{result.reply}\n\n---\n\n{session_summary}"
        self.session.add("assistant", combined, Stage.SUMMARY)
        self.session.stage = Stage.COMPLETE
        return WorkflowReply(
            message=combined,
            stage=Stage.SUMMARY,
            done=True,
        )

    def _trigger_escalation(
        self,
        event: EscalationEvent,
        *,
        partial_reply: str | None = None,
        confidence: float = 1.0,
    ) -> WorkflowReply:
        self.session.escalation.record(event)
        log_escalation(
            sop_id=self.sop.sop_id,
            customer_message=event.user_message,
            trigger=event.reason.value,
            confidence=confidence,
            escalated=True,
        )
        self.session.handoff_note = explain_handoff(
            self.session,
            self.sop,
            self.provider if self.use_llm_handoff_note else None,
        )
        logger.info("Workflow escalation: %s", self.session.handoff_note)

        self.session.stage = Stage.ESCALATED
        parts = []
        if partial_reply:
            parts.append(partial_reply)
        parts.append(self.sop.conversation.handoff_message)
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
                return generate_summary(self.session, self.sop, self.provider)
            except Exception:
                logger.exception("LLM summary failed; using deterministic summary")
        return format_summary_deterministic(self.session, self.sop)

    def _finalize_after_summary(self) -> WorkflowReply:
        return WorkflowReply(
            message=self.sop.conversation.closing_message,
            stage=Stage.COMPLETE,
            done=True,
            escalated=self.session.escalation.escalated,
        )

    def save_transcript(self, directory: Path) -> Path:
        return self.session.save_transcript(directory, sop_id=self.sop.sop_id)


def _new_id() -> str:
    return datetime_id()


def datetime_id() -> str:
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{uuid.uuid4().hex[:8]}"
