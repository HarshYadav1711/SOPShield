# SOP data files

Each business is one JSON file. SOPShield loads these at runtime; there is no database.

## Canonical sources

| File | CLI id | Purpose |
|------|--------|---------|
| `bloom_aesthetics_demo.json` | `bloom_aesthetics_demo` | Default demo — boutique medical aesthetics |
| `northstar_dental.json` | `northstar_dental` | Dental practice with extended escalation patterns |

Alias: `--sop bloom_aesthetics` resolves to `bloom_aesthetics_demo.json`.

## Required fields (validated on load)

| Field | Where it lives |
|-------|----------------|
| `business_name` | `document.business_name` |
| `services` | `qualification.services` and/or `sections[]` with `id: "services"` |
| `escalation_rules` | `escalation` config (patterns, thresholds) and/or `sections[]` with `id: "escalation"` |
| `booking_policy` | `sections[]` with `id: "booking"` and non-empty `body` |

Incomplete files fail at load time with a clear error message. The CLI does not start a session against an invalid SOP.

## Adding a business

1. Copy `bloom_aesthetics_demo.json` as a template.
2. Set `document.id` to your CLI id (e.g. `my_clinic`).
3. Fill contact, qualification, escalation, and sections.
4. Run `python main.py --sop my_clinic`.

Markdown (`.md`) SOP files are still supported for custom paths, but JSON is recommended for qualification and escalation configuration.
