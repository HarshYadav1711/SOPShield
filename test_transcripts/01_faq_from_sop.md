# FAQ answered from SOP

**SOP:** `bloom_aesthetics_demo`  
**Trigger:** Customer asks about Saturday hours (covered in SOP)  
**Expected:** Grounded answer, no escalation, qualification begins after first successful FAQ

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** Hi — are you open on Saturdays? What time do you close?

**Assistant:** Thanks for asking. Saturday: 10:00 AM - 4:00 PM If you'd like to book or need anything else, I'm happy to help.

Before we wrap up, I'd like to ask a couple of quick questions so our front-desk team can follow up — only what's helpful for booking. You can type 'skip' on any question.

Which treatment were you hoping to learn about or book? (For example, Botox, fillers, laser hair removal, or a chemical peel.)

---

**Checks**

- Retrieval matched `Hours of operation`
- Confidence ≥ 0.35; `answered_from_sop=True`
- No escalation; stage moves to qualification
