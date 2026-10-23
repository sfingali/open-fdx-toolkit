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
| `fadein_mcp/` | MCP server — inspect, search, diff and edit `.fadein` drafts from an AI agent |

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

## Fade In MCP Server

`fadein_mcp/` is a [Model Context Protocol](https://modelcontextprotocol.io)
server over stdio, so an AI agent can work on `.fadein` drafts without Fade In
running and without a Sync/Dropbox/Drive integration: point it at a file path.

```bash
pip install "open-fdx-toolkit[mcp]"     # or: pip install mcp>=1.2,<2
python -m fadein_mcp.server            # speaks MCP on stdin/stdout
```

Register it with any MCP client (Hermes, Claude Desktop, …) as a stdio server
command, e.g. `python -m fadein_mcp.server` with `PYTHONPATH` pointing at this
repo. `FADEIN_DRAFTS_DIR` sets the folder used when a tool is given a bare
filename instead of an absolute path.

### Tools

| Tool | What it returns |
|------|-----------------|
| `list_scripts` | Screenplay files in a folder, newest first |
| `script_info` | Page count, scenes, words, characters, locations, revision, hash |
| `list_scenes` | Scene headings with main characters, word counts, opening lines |
| `get_scene` | Full text of `"12"`, `"12-15"` or `"12,14,20"` |
| `search_script` | Matches across headings, action and dialogue, with scene numbers |
| `character_report` | Per-character scenes and dialogue words, cues normalised |
| `location_report` | Locations with INT/EXT, time of day and scene numbers |
| `compare_drafts` | Page/scene/word deltas, scenes added/removed, most-changed scenes |
| `replace_text` | Surgical find-and-replace, verified, written to a new file |
| `convert_script` | Convert between `.fadein`, `.fdx`, `.fountain`, `.pdf`, `.txt` |

### Why page count comes from the document

An OSF file states the page count Fade In computed
(`<info pagecount="101">`). Estimating pages from scenes is wrong — a 101-page
draft of 202 scenes must not be reported as 25 pages. `script_info` reads the
attribute.

### Editing without destroying the draft

`replace_text` does not rebuild the document from the parsed model. It edits the
text runs of matched `<para>` blocks inside `document.xml` and copies every other
zip entry through untouched, so revision marks, revision colours, styling,
script notes and embedded assets survive. It then re-parses the result and
reports scene count, page count and word count before and after.

Safety properties:

- The source file is never overwritten; omit `out_path` and a ` (edited)` copy
  appears beside it.
- `dry_run=True` returns the hit count and a preview diff without writing.
- `scene="44-46"` restricts edits to a scene range.
- Verification fails loudly rather than silently: a drop in scene count or a
  changed page count comes back in `checks`.

Limitation: within an edited paragraph the text is flattened into its first run,
so inline emphasis inside that paragraph is lost. Paragraphs that are not
matched are byte-identical.

## Ground-Truth Verification

The test suite can validate every parser against real production files when you
point it at one, via environment variables:

```
SAMPLE_FDX=/path/to/draft.fdx SAMPLE_PDF=/path/to/draft.pdf \
SAMPLE_FOUNTAIN=/path/to/draft.fountain python -m pytest tests/ -q
```

Those tests skip when the variables are unset, so the suite passes on a clean
checkout. Screenplay drafts are never committed to this repository.

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
- Fade In stores scene numbers in the paragraph attribute
  (`<para number="12">`), not as trailing `#N#` text; the parser reads the
  attribute. Fountain carries scene numbers as trailing `#12#`.
