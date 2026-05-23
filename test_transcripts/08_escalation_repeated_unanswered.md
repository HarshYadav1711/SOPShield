# Transcript: Escalation — repeated unanswered questions

**Behavior:** Stage 3 — two consecutive SOP misses  
**Commands:**
```bash
sopshield -m "Do you sell pet grooming kits?" -m "What colors of pet grooming kits do you have?"
```

---

**Customer:** Do you sell pet grooming kits?

**Assistant:** I don't have that information in our clinic guidelines…

**Customer:** What colors of pet grooming kits do you have?

**Assistant:** [Partial safe reply if any]  
I'm connecting you with our front-desk team now…

---

## Session Summary (excerpt)

### 5. Escalation status
ESCALATED — repeated_unanswered

---

**Validation notes**
- `unanswered_streak` reaches 2
- Second failure triggers escalation even without anger or explicit request
