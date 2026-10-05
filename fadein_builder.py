"""Zero-dependency Fade In (.fadein / Open Screenplay Format) builder.

Builds a valid OSF ``document.xml`` inside a ``.fadein`` ZIP archive from
``ParsedScene`` objects produced by ``fdx_parser`` (or ``fadein_parser``).

Scene numbers are written the way Fade In stores them: as a ``number``
attribute on the scene-heading paragraph (``<para number="12">``), with the
heading text left as is.
"""

from __future__ import annotations

import io
import uuid
import zipfile
import xml.etree.ElementTree as ET

from fdx_parser import ParsedParagraph, ParsedScene, ScriptNote

__all__ = ["build_fadein"]

_DOCUMENT_TYPE = "Open Screenplay Format document"
_DOCUMENT_VERSION = "30"


def _strip_outer_parentheses(text: str) -> str:
    """Strip one outer pair of parentheses for Fade In Parenthetical style.

    Fade In stores parentheticals without the surrounding parentheses
    (``excited`` rather than ``(excited)``).  Only strip when the first and
    last characters are a matching pair, e.g. ``(a beat)`` -> ``a beat`` but
    ``(angry) (sotto)`` is left alone.
    """
    if len(text) >= 2 and text.startswith("(") and text.endswith(")"):
        inner = text[1:-1]
        if inner.count("(") == inner.count(")"):
            return inner
    return text


def _style_attrs_for_type(ptype: str) -> dict[str, str]:
    """Return the OSF ``<style>`` attributes for an FDX paragraph type."""
    if ptype == "Scene Heading":
        return {"basestylename": "Scene Heading"}
    if ptype == "Action":
        return {"basestylename": "Action"}
    if ptype == "Character":
        return {"basestylename": "Character"}
    if ptype == "Parenthetical":
        return {"basestylename": "Parenthetical"}
    if ptype == "Dialogue":
        return {"basestylename": "Dialogue"}
    if ptype == "Transition":
        return {"basestylename": "Transition"}
    if ptype == "Shot":
        return {"basestylename": "Shot"}
    if ptype == "Center":
        # Fade In's OSF convention for centered body text.
        return {"basestylename": "Action", "align": "center"}
    if ptype == "Normal Text":
        return {
            "name": "Normal Text",
            "label": "Normal Text",
            "font": "Courier",
            "size": "12",
        }
    # Best-effort fallback for paragraph types without a built-in OSF style.
    return {"basestylename": "Action"}


def _make_para(ptype: str, text: str) -> ET.Element:
    """Create a Fade In ``<para>`` element."""
    para = ET.Element("para")
    ET.SubElement(para, "style", _style_attrs_for_type(ptype))
    text_el = ET.SubElement(para, "text")
    text_el.text = text
    return para


def _make_settings() -> ET.Element:
    """Minimal page-geometry settings block used by Fade In."""
    return ET.Element(
        "settings",
        {
            "page_width": "2159",
            "page_height": "2794",
            "margin_top": "317",
            "margin_bottom": "220",
            "margin_left": "317",
            "margin_right": "317",
            "normal_linesperinch": "6.0",
            "element_spacing": "1.00",
            "break_on_sentences": "true",
            "dialogue_continues": "true",
            "dialogue_pagebreaks": "true",
            "cont_text": "(cont'd)",
            "more_text": "(MORE)",
            "scenes_continue": "false",
            "continued_text": "CONTINUED",
            "number_continued": "true",
            "scene_time_separator": " - ",
            "page_header": "#.",
            "page_footer": "",
            "header_alignment": "3",
            "footer_alignment": "3",
            "header_first_page": "false",
            "footer_first_page": "false",
            "pages_locked": "false",
            "pagenumber_start": "1",
            "pagenumber_mode": "1AB",
            "scene_numbering": "false",
            "scenenumber_mode": "1AB",
            "scenenumber_skip_io": "false",
            "scenenumber_start": "1",
            "scenenumber_format": "#",
            "scenenumber_position": "3",
            "scenes_locked": "false",
            "dialogue_numbering": "false",
            "dialoguenumber_start": "1",
            "dialoguenumber_format": "(#)",
            "dialogue_locked": "false",
            "revision": "0",
            "show_revisions": "true",
            "show_all_revisions": "true",
        },
    )


def _make_styles() -> ET.Element:
    """The standard built-in Fade In style definitions."""
    styles = ET.Element("styles")
    style_defs = [
        {"name": "Normal Text", "builtin": "1", "builtin_index": "0", "label": "Normal Text", "font": "Courier", "size": "12"},
        {"name": "Scene Heading", "builtin": "1", "builtin_index": "1", "label": "Scene Heading", "basestylename": "Normal Text", "style_enter": "Action", "style_tab_after": "Action", "font": "Courier", "size": "12", "spacebefore": "2.0", "keepwithnext": "1", "allcaps": "1"},
        {"name": "Action", "builtin": "1", "builtin_index": "2", "label": "Action", "basestylename": "Normal Text", "style_tab_before": "Character", "font": "Courier", "size": "12", "spacebefore": "1.0"},
        {"name": "Character", "builtin": "1", "builtin_index": "3", "label": "Character", "basestylename": "Normal Text", "style_enter": "Dialogue", "style_tab_before": "Action", "style_tab_after": "Parenthetical", "font": "Courier", "size": "12", "spacebefore": "1.0", "keepwithnext": "1", "leftindent": "635", "allcaps": "1"},
        {"name": "Parenthetical", "builtin": "1", "builtin_index": "4", "label": "Parenthetical", "basestylename": "Normal Text", "style_enter": "Dialogue", "style_tab_before": "Dialogue", "style_tab_after": "Dialogue", "font": "Courier", "size": "12", "keepwithnext": "1", "leftindent": "508", "rightindent": "508"},
        {"name": "Dialogue", "builtin": "1", "builtin_index": "5", "label": "Dialogue", "basestylename": "Normal Text", "style_enter": "Action", "style_tab_before": "Parenthetical", "style_tab_after": "Parenthetical", "font": "Courier", "size": "12", "leftindent": "330", "rightindent": "254"},
        {"name": "Transition", "builtin": "1", "builtin_index": "6", "label": "Transition", "basestylename": "Normal Text", "style_enter": "Scene Heading", "style_tab_after": "Action", "font": "Courier", "size": "12", "spacebefore": "1.0", "align": "right", "leftindent": "1016", "rightindent": "127", "allcaps": "1"},
        {"name": "Shot", "builtin": "1", "builtin_index": "7", "label": "Shot", "basestylename": "Normal Text", "style_enter": "Action", "style_tab_after": "Action", "font": "Courier", "size": "12", "spacebefore": "1.0", "keepwithnext": "1", "allcaps": "1"},
    ]
    for attrs in style_defs:
        ET.SubElement(styles, "style", attrs)
    ET.SubElement(styles, "header_style", {"basestylename": "Normal Text"})
    ET.SubElement(styles, "footer_style", {"basestylename": "Normal Text"})
    return styles


def _make_titlepage(title_page: dict | None) -> ET.Element:
    """Create a minimal Fade In title page.

    Title and Author entries are centered paragraphs with ``bookmark``
    attributes, matching Fade In's OSF convention.
    """
    titlepage = ET.Element("titlepage")

    def add_para(bookmark: str, text: str, center: bool) -> None:
        para = ET.Element("para")
        if bookmark:
            para.set("bookmark", bookmark)
        style_attrs = {"basestylename": "Normal Text"}
        if center:
            style_attrs["align"] = "center"
        ET.SubElement(para, "style", style_attrs)
        text_el = ET.SubElement(para, "text")
        text_el.text = text
        titlepage.append(para)

    if not title_page:
        add_para("", "", False)
        return titlepage

    for key, value in title_page.items():
        text = str(value) if value is not None else ""
        canonical_key = str(key)
        lowered = canonical_key.lower()
        if lowered in ("title", "author"):
            add_para(canonical_key.title(), text, center=True)
        elif lowered in ("copyright", "draft", "contact"):
            add_para(canonical_key.title(), text, center=False)
        else:
            add_para(canonical_key, text, center=False)

    return titlepage


_STANDARD_SCENE_INTROS = ("INT.", "EXT.", "INT./EXT.")
_STANDARD_SCENE_TIMES = (
    "DAY",
    "NIGHT",
    "MORNING",
    "AFTERNOON",
    "EVENING",
    "LATER",
    "MOMENTS LATER",
    "CONTINUOUS",
    "THE NEXT DAY",
)
_STANDARD_EXTENSIONS = ("(V.O.)", "(O.S.)", "(O.C.)", "(SUBTITLE)")
_STANDARD_TRANSITIONS = (
    "CUT TO:",
    "FADE IN:",
    "FADE OUT",
    "FADE TO:",
    "DISSOLVE TO:",
    "BACK TO:",
    "MATCH CUT TO:",
    "JUMP CUT TO:",
    "FADE TO BLACK",
)


def _make_lists(scenes: list[ParsedScene]) -> ET.Element:
    """Create Fade In's smart-list block, populated from the script."""
    lists = ET.Element("lists")

    characters_el = ET.SubElement(lists, "characters")
    seen_characters: set[str] = set()
    for scene in scenes:
        for name in scene.characters:
            if name and name not in seen_characters:
                seen_characters.add(name)
                ET.SubElement(characters_el, "character", {"name": name})

    locations_el = ET.SubElement(lists, "locations")
    seen_locations: set[str] = set()
    for scene in scenes:
        for location in (scene.location, scene.set_name):
            if location and location not in seen_locations:
                seen_locations.add(location)
                ET.SubElement(locations_el, "location", {"name": location})

    scene_intros_el = ET.SubElement(lists, "scene_intros")
    for name in _STANDARD_SCENE_INTROS:
        ET.SubElement(scene_intros_el, "scene_intro", {"name": name})

    scene_times_el = ET.SubElement(lists, "scene_times")
    for name in _STANDARD_SCENE_TIMES:
        ET.SubElement(scene_times_el, "scene_time", {"name": name})

    extensions_el = ET.SubElement(lists, "extensions")
    for name in _STANDARD_EXTENSIONS:
        ET.SubElement(extensions_el, "extension", {"name": name})

    transitions_el = ET.SubElement(lists, "transitions")
    for name in _STANDARD_TRANSITIONS:
        ET.SubElement(transitions_el, "transition", {"name": name})

    return lists


def build_fadein(scenes: list[ParsedScene], title_page: dict | None = None) -> bytes:
    """Build a Fade In ``.fadein`` ZIP archive from parsed scenes.

    Args:
        scenes: ``ParsedScene`` objects in script order.
        title_page: Optional mapping of title-page bookmark keys to text
            values.  ``title`` and ``author`` (case-insensitive) become
            centered paragraphs with ``bookmark="Title"`` and
            ``bookmark="Author"`` respectively.

    Returns:
        Raw bytes of a ZIP archive containing a single ``document.xml``.
    """
    root = ET.Element(
        "document",
        {"type": _DOCUMENT_TYPE, "version": _DOCUMENT_VERSION},
    )
    ET.SubElement(
        root,
        "info",
        {"uuid": str(uuid.uuid4()), "pagecount": "1"},
    )
    root.append(_make_settings())
    root.append(_make_styles())

    paragraphs_el = ET.SubElement(root, "paragraphs")
    for scene in scenes:
        heading = _make_para("Scene Heading", (scene.slugline or "").strip())
        number = (scene.scene_number or "").strip()
        if number:
            heading.set("number", number)
        paragraphs_el.append(heading)

        if scene.paragraphs:
            for para in scene.paragraphs:
                text = para.text
                if para.type == "Parenthetical":
                    text = _strip_outer_parentheses(text)
                paragraphs_el.append(_make_para(para.type, text))
        else:
            # Fall back to body lines for scenes without structured paragraphs.
            for line in scene.body_lines:
                paragraphs_el.append(_make_para("Action", line))

    root.append(_make_titlepage(title_page))
    ET.SubElement(root, "spelling", {"language": "en_US"})
    root.append(_make_lists(scenes))

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("document.xml", xml_bytes)
    return buf.getvalue()
