# Transcript: Full session — FAQ, qualification, summary

**Behavior:** Stages 1 → 2 → 4 (no escalation)  
**Command:** `sopshield -m "What are your hours on Saturday?" -m "Botox" -m "new client" -m "555-0142"`

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** What are your hours on Saturday?

**Assistant:** [SOP-grounded Saturday hours — 10:00 AM – 4:00 PM]

Before we wrap up, I'd like to ask a couple of quick questions so our front-desk team can follow up — only what's helpful for booking. You can type 'skip' on any question.

Which treatment were you hoping to learn about or book? (For example, Botox, fillers, laser hair removal, or a chemical peel.)

**Customer:** Botox

**Assistant:** Got it — Botox. Have you visited Bloom Aesthetics before, or would this be your first time with us?

**Customer:** new client

**Assistant:** Thanks — I've noted you're a new client. What's the best phone number or email for our front-desk team to follow up?

**Customer:** 555-0142

**Assistant:** Perfect — we'll use 555-0142 to reach you. Thank you — I have what our team needs for follow-up. Here's a quick summary of your visit:

**Lead qualification**  
Service: Botox · Client: new · Contact: 555-0142

_Captured during intake:_
- Service interest: Botox
- Client status: new
- Contact: 555-0142

---

## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
Primary topic from conversation: What are your hours on Saturday?

### 2. Key details
- Service: Botox · Client: new · Contact: 555-0142

### 3. SOP gaps
- None recorded

### 4. Recommended next action
Send booking link or confirm appointment per SOP if customer is ready.

### 5. Escalation status
None

---

## Stored qualification record

```json
{
  "service_interest": "Botox",
  "service_detail": null,
  "client_status": "new",
  "contact": "555-0142",
  "pending_field": null,
  "completed": true
}
```

**Validation notes**
- Three targeted questions (service, client status, contact) — no numbered script
- Answers stored in `qualification_state` and audit list `qualification`
- Compact lead summary generated before session summary
- FAQ answers remain SOP-grounded; escalation rules unchanged
