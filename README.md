# SOPShield

SOPShield is a **SOP-first** front-desk assistant for small clinics. It runs a full support conversation in the terminal: answer policy questions from a written Standard Operating Procedures file, collect light lead qualification, detect when a human should take over, and produce a structured handoff summary.

Facts come from your SOP—not from model memory. If the document does not cover a topic, the assistant says so and escalates instead of guessing.

**Runtime path:** `main.py` → `sopshield.cli` → `workflow.py` (stages + escalation). All application code lives under `src/sopshield/`; SOP content lives in `data/` as versioned JSON.

**Sample businesses** (one file per business; see [data/README.md](data/README.md))

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

### Design rationale

- **Lightweight workflow** — Four fixed stages (FAQ → qualification → summary, with escalation evaluated throughout) keep transcripts easy to audit. There is no agent graph or tool loop; each turn has one job.
- **Deterministic escalation** — Handoff decisions are regex and threshold rules in `escalation.py`, not model judgment. The same input yields the same reason code, which matters for compliance review and regression tests.
- **Strict SOP grounding** — Retrieval gates, excerpt-only prompts, and post-checks limit invented policy. The default `RuleBasedProvider` composes answers from retrieved lines only.
- **Multi-SOP support** — Each business is a JSON file (`document.id` + sections). The loader validates required fields and resolves `--sop <id>` without code changes, so one codebase serves multiple clinic profiles.

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

| Stage | Module |
|-------|--------|
| Orchestration | `workflow.py`, `session.py` |
| 1. FAQ | `stages/faq.py`, `sop/retrieval.py`, `sop/grounding.py`, optional `providers/` |
| 2. Qualification | `stages/qualification.py` (templated; no LLM) |
| 3. Escalation | `escalation.py` (lexical rules + confidence; runs before/after FAQ) |
| 4. Summary | `stages/summary.py` (deterministic template default) |

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

## Architecture

```
main.py                      # Entry: delegates to sopshield.cli
pyproject.toml               # Package metadata; optional [dev|ollama|openai]
data/
  README.md                  # SOP schema and required fields
  bloom_aesthetics_demo.json # Default business SOP
  northstar_dental.json      # Second business (extended escalation config)
src/sopshield/
  cli.py                     # Interactive / -m batch mode, transcript save
  workflow.py                # Stage state machine
  session.py                 # Turns, qualification state, transcript I/O
  escalation.py              # Rule-based handoff triggers
  prompts.py                 # FAQ / summary prompt templates
  sop/
    loader.py                # JSON load, resolve --sop id, list_sops
    validation.py            # Required-field checks at load time
    retrieval.py             # Lexical section retrieval
    grounding.py             # Answer support and numeric post-check
  stages/                    # faq, qualification, summary
  providers/                 # rule (default), ollama, openai
prompt_design.md             # Prompt and safety design notes
test_transcripts/            # Reference conversations
tests/                       # Pytest
transcripts/                 # Per-session logs (gitignored)
```

---

## Running tests

```bash
pytest
```

---

## Design tradeoffs

| Choice | Why | Limitation |
|--------|-----|------------|
| Staged workflow vs. single agent | Predictable transcripts; clear operator handoff sections | Less flexible than free-form chat |
| Lexical retrieval | No embedding service; scores are explainable in logs | Unusual phrasing may score low → safe escalation |
| Rule-based escalation | Same triggers in tests and production; provider-agnostic | Regex is not a full sentiment model |
| Rule-based default provider | Runs offline; no API keys for CI | Wording is less natural than an LLM |
| JSON SOP per business | Policy changes without redeploying code | No admin UI for editing SOPs |
| CLI channel | Thin surface for integration testing | No web widget or CRM connector in-tree |

The scope is intentionally narrow: one orchestrator, file-based SOPs, and optional LLM only where phrasing helps (FAQ/summary). A database, dashboard, or multi-agent layer would sit outside this package.

---

## Operational safety

- **Load-time validation** — `sop/validation.py` rejects SOPs missing `business_name`, services, escalation rules, or booking policy before a session starts.
- **Retrieval gate** — FAQ runs only when section match confidence meets the SOP threshold (default `0.35`).
- **Excerpt isolation** — Models see retrieved sections for the current turn, not the full document.
- **Escalation precedence** — Complaints, clinical safety, and explicit human requests are checked before generation; low confidence and SOP gaps trigger handoff after an attempted answer.
- **Fixed handoff copy** — Customer-facing escalation text comes from the SOP, not from model improvisation.
- **Deterministic summary** — Six-section operator summary is template-built by default; escalation status is not re-decided by the model.
- **Session transcripts** — Full turn log under `transcripts/` for post-incident review.

Details: [prompt_design.md](prompt_design.md).

---

## Adding a new business

1. Add `data/your_clinic.json` with `document`, `contact`, `conversation`, `qualification`, `escalation`, and `sections`.
2. Run `python main.py --sop your_clinic`.

Factual answers always originate from that file. See `data/README.md` and `data/bloom_aesthetics_demo.json` for the schema and a complete example.

---

## License

Use and modify as needed for internal workflows. Bundled SOP content is fictional sample data unless you replace it with your own policies.
