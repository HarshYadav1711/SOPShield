# SOPShield

SOPShield is a **SOP-first** customer support workflow for SMB clinics. It simulates a full chat session in four stages—FAQ, lead qualification, escalation detection, and a structured handoff summary—while answering **only** from a documented Standard Operating Procedures file.

**Sample business:** [Bloom Aesthetics Clinic](data/bloom_aesthetics_sop.json) (hours, services, booking, cancellation, escalation rules). A [markdown copy](data/bloom_aesthetics_sop.md) is also available.

---

## Quick start

**Requirements:** Python 3.11+

```bash
cd SOPShield
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -e ".[dev]"
sopshield
```

Interactive CLI: type your questions, then `quit` to end. Transcripts are saved under `transcripts/`.

**Non-interactive (CI / demos):**

```bash
sopshield -m "What are your hours on Saturday?" -m "Botox" -m "new client" -m "555-0142"
```

---

## Workflow stages

| Stage | Behavior |
|-------|----------|
| **1. FAQ** | Retrieves relevant SOP sections, answers from excerpts only |
| **2. Qualification** | Asks 3 structured questions; stores answers on the session |
| **3. Escalation** | Rule-based detection: low confidence, out-of-scope, anger, complaints, explicit human request, repeated unanswered questions |
| **4. Summary** | Structured summary: intent, key details, SOP gaps, next action, escalation status |

See [prompt_design.md](prompt_design.md) for prompts, safety layers, and escalation thresholds.

---

## Providers (default = free)

| Flag | Backend | Notes |
|------|---------|--------|
| `--provider rule` | Rule-based (default) | No API keys; uses retrieved SOP text |
| `--provider ollama` | [Ollama](https://ollama.com) | Local models; run `ollama serve` first |
| `--provider openai` | OpenAI API | `pip install -e ".[openai]"` + `OPENAI_API_KEY` |

```bash
sopshield --provider ollama
sopshield --provider openai --llm-summary
```

---

## Project layout

```
data/bloom_aesthetics_sop.json # Structured source of truth (default)
data/bloom_aesthetics_sop.md   # Markdown alternative (.md also supported)
src/sopshield/
  cli.py                       # CLI entry
  workflow.py                  # Stage orchestration
  escalation.py                # Escalation rules
  sop/                         # Load + retrieve SOP
  stages/                      # FAQ, qualification, summary
  providers/                   # Pluggable LLM backends
prompt_design.md               # Prompts & safety design
test_transcripts/              # Sample conversations per behavior
tests/                         # Pytest suite
transcripts/                   # Runtime session logs (gitignored)
```

---

## Running tests

```bash
pytest
```

---

## Sample transcripts

Review expected behaviors in [test_transcripts/](test_transcripts/):

- FAQ success from SOP  
- Full qualification + summary  
- Escalation: low confidence / SOP gap  
- Escalation: angry sentiment  
- Escalation: out-of-scope  
- Escalation: explicit human request  
- Escalation: complaint  

---

## Tradeoffs & limitations

| Choice | Why | Limitation |
|--------|-----|------------|
| Lexical retrieval | No embedding API or cost | May miss unusual paraphrases → escalates safely |
| Rule-based default | Reproducible demos without GPU/API | Less natural phrasing than a local LLM |
| Regex escalation | Auditable for reviewers | Not a full sentiment model |
| Single SOP markdown file | Easy to swap fictional SMB | No versioning UI |
| CLI only | Matches assessment scope | No web widget |

**Not included (by design):** database, dashboard, multi-agent orchestration, frontend, or bonus features not in the rubric.

---

## Walkthrough video

Record a short screen capture showing:

1. `sopshield` greeting  
2. An FAQ answered from the SOP (e.g., Saturday hours)  
3. Qualification questions completed  
4. One escalation example (`sopshield -m "I need a manager"`)  
5. Transcript file in `transcripts/` and a glance at `prompt_design.md`

---

## Data source

All factual answers come from `data/bloom_aesthetics_sop.json` (or `.md`). To use another fictional SMB, replace that file—JSON uses a `sections` array with `title` and `body`; markdown uses `##` headings for retrieval.

---

## License

Assessment / portfolio use. SOP content is fictional sample data for Bloom Aesthetics Clinic.
