# Escalation — pricing negotiation

**SOP:** `bloom_aesthetics_demo`  
**Command:**

```bash
python main.py --sop bloom_aesthetics_demo -m "What's your lowest price? Can you beat this competitor?"
```

**Trigger:** Discount / competitor price-match language; SOP routes pricing discretion to staff

---

**Assistant:** Hello, and thank you for contacting Bloom Aesthetics Clinic. I'm here to help with hours, services, booking, and policies. What can I help you with today?

**Customer:** What's your lowest price? Can you beat this competitor?

**Assistant:** I'm connecting you with our front-desk team now. They'll follow up shortly at the number on your account. Support email: support@bloom-aesthetics.example (business hours).

---

## Session Summary — Bloom Aesthetics Clinic

### 1. Customer intent
Pricing or billing inquiry

### 5. Escalation reason
- **pricing_negotiation**: Pricing negotiation or discount pressure beyond published SOP rates.
- Operator note: Pricing outside bot scope — manager or front desk to quote. (pricing_negotiation)

### 6. Recommended next action
Front desk to share published pricing — no ad-hoc discounts via chat.

---

**Checks**

- Distinct from generic `out_of_scope`
- No competitor-matched price or package quote generated
- Human team owns negotiation per pricing SOP section
