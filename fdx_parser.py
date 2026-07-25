"""open-fdx-toolkit: Zero-dependency Final Draft (.fdx) XML parser.

Extracts structured screenplay data from Final Draft 8+ XML files into
clean Python dataclasses — scenes, characters, dialogue, actions, page
lengths, and narrative positions. No external dependencies beyond stdlib.

Usage:
    from fdx_parser import parse_file

    scenes = parse_file("my_script.fdx")
    for s in scenes:
        print(f"Scene {s.scene_number}: {s.slugline}")
        print(f"  Characters: {', '.join(s.characters[:3])}")
        print(f"  Page length: {s.page_eighths}/8")
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__version__ = "0.1.0"
__all__ = ["ParsedScene", "ParsedParagraph", "ScriptNote", "DualDialoguePair", "parse_file", "parse_fdx"]


@dataclass
class ParsedParagraph:
    """A single paragraph within a scene, with type and optional text style."""

    type: str  # "Action", "Character", "Dialogue", "Parenthetical", etc.
    text: str
    styles: list[str] = field(default_factory=list)  # ["Bold", "Italic"], etc.


@dataclass
class ScriptNote:
    """A script note attached to a scene."""

    name: str
    text: str
    author: str = ""
    date_time: str = ""
    color: str = ""


@dataclass
class DualDialoguePair:
    """A pair of simultaneous dialogue blocks."""

    character_a: str
    dialogue_a: str
    character_b: str
    dialogue_b: str


@dataclass
class ParsedScene:
    """A single scene extracted from an FDX file."""

    scene_number: str
    scene_number_source: str = "script"
    slugline: str = ""
    interior_exterior: str = ""
    location: str = ""
    set_name: str = ""
    time_of_day: str = ""
    body_lines: list[str] = field(default_factory=list)
    characters: list[str] = field(default_factory=list)
    paragraphs: list[ParsedParagraph] = field(default_factory=list)
    page_eighths: int = 1
    narrative_position_hint: str | None = None
    has_dual_dialogue: bool = False
    dual_dialogue_pairs: list[DualDialoguePair] = field(default_factory=list)
    synopsis: str = ""
    script_notes: list[ScriptNote] = field(default_factory=list)
    story_date_marker: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_number": self.scene_number,
            "scene_number_source": self.scene_number_source,
            "slugline": self.slugline,
            "interior_exterior": self.interior_exterior,
            "location": self.location,
            "set_name": self.set_name,
            "time_of_day": self.time_of_day,
            "body_lines": self.body_lines,
            "characters": self.characters,
            "paragraphs": [
                {"type": p.type, "text": p.text, "styles": p.styles}
                for p in self.paragraphs
            ],
            "page_eighths": self.page_eighths,
            "narrative_position_hint": self.narrative_position_hint,
            "has_dual_dialogue": self.has_dual_dialogue,
            "dual_dialogue_pairs": [
                {"character_a": d.character_a, "dialogue_a": d.dialogue_a,
                 "character_b": d.character_b, "dialogue_b": d.dialogue_b}
                for d in self.dual_dialogue_pairs
            ],
            "synopsis": self.synopsis,
            "script_notes": [
                {"name": s.name, "text": s.text, "author": s.author}
                for s in self.script_notes
            ],
            "story_date_marker": self.story_date_marker,
        }


# Slugline extraction regex — handles INT, EXT, I/E, and sub-locations
_SLUG_RE = re.compile(
    r"^(INT\.?/?EXT\.?|EXT\.?|INT\.?|I/?E\.?)\s+(.+?)\s*$",
    re.IGNORECASE,
)

_KNOWN_TIMES = frozenset({
    "DAY", "NIGHT", "DAWN", "DUSK", "MORNING", "AFTERNOON", "EVENING",
    "CONTINUOUS", "LATER", "MOMENTS LATER", "SAME", "MAGIC HOUR",
    "SUNRISE", "SUNSET",
})


def _parse_slugline(slug: str) -> dict[str, str]:
    """Parse a scene heading into interior_exterior, location, set_name, time."""
    slug = slug.strip()
    m = _SLUG_RE.match(slug)
    if not m:
        return {
            "interior_exterior": "",
            "location": slug,
            "set_name": slug,
            "time_of_day": "",
        }

    prefix = m.group(1).upper().rstrip(".")
    if "/" in prefix:
        ie = "INT/EXT"
    elif prefix == "INT":
        ie = "INT"
    elif prefix == "EXT":
        ie = "EXT"
    else:
        ie = prefix

    body = m.group(2).strip()
    time_of_day = ""
    parts = body.rsplit(" - ", 1)
    if len(parts) == 2:
        last = parts[1].strip()
        last_clean = re.sub(r"\(.*?\)", "", last).strip().upper()
        if last_clean in _KNOWN_TIMES:
            time_of_day = last
            body = parts[0].strip()

    body_parts = body.rsplit(" - ", 1)
    if len(body_parts) == 2:
        location = body_parts[0].strip()
        set_name = body_parts[1].strip()
    else:
        location = body.strip()
        set_name = location

    return {
        "interior_exterior": ie,
        "location": location,
        "set_name": set_name,
        "time_of_day": time_of_day,
    }


def _get_text_and_styles(el: ET.Element) -> tuple[str, list[list[str]]]:
    """Extract joined text and per-element style lists from <Text> children."""
    text_parts: list[str] = []
    style_parts: list[list[str]] = []
    for t in el.findall("Text"):
        text_parts.append(t.text or "")
        style_str = (t.get("Style") or "").strip()
        if style_str and style_str not in ("0",):
            style_parts.append([s.strip() for s in style_str.split("+") if s.strip()])
        else:
            style_parts.append([])
    return "".join(text_parts), style_parts


def _flatten_styles(style_lists: list[list[str]]) -> list[str]:
    """Flatten and deduplicate style lists from multiple <Text> elements."""
    seen: set[str] = set()
    result: list[str] = []
    for styles in style_lists:
        for s in styles:
            if s not in seen:
                seen.add(s)
                result.append(s)
    return result


def _estimate_page_eighths(length_str: str) -> int:
    """Convert FDX 'N/8' length to integer eighths."""
    try:
        return int(length_str.split("/")[0])
    except (ValueError, IndexError):
        return 1


def _detect_narrative(slugline: str) -> str | None:
    """Detect non-linear narrative markers in a slugline."""
    upper = slugline.upper()
    if "FLASHBACK" in upper:
        return "flashback"
    if "FLASH FORWARD" in upper:
        return "flashforward"
    if "DREAM" in upper:
        return "dream"
    if "MEMORY" in upper:
        return "memory"
    return None


def parse_fdx(text: str) -> list[ParsedScene]:
    """Parse FDX XML text into a list of ParsedScene objects.

    Handles:
    - Scene headings with location/set/time extraction
    - Scene properties (page length, scene number)
    - Character cues, dialogue, and action paragraphs
    - Flashback/dream/memory detection from sluglines
    - Automatic scene numbering for un-numbered scenes

    Args:
        text: Raw FDX XML string.

    Returns:
        List of ParsedScene dataclasses, one per scene, in script order.
    """
    root = ET.fromstring(text)
    content = root.find("Content")
    if content is None:
        return []

    paragraphs = content.findall("Paragraph")
    scenes: list[ParsedScene] = []

    current_slugline: str | None = None
    current_body: list[str] = []
    current_chars: list[str] = []
    current_paragraphs: list[ParsedParagraph] = []
    current_page_eighths: int = 1
    current_narrative: str | None = None
    current_scene_num: str = ""
    current_synopsis: str = ""
    current_script_notes: list[ScriptNote] = []
    current_dual_pairs: list[DualDialoguePair] = []
    auto_num: int = 0
    has_dual: bool = False

    for para in paragraphs:
        ptype = para.get("Type", "")
        text, style_lists = _get_text_and_styles(para)
        text = text.strip()
        styles = _flatten_styles(style_lists)

        # Extract ScriptNotes and DualDialogue BEFORE the text-emptiness skip,
        # since General paragraphs wrapping these have no direct <Text> children.
        for sn in para.findall("ScriptNote"):
            sn_para = sn.find("Paragraph")
            sn_text = "".join(t.text or "" for t in (sn_para.findall("Text") if sn_para is not None else [])).strip()
            if sn_text:
                current_script_notes.append(ScriptNote(
                    name=sn.get("Name", ""),
                    text=sn_text,
                    author=sn.get("Author", ""),
                    date_time=sn.get("DateTime", ""),
                    color=sn.get("Color", ""),
                ))

        has_dd_child = para.find("DualDialogue") is not None

        if not text and ptype != "Scene Heading" and not has_dd_child:
            continue

        # Track as structured paragraph
        pp = ParsedParagraph(type=ptype, text=text, styles=styles)

        if ptype == "Scene Heading":
            # Save previous scene
            if current_slugline is not None:
                auto_num += 1
                parsed = _parse_slugline(current_slugline)
                scenes.append(ParsedScene(
                    scene_number=current_scene_num or str(auto_num),
                    scene_number_source="script" if current_scene_num else "auto",
                    slugline=current_slugline,
                    interior_exterior=parsed["interior_exterior"],
                    location=parsed["location"],
                    set_name=parsed["set_name"],
                    time_of_day=parsed["time_of_day"],
                    body_lines=current_body.copy(),
                    characters=list(set(current_chars)),
                    paragraphs=current_paragraphs.copy(),
                    page_eighths=current_page_eighths,
                    has_dual_dialogue=has_dual,
                    dual_dialogue_pairs=current_dual_pairs.copy(),
                    synopsis=current_synopsis,
                    script_notes=current_script_notes.copy(),
                    narrative_position_hint=current_narrative,
                ))

            # Start new scene
            current_slugline = text
            current_narrative = _detect_narrative(text)
            current_body = []
            current_chars = []
            current_paragraphs = []
            current_dual_pairs = []
            current_script_notes = []
            current_synopsis = ""
            has_dual = False
            sp = para.find("SceneProperties")
            current_scene_num = sp.get("Number", "") if sp is not None else ""
            current_page_eighths = (
                _estimate_page_eighths(sp.get("Length", "1/8"))
                if sp is not None
                else 1
            )
            # Extract synopsis from SceneProperties/Summary
            if sp is not None:
                summary = sp.find("Summary")
                if summary is not None:
                    summary_para = summary.find("Paragraph")
                    if summary_para is not None:
                        current_synopsis = "".join(
                            t.text or "" for t in summary_para.findall("Text")
                        ).strip()

        elif ptype == "Character":
            current_chars.append(text)
            current_body.append(text)
            current_paragraphs.append(pp)
            # Walk DualDialogue children if present
            dual = para.find("DualDialogue")
            if dual is not None:
                has_dual = True
                dd_chars: list[str] = []
                dd_dialogue: list[str] = []
                for dd_para in dual.findall("Paragraph"):
                    dd_type = dd_para.get("Type", "")
                    dd_text = "".join(t.text or "" for t in dd_para.findall("Text")).strip()
                    if dd_type == "Character":
                        dd_chars.append(dd_text)
                    elif dd_type == "Dialogue":
                        dd_dialogue.append(dd_text)
                # Pair them up
                for i in range(min(len(dd_chars), len(dd_dialogue))):
                    if i + 1 < len(dd_chars) and i + 1 < len(dd_dialogue):
                        # We have pairs — take two at a time
                        if i % 2 == 0:
                            current_dual_pairs.append(DualDialoguePair(
                                character_a=dd_chars[i], dialogue_a=dd_dialogue[i],
                                character_b=dd_chars[i + 1], dialogue_b=dd_dialogue[i + 1],
                            ))

        elif ptype == "Dialogue":
            current_body.append(text)
            current_paragraphs.append(pp)

        elif ptype == "Parenthetical":
            current_body.append(f"({text})" if not text.startswith("(") else text)
            current_paragraphs.append(pp)

        elif ptype in ("Action", "General", "Transition", "Shot",
                       "Beat", "Cast List", "Center", "Last Revised",
                       "Page #", "Right", "Script", "StoryMap",
                       "Normal Text"):
            current_body.append(text)
            current_paragraphs.append(pp)
            # DualDialogue can appear inside General paragraphs too (Final Draft quirk)
            if ptype == "General":
                dual = para.find("DualDialogue")
                if dual is not None:
                    has_dual = True
                    dd_chars: list[str] = []
                    dd_dialogue: list[str] = []
                    for dd_para in dual.findall("Paragraph"):
                        dd_type = dd_para.get("Type", "")
                        dd_text = "".join(t.text or "" for t in dd_para.findall("Text")).strip()
                        if dd_type == "Character":
                            dd_chars.append(dd_text)
                        elif dd_type == "Dialogue":
                            dd_dialogue.append(dd_text)
                    for i in range(0, min(len(dd_chars), len(dd_dialogue)), 2):
                        if i + 1 < len(dd_chars) and i + 1 < len(dd_dialogue):
                            current_dual_pairs.append(DualDialoguePair(
                                character_a=dd_chars[i], dialogue_a=dd_dialogue[i],
                                character_b=dd_chars[i + 1], dialogue_b=dd_dialogue[i + 1],
                            ))

    # Save final scene
    if current_slugline is not None:
        parsed = _parse_slugline(current_slugline)
        auto_num += 1
        scenes.append(ParsedScene(
            scene_number=current_scene_num or str(auto_num),
            scene_number_source="script" if current_scene_num else "auto",
            slugline=current_slugline,
            interior_exterior=parsed["interior_exterior"],
            location=parsed["location"],
            set_name=parsed["set_name"],
            time_of_day=parsed["time_of_day"],
            body_lines=current_body.copy(),
            characters=list(set(current_chars)),
            paragraphs=current_paragraphs.copy(),
            page_eighths=current_page_eighths,
            has_dual_dialogue=has_dual,
            dual_dialogue_pairs=current_dual_pairs.copy(),
            synopsis=current_synopsis,
            script_notes=current_script_notes.copy(),
            narrative_position_hint=current_narrative,
        ))

    return scenes


def parse_file(path: str | Path) -> list[ParsedScene]:
    """Parse an FDX file from disk.

    Args:
        path: Path to a .fdx file.

    Returns:
        List of ParsedScene dataclasses.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ET.ParseError: If the file isn't valid XML.
    """
    return parse_fdx(Path(path).read_text(encoding="utf-8"))
