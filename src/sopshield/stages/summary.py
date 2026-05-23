"""Stage 4 — structured end-of-session summary."""

from __future__ import annotations

from sopshield.escalation import EscalationEvent
from sopshield.prompts import SUMMARY_SYSTEM, SUMMARY_USER_TEMPLATE
from sopshield.providers.base import LLMProvider
from sopshield.session import Session


def generate_summary(session: Session, provider: LLMProvider) -> str:
    esc_lines = (
        "\n".join(f"- {e.reason.value}: {e.detail}" for e in session.escalation.events)
        or "(none)"
    )
    qual_lines = (
        "\n".join(f"- Q: {q.question}\n  A: {q.answer}" for q in session.qualification)
        or "(none collected)"
    )
    gaps = "\n".join(f"- {g}" for g in session.sop_gaps) or "(none)"

    user_prompt = SUMMARY_USER_TEMPLATE.format(
        transcript=session.transcript_text(),
        qualification=qual_lines,
        escalations=esc_lines,
        sop_gaps=gaps,
    )
    response = provider.complete(SUMMARY_SYSTEM, user_prompt)
    return response.text


def format_summary_deterministic(session: Session) -> str:
    """Fallback summary without LLM — always available."""
    intent = _infer_intent(session)
    key_details = _format_qualification(session)
    gaps = "\n".join(f"  - {g}" for g in session.sop_gaps) or "  - None recorded"
    if session.escalation.escalated:
        esc_status = "ESCALATED — " + "; ".join(
            e.reason.value for e in session.escalation.events
        )
        next_action = "Human agent to contact customer within one business day."
    else:
        esc_status = "None"
        next_action = "Send booking link or confirm appointment per SOP if customer is ready."

    return f"""## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
{intent}

### 2. Key details
{key_details}

### 3. SOP gaps
{gaps}

### 4. Recommended next action
{next_action}

### 5. Escalation status
{esc_status}
"""


def _infer_intent(session: Session) -> str:
    user_msgs = [t.content for t in session.turns if t.role == "user"]
    if not user_msgs:
        return "Unknown — no messages captured."
    first = user_msgs[0][:200]
    return f"Primary topic from conversation: {first}"


def _format_qualification(session: Session) -> str:
    if not session.qualification:
        return "  - No qualification answers recorded."
    lines = []
    for q in session.qualification:
        lines.append(f"  - {q.question} -> {q.answer}")
    return "\n".join(lines)
