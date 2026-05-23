from pathlib import Path

from sopshield.providers.rule import RuleBasedProvider
from sopshield.session import Stage
from sopshield.workflow import ConversationWorkflow

SOP = Path(__file__).resolve().parents[1] / "data" / "bloom_aesthetics_demo.json"


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
    assert "### 1. Customer intent" in r4.message
    assert "### 6. Recommended next action" in r4.message


def test_escalation_explicit():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    r = wf.handle("I want to speak to a human please")
    assert r.escalated
    assert r.done
    assert "connecting you" in r.message.lower()
    assert "### 5. Escalation reason" in r.message
    assert "explicit_escalation" in r.message


def test_escalation_pricing():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    r = wf.handle("What's your lowest price? Can you beat this competitor?")
    assert r.escalated
    assert "pricing_negotiation" in r.message
