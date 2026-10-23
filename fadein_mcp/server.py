"""Fade In MCP server — read, diff, search and edit .fadein screenplays.

Run over stdio:  python -m fadein_mcp.server
Transport is stdio only; every tool takes a file path.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import core

mcp = FastMCP("fadein")


def _resolve(path: str) -> str:
    """Accept absolute paths, ~, or a bare filename inside the drafts folder."""
    p = Path(path).expanduser()
    if p.is_absolute():
        return str(p)
    candidate = core.DEFAULT_DRAFTS_DIR / p
    return str(candidate if candidate.exists() else p)


@mcp.tool()
def list_scripts(folder: str | None = None, pattern: str = "*") -> dict:
    """List screenplay files (newest first) in the drafts folder or a given folder.

    Use this first when you do not know the exact filename. `pattern` is a glob
    such as "THE WAIF*" to narrow to one production.
    """
    return core.list_scripts(_resolve(folder) if folder else None, pattern)


@mcp.tool()
def script_info(path: str) -> dict:
    """Summarise a screenplay: real Fade In page count, scene count, words,
    character count, locations, flashback scenes, revision level, file hash.

    Page count is read from the document's own `pagecount` attribute — the
    number Fade In computed — never estimated from scene counts.
    """
    return core.script_info(_resolve(path))


@mcp.tool()
def list_scenes(
    path: str, offset: int = 0, limit: int = 40, contains: str | None = None
) -> dict:
    """Page through scene headings: number, slugline, main characters, word
    count, and the opening line of each scene. `contains` filters on any text
    inside the scene (case-insensitive)."""
    return core.list_scenes(_resolve(path), offset=offset, limit=limit, contains=contains)


@mcp.tool()
def get_scene(path: str, scenes: str) -> dict:
    """Return full text for one or more scenes. `scenes` accepts "12", "12-15",
    or "12,14,20"."""
    return core.get_scene(_resolve(path), scenes)


@mcp.tool()
def search_script(
    path: str,
    query: str,
    regex: bool = False,
    limit: int = 40,
    context_chars: int = 60,
) -> dict:
    """Search every element of a screenplay (headings, action, dialogue),
    returning scene numbers, element types and surrounding context. Set
    `regex` to treat `query` as a regular expression."""
    return core.search(
        _resolve(path), query, regex=regex, limit=limit, context_chars=context_chars
    )


@mcp.tool()
def character_report(path: str) -> dict:
    """Per-character breakdown: scene appearances and dialogue word counts.

    Character cues are normalised, so "BEN", "Ben" and "BEN (CONT'D)" collapse
    into one character — which the raw file does not do.
    """
    return core.character_report(_resolve(path))


@mcp.tool()
def location_report(path: str) -> dict:
    """Locations grouped from sluglines with INT/EXT and time of day, plus the
    scene numbers set in each."""
    return core.location_report(_resolve(path))


@mcp.tool()
def compare_drafts(path_a: str, path_b: str) -> dict:
    """Diff two drafts: page/scene/word deltas, scenes added and removed, and
    the most-changed scenes with paragraph and word counts. Scenes are matched
    on normalised sluglines (occurrence-aware), so renumbering does not read as
    a rewrite."""
    return core.compare_drafts(_resolve(path_a), _resolve(path_b))


@mcp.tool()
def replace_text(
    path: str,
    find: str,
    replace: str,
    out_path: str | None = None,
    case_sensitive: bool = True,
    scene: str | None = None,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """Replace text in a .fadein file, then verify scene count and page count.

    Surgical: only the text of matched paragraphs changes; marks, revision
    colours, styling and every other zip entry (embedded assets) are copied
    through. The source file is never overwritten — omit `out_path` and a
    " (edited)" copy appears beside it.

    `scene` restricts edits to scenes ("44", "44-46", "44,50"). Start with
    `dry_run=True` to see the preview and hit count, then run it for real.
    """
    return core.replace_text(
        _resolve(path),
        find,
        replace,
        out_path=out_path,
        case_sensitive=case_sensitive,
        scene=scene,
        dry_run=dry_run,
        limit=limit,
    )


@mcp.tool()
def convert_script(path: str, out_path: str) -> dict:
    """Convert a screenplay between .fadein, .fdx, .fountain, .pdf and .txt.

    Conversion is a rebuild from parsed scenes: reliable for text, but it drops
    Fade In-only extras (revision marks, embedded assets). Use replace_text for
    edits that must preserve those.
    """
    return core.convert_script(_resolve(path), out_path)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
