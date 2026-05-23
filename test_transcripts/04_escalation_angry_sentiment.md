# Transcript: Escalation — angry / frustrated sentiment

**Behavior:** Stage 3 — hostile or frustrated language → immediate handoff + structured summary  
**Command:** `sopshield -m "This is ridiculous, I'm furious about my appointment!"`

---

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

**Validation notes**
- Escalation fires on deterministic regex before any FAQ generation
- No invented remediation or compensation
- Summary gives operator intent, escalation reason, and concrete next step
- Escalation logged in transcript file under `ESCALATION LOG`
