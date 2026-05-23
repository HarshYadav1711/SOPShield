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

from sopshield.providers.base import LLMProvider
from sopshield.providers.ollama import OllamaProvider
from sopshield.providers.rule_based import RuleBasedProvider
from sopshield.workflow import ConversationWorkflow

DEFAULT_SOP = Path(__file__).resolve().parents[2] / "data" / "bloom_aesthetics_sop.json"
DEFAULT_TRANSCRIPTS = Path(__file__).resolve().parents[2] / "transcripts"


def _build_provider(name: str) -> LLMProvider:
    if name == "rule":
        return RuleBasedProvider()
    if name == "ollama":
        return OllamaProvider()
    if name == "openai":
        from sopshield.providers.openai_api import OpenAIProvider

        return OpenAIProvider()
    raise ValueError(f"Unknown provider: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SOPShield — SOP-grounded customer support workflow (CLI)",
    )
    parser.add_argument(
        "--sop",
        type=Path,
        default=DEFAULT_SOP,
        help="Path to SOP file (.json or .md)",
    )
    parser.add_argument(
        "--provider",
        choices=["rule", "ollama", "openai"],
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

    if not args.sop.is_file():
        print(f"SOP file not found: {args.sop}", file=sys.stderr)
        return 1

    provider = _build_provider(args.provider)
    workflow = ConversationWorkflow.from_paths(
        args.sop,
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
