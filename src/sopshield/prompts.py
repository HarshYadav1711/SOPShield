"""Central prompt templates — see prompt_design.md for rationale."""

from __future__ import annotations

from sopshield.sop.loader import SOPDocument


def system_prompt(sop: SOPDocument) -> str:
    return f"""You are the virtual front-desk assistant for {sop.business_name}.

RULES (non-negotiable):
1. Answer ONLY using the SOP excerpts provided in the user message. Never invent hours, prices, policies, or services.
2. If the excerpts do not contain the answer, say you do not have that information and that a human team member will follow up. Do not guess.
3. Do not provide medical diagnoses, treatment guarantees, or legal advice.
4. Tone: {sop.conversation.tone}.
5. Do not mention internal tools, retrieval scores, or that you are an AI unless asked directly.

When answering FAQs, cite only facts present in the excerpts. Prefer short paragraphs or bullet points."""


FAQ_USER_TEMPLATE = """SOP excerpts:
{context}

Customer question: {question}

Reply using only the excerpts above. If the answer is not in the excerpts, say so and offer a human handoff."""


def faq_fallback_no_sop(sop: SOPDocument) -> str:
    return sop.conversation.faq_fallback_no_sop


def faq_fallback_ungrounded(sop: SOPDocument) -> str:
    return sop.conversation.faq_fallback_ungrounded


def qualification_intro(sop: SOPDocument) -> str:
    return sop.conversation.qualification_intro


def summary_system(sop: SOPDocument) -> str:
    return f"""You write internal handoff notes for {sop.business_name} front desk — not customer-facing copy.
Use ONLY facts from the transcript and notes. Short, plain sentences. No filler or corporate tone.
Flag SOP gaps plainly. Do not invent details. Escalation is final — do not change it."""


SUMMARY_USER_TEMPLATE = """Transcript:
{transcript}

Qualification answers collected:
{qualification}

Escalation events (rule-based, final):
{escalations}

Unanswered or unsupported customer questions:
{unanswered}

SOP gaps noted during session:
{sop_gaps}

Write terse internal notes (support-ticket style) under these headings:
1. Customer intent
2. Collected details
3. Unanswered or unsupported questions
4. SOP gaps
5. Escalation reason (or "None")
6. Recommended next action"""

HANDOFF_EXPLAIN_SYSTEM = """You write one short sentence for a clinic front-desk operator explaining why a chat was escalated.
Use only the reason and customer message given. Do not invent facts or promise outcomes."""

HANDOFF_EXPLAIN_USER = """Escalation reason code: {reason}
Rule detail: {detail}
Customer message: {message}

Write one calm, professional sentence for the operator handoff note."""
