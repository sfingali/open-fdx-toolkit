"""Fountain screenplay parser for open-fdx-toolkit.

Parses a subset of the Fountain plain-text screenplay format into the same
``ParsedScene`` / ``ParsedParagraph`` / ``ScriptNote`` dataclasses used by the
FDX parser, so downstream tooling sees one consistent shape.

Supported Fountain elements
---------------------------
- Title page ``Key: value`` blocks at the top of the document
- Scene headings, including trailing ``#N#`` scene numbers
- Character cues, with extensions such as ``(O.S.)`` / ``(V.O.)``
- Dialogue and parentheticals
- Transitions (``CUT TO:``, ``FADE OUT.``, etc.)
- Centered text (``>center<`` and underscore-wrapped ``_center_``)
- Dual dialogue via the ``^`` marker on a character cue
- Notes (``[[note]]``)
- Boneyard comments (``/* comment */``)
- Line-break escapes (a line ending in two spaces or a backslash)
- Page breaks (``===``)

When a document uses explicit ``#N#`` scene numbers, an INT/EXT line without
one is treated as action rather than as an un-numbered scene heading.  This
matches the the sample script fountain/FDX ground-truth pair, where an un-numbered
slugline-style line is an action paragraph in the FDX export.
In documents with no explicit scene numbers, every INT/EXT line is a scene
heading and scenes are auto-numbered in order.
"""

from __future__ import annotations

import re

from fdx_parser import (
    DualDialoguePair,
    ParsedParagraph,
    ParsedScene,
    ScriptNote,
    _detect_narrative,
    _parse_slugline,
)

__all__ = ["parse_fountain"]

_SLUG_RE = re.compile(
    r"^(INT\.?/?EXT\.?|EXT\.?|INT\.?|I/?E\.?)\s+(.+?)\s*$",
    re.IGNORECASE,
)
_SCENE_NUM_RE = re.compile(r"#(\d+)#\s*$")
_TITLE_KEY_RE = re.compile(r"^([^:]+):\s*(.*)$", re.DOTALL)
_NOTE_RE = re.compile(r"^\[\[(.*)\]\]\s*$", re.DOTALL)
_PAGE_BREAK_RE = re.compile(r"^={3,}\s*$")
_TRANSITION_RE = re.compile(r"^[A-Z][A-Z0-9 .'\-/]*TO:\s*$")
_TERMINAL_PUNCT_SPACE_RE = re.compile(r"[.!?]$")

# Transitions that don't end in "TO:".
_EXTRA_TRANSITIONS = frozenset({
    "FADE OUT.", "FADE IN:", "FADE OUT", "FADE IN", "SMASH CUT TO:",
    "CUT TO BLACK.", "FADE TO BLACK.",
})


def _strip_boneyard(text: str) -> str:
    """Remove ``/* ... */`` boneyard comments from the raw text."""
    out: list[str] = []
    i = 0
    in_boneyard = False
    while i < len(text):
        if not in_boneyard:
            start = text.find("/*", i)
            if start == -1:
                out.append(text[i:])
                break
            out.append(text[i:start])
            end = text.find("*/", start + 2)
            if end == -1:
                in_boneyard = True
                i = start + 2
            else:
                i = end + 2
        else:
            end = text.find("*/", i)
            if end == -1:
                i = len(text)
            else:
                in_boneyard = False
                i = end + 2
    return "".join(out)


def _logical_paragraphs(lines: list[str]) -> list[str | None]:
    """Group physical lines into logical paragraphs.

    A blank physical line becomes ``None`` (a paragraph separator).  A line
    ending in two spaces (Fountain line-break) or a backslash joins the next
    physical line into the same logical paragraph with a ``\\n`` between the
    two pieces.
    """
    paragraphs: list[str | None] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        if raw.strip() == "":
            paragraphs.append(None)
            i += 1
            continue

        parts: list[str] = []
        while i < len(lines):
            raw = lines[i]
            if raw.endswith("  "):
                parts.append(raw[:-2].rstrip())
                i += 1
            elif raw.endswith("\\"):
                parts.append(raw[:-1].rstrip())
                i += 1
            else:
                parts.append(raw.rstrip())
                i += 1
                break
        if parts:
            paragraphs.append("\n".join(parts))
    return paragraphs


def _strip_extension(cue: str) -> str:
    """Remove trailing parenthetical extensions from a character cue."""
    previous = None
    while previous != cue:
        previous = cue
        cue = re.sub(r"\s*\([^)]*\)\s*$", "", cue)
    return cue.strip()


def _is_transition(text: str) -> bool:
    """Return True for Fountain transition lines."""
    s = text.strip()
    if not s:
        return False
    if _TRANSITION_RE.fullmatch(s):
        return True
    return s.upper() in _EXTRA_TRANSITIONS


def _is_character_candidate(text: str) -> bool:
    """Return True if *text* looks like an uppercase character cue."""
    s = text.strip()
    if s.endswith("^"):
        s = s[:-1].rstrip()
    name = _strip_extension(s)
    if not name:
        return False
    if not name.isupper():
        return False
    if not any(c.isalpha() for c in name):
        return False
    return True


def _is_parenthetical(text: str) -> bool:
    s = text.strip()
    return s.startswith("(") and s.endswith(")")


def _is_dialogue_like(text: str) -> bool:
    """Return True for a line that can follow a character cue as dialogue."""
    s = text.strip()
    if not s:
        return False
    if not any(c.isalpha() for c in s):
        return False
    if _is_transition(s):
        return False
    if _is_parenthetical(s):
        return False
    if s.startswith("[["):
        return False
    if s.startswith(">") and s.endswith("<"):
        return False
    if s.startswith("_") and s.endswith("_"):
        return False
    if _PAGE_BREAK_RE.fullmatch(s):
        return False
    slug_candidate = _SCENE_NUM_RE.sub("", s).rstrip()
    if _SLUG_RE.match(slug_candidate):
        return False
    return True


def _classify_paragraph(
    paragraph: str,
    idx: int,
    paragraphs: list[str | None],
    seen_explicit_scene_number: bool,
) -> tuple[str, str]:
    """Classify a logical paragraph into a (type, text) pair.

    Scene headings return ``("scene_heading", slugline)`` and the scene number
    is extracted separately from the paragraph's first line.
    """
    text = paragraph.strip()
    first = paragraph.split("\n")[0].strip()

    if _PAGE_BREAK_RE.fullmatch(text):
        return ("page_break", "===")

    note_m = _NOTE_RE.fullmatch(text)
    if note_m:
        return ("note", note_m.group(1).strip())

    # Standard Fountain centered text: >center<.  Underscores inside a
    # centered block (e.g. >_THE END_<) are treated as decoration and removed.
    if text.startswith(">") and text.endswith("<"):
        inner = text[1:-1].strip()
        if inner.startswith("_") and inner.endswith("_") and len(inner) >= 2:
            inner = inner[1:-1].strip()
        return ("center", inner)

    # This repo's Fountain dialect uses underscore-wrapped lines for centered
    # action shots (e.g. _ON BEN_).
    if text.startswith("_") and text.endswith("_") and len(text) >= 2:
        return ("center", text[1:-1].strip())

    # A leading ! forces an action paragraph.
    if text.startswith("!"):
        return ("action", text[1:].strip())

    # Scene heading, with optional trailing #N#.
    scene_num = ""
    slugline = first
    scene_m = _SCENE_NUM_RE.search(first)
    if scene_m:
        scene_num = scene_m.group(1)
        slugline = first[:scene_m.start()].rstrip()
    if _SLUG_RE.match(slugline):
        if scene_num:
            return ("scene_heading", slugline)
        if not seen_explicit_scene_number:
            return ("scene_heading", slugline)
        # The document uses explicit scene numbers, so an un-numbered
        # slugline-style line is action (matches the the sample script FDX export).
        return ("action", text)

    if _is_transition(first):
        return ("transition", first)

    if _is_character_candidate(first):
        raw_cue = first.rstrip()
        name_for_check = raw_cue[:-1].rstrip() if raw_cue.endswith("^") else raw_cue
        name_part = _strip_extension(name_for_check)
        # All-caps action lines often end with punctuation and contain a
        # space (e.g. "BANG BANG BANG.").  Character names with initials
        # ("T.R.") have no space, so they remain valid.
        if _TERMINAL_PUNCT_SPACE_RE.search(name_part) and " " in name_part:
            return ("action", text)

        # In Fountain a character cue is followed immediately by dialogue or
        # by a parenthetical and then dialogue.
        target: str | None = None
        if idx + 1 < len(paragraphs) and paragraphs[idx + 1] is not None:
            target = paragraphs[idx + 1].strip()
            if _is_parenthetical(target):
                if idx + 2 < len(paragraphs) and paragraphs[idx + 2] is not None:
                    target = paragraphs[idx + 2].strip()
                else:
                    target = None
        if target is not None and _is_dialogue_like(target):
            cue_text = raw_cue[:-1].rstrip() if raw_cue.endswith("^") else raw_cue
            return ("character", cue_text)
        return ("action", text)

    if _is_parenthetical(text):
        return ("parenthetical", text)

    return ("action", text)


def _finalize_dialogue_block(
    scene: ParsedScene | None,
    *,
    pending_dual: tuple[str, list[str]] | None,
    block_char: str | None,
    block_dialogue: list[str],
    block_dual: bool,
) -> tuple[tuple[str, list[str]] | None, str | None, list[str], bool]:
    """Close the current dialogue block, creating a dual-dialogue pair if one
    is pending and the current block is the second half of the pair."""
    if block_char is None:
        return pending_dual, None, [], False

    new_pending = pending_dual
    if new_pending is None:
        if block_dual:
            new_pending = (block_char, list(block_dialogue))
    else:
        char_a, dialogue_a = new_pending
        if dialogue_a and block_dialogue and scene is not None:
            scene.dual_dialogue_pairs.append(DualDialoguePair(
                character_a=char_a,
                dialogue_a="\n".join(dialogue_a),
                character_b=block_char,
                dialogue_b="\n".join(block_dialogue),
            ))
            scene.has_dual_dialogue = True
        new_pending = None
    return new_pending, None, [], False


def _append_characters_unique(scene: ParsedScene) -> None:
    seen: set[str] = set()
    unique: list[str] = []
    for char in scene.characters:
        if char not in seen:
            seen.add(char)
            unique.append(char)
    scene.characters = unique


def parse_fountain(text: str) -> list[ParsedScene]:
    """Parse Fountain screenplay text into a list of ParsedScene objects.

    Args:
        text: Raw Fountain text.

    Returns:
        List of ParsedScene dataclasses, one per scene, in script order.
    """
    text = _strip_boneyard(text)
    paragraphs = _logical_paragraphs(text.splitlines())

    # Title page: leading ``Key: value`` lines before the first blank line /
    # first screenplay element.
    title_page: list[tuple[str, str]] = []
    idx = 0
    while idx < len(paragraphs):
        paragraph = paragraphs[idx]
        if paragraph is None:
            break
        m = _TITLE_KEY_RE.match(paragraph)
        if not m:
            break
        title_page.append((m.group(1).strip(), m.group(2).strip()))
        idx += 1

    scenes: list[ParsedScene] = []
    seen_explicit_scene_number = False
    auto_num = 0
    title_page_attached = False

    current: ParsedScene | None = None
    in_dialogue = False
    block_char: str | None = None
    block_dialogue: list[str] = []
    block_dual = False
    pending_dual: tuple[str, list[str]] | None = None

    def _new_scene(slugline: str, scene_num: str) -> ParsedScene:
        parsed = _parse_slugline(slugline)
        return ParsedScene(
            scene_number=scene_num or "",
            scene_number_source="script" if scene_num else "auto",
            slugline=slugline,
            interior_exterior=parsed["interior_exterior"],
            location=parsed["location"],
            set_name=parsed["set_name"],
            time_of_day=parsed["time_of_day"],
            body_lines=[],
            characters=[],
            paragraphs=[],
            page_eighths=1,
            narrative_position_hint=_detect_narrative(slugline),
        )

    def _finalize_block() -> None:
        nonlocal pending_dual, block_char, block_dialogue, block_dual, in_dialogue
        pending_dual, block_char, block_dialogue, block_dual = _finalize_dialogue_block(
            current,
            pending_dual=pending_dual,
            block_char=block_char,
            block_dialogue=block_dialogue,
            block_dual=block_dual,
        )
        in_dialogue = False

    def _flush_scene() -> None:
        nonlocal current, title_page_attached, pending_dual, block_char, block_dialogue, block_dual, in_dialogue
        if current is None:
            pending_dual = None
            return
        _append_characters_unique(current)
        if title_page and not title_page_attached:
            current.script_notes = [ScriptNote(name=key, text=value) for key, value in title_page]
            title_page_attached = True
        scenes.append(current)
        current = None
        pending_dual = None
        block_char = None
        block_dialogue = []
        block_dual = False
        in_dialogue = False

    for pos, paragraph in enumerate(paragraphs):
        if paragraph is None:
            _finalize_block()
            continue

        if in_dialogue:
            # Everything until the next blank line belongs to the current
            # dialogue block (Fountain rule).
            if _is_parenthetical(paragraph):
                parenthetical_text = paragraph.strip()
                current.paragraphs.append(ParsedParagraph(type="Parenthetical", text=parenthetical_text))
                current.body_lines.append(parenthetical_text)
            else:
                dialogue_text = paragraph.strip()
                current.paragraphs.append(ParsedParagraph(type="Dialogue", text=dialogue_text))
                current.body_lines.append(dialogue_text)
                block_dialogue.append(dialogue_text)
            continue

        kind, value = _classify_paragraph(paragraph, pos, paragraphs, seen_explicit_scene_number)

        if kind == "scene_heading":
            _finalize_block()
            _flush_scene()
            slugline = value
            scene_num_m = _SCENE_NUM_RE.search(paragraph.split("\n")[0].strip())
            scene_num = scene_num_m.group(1) if scene_num_m else ""
            auto_num += 1
            current = _new_scene(slugline, scene_num)
            if scene_num:
                current.scene_number = scene_num
                current.scene_number_source = "script"
                seen_explicit_scene_number = True
            else:
                current.scene_number = str(auto_num)
                current.scene_number_source = "auto"
            continue

        if current is None:
            continue

        if kind == "note":
            current.script_notes.append(ScriptNote(name="", text=value))
        elif kind == "page_break":
            current.paragraphs.append(ParsedParagraph(type="Page Break", text="==="))
        elif kind == "center":
            current.paragraphs.append(ParsedParagraph(type="Center", text=value))
            current.body_lines.append(value)
        elif kind == "transition":
            current.paragraphs.append(ParsedParagraph(type="Transition", text=value))
            current.body_lines.append(value)
        elif kind == "character":
            _finalize_block()
            block_char = value
            block_dialogue = []
            block_dual = paragraph.split("\n")[0].rstrip().endswith("^")
            in_dialogue = True
            current.paragraphs.append(ParsedParagraph(type="Character", text=value))
            current.characters.append(value)
            current.body_lines.append(value)
        else:
            current.paragraphs.append(ParsedParagraph(type="Action", text=value))
            current.body_lines.append(value)

    _finalize_block()
    _flush_scene()
    return scenes
