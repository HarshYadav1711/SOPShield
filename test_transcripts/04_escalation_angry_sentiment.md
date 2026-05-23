# Escalation — angry / frustrated tone

**SOP:** `bloom_aesthetics_demo`  
**Command:**

```bash
python main.py --sop bloom_aesthetics_demo -m "This is ridiculous, I'm furious about my appointment!"
```

**Trigger:** Angry sentiment regex fires before FAQ generation

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** This is ridiculous, I'm furious about my appointment!

**Assistant:** I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account. Support email: support@bloom-aesthetics.example (business hours).

---

## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
Booking or appointment — customer distressed; human follow-up required.

### 2. Collected details
- None collected.

### 3. Unanswered or unsupported questions
- None.

### 4. SOP gaps
- None recorded.

### 5. Escalation reason
- **angry_sentiment**: Customer tone appears angry or distressed.
- Operator note: De-escalate; customer upset — prioritize callback. (angry_sentiment)

### 6. Recommended next action
Senior front-desk callback same day; acknowledge frustration first.

---

**Checks**

- No FAQ answer attempted; no invented compensation or reschedule promise
- Summary gives operator intent, reason, and a concrete next step
- Escalation recorded in runtime transcript under escalation log
