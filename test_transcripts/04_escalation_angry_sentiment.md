# Escalation — angry / frustrated tone

**SOP:** `bloom_aesthetics_demo`  
**Command:**

```bash
python main.py --sop bloom_aesthetics_demo -m "this is ridiculous, I'm furious about my appointment"
```

**Trigger:** Angry sentiment regex fires before FAQ generation

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** this is ridiculous, I'm furious about my appointment

**Assistant:** I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account. Support email: support@bloom-aesthetics.example (business hours).

---

## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
Booking / appointment; needs callback.

### 2. Collected details
- None.

### 3. Unanswered or unsupported questions
- None.

### 4. SOP gaps
- None.

### 5. Escalation reason
- angry_sentiment: Upset or frustrated tone
- Note: Upset — priority callback.

### 6. Recommended next action
Same-day callback; acknowledge frustration first.

---

**Checks**

- No FAQ answer attempted; no invented compensation or reschedule promise
- Summary gives operator intent, reason, and a concrete next step
- Escalation recorded in runtime transcript under escalation log
