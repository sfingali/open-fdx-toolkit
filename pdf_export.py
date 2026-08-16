"""PDF screenplay exporter for open-fdx-toolkit.

Renders ``ParsedScene`` objects (from ``fdx_parser`` / ``fountain_parser`` /
``fadein_parser`` / ``pdf_import``) into a professionally formatted screenplay
PDF using Courier 12pt with standard Final Draft-style margins:

- Action: 1.5" left margin, full width
- Dialogue: 2.5" left, 2.5" right
- Character: 3.7" left
- Parenthetical: 3.1" left
- Scene headings: 1.5" left, bold-ish (all-caps)
- Transitions: right-aligned

``pymupdf`` is an optional dependency (``pip install pymupdf``).
"""

from __future__ import annotations

import re

from fdx_parser import ParsedScene

__all__ = ["build_pdf", "write_pdf"]

# Page geometry (US Letter, points)
PAGE_W = 612.0
PAGE_H = 792.0
MARGIN_TOP = 36.0
MARGIN_BOTTOM = 36.0
LINE_H = 14.4  # 12pt Courier at 1.2 line spacing

# Element margins (Final Draft defaults)
M_ACTION = 1.5 * 72.0  # 108
M_DIALOGUE = 2.5 * 72.0  # 180
M_CHARACTER = 3.7 * 72.0  # 266.4
M_PAREN = 3.1 * 72.0  # 223.2
M_RIGHT = 1.0 * 72.0  # 72

# Courier 12pt advances 7.2pt per character (0.6em)
CHAR_W = 7.2

_WRAP_RE = re.compile(r"\s+")


def _wrap(text: str, width_pt: float) -> list[str]:
    """Wrap text to fit the given width at Courier 12pt."""
    max_chars = max(1, int(width_pt // CHAR_W))
    words = _WRAP_RE.split(text.strip())
    if not words:
        return [""]
    lines: list[str] = []
    cur = ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= max_chars:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class _Page:
    """Accumulates lines and flushes to pymupdf pages when full."""

    def __init__(self, doc, page_number: int = 1):
        self.doc = doc
        self.page = doc.new_page(width=PAGE_W, height=PAGE_H)
        self.y = MARGIN_TOP
        self.page_number = page_number
        self._draw_footer()

    def _draw_footer(self) -> None:
        # Page number top-right with trailing period — matches Fade In's
        # default page_header="#." convention.
        self.page.insert_text(
            (PAGE_W - M_RIGHT - 3 * CHAR_W, MARGIN_TOP + 4),
            f"{self.page_number}.",
            fontsize=12,
            fontname="courier",
        )

    def _new_page(self) -> None:
        self.page_number += 1
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.y = MARGIN_TOP
        self._draw_footer()

    def emit(self, text: str, left: float, right: float = M_RIGHT,
             bold: bool = False) -> None:
        width = PAGE_W - left - right
        for line in _wrap(text, width):
            if self.y > PAGE_H - MARGIN_BOTTOM:
                self._new_page()
            self.page.insert_text(
                (left, self.y),
                line,
                fontsize=12,
                fontname="courier-bold" if bold else "courier",
            )
            self.y += LINE_H

    def blank(self) -> None:
        self.y += LINE_H * 0.75


def _paragraph_lines(scene: ParsedScene) -> list[tuple[str, str]]:
    """Flatten a scene into (type, text) rows for layout."""
    rows: list[tuple[str, str]] = [("Scene Heading", scene.slugline)]
    for p in scene.paragraphs:
        rows.append((p.type, p.text))
    return rows


def build_pdf(scenes: list[ParsedScene], title: str = "",
              title_page: dict | None = None) -> bytes:
    """Render scenes into a screenplay PDF, returning the PDF bytes.

    Args:
        scenes: ParsedScene list in script order.
        title: Optional title shown centered on the first page (legacy
            inline behavior — kept for backward compatibility).
        title_page: Optional dict of title-page fields, each rendered
            centered on its own dedicated page before the script:

            - ``title`` (str) — script title, large all-caps
            - ``credit`` (str) — e.g. "Production Draft" / "Screenplay by"
            - ``author`` (str) — writer name(s)
            - ``date`` (str) — draft date
            - ``extra`` (list[str]) — additional centered lines
              (studio, contact, etc.)

            When provided, the title page is followed by a page break so
            scene 1 starts on a fresh page.

    Returns:
        PDF file bytes.
    """
    try:
        import pymupdf  # optional dependency
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "PDF export requires pymupdf: pip install pymupdf"
        ) from e

    doc = pymupdf.open()

    if title_page:
        _draw_title_page(doc, title_page)
        # Scene 1 starts on a fresh page
        page = _Page(doc)
    else:
        page = _Page(doc)
        if title:
            page.emit("", 108, 72)
            page.emit(title.upper(), 108, 72, bold=True)
            page.emit("", 108, 72)
            page.emit("", 108, 72)

    for scene in scenes:
        rows = _paragraph_lines(scene)
        prev_type = None
        for ptype, text in rows:
            if not text.strip():
                continue
            # Standard screenplay paragraph spacing: blank line between
            # distinct paragraph blocks (scene heading, action, character,
            # dialogue), but NOT between consecutive dialogue lines or a
            # parenthetical and its dialogue.
            if ptype != prev_type:
                if prev_type is not None and not (
                    (prev_type == "Character" and ptype == "Parenthetical")
                    or (prev_type == "Parenthetical" and ptype == "Dialogue")
                    or (prev_type == "Dialogue" and ptype == "Dialogue")
                ):
                    page.blank()
            prev_type = ptype
            if ptype == "Scene Heading":
                page.emit(text, M_ACTION, M_RIGHT, bold=True)
            elif ptype == "Action":
                page.emit(text, M_ACTION, M_RIGHT)
            elif ptype == "Character":
                page.emit(text, M_CHARACTER, M_RIGHT)
            elif ptype == "Parenthetical":
                page.emit(text, M_PAREN, M_RIGHT)
            elif ptype == "Dialogue":
                page.emit(text, M_DIALOGUE, M_RIGHT)
            elif ptype == "Transition":
                # Right-aligned single line. Left already accounts for the
                # right margin, so pass right=0 to avoid the floating-point
                # wrap bug (50.4 // 7.2 == 6.999... -> wraps "CUT TO:").
                page.emit(text, PAGE_W - M_RIGHT - len(text) * CHAR_W, 0)
            elif ptype == "Center":
                width = PAGE_W - M_ACTION - M_RIGHT
                centered = (PAGE_W - len(text) * CHAR_W) / 2
                page.emit(text, max(centered, M_ACTION), M_RIGHT)
            elif ptype == "Shot":
                page.emit(text, M_ACTION, M_RIGHT)
            else:  # General, Beat, etc. — render as action
                page.emit(text, M_ACTION, M_RIGHT)

    data = doc.tobytes()
    doc.close()
    return data


def _draw_title_page(doc, tp: dict) -> None:
    """Render a dedicated screenplay title page (WGA-style layout).

    Title centered around 1/3 down; writer credit block ~1/2; date lower.
    No page number on the title page.
    """
    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    def center(text: str, y: float, fontsize: float = 12.0,
               bold: bool = False) -> None:
        width = len(text) * CHAR_W * (fontsize / 12.0)
        x = max((PAGE_W - width) / 2, M_ACTION)
        page.insert_text((x, y), text, fontsize=fontsize,
                         fontname="courier-bold" if bold else "courier")

    title = (tp.get("title") or "").upper()
    if title:
        center(title, PAGE_H * 0.33, fontsize=16.0, bold=True)

    credit = tp.get("credit")
    author = tp.get("author")
    extra = tp.get("extra", [])
    y = PAGE_H * 0.50
    if credit:
        center(credit, y)
        y += LINE_H
    if author:
        center(author, y)
        y += LINE_H

    for line in extra:
        center(line, y)
        y += LINE_H

    date = tp.get("date")
    if date:
        center(date, PAGE_H * 0.78)


def write_pdf(path: str, scenes: list[ParsedScene], title: str = "",
              title_page: dict | None = None) -> None:
    """Render scenes to a screenplay PDF file on disk."""
    data = build_pdf(scenes, title=title, title_page=title_page)
    with open(path, "wb") as f:
        f.write(data)
