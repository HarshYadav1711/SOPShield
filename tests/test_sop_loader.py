"""Tests for multi-SOP loading and discovery."""

from pathlib import Path

import pytest

from sopshield.sop.loader import list_sops, load_sop, resolve_sop_path

DATA = Path(__file__).resolve().parents[1] / "data"


def test_list_sops_discovers_configured_businesses():
    ids = list_sops(DATA)
    assert "bloom_aesthetics_demo" in ids
    assert "northstar_dental" in ids


def test_resolve_sop_by_id():
    path = resolve_sop_path("bloom_aesthetics_demo", DATA)
    assert path.name == "bloom_aesthetics_demo.json"


def test_resolve_sop_missing_raises():
    with pytest.raises(FileNotFoundError):
        resolve_sop_path("nonexistent_business", DATA)


def test_bloom_demo_matches_assignment_content():
    doc = load_sop(DATA / "bloom_aesthetics_demo.json")
    assert doc.business_name == "Bloom Aesthetics Clinic"
    assert doc.sop_id == "bloom_aesthetics_demo"
    hours = doc.section_by_id("hours")
    assert hours is not None
    assert "Saturday" in hours.body
    assert "10:00 AM - 4:00 PM" in hours.body
    assert doc.contact.phone == "555-0142"
    assert len(doc.qualification.services) >= 5


def test_northstar_dental_advanced_escalation_config():
    doc = load_sop(DATA / "northstar_dental.json")
    assert doc.business_name == "Northstar Dental"
    assert doc.escalation.sensitive_patterns
    assert doc.escalation.handoff_notes
    assert doc.section_by_id("insurance") is not None
    assert "48 hours" in doc.section_by_id("cancellation").body
