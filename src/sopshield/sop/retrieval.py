"""Simple lexical retrieval over SOP sections (no external embeddings API)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from sopshield.sop.loader import SOPDocument, SOPSection

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "when",
        "where",
        "how",
        "do",
        "does",
        "did",
        "can",
        "could",
        "you",
        "your",
        "i",
        "me",
        "my",
        "we",
        "our",
        "on",
        "in",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "if",
        "it",
        "be",
        "with",
        "about",
        "tell",
    }
)


@dataclass(frozen=True)
class RetrievalResult:
    sections: list[SOPSection]
    confidence: float
    matched_terms: list[str]

    @property
    def has_match(self) -> bool:
        return bool(self.sections) and self.confidence > 0.0


def tokenize_query(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP}


def _tokenize(text: str) -> set[str]:
    return tokenize_query(text)


def retrieve(sop: SOPDocument, query: str, top_k: int = 3) -> RetrievalResult:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return RetrievalResult(sections=[], confidence=0.0, matched_terms=[])

    scored: list[tuple[float, SOPSection, list[str]]] = []
    for section in sop.sections:
        section_tokens = _tokenize(section.title + " " + section.body)
        overlap = query_tokens & section_tokens
        if not overlap:
            continue
        # BM25-lite: favor overlap density and title hits
        title_tokens = _tokenize(section.title)
        title_boost = 1.5 if overlap & title_tokens else 1.0
        score = (len(overlap) / math.sqrt(len(section_tokens) + 1)) * title_boost
        scored.append((score, section, sorted(overlap)))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return RetrievalResult(sections=[], confidence=0.0, matched_terms=[])

    best_score, best_section, matched = scored[0]
    title_tokens = _tokenize(best_section.title)
    title_overlap = bool(set(matched) & title_tokens)
    # Favor proportion of query terms matched (auditable for escalation threshold)
    coverage = len(matched) / max(len(query_tokens), 1)
    confidence = min(1.0, coverage * (1.25 if title_overlap else 1.0) + best_score * 0.15)
    top = [s for _, s, _ in scored[:top_k]]
    return RetrievalResult(sections=top, confidence=confidence, matched_terms=matched)
