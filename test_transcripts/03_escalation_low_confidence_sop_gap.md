# Escalation — low confidence (SOP miss)

**SOP:** `bloom_aesthetics_demo`  
**Command:**

```bash
python main.py --sop bloom_aesthetics_demo -m "Do you offer international shipping of skincare products?"
```

**Trigger:** Topic not in SOP; retrieval scores below threshold (0.35)

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** Do you offer international shipping of skincare products?

**Assistant:** I don't have that information in our clinic guidelines. A member of our front-desk team will follow up with you shortly.

I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account. Support email: support@bloom-aesthetics.example (business hours).

---

## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
General inquiry: Do you offer international shipping of skincare products?

### 2. Collected details
- None collected.

### 3. Unanswered or unsupported questions
- Do you offer international shipping of skincare products?

### 4. SOP gaps
- Do you offer international shipping of skincare products?

### 5. Escalation reason
- **low_confidence**: Retrieval confidence 0.22 below threshold 0.35.
- Operator note: Low SOP match — verify answer manually before replying. (low_confidence)

### 6. Recommended next action
Research SOP/update KB, then respond with verified information.

---

**Checks**

- No fabricated shipping policy
- Fallback copy from SOP; handoff message appended
- Gap logged for SOP owner review

**Related rule:** If confidence were ≥ 0.35 but lines still did not answer the question, reason would be `sop_gap` instead (`tests/test_escalation.py::test_sop_gap_when_confidence_ok`).
