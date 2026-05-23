# SOPShield

SOPShield is a **SOP-first** customer support workflow for SMB clinics. It simulates a full chat session in four stages—FAQ, lead qualification, escalation detection, and a structured handoff summary—while answering **only** from a documented Standard Operating Procedures file.

**Sample businesses:** [Bloom Aesthetics Demo](data/bloom_aesthetics_demo.json) (assignment example) · [Northstar Dental](data/northstar_dental.json) (advanced escalation workflow)

---

## Quick start

**Requirements:** Python 3.11+

```bash
cd SOPShield
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -e ".[dev]"
python main.py --sop bloom_aesthetics_demo
```

Interactive CLI: type your questions, then `quit` to end. Transcripts are saved under `transcripts/`.

**Select a business SOP:**

```bash
python main.py --sop bloom_aesthetics_demo
python main.py --sop northstar_dental
python main.py --list-sops
```

**Non-interactive (CI / demos):**

```bash
python main.py --sop bloom_aesthetics_demo -m "What are your hours on Saturday?" -m "Botox" -m "new client" -m "555-0142"
```

---

## Workflow stages

| Stage | Behavior |
|-------|----------|
| **1. FAQ** | Retrieves relevant SOP sections, answers from excerpts only |
| **2. Qualification** | Asks 3 structured questions; stores answers on the session |
| **3. Escalation** | Rule-based detection: explicit human request, angry/frustrated tone, complaints, pricing pressure, sensitive clinical questions, out-of-scope, low confidence, repeated unanswered |
| **4. Summary** | Operator summary: intent, collected details, unanswered questions, SOP gaps, escalation reason, next action |

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
data/
  bloom_aesthetics_demo.json   # Assignment example (default)
  northstar_dental.json        # Advanced SMB escalation demo
  bloom_aesthetics_sop.json    # Legacy alias (optional)
  bloom_aesthetics_sop.md      # Markdown alternative (.md also supported)
main.py                        # python main.py --sop <id>
src/sopshield/
  cli.py                       # CLI entry (also: sopshield)
  workflow.py                  # Stage orchestration
  escalation.py                # Escalation rules (SOP-configurable)
  sop/                         # Load, discover, retrieve SOP
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
- Escalation: angry / frustrated sentiment (with full summary)  
- Escalation: out-of-scope  
- Escalation: explicit human request  
- Escalation: complaint  
- Escalation: pricing negotiation  
- Full session: qualification + final summary  

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

All factual answers come from JSON SOP files in `data/`. Each file defines business identity, conversation copy, qualification fields, escalation rules, and retrievable policy sections. Add a new SMB by dropping a new JSON file in `data/` and running `python main.py --sop <id>`.

---

## License

Assessment / portfolio use. SOP content is fictional sample data for Bloom Aesthetics Clinic.
