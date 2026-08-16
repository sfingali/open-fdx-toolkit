# Open FDX Toolkit

> **Build tools that work with Final Draft files. Zero dependencies. Open source.**

Parse, build, and convert screenplay files across all major formats —
**Final Draft (`.fdx`), Fountain (`.fountain`), Fade In (`.fadein`), PDF,
and plain text** — into one consistent Python data model. This toolkit
exists to help developers build pre-production software — breakdown tools,
AI assistants, scheduling bridges, format converters — without fighting
proprietary XML formats.

Part of the open pre-production toolchain alongside
[open-moviemagic-toolkit](https://github.com/sfingali/open-moviemagic-toolkit).

---

## Disclaimer

**This project is not affiliated with, endorsed by, or connected to Final Draft,
Cast & Crew, or Entertainment Partners.** Final Draft is a registered trademark
of Cast & Crew. The `.fdx` and `.fadein` formats were reverse-engineered from
files produced by Final Draft, Fade In, and other applications. No proprietary
code, documentation, or trade secrets were used. All format knowledge comes from
public sources and analysis of files legally obtained by the project's
maintainers.

---

## Installation

```bash
pip install open-fdx-toolkit
# PDF import/export requires pymupdf:
pip install "open-fdx-toolkit[pdf]"
```

Or from source:

```bash
git clone https://github.com/sfingali/open-fdx-toolkit.git
cd open-fdx-toolkit
pip install -e ".[dev,pdf]"
```

## Quick Start

```python
from fdx_parser import parse_file

scenes = parse_file("my_script.fdx")

for s in scenes:
    print(f"Scene {s.scene_number}: {s.slugline}")
    print(f"  {s.interior_exterior}/{s.time_of_day} — {s.location}")
    print(f"  Characters: {', '.join(s.characters[:5])}")
```

## What's Inside

| Module | Purpose |
|--------|---------|
| `fdx_parser.py` | Parse `.fdx` XML → structured Python dataclasses |
| `fdx_builder.py` | Build `.fdx` XML from Python — roundtrip support |
| `fountain_parser.py` | Parse Fountain (`.fountain`) → same dataclasses |
| `fountain_builder.py` | Serialize dataclasses → Fountain markup |
| `fadein_parser.py` | Parse `.fadein` (ZIP + OSF XML) → dataclasses |
| `fadein_builder.py` | Build `.fadein` ZIP from dataclasses |
| `pdf_import.py` | Extract screenplay structure from text-layer PDFs (layout-based) |
| `pdf_export.py` | Render dataclasses → professionally formatted screenplay PDF |
| `txt_import.py` | Classify plain-text screenplays (heuristics) |
| `script_cli.py` | `script-cli` — inspect & convert any format |
| `fdx_cli.py` | `fdx-info` — terminal inspector (legacy) |

## Converting Between Formats

```bash
script-cli convert script.pdf script.fountain     # PDF → Fountain
script-cli convert script.pdf script.fdx          # PDF → Final Draft
script-cli convert script.pdf script.fadein       # PDF → Fade In
script-cli convert script.fdx script.fountain     # FDX → Fountain
script-cli convert script.fountain script.fdx     # Fountain → FDX
script-cli info script.pdf --characters --locations
```

Format is selected by file extension. All parsers produce the same
`ParsedScene` dataclass list, so any format converts to any other via the
shared model.

## Inspecting a script

```bash
script-cli info script.fdx --scenes          # scene list with lengths
script-cli info script.fdx --characters      # cast with scene counts
script-cli info script.fdx --locations       # locations with scene counts
script-cli info script.fdx --flashbacks      # non-linear scenes
```

## Ground-Truth Verification

The test suite validates every parser against real production files
(the sample script, 278 scenes) when present at the standard paths:

- `/opt/data/home/projects/the-sample/the sample script.fountain`
- `/opt/data/home/projects/the-sample/drafts/the sample script - 03-18-26b - FINGLETON.fdx`
- `/opt/data/home/projects/the-sample/drafts/the sample script - 03-17-26 - FINGLETON.pdf`

Cross-format tests assert identical scene counts, sluglines, character sets,
and location sets across FDX ↔ Fountain ↔ Fade In ↔ PDF. The suite also
includes synthetic round-trip tests that run anywhere.

## Notes

- All core formats (FDX, Fountain, Fade In, text) are zero-dependency
  (stdlib only). PDF support needs `pymupdf` (`pip install "open-fdx-toolkit[pdf]"`).
- PDF import works on text-layer PDFs (Final Draft / Fade In exports).
  Scanned PDFs need OCR first — see the `ocr-and-documents` skill.
- `.fadein` files are ZIP archives wrapping an `document.xml` in Fade In's
  Open Screenplay Format (OSF).
- Scene numbers travel as trailing `#N#` on scene headings (Fountain and
  Fade In conventions).
