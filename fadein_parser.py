"""Zero-dependency Fade In (.fadein / Open Screenplay Format) parser.

Parses the ``document.xml`` inside a ``.fadein`` ZIP archive into the same
``ParsedScene`` / ``ParsedParagraph`` / ``ScriptNote`` dataclasses used by
``fdx_parser``.

Fade In's OSF paragraph style names map 1:1 to Final Draft paragraph types:
``Scene Heading``, ``Action``, ``Character``, ``Parenthetical``,
``Dialogue``, ``Transition``, etc.  Scene numbers are stored in Fade In's
convention as a trailing ``#N#`` on the scene-heading text, so a heading
``INT. KITCHEN - DAY #12#`` parses as slugline ``INT. KITCHEN - DAY`` with
scene number ``12``.
"""

from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET

from fdx_parser import (
    ParsedParagraph,
    ParsedScene,
    ScriptNote,
    _detect_narrative,
    _parse_slugline,
)

__all__ = ["parse_fadein_bytes"]

# Trailing Fade In scene-number convention: "SLUGLINE #N#".
_SCENE_NUMBER_RE = re.compile(
    r"^(?P<slug>.*?)\s*#(?P<number>[^#]+)#\s*$",
    re.DOTALL,
)


def _split_scene_number(heading_text: str) -> tuple[str, str]:
    """Return (slugline, scene_number) for a scene-heading text.

    Scene numbers may be absent, in which case the caller auto-numbers.
    """
    match = _SCENE_NUMBER_RE.match(heading_text)
    if match:
        return match.group("slug").strip(), match.group("number").strip()
    return heading_text.strip(), ""


def _style_type(style: ET.Element | None) -> str:
    """Determine the FDX paragraph type for a Fade In ``<style>`` element."""
    if style is None:
        return ""

    base_style = style.get("basestylename") or style.get("basestyle") or ""
    style_name = style.get("name") or ""
    align = style.get("align")

    # Fade In stores centered body text as an Action/Normal Text paragraph
    # with align="center".  Fountain's Center type maps to this convention.
    if align == "center" and base_style in ("Action", "Normal Text", ""):
        return "Center"

    if base_style:
        return base_style
    if style_name:
        return style_name
    return ""


def _para_text(para: ET.Element) -> str:
    """Joined text of ALL of a paragraph's ``<text>`` runs.

    Fade In splits a paragraph into several ``<text>`` runs whenever the
    formatting or revision state changes mid-line (e.g. ``<text>INT. </text>
    <text revision="1">FORESTER (MOVING)</text><text> - DAY</text>``).
    Reading only the first run truncated such headings to ``INT.``.
    """
    return "".join("".join(t.itertext()) for t in para.findall("text")).strip()


def _append_scene(
    scenes: list[ParsedScene],
    slugline: str,
    scene_number: str,
    body_lines: list[str],
    characters: list[str],
    paragraphs: list[ParsedParagraph],
    auto_num: int,
) -> None:
    """Build and append a ParsedScene using fdx_parser's slugline parsing."""
    parsed = _parse_slugline(slugline)
    scenes.append(
        ParsedScene(
            scene_number=scene_number or str(auto_num),
            scene_number_source="script" if scene_number else "auto",
            slugline=slugline,
            interior_exterior=parsed["interior_exterior"],
            location=parsed["location"],
            set_name=parsed["set_name"],
            time_of_day=parsed["time_of_day"],
            body_lines=body_lines.copy(),
            characters=list(dict.fromkeys(characters)),
            paragraphs=paragraphs.copy(),
            narrative_position_hint=_detect_narrative(slugline),
        )
    )


def parse_fadein_bytes(data: bytes) -> list[ParsedScene]:
    """Parse a ``.fadein`` ZIP archive's ``document.xml`` into scenes.

    Args:
        data: Raw bytes of a Fade In ``.fadein`` file (a ZIP archive
            containing ``document.xml``).

    Returns:
        List of ``ParsedScene`` dataclasses, one per scene, in script order.
    """
    if not data:
        return []

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        if not names:
            return []
        if "document.xml" in names:
            document_name = "document.xml"
        else:
            document_name = next(
                (name for name in names if name.lower().endswith(".xml")),
                names[0],
            )
        xml_bytes = zf.read(document_name)

    root = ET.fromstring(xml_bytes)
    paragraphs_el = root.find("paragraphs")
    if paragraphs_el is None:
        return []

    scenes: list[ParsedScene] = []
    current_slugline: str | None = None
    current_body: list[str] = []
    current_chars: list[str] = []
    current_paragraphs: list[ParsedParagraph] = []
    current_scene_num = ""
    auto_num = 0

    for para in paragraphs_el.findall("para"):
        ptype = _style_type(para.find("style"))
        text = _para_text(para)

        if ptype == "Scene Heading":
            slugline, scene_num = _split_scene_number(text)
            if not slugline:
                continue

            if current_slugline is not None:
                auto_num += 1
                _append_scene(
                    scenes,
                    current_slugline,
                    current_scene_num,
                    current_body,
                    current_chars,
                    current_paragraphs,
                    auto_num,
                )

            current_slugline = slugline
            current_scene_num = scene_num
            current_body = []
            current_chars = []
            current_paragraphs = []
            continue

        if not text:
            continue
        if current_slugline is None:
            # Like fdx_parser, paragraphs before the first scene heading are
            # not attached to a scene.
            continue

        if ptype == "Character":
            pp = ParsedParagraph(type=ptype, text=text)
            current_chars.append(text)
            current_body.append(text)
            current_paragraphs.append(pp)
        elif ptype == "Dialogue":
            pp = ParsedParagraph(type=ptype, text=text)
            current_body.append(text)
            current_paragraphs.append(pp)
        elif ptype == "Parenthetical":
            wrapped = text if text.startswith("(") else f"({text})"
            pp = ParsedParagraph(type="Parenthetical", text=wrapped)
            current_body.append(wrapped)
            current_paragraphs.append(pp)
        elif ptype in (
            "Action",
            "General",
            "Transition",
            "Shot",
            "Beat",
            "Cast List",
            "Center",
            "Last Revised",
            "Page #",
            "Right",
            "Script",
            "StoryMap",
            "Normal Text",
        ):
            pp = ParsedParagraph(type=ptype, text=text)
            current_body.append(text)
            current_paragraphs.append(pp)
        # Unknown paragraph styles are intentionally ignored to avoid
        # polluting the scene body.

    if current_slugline is not None:
        auto_num += 1
        _append_scene(
            scenes,
            current_slugline,
            current_scene_num,
            current_body,
            current_chars,
            current_paragraphs,
            auto_num,
        )

    return scenes
