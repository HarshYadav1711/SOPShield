"""Stage 1 — FAQ answering grounded in SOP retrieval only."""

from __future__ import annotations

from dataclasses import dataclass

from sopshield.prompts import FAQ_USER_TEMPLATE, SYSTEM_PROMPT
from sopshield.providers.base import LLMProvider
from sopshield.sop.loader import SOPDocument
from sopshield.sop.retrieval import retrieve


@dataclass
class FAQResult:
    reply: str
    confidence: float
    answered_from_sop: bool
    context_used: str


def answer_faq(
    sop: SOPDocument,
    question: str,
    provider: LLMProvider,
    *,
    min_confidence: float = 0.35,
) -> FAQResult:
    retrieval = retrieve(sop, question)
    if not retrieval.has_match or retrieval.confidence < min_confidence:
        return FAQResult(
            reply=(
                "I don't have that information in our clinic guidelines. "
                "I'll connect you with our front-desk team so they can help you directly."
            ),
            confidence=retrieval.confidence,
            answered_from_sop=False,
            context_used="",
        )

    context = retrieval.sections[0].text
    user_prompt = FAQ_USER_TEMPLATE.format(context=context, question=question)
    response = provider.complete(SYSTEM_PROMPT, user_prompt)

    # Grounding check: response must not claim facts outside context (basic guard)
    answered = _response_grounded(response.text, context)
    confidence = retrieval.confidence
    if response.confidence is not None:
        confidence = min(confidence, response.confidence)

    if not answered:
        return FAQResult(
            reply=(
                "I want to make sure you get accurate information. "
                "Let me have our team follow up with you on that."
            ),
            confidence=confidence,
            answered_from_sop=False,
            context_used=context,
        )

    return FAQResult(
        reply=response.text,
        confidence=confidence,
        answered_from_sop=True,
        context_used=context,
    )


def _response_grounded(reply: str, context: str) -> bool:
    """Reject replies that cite specific numbers or policies absent from context."""
    import re

    numbers = set(re.findall(r"\b\d{1,4}\b", reply))
    context_numbers = set(re.findall(r"\b\d{1,4}\b", context))
    suspicious = numbers - context_numbers
    # Allow common small numbers not in SOP (e.g. "a few")
    suspicious -= {"1", "2", "3"}
    if len(suspicious) > 2:
        return False
    if "don't have" in reply.lower() or "do not have" in reply.lower():
        return False
    return True
