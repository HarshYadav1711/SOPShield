# SOPShield

SOPShield is a **SOP-first** front-desk assistant for small clinics. It runs a full support conversation in the terminal: answer policy questions from a written Standard Operating Procedures file, collect light lead qualification, detect when a human should take over, and produce a structured handoff summary.

Facts come from your SOP—not from model memory. If the document does not cover a topic, the assistant says so and escalates instead of guessing.

**Sample businesses**

| SOP id | Use case |
|--------|----------|
| `bloom_aesthetics_demo` | Boutique medical aesthetics (default) |
| `northstar_dental` | Dental practice with extended escalation patterns |

---

## What it does

- **Grounded FAQ** — Retrieves relevant SOP sections and answers only from those excerpts.
- **Lead qualification** — Asks a small set of templated questions (service interest, new vs returning, contact), skipping fields already inferred from the chat.
- **Escalation** — Rule-based detection for low retrieval confidence, SOP gaps, complaints, angry tone, pricing pressure, clinical safety, out-of-scope topics, and explicit requests for a person.
- **Session summary** — Six-section operator summary: intent, collected details, unanswered questions, SOP gaps, escalation reason, recommended next action.
- **Transcripts** — Every session is saved under `transcripts/` for review.

See [prompt_design.md](prompt_design.md) for prompts, safety layers, and escalation thresholds. Example conversations are in [test_transcripts/](test_transcripts/).

---

## How the workflow works

```
Greeting (FAQ stage)
    → Customer asks a policy question
    → Retrieve SOP sections → answer or safe fallback
    → [If grounded] Qualification (1–3 templated questions)
    → Summary (deterministic by default)
```

Escalation rules run **before** FAQ generation (e.g. “speak to a manager”) and **after** each FAQ attempt (e.g. low confidence). On escalation, the customer sees the SOP handoff message and the same structured summary as a normal session end.

| Stage | Implementation |
|-------|----------------|
| 1. FAQ | `stages/faq.py` + retrieval + optional LLM |
| 2. Qualification | `stages/qualification.py` (no LLM) |
| 3. Escalation | `escalation.py` (regex + confidence rules) |
| 4. Summary | `stages/summary.py` (template default; optional LLM) |

---

## How to run it

**Requirements:** Python 3.11+

```bash
cd SOPShield
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -e ".[dev]"
python main.py
```

Interactive mode: type questions, then `quit` to end. Transcripts are written to `transcripts/`.

**Choose a business SOP**

```bash
python main.py --sop bloom_aesthetics_demo
python main.py --sop northstar_dental
python main.py --list-sops
```

**Non-interactive (scripts, CI, demos)**

```bash
python main.py --sop bloom_aesthetics_demo -m "What are your hours on Saturday?" -m "Botox" -m "new client" -m "555-0142"
```

After install, the same entry point is available as `sopshield`.

---

## Dependencies

| Component | Default install | Optional |
|-----------|-----------------|----------|
| Runtime | Python 3.11+, stdlib only | — |
| Package | `pip install -e .` | — |
| Tests | — | `pip install -e ".[dev]"` → pytest |
| Local LLM | — | `pip install -e ".[ollama]"` + [Ollama](https://ollama.com) running |
| OpenAI | — | `pip install -e ".[openai]"` + `OPENAI_API_KEY` |

Core dependencies are intentionally empty in `pyproject.toml` so the default path runs offline with `RuleBasedProvider`.

**Providers**

| Flag | Backend |
|------|---------|
| `--provider rule` | Deterministic answers from retrieved SOP text (default) |
| `--provider ollama` | Local model via Ollama |
| `--provider openai` | OpenAI API |

```bash
sopshield --provider ollama
sopshield --provider openai --llm-summary
```

---

## Project layout

```
data/                    # SOP JSON (and optional .md) per business
main.py                  # CLI wrapper
src/sopshield/
  cli.py                 # Argument parsing, interactive loop
  workflow.py            # Stage orchestration
  escalation.py          # Escalation rules
  prompts.py             # System / user prompt templates
  sop/                   # Load, list, retrieve, ground
  stages/                # FAQ, qualification, summary
  providers/             # rule, ollama, openai
prompt_design.md         # Prompt and safety rationale
test_transcripts/        # Reference conversations
tests/                   # Pytest
transcripts/             # Runtime logs (gitignored)
```

---

## Running tests

```bash
pytest
```

---

## Tradeoffs and limitations

| Choice | Benefit | Cost |
|--------|---------|------|
| Lexical retrieval | No embedding API; scores are inspectable | Paraphrases may score low → escalation |
| Rule-based default | Reproducible without GPU or API keys | Less natural phrasing than a tuned LLM |
| Regex escalation | Auditable, fast, unit-testable | Not a full sentiment or intent model |
| JSON SOP per business | Easy to swap or version in git | No built-in SOP editor UI |
| CLI only | Simple to ship and demo | No web widget or CRM integration |
| Single-session FAQ miss → handoff | Fast, safe default | `repeated_unanswered` is defined for streak ≥ 2 but the CLI escalates on the first unsupported FAQ today |

SOPShield does **not** include a database, admin dashboard, multi-agent orchestration, or a customer-facing web UI. Those are out of scope for this reference implementation.

---

## Why the implementation is intentionally minimal

The goal is a **reviewable safety pattern**, not a production SaaS stack.

- **One orchestrator** (`workflow.py`) makes the stage order obvious.
- **Rules own escalation** so behavior does not change when you swap LLM providers.
- **Deterministic summary by default** guarantees every session ends with the same six sections for operators.
- **SOP as data** lets a clinic owner edit policy in JSON/Markdown without touching Python.
- **Zero required API keys** keeps CI and local demos frictionless.

You can add embeddings, a web channel, or CRM webhooks later without rewriting the stage model—the boundaries are already separated.

---

## Adding a new business

1. Add `data/your_clinic.json` with `document`, `contact`, `conversation`, `qualification`, `escalation`, and `sections`.
2. Run `python main.py --sop your_clinic`.

Factual answers always originate from that file. See `data/bloom_aesthetics_demo.json` for a complete example.

---

## License

Portfolio / demonstration use. SOP content is fictional sample data unless you replace it with your own policies.
