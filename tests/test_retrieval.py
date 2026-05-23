from pathlib import Path

from sopshield.sop.loader import load_sop
from sopshield.sop.retrieval import retrieve

SOP = Path(__file__).resolve().parents[1] / "data" / "bloom_aesthetics_sop.json"


def test_retrieve_hours():
    sop = load_sop(SOP)
    result = retrieve(sop, "What are your hours on Saturday?")
    assert result.has_match
    assert result.confidence >= 0.35
    titles = [s.title.lower() for s in result.sections]
    assert any("hour" in t for t in titles)


def test_retrieve_unknown_low_confidence():
    sop = load_sop(SOP)
    result = retrieve(sop, "xyzzy florbag heliotrope")
    assert not result.has_match or result.confidence < 0.35
