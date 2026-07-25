# Open FDX Parser

Zero-dependency Python parser for Final Draft (`.fdx`) screenplay files.

Extracts structured data from Final Draft 8+ XML into clean dataclasses —
scenes, characters, dialogue, actions, page lengths, and narrative positions.
No external dependencies beyond the Python standard library.

## Installation

```bash
pip install open-fdx-parser
```

Or from source:

```bash
git clone https://github.com/sfingali/open-fdx-parser.git
cd open-fdx-parser
pip install -e .
```

## Quick Start

```python
from fdx_parser import parse_file

scenes = parse_file("my_script.fdx")

for s in scenes:
    print(f"Scene {s.scene_number}: {s.slugline}")
    print(f"  {s.interior_exterior}/{s.time_of_day} — {s.location}")
    print(f"  Characters: {', '.join(s.characters[:5])}")
    print(f"  Page: {s.page_eighths}/8")
    print()
```

Or from a string:

```python
from fdx_parser import parse_fdx

with open("my_script.fdx") as f:
    scenes = parse_fdx(f.read())
```

## ParsedScene Fields

| Field | Type | Description |
|-------|------|-------------|
| `scene_number` | `str` | Scene number (script-supplied or auto) |
| `scene_number_source` | `str` | `"script"` or `"auto"` |
| `slugline` | `str` | Full scene heading text |
| `interior_exterior` | `str` | `"INT"`, `"EXT"`, or `"INT/EXT"` |
| `location` | `str` | Primary location name |
| `set_name` | `str` | Sub-location / set |
| `time_of_day` | `str` | `"DAY"`, `"NIGHT"`, `"DAWN"`, etc. |
| `body_lines` | `list[str]` | All text lines: action, character cues, dialogue |
| `characters` | `list[str]` | Unique character names in this scene |
| `page_eighths` | `int` | Scene length in eighths of a page (1-8) |
| `narrative_position_hint` | `str or None` | `"flashback"`, `"dream"`, `"memory"`, etc. |
| `has_dual_dialogue` | `bool` | Dual dialogue present |
| `story_date_marker` | `str or None` | Time jump marker (from FDX metadata) |

## Features

- **No dependencies** — stdlib `xml.etree.ElementTree` only, no pip install cascade
- **Scene heading parsing** — extracts INT/EXT, location, set name, time of day
- **Page length** — reads FDX `SceneProperties` for exact page eighths
- **Character detection** — collects character names per scene
- **Narrative markers** — detects FLASHBACK, DREAM, MEMORY, FLASH FORWARD
- **Auto-numbering** — handles un-numbered scenes with deterministic IDs
- **Dataclass output** — clean `ParsedScene` objects with `to_dict()` method
- **Python 3.10+** — type-safe with full type hints

## Why another FDX parser?

Existing libraries either pull in heavy dependencies or don't expose the
structured data that AI-assisted pre-production tools need. This parser
is intentionally minimal — a single file, zero deps, and an API surface
of exactly two functions. It powers the import pipeline in [Shotbreak](https://github.com/sfingali/shotbreak)
but is completely standalone.

## License

MIT
