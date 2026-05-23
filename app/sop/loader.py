"""Load and chunk the Standard Operating Procedures document."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.models import SopSectionRef


@dataclass(frozen=True)
class SOPSection:
    title: str
    body: str

    @property
    def text(self) -> str:
        return f"## {self.title}\n\n{self.body.strip()}"

    def to_ref(self) -> SopSectionRef:
        return SopSectionRef(title=self.title, body=self.body)


@dataclass
class SOPDocument:
    path: Path
    sections: list[SOPSection]
    raw: str

    def as_context(self, sections: list[SOPSection]) -> str:
        return "\n\n---\n\n".join(section.text for section in sections)


def load_sop(path: Path | str) -> SOPDocument:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    sections = _parse_sections(raw)
    return SOPDocument(path=path, sections=sections, raw=raw)


def _parse_sections(markdown: str) -> list[SOPSection]:
    """Split markdown on level-2 headings into retrievable sections."""
    parts = re.split(r"(?m)^## ", markdown)
    sections: list[SOPSection] = []
    for part in parts[1:]:
        lines = part.strip().split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if title.lower().startswith("bloom aesthetics"):
            continue
        sections.append(SOPSection(title=title, body=body))
    return sections
