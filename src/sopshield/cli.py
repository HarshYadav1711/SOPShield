"""CLI entry point for interactive SOPShield sessions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows consoles may default to cp1252; keep output readable.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sopshield.sop.loader import data_directory, list_sops, resolve_sop_path
from sopshield.startup import (
    SUPPORTED_PROVIDERS,
    StartupError,
    build_provider,
    validate_sop,
)
from sopshield.workflow import ConversationWorkflow

DEFAULT_SOP = "bloom_aesthetics_demo"
DEFAULT_TRANSCRIPTS = Path(__file__).resolve().parents[2] / "transcripts"


def main(argv: list[str] | None = None) -> int:
    available = list_sops()
    parser = argparse.ArgumentParser(
        description="SOPShield — SOP-grounded customer support workflow (CLI)",
    )
    parser.add_argument(
        "--sop",
        default=DEFAULT_SOP,
        help=(
            "SOP id or file path (default: bloom_aesthetics_demo). "
            f"Available: {', '.join(available) or 'none'}"
        ),
    )
    parser.add_argument(
        "--list-sops",
        action="store_true",
        help="List SOP ids discovered in the data/ directory and exit",
    )
    parser.add_argument(
        "--provider",
        choices=list(SUPPORTED_PROVIDERS),
        default="rule",
        help="LLM backend (default: rule = no API, offline)",
    )
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        default=DEFAULT_TRANSCRIPTS,
        help="Where to save session transcripts",
    )
    parser.add_argument(
        "--llm-summary",
        action="store_true",
        help="Use provider for summary text (deterministic summary is default)",
    )
    parser.add_argument(
        "--llm-handoff-note",
        action="store_true",
        help="Use provider to elaborate escalation handoff note (rules still decide escalation)",
    )
    parser.add_argument(
        "--message",
        "-m",
        action="append",
        dest="messages",
        help="Non-interactive: process messages in order, then exit",
    )
    args = parser.parse_args(argv)

    if args.list_sops:
        data_dir = data_directory()
        ids = list_sops(data_dir)
        if not ids:
            print(f"No SOP JSON files found in {data_dir}", file=sys.stderr)
            return 1
        for sop_id in ids:
            path = resolve_sop_path(sop_id, data_dir)
            print(f"{sop_id}\t{path}")
        return 0

    try:
        sop_path = validate_sop(args.sop)
        provider = build_provider(args.provider)
    except StartupError as exc:
        print(exc.message(), file=sys.stderr)
        return 1

    workflow = ConversationWorkflow.from_paths(
        sop_path,
        provider,
        use_llm_summary=args.llm_summary,
        use_llm_handoff_note=args.llm_handoff_note,
    )

    reply = workflow.start()
    print(f"\nAssistant: {reply.message}\n")

    def process_line(line: str) -> bool:
        nonlocal reply
        if line.strip().lower() in {"quit", "exit", "bye"}:
            return False
        reply = workflow.handle(line)
        print(f"\nAssistant: {reply.message}\n")
        return not reply.done

    if args.messages:
        for msg in args.messages:
            if not process_line(msg):
                break
    else:
        print("Type your message (or 'quit' to end early).\n")
        while True:
            try:
                line = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if line.lower() in {"quit", "exit", "bye"}:
                break
            if not process_line(line):
                break

    path = workflow.save_transcript(args.transcripts_dir)
    print(f"Transcript saved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
