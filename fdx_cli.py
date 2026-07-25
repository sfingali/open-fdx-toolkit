"""CLI for open-fdx-toolkit — quick FDX file inspection from the terminal."""

from __future__ import annotations

import argparse

from fdx_parser import parse_file


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fdx-info",
        description="Inspect a Final Draft (.fdx) screenplay file.",
    )
    parser.add_argument("path", help="Path to .fdx file")
    parser.add_argument("--characters", "-c", action="store_true", help="List all characters")
    parser.add_argument("--locations", "-l", action="store_true", help="List all locations")
    parser.add_argument("--scenes", "-s", action="store_true", help="List all scenes")
    parser.add_argument("--flashbacks", "-f", action="store_true", help="List flashback scenes")

    args = parser.parse_args()

    try:
        scenes = parse_file(args.path)
    except FileNotFoundError:
        print(f"Error: file not found: {args.path}")
        return
    except Exception as e:
        print(f"Error parsing FDX: {e}")
        return

    print(f"Scenes: {len(scenes)}")

    if args.characters:
        chars = sorted(set(
            c for s in scenes for c in s.characters
        ))
        print(f"Characters: {len(chars)}")
        for c in chars:
            count = sum(1 for s in scenes if c in s.characters)
            print(f"  {c} ({count} scenes)")

    if args.locations:
        locs = sorted(set(s.location for s in scenes if s.location))
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


if __name__ == "__main__":
    main()
