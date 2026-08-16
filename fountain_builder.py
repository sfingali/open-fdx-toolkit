"""Fountain builder for open-fdx-toolkit.

Serializes ``ParsedScene`` objects (from ``fdx_parser`` / ``fadein_parser`` /
``pdf_import``) into Fountain plain-text screenplay markup.

Fountain conventions used:
- Scene headings: ``INT. KITCHEN - DAY #12#`` (scene number as trailing ``#N#``)
- Character cues: ``BEN`` / ``MARIE (O.S.)``, followed by dialogue lines
- Parentheticals: ``(a beat)`` between cue and dialogue
- Centered elements: ``_ON BEN_`` (underscore-wrapped)
- Transitions: ``CUT TO:`` on their own line
- Title page: ``Title:`` / ``Author:`` key-value blocks at the top
- Scene separators: blank lines between elements
"""

from __future__ import annotations

from fdx_parser import ParsedScene

__all__ = ["build_fountain", "write_fountain"]

# Fountain requires blank lines between most elements; dialogue lines within
# one block stay contiguous.
_TITLE_FIELDS = ("Title", "Credit", "Author", "Source", "Draft date",
                 "Copyright", "Contact")


def _title_block(scenes: list[ParsedScene], title: str | None = None,
                 author: str | None = None) -> list[str]:
    """Build the Fountain title-page key:value block, if any metadata exists."""
    fields: list[str] = []
    if title:
        fields.append(f"Title: {title}")
    if author:
        fields.append(f"Author: {author}")
    # Pull Title/Author from the first scene's script_notes if not given
    if scenes and not fields:
        for note in scenes[0].script_notes:
            if note.name.lower() in ("title", "author", "draft date", "copyright"):
                fields.append(f"{note.name}: {note.text}")
    if not fields:
        return []
    return fields + [""]


def _fountain_lines(scene: ParsedScene) -> list[str]:
    """Serialize one scene's paragraphs into Fountain lines."""
    out: list[str] = []

    def _sep() -> None:
        if out and out[-1] != "":
            out.append("")

    # Scene heading with trailing scene number. Always write the number when
    # present (auto or script) — an unnumbered document makes the Fountain
    # parser treat bare INT./EXT. action lines as scene headings, breaking
    # round-trips for FDX files with auto-numbered scenes.
    slug = scene.slugline.strip()
    if scene.scene_number:
        slug = f"{slug} #{scene.scene_number}#"
    out.append(slug)

    # Track dialogue blocks: character cue + parenthetical + dialogue lines
    # must be contiguous (no blank lines between them in Fountain).
    in_dialogue = False
    for p in scene.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        if p.type == "Action":
            if in_dialogue:
                out.append("")
                in_dialogue = False
            _sep()
            # All-caps action lines (e.g. "PRESENT-", "NEXT TO HIS BELOVED,
            # JOYCE") would be re-parsed as character cues; force them back
            # to action with Fountain's "!" marker.
            if t.isupper() and any(c.isalpha() for c in t):
                out.append(f"!{t}")
            else:
                out.append(t)
        elif p.type == "Character":
            if in_dialogue:
                out.append("")
            out.append(t)
            in_dialogue = True
        elif p.type == "Parenthetical":
            out.append(t if t.startswith("(") else f"({t})")
            in_dialogue = True
        elif p.type == "Dialogue":
            out.append(t)
            in_dialogue = True
        elif p.type == "Transition":
            if in_dialogue:
                out.append("")
                in_dialogue = False
            _sep()
            out.append(t)
        elif p.type == "Center":
            if in_dialogue:
                out.append("")
                in_dialogue = False
            _sep()
            out.append(f"_{t}_")
        elif p.type == "Shot":
            if in_dialogue:
                out.append("")
                in_dialogue = False
            _sep()
            out.append(t.upper())
        else:  # General, Beat, Page Break, etc.
            if in_dialogue:
                out.append("")
                in_dialogue = False
            _sep()
            out.append(t)
    return out


def build_fountain(scenes: list[ParsedScene], title: str | None = None,
                   author: str | None = None) -> str:
    """Serialize scenes into Fountain text.

    Args:
        scenes: ParsedScene list in script order.
        title: Optional script title for the Fountain title page.
        author: Optional author name for the Fountain title page.

    Returns:
        Fountain markup as a string.
    """
    blocks: list[str] = _title_block(scenes, title, author)
    for scene in scenes:
        lines = _fountain_lines(scene)
        if blocks and blocks[-1] != "":
            blocks.append("")
        blocks.extend(lines)
    # Ensure exactly one trailing blank line
    while blocks and blocks[-1] == "":
        blocks.pop()
    blocks.append("")
    return "\n".join(blocks)


def write_fountain(path: str, scenes: list[ParsedScene],
                   title: str | None = None, author: str | None = None) -> None:
    """Serialize scenes to a Fountain file on disk."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_fountain(scenes, title=title, author=author))
