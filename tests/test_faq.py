"""FAQ stage — strict SOP grounding and escalation paths."""

from pathlib import Path

from sopshield.providers.rule_based import RuleBasedProvider
from sopshield.session import Stage
from sopshield.sop.loader import load_sop
from sopshield.sop.grounding import sop_supports_answer
from sopshield.stages.faq import answer_faq
from sopshield.workflow import ConversationWorkflow

SOP_JSON = Path(__file__).resolve().parents[1] / "data" / "bloom_aesthetics_sop.json"
SOP_MD = Path(__file__).resolve().parents[1] / "data" / "bloom_aesthetics_sop.md"


def test_load_structured_json_sop():
    doc = load_sop(SOP_JSON)
    assert len(doc.sections) >= 5
    titles = {s.title for s in doc.sections}
    assert "Hours of operation" in titles


def test_faq_answered_from_sop_saturday_hours():
    sop = load_sop(SOP_JSON)
    provider = RuleBasedProvider()
    result = answer_faq(sop, "What are your hours on Saturday?", provider)

    assert result.answered_from_sop
    assert not result.needs_escalation
    assert result.confidence >= 0.35
    assert "10:00" in result.reply
    assert "Saturday" in result.reply
    assert "don't have" not in result.reply.lower()


def test_faq_out_of_sop_escalates():
    sop = load_sop(SOP_JSON)
    provider = RuleBasedProvider()
    result = answer_faq(
        sop,
        "Do you offer international shipping of skincare products?",
        provider,
    )

    assert not result.answered_from_sop
    assert result.needs_escalation
    assert "don't have" in result.reply.lower() or "accurate information" in result.reply.lower()
    assert "shipping" not in result.reply.lower() or "don't have" in result.reply.lower()


def test_sop_supports_answer_requires_overlap():
    sop = load_sop(SOP_JSON)
    hours = next(s for s in sop.sections if "hour" in s.title.lower())
    assert sop_supports_answer("Saturday hours", [hours])
    assert not sop_supports_answer("international skincare shipping", [hours])


def test_transcript_faq_from_sop_workflow():
    wf = ConversationWorkflow.from_paths(SOP_JSON, RuleBasedProvider())
    wf.start()
    reply = wf.handle("What are your hours on Saturday?")

    assert "10:00" in reply.message
    assert not wf.session.escalation.escalated
    assert wf.session.stage == Stage.QUALIFICATION


def test_transcript_sop_gap_workflow():
    wf = ConversationWorkflow.from_paths(SOP_JSON, RuleBasedProvider())
    wf.start()
    reply = wf.handle("Do you offer international shipping of skincare products?")

    assert reply.escalated
    assert reply.done
    assert wf.session.sop_gaps
    assert "connecting you" in reply.message.lower()
    assert not any(
        phrase in reply.message.lower()
        for phrase in ("ships worldwide", "free shipping", "we ship")
    )
