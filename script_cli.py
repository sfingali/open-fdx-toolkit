"""CLI for open-fdx-toolkit — inspect and convert screenplay files.

Commands:
    info    Inspect a screenplay file (any supported format)
    convert Convert between formats (fdx, fountain, fadein, pdf, txt)

Format detection is by file extension, with content sniffing for .fadein
(ZIP) and .fdx (XML).

Examples:
    script-cli info script.pdf
    script-cli convert script.pdf script.fountain
    script-cli convert script.fdx script.fadein
    script-cli convert script.pdf script.fdx --title "the sample script"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fdx_parser import parse_file as parse_fdx
from fountain_parser import parse_fountain
from txt_import import parse_txt


def _detect_format(path: str) -> str:
    """Return the format ('fdx', 'fountain', 'fadein', 'pdf', 'txt') for a file."""
    suffix = Path(path).suffix.lower()
    if suffix == ".fdx":
        return "fdx"
    if suffix == ".fountain":
        return "fountain"
    if suffix == ".fadein":
        return "fadein"
    if suffix == ".pdf":
        return "pdf"
    if suffix in (".txt", ".text"):
        return "txt"
    raise ValueError(f"Unrecognized screenplay format: {path}")


def parse_any(path: str):
    """Parse any supported screenplay file into a list of ParsedScene."""
    fmt = _detect_format(path)
    if fmt == "fdx":
        return parse_fdx(path)
    if fmt == "fountain":
        with open(path, encoding="utf-8") as f:
            return parse_fountain(f.read())
    if fmt == "fadein":
        from fadein_parser import parse_fadein_bytes
        return parse_fadein_bytes(Path(path).read_bytes())
    if fmt == "pdf":
        from pdf_import import parse_pdf
        return parse_pdf(path)
    if fmt == "txt":
        return parse_txt(path)
    raise ValueError(f"Unsupported format: {fmt}")


def _write_any(path: str, scenes, title: str = "") -> None:
    fmt = _detect_format(path)
    if fmt == "fdx":
        from fdx_builder import FDXDocument, scene_from_parsed
        doc = FDXDocument(title=title)
        for s in scenes:
            doc.add_scene(scene_from_parsed(s))
        Path(path).write_text(doc.to_xml(), encoding="utf-8")
    elif fmt == "fountain":
        from fountain_builder import write_fountain
        write_fountain(path, scenes, title=title or None)
    elif fmt == "fadein":
        from fadein_builder import build_fadein
        Path(path).write_bytes(build_fadein(scenes, title_page={"Title": title} if title else None))
    elif fmt == "pdf":
        from pdf_export import write_pdf
        write_pdf(path, scenes, title=title)
    elif fmt == "txt":
        from fountain_builder import build_fountain
        # Plain text = Fountain markup stripped of markers; keep it simple
        # and emit Fountain, which most tools can read as plain text too.
        Path(path).write_text(build_fountain(scenes, title=title or None), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported output format: {fmt}")


def cmd_info(args: argparse.Namespace) -> None:
    try:
        scenes = parse_any(args.path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Scenes: {len(scenes)}")

    if args.characters:
        chars = sorted({c for s in scenes for c in s.characters})
        print(f"Characters: {len(chars)}")
        for c in chars:
            count = sum(1 for s in scenes if c in s.characters)
            print(f"  {c} ({count} scenes)")

    if args.locations:
        locs = sorted({s.location for s in scenes if s.location})
        print(f"Locations: {len(locs)}")
        for loc in locs:
            count = sum(1 for s in scenes if s.location == loc)
            print(f"  {loc} ({count} scenes)")

    if args.scenes:
        print("Scenes:")
        for s in scenes:
            chars = f"  [{', '.join(s.characters[:3])}]" if s.characters else ""
            flash = f"  ({s.narrative_position_hint})" if s.narrative_position_hint else ""
            print(f"  {s.scene_number:>4s}  {s.slugline:<50s}  {s.page_eighths}/8{chars}{flash}")

    if args.flashbacks:
        fbs = [s for s in scenes if s.narrative_position_hint]
        print(f"Non-linear scenes: {len(fbs)}")
        for s in fbs:
            print(f"  {s.scene_number}  {s.narrative_position_hint}: {s.slugline}")


def cmd_convert(args: argparse.Namespace) -> None:
    try:
        scenes = parse_any(args.input)
    except Exception as e:
        print(f"Error reading {args.input}: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        _write_any(args.output, scenes, title=args.title or "")
    except Exception as e:
        print(f"Error writing {args.output}: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Converted {args.input} -> {args.output} ({len(scenes)} scenes)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="script-cli",
        description="Inspect and convert screenplay files (fdx, fountain, fadein, pdf, txt).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="Inspect a screenplay file")
    info.add_argument("path")
    info.add_argument("--characters", "-c", action="store_true")
    info.add_argument("--locations", "-l", action="store_true")
    info.add_argument("--scenes", "-s", action="store_true")
    info.add_argument("--flashbacks", "-f", action="store_true")
    info.set_defaults(func=cmd_info)

    conv = sub.add_parser("convert", help="Convert between screenplay formats")
    conv.add_argument("input", help="Input file (fdx/fountain/fadein/pdf/txt)")
    conv.add_argument("output", help="Output file (extension selects format)")
    conv.add_argument("--title", help="Script title for formats with title pages")
    conv.set_defaults(func=cmd_convert)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
