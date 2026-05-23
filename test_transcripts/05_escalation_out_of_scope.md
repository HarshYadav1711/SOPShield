# Escalation — out of scope (financing)

**SOP:** `bloom_aesthetics_demo`  
**Command:**

```bash
python main.py --sop bloom_aesthetics_demo -m "any chance you do a financing plan for laser packages?"
```

**Trigger:** `financing plan` matches configured out-of-scope patterns; SOP says payment plans are not offered

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** any chance you do a financing plan for laser packages?

**Assistant:** I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account. Support email: support@bloom-aesthetics.example (business hours).

---

## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
Asked: any chance you do a financing plan for laser packages?

### 2. Collected details
- Mentioned only: Laser hair removal (not qualified)

### 3. Unanswered or unsupported questions
- None.

### 4. SOP gaps
- None.

### 5. Escalation reason
- out_of_scope: Outside clinic SOP scope
- Note: Off-scope — clarify what we offer.

### 6. Recommended next action
Clarify what the clinic offers; stay in scope.

---

**Checks**

- Immediate handoff; no financing terms invented
- “Laser” in the message may appear in collected details as an inferred mention only
