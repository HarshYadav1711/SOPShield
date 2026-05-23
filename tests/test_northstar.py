"""Tests for Northstar Dental SOP-driven workflow."""

from pathlib import Path

from sopshield.providers.rule import RuleBasedProvider
from sopshield.session import Stage
from sopshield.sop.loader import load_sop
from sopshield.stages.faq import answer_faq
from sopshield.workflow import ConversationWorkflow

SOP = Path(__file__).resolve().parents[1] / "data" / "northstar_dental.json"


def test_northstar_greeting_is_sop_driven():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    reply = wf.start()
    assert "Northstar Dental" in reply.message
    assert "Bloom" not in reply.message


def test_northstar_faq_hours_from_sop():
    sop = load_sop(SOP)
    result = answer_faq(sop, "What are your Saturday hours?", RuleBasedProvider())
    assert result.answered_from_sop
    assert "Saturday" in result.reply
    assert "1:00 PM" in result.reply or "hygiene" in result.reply.lower()


def test_northstar_sensitive_clinical_escalates():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    reply = wf.handle("My face is swelling badly after an extraction and I can't swallow")
    assert reply.escalated
    assert "sensitive_unsupported" in reply.message
    assert "care coordination" in reply.message.lower()


def test_northstar_qualification_dental_services():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    wf.handle("How do I book a cleaning?")
    reply = wf.handle("new patient")
    assert wf.session.stage == Stage.QUALIFICATION
    assert wf.session.qualification_state.client_status == "new"
