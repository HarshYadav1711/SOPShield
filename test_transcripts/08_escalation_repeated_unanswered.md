# Escalation — repeated unanswered (rule) and first-strike CLI behavior

**SOP:** `bloom_aesthetics_demo`

This documents two related behaviors.

## A. Shipped CLI (first unsupported FAQ → handoff)

**Command:**

```bash
python main.py --sop bloom_aesthetics_demo -m "Do you sell pet grooming kits?" -m "What colors of pet grooming kits do you have?"
```

The session ends after the **first** off-topic question. The second `-m` is not processed because the workflow is already complete.

**Customer:** Do you sell pet grooming kits?

**Assistant:** I don't have that information in our clinic guidelines. A member of our front-desk team will follow up with you shortly.

I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account. Support email: support@bloom-aesthetics.example (business hours).

**Escalation reason:** `low_confidence` (retrieval confidence 0.00 below threshold 0.35)

---

## B. Escalation rule — second consecutive miss (`repeated_unanswered`)

When `check_message()` runs twice with `answered_from_sop=False` and confidence **above** the threshold, the second call returns `repeated_unanswered`:

```python
# tests/test_escalation.py — streak reaches unanswered_limit (default 2)
check_message("do you ship products internationally", confidence=0.5, answered_from_sop=False, ...)
check_message("what about international shipping", confidence=0.5, answered_from_sop=False, ...)
# → reason: repeated_unanswered
```

**Representative two-turn customer thread (rule validation):**

**Customer:** Do you ship your skincare line to Canada?

**Assistant:** I don't have that information in our clinic guidelines… *(first miss — would be `sop_gap` at confidence 0.5)*

**Customer:** Okay — what about express shipping to Toronto?

**Assistant:** … *(second miss — `repeated_unanswered` when streak logic applies)*

---

**Checks**

- CLI: safe fallback, no invented product catalog, gap logged
- Rule: `unanswered_streak >= 2` maps to `repeated_unanswered` in `escalation.py`
- See [prompt_design.md](../prompt_design.md) for when first-strike handoff vs streak applies
