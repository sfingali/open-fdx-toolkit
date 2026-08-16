"""Plain-text screenplay importer for open-fdx-toolkit.

Classifies a plain-text screenplay (no Fountain markup, no XML) into
``ParsedScene`` objects using content heuristics:

- Scene headings: lines starting INT./EXT./I-E (case-insensitive)
- Character cues: ALL-CAPS lines followed by a dialogue line
- Parentheticals: lines wrapped in parentheses
- Transitions: ALL-CAPS lines ending in ``TO:`` or known transitions
- Everything else: action

Useful for screenplays exported as bare text (``.txt``) from tools that
strip formatting.
"""

from __future__ import annotations

import re

from fdx_parser import ParsedParagraph, ParsedScene, _detect_narrative, _parse_slugline

__all__ = ["parse_txt", "parse_plain_text"]

_SLUG_RE = re.compile(
    r"^(INT\.?/?EXT\.?|EXT\.?|INT\.?|I/?E\.?)\s+",
    re.IGNORECASE,
)
_TRANSITION_RE = re.compile(r"^[A-Z][A-Z0-9 .'\-/]*TO:\s*$")
_EXTRA_TRANSITIONS = frozenset({
    "FADE OUT.", "FADE IN:", "FADE OUT", "FADE IN", "SMASH CUT TO:",
    "CUT TO BLACK.", "FADE TO BLACK.",
})
_PAREN_RE = re.compile(r"^\(.*\)$")


def _is_transition(s: str) -> bool:
    return bool(_TRANSITION_RE.fullmatch(s)) or s.upper() in _EXTRA_TRANSITIONS


def _is_character_cue(s: str, next_line: str | None) -> bool:
    """All-caps line followed by a non-caps dialogue line."""
    stripped = re.sub(r"\([^)]*\)", "", s).strip()
    if not stripped.isupper() or not any(c.isalpha() for c in stripped):
        return False
    if len(stripped) > 32:
        return False
    if _is_transition(s):
        return False
    if next_line is None or not next_line.strip():
        return False
    nxt = next_line.strip()
    if _SLUG_RE.match(nxt):
        return False
    if _PAREN_RE.fullmatch(nxt):  # parenthetical can follow the cue
        return True
    return not nxt.isupper() or len(nxt) > 32


def _classify(text: str, next_line: str | None) -> tuple[str, str]:
    s = text.strip()
    if not s:
        return ("blank", "")
    if _SLUG_RE.match(s):
        return ("Scene Heading", s)
    if _is_transition(s):
        return ("Transition", s)
    if _PAREN_RE.fullmatch(s):
        return ("Parenthetical", s)
    if _is_character_cue(s, next_line):
        return ("Character", s)
    return ("Action", s)


def parse_plain_text(text: str) -> list[ParsedScene]:
    """Parse plain-text screenplay into ParsedScene objects.

    Args:
        text: Raw plain text, one paragraph per line.

    Returns:
        List of ParsedScene dataclasses, one per scene, in script order.
    """
    raw_lines = text.splitlines()
    lines = [l.strip() for l in raw_lines]
    # Skip title page: leading non-slug lines before the first scene heading
    start = 0
    while start < len(lines):
        if _SLUG_RE.match(lines[start]):
            break
        start += 1

    scenes: list[ParsedScene] = []
    current: ParsedScene | None = None
    auto_num = 0
    in_dialogue = False

    for i in range(start, len(lines)):
        s = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        ptype, text = _classify(s, nxt)

        if ptype == "blank":
            in_dialogue = False
            continue
        if ptype == "Scene Heading":
            if current is not None:
                scenes.append(current)
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
            in_dialogue = False
            continue
        if current is None:
            continue

        if ptype == "Character":
            current.paragraphs.append(ParsedParagraph(type="Character", text=text))
            current.body_lines.append(text)
            if text not in current.characters:
                current.characters.append(text)
            in_dialogue = True
        elif ptype == "Dialogue" or (in_dialogue and ptype == "Action"):
            current.paragraphs.append(ParsedParagraph(type="Dialogue", text=text))
            current.body_lines.append(text)
        elif ptype == "Parenthetical":
            current.paragraphs.append(ParsedParagraph(type="Parenthetical", text=text))
            current.body_lines.append(text)
        else:  # Action / Transition
            current.paragraphs.append(ParsedParagraph(type=ptype, text=text))
            current.body_lines.append(text)
            in_dialogue = False

    if current is not None:
        scenes.append(current)
    return scenes


def parse_txt(path: str) -> list[ParsedScene]:
    """Parse a plain-text screenplay file from disk."""
    with open(path, encoding="utf-8") as f:
        return parse_plain_text(f.read())
