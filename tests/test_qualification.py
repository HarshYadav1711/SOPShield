"""Tests for stateful lead qualification."""

from pathlib import Path

import pytest

from sopshield.providers.rule_based import RuleBasedProvider
from sopshield.session import Stage
from sopshield.stages.qualification import (
    detect_contact,
    detect_service,
    format_qualification_summary,
    prefill_from_conversation,
    process_qualification_turn,
    start_qualification,
)
from sopshield.workflow import ConversationWorkflow

SOP = Path(__file__).resolve().parents[1] / "data" / "bloom_aesthetics_sop.json"


def test_detect_service_and_contact():
    assert detect_service("I'm interested in Botox for my forehead") == "Botox"
    assert detect_contact("Reach me at jane@example.com") == "jane@example.com"
    assert detect_contact("Call 555-0142") == "555-0142"


def test_prefill_skips_redundant_service_question():
    from sopshield.session import Session

    session = Session(session_id="test-prefill")
    session.add("user", "I'm interested in Botox — what are your Saturday hours?", Stage.FAQ)
    prefill_from_conversation(session)
    assert session.qualification_state.service_interest == "Botox"
    prompt = start_qualification(session)
    assert "Which treatment" not in prompt
    assert "visited Bloom Aesthetics before" in prompt


def test_vague_service_triggers_follow_up():
    from sopshield.session import Session

    session = Session(session_id="test-vague")
    session.qualification_state.service_interest = "something for my face"
    result = process_qualification_turn(session, "forehead lines and crow's feet")
    assert session.qualification_state.service_detail is not None
    assert result.done is False or session.qualification_state.client_status


def test_full_qualification_flow_stores_structured_state():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    wf.handle("What are your hours on Saturday?")
    wf.handle("Botox")
    wf.handle("new client")
    r = wf.handle("555-0100")

    state = wf.session.qualification_state
    assert state.completed
    assert state.service_interest == "Botox"
    assert state.client_status == "new"
    assert state.contact == "555-0100"
    assert len(wf.session.qualification) == 3
    assert r.done
    assert "Lead qualification" in r.message
    assert "Session Summary" in r.message


def test_qualification_summary_compact():
    wf = ConversationWorkflow.from_paths(SOP, RuleBasedProvider())
    wf.start()
    wf.handle("What are your hours on Saturday?")
    wf.handle("Botox")
    wf.handle("new client")
    wf.handle("555-0100")

    summary = format_qualification_summary(wf.session)
    assert "Service: Botox" in summary
    assert "Client: new" in summary
    assert "Contact: 555-0100" in summary


def test_skip_answer_recorded():
    from sopshield.session import Session

    session = Session(session_id="test-skip")
    state = session.qualification_state
    state.service_interest = "Botox"
    state.client_status = "new"
    state.pending_field = "contact"
    result = process_qualification_turn(session, "skip")
    assert state.contact == "not provided"
    assert result.done
