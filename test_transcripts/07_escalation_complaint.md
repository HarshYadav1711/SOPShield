# Escalation — billing / service complaint

**SOP:** `bloom_aesthetics_demo`  
**Command:**

```bash
python main.py --sop bloom_aesthetics_demo -m "I want to file a complaint, I was overcharged for my filler appointment"
```

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** I want to file a complaint, I was overcharged for my filler appointment

**Assistant:** I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account. Support email: support@bloom-aesthetics.example (business hours).

---

## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
Booking or appointment

### 2. Collected details
- Mentioned service (not fully qualified): Dermal fillers

### 5. Escalation reason
- **complaint**: Complaint, refund, or service-harm language detected.
- Operator note: Review complaint and billing/service notes before contact. (complaint)

### 6. Recommended next action
Open complaint ticket; supervisor review before clinical discussion.

---

**Checks**

- Complaint lexicon matched (`complaint`, `overcharged`) before FAQ
- No refund amount or resolution invented
- “Filler” may be noted as a mentioned service only—not a qualified lead
