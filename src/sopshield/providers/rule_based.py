"""Deterministic provider for offline runs and tests — no API keys required."""

from __future__ import annotations

import re

from sopshield.prompts import FAQ_FALLBACK_NO_SOP, FAQ_FALLBACK_UNGROUNDED
from sopshield.providers.base import LLMProvider, ProviderResponse
from sopshield.sop.grounding import sop_supports_answer
from sopshield.sop.loader import SOPSection

# Extract answer instruction from our structured user prompt
_CONTEXT_RE = re.compile(
    r"SOP excerpts:\s*\n(?P<context>.*?)\n\nCustomer question:",
    re.DOTALL | re.IGNORECASE,
)
_QUESTION_RE = re.compile(r"Customer question:\s*(?P<q>[^\n]+)")


class RuleBasedProvider(LLMProvider):
    """Compose calm, professional replies strictly from provided SOP context."""

    def complete(self, system: str, user: str) -> ProviderResponse:
        ctx_match = _CONTEXT_RE.search(user)
        q_match = _QUESTION_RE.search(user)
        context = ctx_match.group("context").strip() if ctx_match else ""
        question = q_match.group("q").strip() if q_match else user.strip()

        if not context or context.startswith("(No matching"):
            return ProviderResponse(text=FAQ_FALLBACK_NO_SOP, confidence=0.0)

        sections = _sections_from_context(context)
        if not sop_supports_answer(question, sections):
            return ProviderResponse(text=FAQ_FALLBACK_NO_SOP, confidence=0.0)

        first_block = context.split("\n\n---\n\n")[0] if context else context
        answer_bits = _extract_facts(first_block, question=question)
        if not answer_bits:
            return ProviderResponse(text=FAQ_FALLBACK_UNGROUNDED, confidence=0.2)

        body = answer_bits[0]
        reply = (
            f"Thanks for asking. {body} "
            "If you'd like to book or need anything else, I'm happy to help."
        )
        return ProviderResponse(text=reply, confidence=0.75)


def _sections_from_context(context: str) -> list[SOPSection]:
    sections: list[SOPSection] = []
    for block in context.split("\n\n---\n\n"):
        block = block.strip()
        if not block.startswith("## "):
            continue
        lines = block.split("\n", 1)
        title = lines[0].lstrip("#").strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        sections.append(SOPSection(title=title, body=body))
    return sections


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
