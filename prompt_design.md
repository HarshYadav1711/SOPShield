# SOPShield — Prompt & Safety Design

This document explains how SOPShield stays grounded in the Standard Operating Procedures (SOP), when it escalates, and how tone is enforced. The canonical system prompt lives in `src/sopshield/prompts.py`.

---

## Full system prompt (FAQ stage)

```
You are the virtual front-desk assistant for Bloom Aesthetics Clinic.

RULES (non-negotiable):
1. Answer ONLY using the SOP excerpts provided in the user message. Never invent hours, prices, policies, or services.
2. If the excerpts do not contain the answer, say you do not have that information and that a human team member will follow up. Do not guess.
3. Do not provide medical diagnoses, treatment guarantees, or legal advice.
4. Tone: calm, professional, warm, and concise — appropriate for a small aesthetics clinic.
5. Do not mention internal tools, retrieval scores, or that you are an AI unless asked directly.

When answering FAQs, cite only facts present in the excerpts. Prefer short paragraphs or bullet points.
```

Each user turn includes **only** retrieved SOP sections (not the full document), formatted as:

```
SOP excerpts:
{retrieved sections}

Customer question: {question}

Reply using only the excerpts above. If the answer is not in the excerpts, say so and offer a human handoff.
```

---

## Hallucination prevention

| Layer | Mechanism |
|-------|-----------|
| **Retrieval gate** | Questions must match SOP sections above a confidence threshold (`0.35`) before any model is called. |
| **Context isolation** | The model never sees the full SOP—only top-ranked sections for that turn. |
| **Instruction** | System + user prompts forbid inventing facts and require an explicit “not in guidelines” response. |
| **Post-check** | `_response_grounded()` flags replies that introduce many numeric claims absent from retrieved text. |
| **Offline default** | `RuleBasedProvider` composes answers only from retrieved lines—no generative drift in default mode. |
| **SOP gap log** | Unanswered topics are stored on the session for the summary’s “SOP gaps” section. |

If retrieval fails, the workflow **does not** call the model with empty context; it returns a fixed safe message and escalates when appropriate.

---

## Confidence-based escalation logic

Confidence comes from lexical overlap between the customer message and SOP section titles/bodies (BM25-lite scoring, normalized to `0–1`).

| Signal | Threshold / rule | Escalation reason |
|--------|------------------|-------------------|
| Low retrieval confidence | `< 0.35` | `low_confidence` |
| No SOP support for answer | `answered_from_sop=False` | `sop_gap` (first time) |
| Same failure twice | `unanswered_streak >= 2` | `repeated_unanswered` |
| Angry language | Regex lexicon | `angry_sentiment` |
| Complaint / refund / clinical harm | Regex lexicon | `complaint` |
| Explicit human request | Regex lexicon | `explicit_escalation` |
| Out-of-scope topics | Regex (insurance, surgery, financing, etc.) | `out_of_scope` |

Escalation is **rule-first** (auditable in `escalation.py`). Optional LLM backends do not override these triggers.

Handoff copy is fixed and aligned with the SOP:

> *I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account.*

---

## Tone & persona reasoning

**Persona:** Front-desk coordinator at a boutique aesthetics clinic—not a generic “AI helper.”

**Tone principles:**
- **Calm** — de-escalation language; no arguing or over-apologizing.
- **Professional** — complete sentences, no slang; suitable for SMB owners reviewing transcripts.
- **Human** — brief empathy (“Thanks for asking”) without performative filler.
- **Scoped** — short answers; offer booking help only when relevant to the SOP.

Qualification questions are templated (not generated) so they stay consistent and reviewable. Summaries use a deterministic template by default; optional LLM summary mode must still receive the full transcript and explicit gap list.

---

## Stage-specific prompts

### Stage 2 — Qualification

No LLM generation. Three fixed questions:
1. Service interest  
2. New vs returning client  
3. Contact for follow-up  

Intro: warm transition after the first successful FAQ answer.

### Stage 4 — Summary

System prompt requires sections: Customer intent, Key details, SOP gaps, Next action, Escalation status. Default path uses `format_summary_deterministic()` so summaries are always available without an API.

---

## Provider abstraction

All stages call `LLMProvider.complete(system, user)`:

| Provider | Use case |
|----------|----------|
| `rule` (default) | Free, deterministic, ideal for tests and demos |
| `ollama` | Local free models via Ollama |
| `openai` | Optional; isolated in `openai_api.py` |

Swapping providers does not change escalation rules or retrieval gates.

---

## Design tradeoffs

- **Lexical retrieval** avoids embedding API costs but may miss paraphrases → mitigated by conservative escalation on low confidence.
- **Early transition to qualification** after the first grounded FAQ keeps sessions short for assessment; transcripts demonstrate each stage explicitly.
- **Regex sentiment** is imperfect but transparent; production systems might add a lightweight classifier later without changing workflow shape.
