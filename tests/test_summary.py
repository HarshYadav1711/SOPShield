from pathlib import Path

from sopshield.providers.rule_based import RuleBasedProvider
from sopshield.stages.summary import format_summary_deterministic, infer_customer_intent
from sopshield.workflow import ConversationWorkflow

SOP = Path(__file__).resolve().parents[1] / "data" / "bloom_aesthetics_demo.json"


def test_summary_sections_full_session():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    wf.handle("What are your hours on Saturday?")
    wf.handle("Botox")
    wf.handle("new client")
    wf.handle("555-0142")

    summary = format_summary_deterministic(wf.session, wf.sop)
    for heading in (
        "### 1. Customer intent",
        "### 2. Collected details",
        "### 3. Unanswered or unsupported questions",
        "### 4. SOP gaps",
        "### 5. Escalation reason",
        "### 6. Recommended next action",
    ):
        assert heading in summary
    assert "Botox" in summary
    assert "555-0142" in summary
    assert "Escalation reason\nNone" in summary.replace("\r\n", "\n")


def test_summary_angry_escalation():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    wf.handle("This is ridiculous, I'm furious about my appointment!")

    summary = format_summary_deterministic(wf.session, wf.sop)
    assert "angry_sentiment" in summary
    assert "distressed" in infer_customer_intent(wf.session, wf.sop).lower() or "concern" in summary.lower()
    assert wf.session.handoff_note
    assert "De-escalate" in wf.session.handoff_note or "upset" in wf.session.handoff_note.lower()


def test_summary_tracks_unanswered_on_sop_gap():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    wf.handle("Do you offer international shipping of skincare products?")

    assert wf.session.unanswered_questions
    summary = format_summary_deterministic(wf.session, wf.sop)
    assert "international shipping" in summary.lower() or "skincare" in summary.lower()
