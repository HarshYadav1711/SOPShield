from pathlib import Path

from sopshield.providers.rule_based import RuleBasedProvider
from sopshield.session import Stage
from sopshield.workflow import ConversationWorkflow

SOP = Path(__file__).resolve().parents[1] / "data" / "bloom_aesthetics_sop.json"


def test_faq_then_qualification_flow():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    r1 = wf.handle("What are your hours on Saturday?")
    assert wf.session.stage in (Stage.QUALIFICATION, Stage.FAQ)
    assert "Saturday" in r1.message or "10" in r1.message or "hour" in r1.message.lower()

    r2 = wf.handle("Botox")
    assert wf.session.stage == Stage.QUALIFICATION

    r3 = wf.handle("new client")
    r4 = wf.handle("555-0100")
    assert r4.done
    assert "Session Summary" in r4.message or "Customer intent" in r4.message


def test_escalation_explicit():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    r = wf.handle("I want to speak to a human please")
    assert r.escalated
    assert r.done
    assert "connecting you" in r.message.lower()
