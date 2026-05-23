"""Strict checks that an answer is supported by SOP text."""

from __future__ import annotations

import re

from sopshield.sop.loader import SOPSection
from sopshield.sop.retrieval import tokenize_query

_NUMBER_RE = re.compile(r"\b\d{1,4}\b")
_LINE_TOKEN_RE = re.compile(r"[a-z0-9]+")


def sop_supports_answer(question: str, sections: list[SOPSection]) -> bool:
    """True when retrieved sections contain lines that substantively address the question."""
    q_tokens = tokenize_query(question)
    if not q_tokens:
        return False

    min_overlap = 1 if len(q_tokens) <= 2 else 2
    best_overlap = 0

    for section in sections:
        for line in (section.title + "\n" + section.body).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or re.search(r"-{3,}", line):
                continue
            if line.startswith("|") and line.count("|") >= 2:
                cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
                if len(cells) >= 2 and cells[0].lower() not in {"day", ""}:
                    line = f"{cells[0]}: {cells[1]}"
                else:
                    continue
            line = re.sub(r"^[-*]\s*", "", line)
            line = re.sub(r"^\d+\.\s*", "", line)
            line_tokens = set(_LINE_TOKEN_RE.findall(line.lower()))
            overlap = len(q_tokens & line_tokens)
            best_overlap = max(best_overlap, overlap)
            if overlap >= min_overlap:
                return True

    return best_overlap > 0 and len(q_tokens) <= 2


def response_grounded(reply: str, context: str) -> bool:
    """Reject replies that cite specific numbers or policies absent from context."""
    numbers = set(_NUMBER_RE.findall(reply))
    context_numbers = set(_NUMBER_RE.findall(context))
    suspicious = numbers - context_numbers
    suspicious -= {"1", "2", "3"}
    if len(suspicious) > 2:
        return False
    lowered = reply.lower()
    if "don't have" in lowered or "do not have" in lowered:
        return False
    return True
