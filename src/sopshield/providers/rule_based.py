"""Deterministic provider for offline runs and tests — no API keys required."""

from __future__ import annotations

import re

from sopshield.providers.base import LLMProvider, ProviderResponse

# Extract answer instruction from our structured user prompt
_CONTEXT_RE = re.compile(
    r"SOP excerpts:\s*\n(?P<context>.*?)\n\nCustomer question:",
    re.DOTALL | re.IGNORECASE,
)
_QUESTION_RE = re.compile(r"Customer question:\s*(?P<q>.+?)\s*$", re.DOTALL)


class RuleBasedProvider(LLMProvider):
    """Compose calm, professional replies strictly from provided SOP context."""

    def complete(self, system: str, user: str) -> ProviderResponse:
        ctx_match = _CONTEXT_RE.search(user)
        q_match = _QUESTION_RE.search(user)
        context = ctx_match.group("context").strip() if ctx_match else ""
        question = q_match.group("q").strip() if q_match else user.strip()

        if not context or context.startswith("(No matching"):
            return ProviderResponse(
                text=(
                    "I don't have that information in our clinic guidelines. "
                    "I'll connect you with our front-desk team so they can help you directly."
                ),
                confidence=0.0,
            )

        # Use the first SOP section in context (highest retrieval rank)
        first_section = context.split("\n\n---\n\n")[0] if context else context
        answer_bits = _extract_facts(first_section, question=question)
        if not answer_bits:
            return ProviderResponse(
                text=(
                    "I want to make sure you get accurate information. "
                    "Let me have our team follow up with you on that."
                ),
                confidence=0.2,
            )

        body = " ".join(answer_bits[:3])
        reply = (
            f"Thanks for asking. Based on our clinic guidelines: {body} "
            "If you'd like to book or need anything else, I'm happy to help."
        )
        return ProviderResponse(text=reply, confidence=0.75)


def _extract_facts(context: str, question: str = "") -> list[str]:
    from sopshield.sop.retrieval import tokenize_query

    q_tokens = tokenize_query(question)
    facts: list[tuple[int, str]] = []
    for line in context.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        raw = line
        if line.startswith("|"):
            if re.search(r"-{3,}", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
            if len(cells) >= 2 and cells[0].lower() not in {"day", ""}:
                raw = f"{cells[0]}: {cells[1]}"
            else:
                continue
        line = re.sub(r"^[-*]\s*", "", raw)
        line = re.sub(r"^\d+\.\s*", "", line)
        if len(line) < 12:
            continue
        line_tokens = set(re.findall(r"[a-z0-9]+", line.lower()))
        overlap = len(q_tokens & line_tokens)
        facts.append((overlap, line.rstrip(".")))
    facts.sort(key=lambda x: x[0], reverse=True)
    if not facts:
        return []
    best_score = max(s for s, _ in facts)
    ranked = [f for s, f in facts if s == best_score and s > 0]
    if not ranked:
        ranked = [facts[0][1]]
    return ranked[:1]
