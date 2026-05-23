# Escalation — low confidence (SOP miss)

**SOP:** `bloom_aesthetics_demo`  
**Command:**

```bash
python main.py --sop bloom_aesthetics_demo -m "can you ship your products overseas?"
```

**Trigger:** Topic not in SOP; retrieval scores below threshold (0.35)

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** can you ship your products overseas?

**Assistant:** I don't have that information in our clinic guidelines. A member of our front-desk team will follow up with you shortly.

I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account. Support email: support@bloom-aesthetics.example (business hours).

---

## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
Asked: can you ship your products overseas?

### 2. Collected details
- None.

### 3. Unanswered or unsupported questions
- can you ship your products overseas?

### 4. SOP gaps
- can you ship your products overseas?

### 5. Escalation reason
- low_confidence: Weak SOP match — verify before replying
- Note: Weak SOP match — verify before replying.

### 6. Recommended next action
Check SOP/KB, then reply with verified info.

---

**Checks**

- No fabricated shipping policy
- Fallback copy from SOP; handoff message appended
- Gap logged for SOP owner review

**Related rule:** If confidence were ≥ 0.35 but lines still did not answer the question, reason would be `sop_gap` instead (`tests/test_escalation.py::test_sop_gap_when_confidence_ok`).
