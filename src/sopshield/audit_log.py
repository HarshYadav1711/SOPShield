"""Append-only structured audit log for escalation events."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

ESCALATION_LOG_NAME = "escalations.jsonl"


def logs_directory() -> Path:
    """Project logs/ directory (sibling of transcripts/)."""
    return Path(__file__).resolve().parents[2] / "logs"


def escalation_log_path(log_dir: Path | None = None) -> Path:
    root = log_dir or logs_directory()
    return root / ESCALATION_LOG_NAME


def log_escalation(
    *,
    sop_id: str,
    customer_message: str,
    trigger: str,
    confidence: float,
    escalated: bool = True,
    log_dir: Path | None = None,
) -> None:
    """Append one JSON record for an escalation. Failures do not propagate."""
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sop": sop_id,
        "customer_message": customer_message,
        "trigger": trigger,
        "confidence": round(float(confidence), 2),
        "escalated": escalated,
    }
    path = escalation_log_path(log_dir)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        logger.warning("Failed to write escalation audit log to %s", path, exc_info=True)
