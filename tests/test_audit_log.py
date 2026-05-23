import json
from pathlib import Path

from sopshield.audit_log import escalation_log_path, log_escalation, logs_directory


def test_logs_directory_is_project_root():
    root = logs_directory()
    assert root.name == "logs"
    assert (root.parent / "data").is_dir()


def test_log_escalation_appends_structured_json(tmp_path: Path):
    log_escalation(
        sop_id="northstar_dental",
        customer_message="This is ridiculous. I want a real person.",
        trigger="angry_sentiment",
        confidence=0.42,
        escalated=True,
        log_dir=tmp_path,
    )
    path = escalation_log_path(tmp_path)
    assert path.is_file()
    entry = json.loads(path.read_text(encoding="utf-8").strip())
    assert entry["sop"] == "northstar_dental"
    assert entry["customer_message"] == "This is ridiculous. I want a real person."
    assert entry["trigger"] == "angry_sentiment"
    assert entry["confidence"] == 0.42
    assert entry["escalated"] is True
    assert entry["timestamp"].endswith("Z")


def test_log_escalation_is_append_only(tmp_path: Path):
    log_escalation(
        sop_id="a",
        customer_message="first",
        trigger="low_confidence",
        confidence=0.1,
        log_dir=tmp_path,
    )
    log_escalation(
        sop_id="b",
        customer_message="second",
        trigger="complaint",
        confidence=1.0,
        log_dir=tmp_path,
    )
    lines = escalation_log_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["sop"] == "b"
