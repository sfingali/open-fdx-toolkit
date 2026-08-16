"""PDF screenplay importer for open-fdx-toolkit.

Extracts screenplay structure from a text-layer PDF using layout geometry
(line x-positions) plus content heuristics, and returns the same
``ParsedScene`` dataclasses used by ``fdx_parser`` so downstream tooling sees
one consistent shape.

How it works
------------
1. ``pymupdf`` extracts every text line with its left x-coordinate.
2. A histogram of x-positions identifies the page's natural margins —
   the most common positions are the action margin (left), dialogue margin,
   and character-cue margin (rightmost).
3. Lines are classified by x-position + content: scene headings (INT./EXT.),
   transitions (``CUT TO:`` etc.), character cues (all-caps, followed by
   dialogue), dialogue (indented), parentheticals, centered lines, action.
4. Noise is filtered: page numbers, ``(CONT'D)`` / ``(MORE)`` continuations,
   and the title page (everything before the first scene heading).

``pymupdf`` is an optional dependency — import this module only when a PDF
path is actually supplied, and install it with ``pip install pymupdf``.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from fdx_parser import (
    ParsedParagraph,
    ParsedScene,
    _detect_narrative,
    _parse_slugline,
)

__all__ = ["parse_pdf", "extract_layout_lines"]

_SLUG_RE = re.compile(
    r"^(INT\.?/?EXT\.?|EXT\.?|INT\.?|I/?E\.?)\s+",
    re.IGNORECASE,
)
_TRANSITION_RE = re.compile(r"^[A-Z][A-Z0-9 .'\-/]*TO:\s*$")
_EXTRA_TRANSITIONS = frozenset({
    "FADE OUT.", "FADE IN:", "FADE OUT", "FADE IN", "SMASH CUT TO:",
    "CUT TO BLACK.", "FADE TO BLACK.", "IRIS OUT.", "MATCH CUT TO:",
})
_CONTINUATION_RE = re.compile(r"^\s*\(?(CONT'D|MORE|CONTINUED)\)?\s*$", re.IGNORECASE)
_PAGE_NUM_RE = re.compile(r"^\d+\.?\s*$")
_PAREN_RE = re.compile(r"^\(.*\)$")


@dataclass
class LayoutLine:
    """A single text line from a PDF with its left x-coordinate (points)."""

    text: str
    x0: float
    page: int = 0
    y: float = 0.0  # vertical position of line top (points from page top)


def extract_layout_lines(pdf_path: str) -> list[LayoutLine]:
    """Extract (text, x0, page) tuples from a text-layer PDF via pymupdf.

    Raises:
        ImportError: If pymupdf is not installed.
        FileNotFoundError: If the PDF path doesn't exist.
    """
    try:
        import pymupdf  # optional dependency
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "PDF import requires pymupdf: pip install pymupdf"
        ) from e

    doc = pymupdf.open(pdf_path)
    lines: list[LayoutLine] = []
    for page_no, page in enumerate(doc):
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                x0 = line["bbox"][0]
                y = line["bbox"][1]
                spans = [s.get("text", "") for s in line.get("spans", [])]
                text = "".join(spans).strip()
                if text:
                    lines.append(LayoutLine(text=text, x0=x0, page=page_no + 1, y=y))
    doc.close()
    return lines


def _detect_margins(lines: list[LayoutLine]) -> tuple[float, float, float]:
    """Return (action_x, dialogue_x, character_x) from the x histogram.

    Screenplay PDFs have three dense x-positions: action (leftmost),
    dialogue (indented), and character cues (most indented). We take the
    three most common positions, ordered left to right.
    """
    counts = Counter(round(l.x0) for l in lines)
    top = [x for x, _ in counts.most_common(3)]
    top.sort()
    if len(top) == 1:
        return top[0], top[0], top[0]
    if len(top) == 2:
        return top[0], top[1], top[1]
    return top[0], top[1], top[2]


def _strip_contd(text: str) -> str:
    """Remove '(cont'd)' / '(CONT'D)' from a character cue.

    Handles both trailing position (``BEN (cont'd)``) and mid-cue position
    (``PARAMEDIC (CONT'D) (O.S.)``). Collapses any double spaces left by
    the removal.
    """
    return re.sub(r"\s{2,}", " ",
                  re.sub(r"\(?\s*(?:cont'?d|contd)\s*\)?", "", text, flags=re.IGNORECASE)).strip()


def _is_initials_name(name: str) -> bool:
    """True for initial-style character names like ``T.R.`` / ``J.R.``.

    These end with a period but are valid character cues in Final Draft /
    Fade In exports (``T.R.`` in the sample script is a character, not a sentence).
    """
    return bool(re.fullmatch(r"[A-Z]\.(?:[A-Z]\.)+", name))


def _is_dialogue_indented(next_line: LayoutLine | None, dialogue_x: float) -> bool:
    """True if the next meaningful line sits at the dialogue margin."""
    return next_line is not None and next_line.x0 >= dialogue_x - 5


def _classify_line(
    line: LayoutLine,
    action_x: float,
    dialogue_x: float,
    character_x: float,
    next_line: LayoutLine | None = None,
    pending_character: bool = False,
) -> tuple[str, str]:
    """Classify one layout line into (type, text).

    ``next_line`` is the following meaningful line, used to decide between
    character cues and centered elements: an all-caps line at the character
    margin is a cue only if the next line is dialogue-indented (Fountain
    rule); otherwise it is a centered element (``ON BEN``, ``THE END``).
    ``pending_character`` marks that the previous meaningful line was a
    character cue, which is required for dialogue classification.
    """
    text = line.text
    s = text.strip()

    # Noise first
    if _PAGE_NUM_RE.fullmatch(s) and len(s) <= 4:
        return ("skip", "")
    if _CONTINUATION_RE.fullmatch(s):
        return ("skip", "")
    if _SLUG_RE.match(s):
        return ("Scene Heading", s)
    if _TRANSITION_RE.fullmatch(s) or s.upper() in _EXTRA_TRANSITIONS:
        return ("Transition", s)
    # Right-aligned transitions: Final Draft renders them at the far-right
    # margin, sometimes split across lines ("FADE TO" / "BLACK").
    if line.x0 >= character_x + 80 and s.isupper() and len(s) <= 40:
        return ("Transition", s)
    if _PAREN_RE.fullmatch(s):
        return ("Parenthetical", s)

    # Character cue: all-caps, short-ish, at the character margin, followed
    # by dialogue-indented text.  Initials names (``T.R.``) are allowed to
    # end with a period.
    if line.x0 >= character_x - 5:
        name = _strip_contd(s)
        stripped = re.sub(r"\([^)]*\)", "", name).strip()
        is_caps = stripped.isupper() or _is_initials_name(stripped)
        not_sentence = stripped.endswith(".") is False or _is_initials_name(stripped)
        if (
            is_caps
            and not_sentence
            and len(stripped) <= 32
            and any(c.isalpha() for c in stripped)
        ):
            if _is_dialogue_indented(next_line, dialogue_x):
                return ("Character", _strip_contd(s))
            # All-caps at the character margin NOT followed by dialogue:
            # centered element (e.g. "ON BEN", "THE END").
            return ("Center", s)

    if line.x0 >= dialogue_x:
        # Dialogue is only valid after a character cue. All-caps lines at the
        # dialogue band without a preceding cue are centered insert text
        # (book covers, titles, gravestones) — render as Center.
        if pending_character:
            return ("Dialogue", s)
        if s.isupper() and len(s) <= 60:
            return ("Center", s)
        return ("Action", s)
    return ("Action", s)


def parse_pdf(pdf_path: str) -> list[ParsedScene]:
    """Parse a text-layer screenplay PDF into ParsedScene objects.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of ParsedScene dataclasses, one per scene, in script order.
        Title-page lines and continuation markers are discarded.
    """
    lines = extract_layout_lines(pdf_path)
    return parse_layout_lines(lines)


def parse_layout_lines(lines: list[LayoutLine]) -> list[ParsedScene]:
    """Classify pre-extracted layout lines into ParsedScene objects.

    Split out so callers can filter lines (revision markers, page numbers,
    deleted-scene blocks) before classification.
    """
    if not lines:
        return []

    action_x, dialogue_x, character_x = _detect_margins(lines)

    # Build a list of meaningful (non-skip) lines so character-cue lookahead
    # sees the next dialogue line, ignoring page numbers and continuations.
    meaningful: list[LayoutLine] = []
    for line in lines:
        s = line.text.strip()
        if not s:
            continue
        if _PAGE_NUM_RE.fullmatch(s) and len(s) <= 4:
            continue
        if _CONTINUATION_RE.fullmatch(s):
            continue
        meaningful.append(line)

    scenes: list[ParsedScene] = []
    current: ParsedScene | None = None
    auto_num = 0
    seen_first_scene = False
    pending_character: str | None = None  # character cue awaiting dialogue

    def _flush_scene() -> None:
        nonlocal current
        if current is not None:
            scenes.append(current)
        current = None

    for idx, line in enumerate(meaningful):
        next_line = meaningful[idx + 1] if idx + 1 < len(meaningful) else None
        if not seen_first_scene:
            # Title page: skip everything before the first scene heading.
            if _SLUG_RE.match(line.text):
                seen_first_scene = True
            else:
                continue

        ptype, text = _classify_line(
            line, action_x, dialogue_x, character_x, next_line,
            pending_character=pending_character is not None,
        )

        if ptype == "skip":
            continue
        if ptype == "Scene Heading":
            _flush_scene()
            auto_num += 1
            parsed = _parse_slugline(text)
            current = ParsedScene(
                scene_number=str(auto_num),
                scene_number_source="auto",
                slugline=text,
                interior_exterior=parsed["interior_exterior"],
                location=parsed["location"],
                set_name=parsed["set_name"],
                time_of_day=parsed["time_of_day"],
                body_lines=[],
                characters=[],
                paragraphs=[],
                narrative_position_hint=_detect_narrative(text),
            )
            pending_character = None
            continue

        if current is None:
            continue

        if ptype == "Character":
            pending_character = text
            current.paragraphs.append(ParsedParagraph(type="Character", text=text))
            current.body_lines.append(text)
            if text not in current.characters:
                current.characters.append(text)
        elif ptype == "Dialogue":
            if pending_character is not None:
                pending_character = None
            current.paragraphs.append(ParsedParagraph(type="Dialogue", text=text))
            current.body_lines.append(text)
        elif ptype == "Parenthetical":
            current.paragraphs.append(ParsedParagraph(type="Parenthetical", text=text))
            current.body_lines.append(text)
        elif ptype == "Center":
            current.paragraphs.append(ParsedParagraph(type="Center", text=text))
            current.body_lines.append(text)
        elif ptype == "Transition":
            current.paragraphs.append(ParsedParagraph(type="Transition", text=text))
            current.body_lines.append(text)
        else:  # Action
            current.paragraphs.append(ParsedParagraph(type="Action", text=text))
            current.body_lines.append(text)
            pending_character = None

    _flush_scene()
    return scenes


def parse_pdf_file(pdf_path: str) -> list[ParsedScene]:
    """Parse a PDF from disk (alias for :func:`parse_pdf`)."""
    return parse_pdf(pdf_path)
