"""Offline engineering knowledge base.

Naive keyword retrieval over Markdown notes bundled with the package (and any
notes the user adds under knowledge/notes/). Deliberately simple and honest
about being so — it exists to answer quick 'how do I raise Fmax'-style
questions without a network, not to impersonate a search engine.
"""
from __future__ import annotations

import re
from pathlib import Path

_NOTES_DIR = Path(__file__).parent / "notes"


class KnowledgeBase:
    def __init__(self, notes_dir: Path | None = None):
        self.passages: list[tuple[str, str]] = []   # (source, text)
        d = notes_dir or _NOTES_DIR
        if d.is_dir():
            for f in sorted(d.glob("*.md")):
                for block in f.read_text().split("\n\n"):
                    block = block.strip()
                    if len(block) > 40:
                        self.passages.append((f.name, block))

    def answer(self, query: str, k: int = 3) -> str:
        terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
        scored = []
        for src, text in self.passages:
            low = text.lower()
            score = sum(low.count(t) for t in terms)
            if score:
                scored.append((score, src, text))
        scored.sort(key=lambda s: -s[0])
        if not scored:
            return "No matching passages in the local knowledge base."
        out = []
        for score, src, text in scored[:k]:
            out.append(f"[{src}]\n{text}")
        return "\n\n---\n\n".join(out)
