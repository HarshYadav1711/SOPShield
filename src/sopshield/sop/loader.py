"""Load and chunk Standard Operating Procedures from the data directory."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@dataclass(frozen=True)
class SOPSection:
    id: str
    title: str
    body: str

    @property
    def text(self) -> str:
        return f"## {self.title}\n\n{self.body.strip()}"


@dataclass
class QualificationConfig:
    services: list[tuple[str, str]] = field(default_factory=list)
    vague_hints: str = (
        r"\b(something|treatment|procedure|help with my face|skin care|"
        r"anti-?aging|wrinkles?|face)\b"
    )
    questions: dict[str, str] = field(default_factory=dict)
    acknowledgments: dict[str, str] = field(default_factory=dict)


@dataclass
class EscalationConfig:
    confidence_threshold: float = 0.35
    unanswered_limit: int = 2
    out_of_scope_patterns: list[str] = field(default_factory=list)
    sensitive_patterns: list[str] = field(default_factory=list)
    handoff_notes: dict[str, str] = field(default_factory=dict)


@dataclass
class ConversationConfig:
    greeting: str = ""
    handoff_message: str = ""
    closing_message: str = ""
    tone: str = "calm, professional, warm, and concise"
    faq_fallback_no_sop: str = ""
    faq_fallback_ungrounded: str = ""
    qualification_intro: str = ""


@dataclass
class ContactConfig:
    phone: str = ""
    email: str = ""
    portal: str = ""


@dataclass
class SOPDocument:
    path: Path
    sop_id: str
    business_name: str
    sections: list[SOPSection]
    raw: str
    document: dict = field(default_factory=dict)
    conversation: ConversationConfig = field(default_factory=ConversationConfig)
    contact: ContactConfig = field(default_factory=ContactConfig)
    qualification: QualificationConfig = field(default_factory=QualificationConfig)
    escalation: EscalationConfig = field(default_factory=EscalationConfig)

    def as_context(self, sections: list[SOPSection]) -> str:
        return "\n\n---\n\n".join(s.text for s in sections)

    def section_by_id(self, section_id: str) -> SOPSection | None:
        for section in self.sections:
            if section.id == section_id:
                return section
        return None


def data_directory() -> Path:
    return DATA_DIR


def list_sops(data_dir: Path | None = None) -> list[str]:
    """Return sorted SOP ids discovered from JSON files in data/."""
    root = data_dir or data_directory()
    if not root.is_dir():
        return []
    ids: list[str] = []
    for path in sorted(root.glob("*.json")):
        sop_id = path.stem
        if sop_id.endswith("_sop"):
            sop_id = sop_id[: -len("_sop")]
        ids.append(sop_id)
    return ids


def resolve_sop_path(name_or_path: str | Path, data_dir: Path | None = None) -> Path:
    """Resolve a SOP id (e.g. bloom_aesthetics_demo) or file path to a concrete file."""
    candidate = Path(name_or_path)
    if candidate.is_file():
        return candidate.resolve()

    root = data_dir or data_directory()
    stem = candidate.stem if candidate.suffix else str(name_or_path)
    for name in (stem, f"{stem}_sop", f"{stem}_demo"):
        path = root / f"{name}.json"
        if path.is_file():
            return path.resolve()

    path = root / f"{stem}.json"
    if path.is_file():
        return path.resolve()

    raise FileNotFoundError(
        f"SOP not found: {name_or_path!r}. Available: {', '.join(list_sops(root)) or '(none)'}"
    )


def load_sop(path: Path | str) -> SOPDocument:
    path = Path(path)
    if path.suffix.lower() == ".json":
        return _load_json(path)
    raw = path.read_text(encoding="utf-8")
    sections = _parse_sections(raw)
    business_name = _infer_business_name(raw, path.stem)
    doc = _build_document(path, path.stem, business_name, sections, raw, {})
    return doc


def _load_json(path: Path) -> SOPDocument:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    sections: list[SOPSection] = []
    for item in data.get("sections", []):
        title = str(item.get("title", "")).strip()
        body = str(item.get("body", "")).strip()
        section_id = str(item.get("id", _slug(title))).strip() or _slug(title)
        if title:
            sections.append(SOPSection(id=section_id, title=title, body=body))

    document_meta = data.get("document", {})
    sop_id = str(document_meta.get("id", path.stem)).strip() or path.stem
    if sop_id.endswith("_sop"):
        sop_id = sop_id[: -len("_sop")]
    business_name = str(
        document_meta.get("business_name")
        or document_meta.get("title", "").split("—")[0].strip()
        or sop_id.replace("_", " ").title()
    ).strip()

    return _build_document(path, sop_id, business_name, sections, raw, data)


def _build_document(
    path: Path,
    sop_id: str,
    business_name: str,
    sections: list[SOPSection],
    raw: str,
    data: dict,
) -> SOPDocument:
    document_meta = dict(data.get("document", {}))
    conversation = _parse_conversation(data, business_name)
    contact = _parse_contact(data)
    qualification = _parse_qualification(data, business_name)
    escalation = _parse_escalation(data, sections)

    return SOPDocument(
        path=path,
        sop_id=sop_id,
        business_name=business_name,
        sections=sections,
        raw=raw,
        document=document_meta,
        conversation=conversation,
        contact=contact,
        qualification=qualification,
        escalation=escalation,
    )


def _parse_conversation(data: dict, business_name: str) -> ConversationConfig:
    conv = data.get("conversation", {})
    contact = data.get("contact", {})
    email = str(contact.get("email", "")).strip()
    email_suffix = f" Support email: {email} (business hours)." if email else ""

    default_greeting = (
        f"Hello, and thank you for contacting {business_name}. "
        "I'm here to help with hours, services, booking, and policies. "
        "What can I help you with today?"
    )
    default_handoff = (
        "I'm connecting you with our front-desk team now. "
        "They'll follow up shortly at the number on your account."
        f"{email_suffix}"
    )
    default_closing = f"Session complete. Thank you for contacting {business_name}."
    default_no_sop = (
        "I don't have that information in our clinic guidelines. "
        "A member of our front-desk team will follow up with you shortly."
    )
    default_ungrounded = (
        "I want to make sure you get accurate information. "
        "Our team will follow up with you on that."
    )
    default_qual_intro = (
        "Before we wrap up, I'd like to ask a couple of quick questions so our "
        "front-desk team can follow up — only what's helpful for booking. "
        "You can type 'skip' on any question."
    )

    return ConversationConfig(
        greeting=str(conv.get("greeting", default_greeting)).strip() or default_greeting,
        handoff_message=str(conv.get("handoff_message", default_handoff)).strip()
        or default_handoff,
        closing_message=str(conv.get("closing_message", default_closing)).strip()
        or default_closing,
        tone=str(
            conv.get(
                "tone",
                "calm, professional, warm, and concise — appropriate for a small clinic",
            )
        ).strip(),
        faq_fallback_no_sop=str(conv.get("faq_fallback_no_sop", default_no_sop)).strip()
        or default_no_sop,
        faq_fallback_ungrounded=str(
            conv.get("faq_fallback_ungrounded", default_ungrounded)
        ).strip()
        or default_ungrounded,
        qualification_intro=str(conv.get("qualification_intro", default_qual_intro)).strip()
        or default_qual_intro,
    )


def _parse_contact(data: dict) -> ContactConfig:
    contact = data.get("contact", {})
    return ContactConfig(
        phone=str(contact.get("phone", "")).strip(),
        email=str(contact.get("email", "")).strip(),
        portal=str(contact.get("portal", "")).strip(),
    )


def _parse_qualification(data: dict, business_name: str) -> QualificationConfig:
    qual = data.get("qualification", {})
    services: list[tuple[str, str]] = []
    for item in qual.get("services", []):
        if isinstance(item, dict):
            pattern = str(item.get("pattern", "")).strip()
            label = str(item.get("label", "")).strip()
            if pattern and label:
                services.append((pattern, label))
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            services.append((str(item[0]), str(item[1])))

    short_name = business_name.split()[0] if business_name else "our clinic"
    default_questions = {
        "service_interest": (
            "Which treatment or service were you hoping to learn about or book?"
        ),
        "service_detail": (
            "Could you tell me a bit more about what you're looking for "
            "so our team can prepare?"
        ),
        "client_status": (
            f"Have you visited {short_name} before, or would this be your first time with us?"
        ),
        "contact": (
            "What's the best phone number or email for our front-desk team to follow up?"
        ),
    }
    questions = {**default_questions, **qual.get("questions", {})}

    default_acks = {
        "service_interest": "Got it — {value}.",
        "service_detail": "Thank you, that's helpful.",
        "client_status": "Thanks — I've noted you're a {value} client.",
        "contact": "Perfect — we'll use {value} to reach you.",
    }
    acknowledgments = {**default_acks, **qual.get("acknowledgments", {})}

    return QualificationConfig(
        services=services,
        vague_hints=str(
            qual.get(
                "vague_hints",
                QualificationConfig().vague_hints,
            )
        ),
        questions=questions,
        acknowledgments=acknowledgments,
    )


def _parse_escalation(data: dict, sections: list[SOPSection]) -> EscalationConfig:
    esc = data.get("escalation", {})
    out_of_scope = list(esc.get("out_of_scope_patterns", []))
    sensitive = list(esc.get("sensitive_patterns", []))

    if not out_of_scope:
        services = next((s for s in sections if s.id == "services"), None)
        if services:
            for match in re.finditer(
                r"\b(?:do not offer|not offer|refer)\b[^.\n]*",
                services.body,
                re.I,
            ):
                phrase = match.group(0).lower()
                for term in re.findall(r"\b[a-z]{4,}\b", phrase):
                    if term not in {"offer", "those", "refer", "requests", "appropriate"}:
                        out_of_scope.append(term)

    return EscalationConfig(
        confidence_threshold=float(esc.get("confidence_threshold", 0.35)),
        unanswered_limit=int(esc.get("unanswered_limit", 2)),
        out_of_scope_patterns=out_of_scope,
        sensitive_patterns=sensitive,
        handoff_notes=dict(esc.get("handoff_notes", {})),
    )


def _parse_sections(markdown: str) -> list[SOPSection]:
    """Split markdown on level-2 headings into retrievable sections."""
    parts = re.split(r"(?m)^## ", markdown)
    sections: list[SOPSection] = []
    for part in parts[1:]:
        lines = part.strip().split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if title.lower().startswith("#"):
            continue
        sections.append(SOPSection(id=_slug(title), title=title, body=body))
    return sections


def _infer_business_name(raw: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)(?:\s+—|\s*$)", raw, re.M)
    if match:
        return match.group(1).strip()
    return fallback.replace("_", " ").title()


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug or "section"
