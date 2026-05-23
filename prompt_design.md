# Prompt & safety design

SOPShield treats the Standard Operating Procedures (SOP) as the only source of truth for customer-facing facts. Prompts, retrieval gates, and escalation rules exist to keep answers accurate, auditable, and appropriate for a small clinic front desk.

The canonical prompt strings live in `src/sopshield/prompts.py`. This document explains what they do and why.

---

## Full system prompt (FAQ stage)

The FAQ system prompt is built per business from the loaded SOP (`system_prompt(sop)`). For **Bloom Aesthetics Clinic**, it resolves to:

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

Each FAQ turn also sends a **user** message shaped like this (from `FAQ_USER_TEMPLATE`):

```
SOP excerpts:
{retrieved sections — never the full SOP file}

Customer question: {question}

Reply using only the excerpts above. If the answer is not in the excerpts, say so and offer a human handoff.
```

### Supplementary prompts (other stages)

**Qualification** does not use an LLM. Copy comes from the SOP JSON (`qualification_intro`, question templates, acknowledgments).

**Summary (optional LLM)** — `summary_system(sop)`:

```
You produce structured session summaries for {business_name} support handoffs.
Use ONLY facts from the conversation transcript and notes provided.
Flag any SOP gaps explicitly. Do not invent customer details.
Escalation was already decided by rules — do not change escalation status.
```

**Handoff note (optional LLM)** — one sentence for operators; must not invent outcomes:

```
You write one short sentence for a clinic front-desk operator explaining why a chat was escalated.
Use only the reason and customer message given. Do not invent facts or promise outcomes.
```

Deterministic summaries and handoff notes are the default so handoffs work without an API.

---

## Tone and persona

**Persona:** A front-desk coordinator at a boutique aesthetics practice—not a generic chatbot or “AI assistant.”

| Principle | Why it matters |
|-----------|----------------|
| **Calm** | Many chats are scheduling or policy questions; tone should not amplify stress. |
| **Professional** | Owners and compliance reviewers read transcripts; language should hold up in QA. |
| **Warm, not chatty** | Brief empathy (“Thanks for asking”) without filler or exaggerated enthusiasm. |
| **Concise** | Mobile customers skim; one clear answer beats a paragraph of disclaimers. |

The tone string is stored in each SOP (`conversation.tone`) so a dental practice and an aesthetics clinic can share the same engine with different voice guidelines.

Qualification uses **fixed templates** (not model-generated questions) so intake stays consistent across sessions and easy to audit.

---

## Hallucination prevention

Generative models will fill gaps if allowed. SOPShield layers constraints so “helpful” guessing is harder than saying “I don’t know.”

| Layer | What it does |
|-------|----------------|
| **Retrieval gate** | FAQ runs only when lexical match confidence meets the SOP threshold (default `0.35`). |
| **Context isolation** | The model sees top-ranked **sections**, not the full SOP—reducing bleed from unrelated policies. |
| **Support check** | `sop_supports_answer()` requires token overlap between the question and retrieved lines before composing a reply. |
| **Prompt contract** | System + user prompts forbid inventing hours, prices, policies, or services. |
| **Post-check** | `response_grounded()` flags replies that introduce many numeric claims absent from retrieved text. |
| **Safe fallbacks** | Fixed copy when retrieval fails or the answer cannot be grounded (`faq_fallback_no_sop`, `faq_fallback_ungrounded`). |
| **Rule-based default** | `RuleBasedProvider` extracts lines from excerpts only—no generative drift in the default path. |
| **SOP gap log** | Unanswered topics are stored on the session and appear in the summary for SOP owners. |

If retrieval fails, the workflow does **not** call the model with empty context. It returns the configured fallback and evaluates escalation.

---

## Confidence-based escalation

Retrieval confidence is a normalized `0–1` score from BM25-style lexical overlap between the customer message and SOP section titles/bodies (`src/sopshield/sop/retrieval.py`).

When a question cannot be answered from the SOP (`answered_from_sop=False`), `check_message()` in `escalation.py` applies:

1. Increment `unanswered_streak`.
2. If `unanswered_streak >= unanswered_limit` (default **2**) → `repeated_unanswered`.
3. Else if `retrieval_confidence < confidence_threshold` (default **0.35**) → `low_confidence`.
4. Else → `sop_gap` (matched sections exist but do not substantively answer the question).

**Immediate lexical escalations** (evaluated before FAQ generation) take priority:

| Signal | Reason code |
|--------|-------------|
| Explicit human / manager request | `explicit_escalation` |
| Complaint, refund, harm language | `complaint` |
| Angry or frustrated tone | `angry_sentiment` |
| Price match / discount pressure | `pricing_negotiation` |
| Clinical safety (pregnancy, meds, symptoms, etc.) | `sensitive_unsupported` |
| Out-of-scope topics (financing, surgery, legal, etc.) | `out_of_scope` |

Optional LLM backends **do not** override these triggers. Handoff copy comes from the SOP (`conversation.handoff_message`).

**Note:** The shipped CLI ends the session on the first unsupported FAQ. The `repeated_unanswered` path is still defined and tested (`tests/test_escalation.py`) for consecutive misses when streak state is preserved—useful if multi-turn FAQ before handoff is added later.

---

## Why answers are constrained to SOP data only

SMB clinics run on written policies: hours, cancellation fees, what services exist, when to escalate. A wrong hour or invented refund policy creates real liability and rework.

SOP-only answers give:

- **Traceability** — reviewers can compare the reply to a specific SOP section.
- **Updateability** — change the JSON/Markdown SOP, not prompt fine-tuning, when policy changes.
- **Honest limits** — “not in our guidelines” is preferable to a confident wrong answer.
- **Role boundaries** — front-desk SOPs are not medical charts; the bot should not diagnose or negotiate custom pricing.

The product is deliberately **not** a general knowledge assistant. Out-of-scope and sensitive patterns exist to route those threads to humans early.

---

## Why the workflow uses strict stages

The pipeline is fixed: **FAQ → Qualification → Escalation (continuous) → Summary**.

```
Customer message
       │
       ▼
┌──────────────┐     lexical rules (complaint, human request, …)
│  Escalation  │◄────────────────────────────────────────────┐
│  pre-check   │                                              │
└──────┬───────┘                                              │
       │ no immediate trigger                                  │
       ▼                                                      │
┌──────────────┐     retrieval + grounded answer              │
│     FAQ      │──────────────────────────────────────────────┤
└──────┬───────┘                                              │
       │ first grounded FAQ                                    │
       ▼                                                      │
┌──────────────┐                                              │
│Qualification │  templated intake (service, client, contact)│
└──────┬───────┘                                              │
       │ complete                                              │
       ▼                                                      │
┌──────────────┐     rule-based or optional LLM              │
│   Summary    │                                              │
└──────────────┘                                              │
       ▲                                                      │
       └──────── escalation anytime ──────────────────────────┘
```

**Why stages are separated:**

| Stage | Rationale |
|-------|-----------|
| **FAQ** | Answer policy questions from retrieved excerpts only; separate “what we know” from “who you are.” |
| **Qualification** | Structured intake for booking handoff; no model creativity on required fields. |
| **Escalation** | Deterministic, testable rules; same behavior with `rule`, Ollama, or OpenAI. |
| **Summary** | Operator artifact with fixed sections; escalation status is never re-decided by the model. |

Mixing FAQ and intake in one free-form chat makes transcripts hard to review and lets models skip intake or invent qualification data. Stages keep each turn’s job obvious in logs under `transcripts/`.

---

## Provider abstraction

Generative steps (FAQ reply, optional summary/handoff note) call `LLMProvider.complete(system, user)`. Everything else—retrieval, grounding checks, escalation, qualification—is local and provider-agnostic.

**Default runtime (`rule`):** offline, stdlib-only, deterministic answers from retrieved SOP lines. This is the intended development and review path: no API keys, reproducible transcripts, and the same escalation behavior as production-like configs.

**Optional backends** swap wording only:

| Provider | Runtime | Role |
|----------|---------|------|
| `rule` (default) | Offline / local | Deterministic FAQ from excerpts; CI and demos |
| `ollama` | Local machine | Natural phrasing via Ollama; data stays on-device |
| `openai` | Cloud API | Hosted model (`pip install -e ".[openai]"` + API key) |

**Why abstract providers?** Teams can demo and test the full workflow without a model service, then enable Ollama or OpenAI when available—without changing stage boundaries, thresholds, or handoff rules.

Swapping `--provider` does not change retrieval thresholds, escalation rules, or qualification templates.

---

## Design tradeoffs

- **Lexical retrieval** avoids embedding cost and keeps behavior explainable; unusual phrasing may score low → safe escalation.
- **First grounded FAQ → qualification** keeps sessions short while still demonstrating each stage in transcripts.
- **Regex sentiment** is imperfect but transparent; a classifier could be added later without changing stage boundaries.
