# Open FDX Toolkit

> **Build tools that work with Final Draft files. Zero dependencies. Open source.**

Parse, build, and validate Final Draft (`.fdx`) screenplay files. This toolkit
exists to help developers build pre-production software — breakdown tools, AI
assistants, scheduling bridges, format converters — without fighting a
proprietary XML format.

Part of the open pre-production toolchain alongside
[open-moviemagic-toolkit](https://github.com/sfingali/open-moviemagic-toolkit).

---

## Disclaimer

**This project is not affiliated with, endorsed by, or connected to Final Draft,
Cast & Crew, or Entertainment Partners.** Final Draft is a registered trademark
of Cast & Crew. The `.fdx` format was reverse-engineered from files produced by
Final Draft, Fade In, and other applications. No proprietary code, documentation,
or trade secrets were used. All format knowledge comes from public sources and
analysis of files legally obtained by the project's maintainers.

---

## Installation

```bash
pip install open-fdx-toolkit
```

Or from source:

```bash
git clone https://github.com/sfingali/open-fdx-toolkit.git
cd open-fdx-toolkit
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
```

## What's Inside

| Module | Purpose |
|--------|---------|
| `fdx_parser.py` | Parse `.fdx` XML → structured Python dataclasses |
| `fdx_builder.py` | Build `.fdx` XML from Python — roundtrip support |
| `fdx_cli.py` | `fdx-info` terminal inspector |
| `FDX_SPEC.md` | Complete format reference with version matrix |

Extracts: scenes, characters, dialogue, actions, transitions, parentheticals,
dual dialogue pairs, scene synopses, script notes, page eighths, narrative
markers, text styles, revision IDs, and production tags.

Handles Final Draft 8+, Fade In, and Trelby exports. [Full spec →](FDX_SPEC.md)

## Developer Toolkit

This library is designed to be embedded in larger applications:

- **AI script breakdown tools** — parse FDX, extract elements, feed to LLM
- **Format converters** — FDX → Fountain, FDX → JSON, FDX → anything
- **Scheduling bridges** — parse FDX into [`Schedule` model](https://github.com/sfingali/open-moviemagic-toolkit), export to MMS
- **Pre-production dashboards** — scene navigators, element grids, continuity checkers
- **CI/CD for screenplays** — diff FDX revisions, validate formatting

## Companion Project

**[open-moviemagic-toolkit](https://github.com/sfingali/open-moviemagic-toolkit)** —
Parse and generate Movie Magic Scheduling files (`.sex`, `.MMS10`). The two
repos together form a complete open pre-production pipeline:

```
open-fdx-toolkit          open-moviemagic-toolkit
  (screenplay)      →        (schedule)
  .fdx parse/build  →  Schedule model → .sex export → MMS import
```

## License

MIT
