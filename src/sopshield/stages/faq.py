"""Stage 1 — FAQ answering grounded in SOP retrieval only."""

from __future__ import annotations

from dataclasses import dataclass

from sopshield.prompts import (
    FAQ_USER_TEMPLATE,
    faq_fallback_no_sop,
    faq_fallback_ungrounded,
    system_prompt,
)
from sopshield.providers.base import LLMProvider
from sopshield.sop.grounding import response_grounded, sop_supports_answer
from sopshield.sop.loader import SOPDocument
from sopshield.sop.retrieval import retrieve


@dataclass
class FAQResult:
    reply: str
    confidence: float
    answered_from_sop: bool
    context_used: str
    needs_escalation: bool = False


def answer_faq(
    sop: SOPDocument,
    question: str,
    provider: LLMProvider,
    *,
    min_confidence: float | None = None,
) -> FAQResult:
    """Answer only when the SOP explicitly supports the question; otherwise escalate."""
    threshold = (
        min_confidence
        if min_confidence is not None
        else sop.escalation.confidence_threshold
    )
    retrieval = retrieve(sop, question)

    if not retrieval.has_match or retrieval.confidence < threshold:
        return _fallback(
            sop,
            retrieval.confidence,
            reason="low_confidence",
        )

    primary = retrieval.sections[0]
    context = primary.text
    if not sop_supports_answer(question, [primary]):
        return _fallback(
            sop,
            retrieval.confidence,
            reason="no_support",
            context_used=context,
        )

    user_prompt = FAQ_USER_TEMPLATE.format(context=context, question=question)
    response = provider.complete(system_prompt(sop), user_prompt)

    answered = response_grounded(response.text, context)
    confidence = retrieval.confidence
    if response.confidence is not None:
        confidence = min(confidence, response.confidence)

    if not answered:
        return _fallback(
            sop,
            confidence,
            reason="ungrounded",
            context_used=context,
        )

    return FAQResult(
        reply=response.text.strip(),
        confidence=confidence,
        answered_from_sop=True,
        context_used=context,
        needs_escalation=False,
    )


def _fallback(
    sop: SOPDocument,
    confidence: float,
    *,
    reason: str,
    context_used: str = "",
) -> FAQResult:
    if reason == "ungrounded":
        reply = faq_fallback_ungrounded(sop)
    else:
        reply = faq_fallback_no_sop(sop)
    return FAQResult(
        reply=reply,
        confidence=confidence,
        answered_from_sop=False,
        context_used=context_used,
        needs_escalation=True,
    )
